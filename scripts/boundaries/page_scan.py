#!/usr/bin/env python3
"""Scan each system's own web page for embedded zone maps.

The Ohio deep dive (NOTES.md) found that agency pages often embed the zone map
the ArcGIS catalog search misses: a Google My Maps iframe, an ArcGIS web map /
app / Experience, or a link to a KML/KMZ/GeoJSON file. For each system this
script fetches the row's Website URL, plus up to --follow same-site links whose
URL or text mentions maps/zones, and pulls out those references. Each one is
resolved to polygon layers, downloaded, and checked for location (distance to
the pin) and size (vs. the current polygon), as arcgis_vet.py does.

    python3 -u scripts/boundaries/page_scan.py --skip-states CO,OH
    python3 -u scripts/boundaries/page_scan.py --states TX --tag tx

Writes scripts/boundaries/candidates/page_candidates{_tag}.csv (one row per
polygon layer found) and page_scan{_tag}.csv (one row per system: fetched,
blocked, map references found). Nothing in data/boundaries/ changes; a layer
that passes still needs the per-system judgment described in NOTES.md
(exclude paratransit, proposed or coming-soon zones; reconcile zone counts).
"""
import argparse
import csv
import html as htmllib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import arcgis_vet as V  # noqa: E402
from add_agency_layers import fetch_kml  # noqa: E402

OUT_DIR = HERE / "candidates"
CACHE = HERE / "cache" / "pages"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) odt-inventory-research"
HEX = r"[0-9a-f]{32}"
FOLLOW_WORDS = re.compile(r"map|zone|service[- _]?area|boundar|micro|on[- _]?demand|flex|where", re.I)
SKIP_LINK = re.compile(r"\.(pdf|jpe?g|png|gif|svg|docx?|xlsx?|zip|mp4)(\?|$)|mailto:|tel:|facebook|twitter|instagram|"
                       r"linkedin|youtube|apps\.apple|play\.google|/(news|events|calendar|jobs|careers)\b", re.I)
# Layer names that are never service zones; skipped before download (speed).
IRRELEVANT = re.compile(r"parcel|tax ?lot|imagery|orthophoto|aerial|zoning|flood|fema|wetland|soil|contour|"
                        r"building|footprint|address|hydrant|sewer|storm|water|utility|police|fire|precinct|"
                        r"voting|ward|council|school|park|trail|sidewalk|crash|tree|census|tract|block group|"
                        r"land ?use|easement|right of way|street|road|centerline|pavement", re.I)
RELEVANT = re.compile(r"micro|on[- _]?demand|flex|zone|service ?area|transit|ride", re.I)
_requests = 0


def fetch_text(url, timeout=25):
    global _requests
    _requests += 1
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000).decode("utf-8", "replace"), r.geturl()


def find_refs(page_html, base):
    """Map references in a page -> set of (kind, id_or_url)."""
    h = htmllib.unescape(page_html)
    refs = set()
    for mid in re.findall(r"google\.com/maps/d/(?:u/\d+/)?(?:embed|viewer|edit|view)\?[^\"'\s>]*?mid=([\w-]+)", h):
        refs.add(("mymaps", mid))
    for pat in (rf'item-id=["\']({HEX})', rf'webmap=({HEX})', rf'appid=({HEX})',
                rf'arcgis\.com/(?:apps/[^"\'\s>]*?|home/item\.html|home/webmap/viewer\.html)\?[^"\'\s>]*?(?:id|webmap|appid)=({HEX})',
                rf'experience\.arcgis\.com/experience/({HEX})', rf'arcgis\.com/apps/[\w/-]+/({HEX})',
                rf'storymaps\.arcgis\.com/stories/({HEX})', rf'arcgis\.com/apps/dashboards/({HEX})'):
        for m in re.findall(pat, h, re.I):
            refs.add(("arcgis_item", m.lower()))
    for u in re.findall(r"https?://[^\"'\s<>]+/(?:FeatureServer|MapServer)(?:/\d+)?", h):
        refs.add(("arcgis_service", u))
    for u in re.findall(r"""["'(]([^"'()\s<>]+\.(?:kml|kmz|geojson))(?:\?[^"'\s<>]*)?["')]""", h, re.I):
        refs.add(("file", urllib.parse.urljoin(base, u)))
    return refs


def follow_links(page_html, base, limit):
    host = urllib.parse.urlparse(base).netloc
    out = []
    for href, text in re.findall(r"<a\s[^>]*href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", page_html, re.I | re.S):
        u = urllib.parse.urljoin(base, htmllib.unescape(href))
        if urllib.parse.urlparse(u).netloc != host or SKIP_LINK.search(u) or u.rstrip("/") == base.rstrip("/"):
            continue
        label = re.sub(r"<[^>]+>", " ", text)
        if FOLLOW_WORDS.search(u) or FOLLOW_WORDS.search(label):
            if u not in out:
                out.append(u)
        if len(out) >= limit:
            break
    return out


def item_layers(item_id, depth=0):
    """ArcGIS item (web map, app, Experience, service) -> [(layer_url, layer_name, item_title)]."""
    item = V.get_json(f"https://www.arcgis.com/sharing/rest/content/items/{item_id}", {"f": "json"}) or {}
    if "error" in item or not item.get("type"):
        return []
    t, title = item["type"], item.get("title", "")
    if t in ("Web Map", "Feature Service", "Map Service"):
        return [(u, n, title) for u, n in V.polygon_layers(item)]
    if depth >= 2:
        return []
    data = V.get_json(f"https://www.arcgis.com/sharing/rest/content/items/{item_id}/data", {"f": "json"}) or {}
    txt = json.dumps(data)
    out = []
    for sub in sorted(set(re.findall(rf'"(?:itemId|webmap|id)":\s*"({HEX})"', txt)) - {item_id})[:8]:
        out += item_layers(sub, depth + 1)
    for u in sorted(set(re.findall(r'https?://[^"]+/(?:FeatureServer|MapServer)(?:/\d+)?', txt)))[:8]:
        out += [(lu, n, title) for lu, n in V.polygon_layers({"type": "Feature Service", "url": u})]
    return out


def resolve(kind, ref):
    """-> [(source_url, layer_name, title, geojson or None, error)]"""
    try:
        if kind == "mymaps":
            gj = fetch_kml(f"https://www.google.com/maps/d/kml?mid={ref}&forcekml=1")
            return [(f"https://www.google.com/maps/d/viewer?mid={ref}", "My Maps", "", gj, "")]
        if kind == "file":
            if ref.lower().split("?")[0].endswith((".kml", ".kmz")):
                return [(ref, Path(ref).name, "", fetch_kml(ref), "")]
            gj = V.get_json(ref)
            return [(ref, Path(ref).name, "", gj if "features" in (gj or {}) else None, (gj or {}).get("error", ""))]
        layers = item_layers(ref) if kind == "arcgis_item" else \
            [(u, n, "") for u, n in V.polygon_layers({"type": "Feature Service", "url": ref})]
        out = []
        for lu, name, title in layers[:8]:
            if IRRELEVANT.search(f"{name} {title}") and not RELEVANT.search(name or ""):
                out.append((lu, name, title, None, "skipped: layer name not transit-related"))
                continue
            gj, err = V.fetch_features(lu)
            out.append((lu, name, title, gj, err))
        return out
    except Exception as e:  # noqa: BLE001
        return [(ref, "", "", None, f"error: {e}"[:150])]


def check(gj, sysrow, cur):
    feats = [f for f in gj.get("features", []) if V.rings(f.get("geometry"))]
    allr = [p for f in feats for p in V.rings(f["geometry"])]
    if not allr:
        return feats, 0, False, None, "no polygons"
    lat, lng = sysrow["lat"], sysrow["lng"]
    area = V.area_sqmi(allr, lat)
    inside = V.contains(allr, lng, lat)
    dist = 0.0 if inside else V.nearest_vertex_miles(allr, lat, lng)
    if dist > V.NEAR_MILES:
        return feats, area, inside, dist, f"wrong place ({dist:.0f} mi from pin)"
    if cur and area and not (0.02 <= area / cur <= 5):
        return feats, area, inside, dist, "area very different"
    return feats, area, inside, dist, "ok"


def labels(feats):
    if not feats:
        return ""
    keys = [k for k in feats[0]["properties"] if re.search(r"name|zone|label|title|service", k, re.I)]
    if not keys:
        return ""
    return " | ".join(sorted({str(f["properties"].get(keys[0])) for f in feats})[:12])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states")
    ap.add_argument("--skip-states", default="")
    ap.add_argument("--all-fidelity", action="store_true", help="also scan rows whose polygon is exact")
    ap.add_argument("--only-exact", action="store_true", help="scan only rows whose polygon is exact")
    ap.add_argument("--follow", type=int, default=4, help="same-site map/zone links to follow per page")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    systems = json.load(open(ROOT / "data" / "systems.json"))
    only = set(args.states.split(",")) if args.states else None
    skip = set(filter(None, args.skip_states.split(",")))
    rows = [s for s in systems if (only is None or s["state"] in only) and s["state"] not in skip
            and (args.all_fidelity
                 or (args.only_exact and (s.get("boundary") or {}).get("fidelity") == "exact")
                 or (not args.only_exact and (not s.get("boundary") or s["boundary"].get("fidelity") == "approximate")))]
    sfx = f"_{args.tag}" if args.tag else ""
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)
    t0 = time.time()
    print(f"Scanning {len(rows)} system pages", flush=True)
    cands, summary = [], []
    for n, s in enumerate(rows, 1):
        url = (s.get("url") or "").strip()
        rec = {"State": s["state"], "Name": s["name"], "Page": url, "Fetched": "", "Pages scanned": 0,
               "Map refs": "", "Layers": 0, "Passing": 0, "Error": ""}
        if not url.startswith("http"):
            rec["Error"] = "no website URL"
            summary.append(rec)
            continue
        refs, pages = set(), []
        try:
            page, final = fetch_text(url)
            rec["Fetched"] = "yes"
            pages.append(final)
            refs |= find_refs(page, final)
            for u in follow_links(page, final, args.follow):
                try:
                    p2, f2 = fetch_text(u)
                    pages.append(f2)
                    refs |= find_refs(p2, f2)
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(0.4)
        except Exception as e:  # noqa: BLE001
            rec["Fetched"] = "no"
            rec["Error"] = str(e)[:120]
        rec["Pages scanned"] = len(pages)
        rec["Map refs"] = "; ".join(f"{k}:{r}" for k, r in sorted(refs))[:500]
        cur = V.current_area(s["state"], s["name"])
        for kind, ref in sorted(refs):
            for src, lname, title, gj, err in resolve(kind, ref):
                row = {"State": s["state"], "Name": s["name"], "Current boundary": (s.get("boundary") or {}).get("type", "(none)"),
                       "Found on": pages[0] if pages else url, "Kind": kind, "Ref": ref, "Source": src,
                       "Title": title, "Layer": lname, "Current area sq mi": round(cur, 1) if cur else ""}
                if gj is None:
                    cands.append({**row, "Check": f"skipped: {err}"[:150]})
                    continue
                try:
                    feats, area, inside, dist, chk = check(gj, s, cur)
                except Exception as e:  # noqa: BLE001  odd geometry shouldn't stop the run
                    cands.append({**row, "Check": f"error: {e}"[:150]})
                    continue
                rec["Layers"] += 1
                rec["Passing"] += chk == "ok"
                cache = CACHE / (re.sub(r"[^\w]+", "_", f"{s['state']}_{s['name']}_{lname or kind}")[:80] + ".geojson")
                cache.write_text(json.dumps(gj), encoding="utf-8")
                cands.append({**row, "Features": len(feats), "Feature names": labels(feats),
                              "Area sq mi": round(area, 1) if area else "",
                              "Area ratio": round(area / cur, 2) if cur and area else "",
                              "Pin inside": "yes" if inside else "no",
                              "Miles to pin": "" if dist is None else round(dist, 1), "Check": chk,
                              "Cached": str(cache.relative_to(ROOT))})
        summary.append(rec)
        if n % 10 == 0 or n == len(rows):
            print(f"  {n}/{len(rows)}  {time.time() - t0:.0f}s  {_requests} page requests  "
                  f"{sum(1 for r in summary if r['Passing'])} systems with a passing layer", flush=True)
        time.sleep(0.4)

    def dump(path, data):
        fields = []
        for r in data:
            fields += [k for k in r if k not in fields]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(data)

    if cands:
        dump(OUT_DIR / f"page_candidates{sfx}.csv", cands)
    dump(OUT_DIR / f"page_scan{sfx}.csv", summary)
    fetched = sum(1 for r in summary if r["Fetched"] == "yes")
    with_refs = sum(1 for r in summary if r["Map refs"])
    passing = sum(1 for r in summary if r["Passing"])
    print(f"Done in {time.time() - t0:.0f}s: {fetched}/{len(summary)} pages fetched, {with_refs} with map references, "
          f"{passing} with a layer passing location/size checks; {_requests} page requests.", flush=True)


if __name__ == "__main__":
    main()
