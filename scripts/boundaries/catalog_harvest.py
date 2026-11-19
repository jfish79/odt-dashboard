#!/usr/bin/env python3
"""Harvest regional/statewide zone layers and match their polygons to systems.

arcgis_search.py and page_scan.py look for one system at a time. MPOs, state
DOTs and regional councils often publish one layer covering many systems
(MassDOT's "Municipal Microtransit Service Area", H-GAC's "Microtransit Service
Areas", CTDOT's bus transit network). This script searches by topic instead:

1. ArcGIS Online catalog and the Socrata open-data network (data.ct.gov,
   etc.; federated entries are followed to their ArcGIS source when possible)
   for phrases like "microtransit service area" and "on-demand zone";
   proposals, candidates and studies are skipped by title.
2. Every polygon in each layer is matched to inventory systems: the system's
   pin inside or within --near miles of the polygon, plus name overlap
   between the polygon's attributes and the system's name/operator/area text.

    python3 -u scripts/boundaries/catalog_harvest.py --skip-states CO,OH

Writes scripts/boundaries/candidates/harvest_layers.csv (layers found) and
harvest_matches.csv (one row per polygon x matched system, best first).
data.gov's catalog API (CKAN) moved in 2026 and isn't queried. Nothing in
data/boundaries/ changes; matches need the usual per-system review.
"""
import argparse
import csv
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

OUT_DIR = HERE / "candidates"
UA = "odt-inventory-boundary-search/1.0"
TOPICS = [
    "microtransit service area", "microtransit service areas", "microtransit zones", "microtransit zone",
    "on-demand service area", "on demand transit zone", "on-demand zones", "demand response service area",
    "mobility on demand zone", "flex zone transit", "microtransit", "on-demand transit",
]
BAD = re.compile(r"\b(candidates?|proposed|proposals?|recommend\w*|draft|future|scenarios?|alternatives?|"
                 r"concepts?|study|analysis|survey|outreach|feedback|suitability|potential|options?|prelim\w*|"
                 r"demographic\w*|ridership|trips?|boardings?|heat ?map|equity|stops?|routes?)\b", re.I)
GENERIC = {"the", "of", "and", "on", "demand", "ondemand", "transit", "transportation", "service", "services",
           "microtransit", "ride", "rides", "area", "areas", "zone", "zones", "city", "county", "regional",
           "public", "flex", "go", "via", "connect", "metro", "authority", "district", "mobility", "app", "to", "in"}
_req = 0


def get_json(url, params=None):
    global _req
    _req += 1
    return V.get_json(url, params)


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 2 and t not in GENERIC}


def arcgis_topic(q, pages=3, bbox=None):
    out = []
    for start in range(1, pages * 100, 100):
        params = {"q": f'({q}) AND (type:"Feature Service" OR type:"Map Service" OR type:"Web Map")',
                  "num": 100, "start": start, "f": "json"}
        if bbox:
            params["bbox"] = bbox
        d = get_json("https://www.arcgis.com/sharing/rest/search", params)
        res = (d or {}).get("results", [])
        out += res
        if len(res) < 100:
            break
        time.sleep(0.3)
    return out


def socrata_topic(q):
    d = get_json("https://api.us.socrata.com/api/catalog/v1", {"q": q, "limit": 100})
    out = []
    for r in (d or {}).get("results", []):
        res, dom = r["resource"], r["metadata"]["domain"]
        href = None
        if res.get("type") == "federated_href":
            v = get_json(f"https://{dom}/api/views/{res['id']}.json") or {}
            href = ((v.get("metadata") or {}).get("accessPoints") or {}).get("text/html")
        out.append({"title": res["name"], "domain": dom, "id": res["id"], "type": res.get("type"), "href": href,
                    "updated": res.get("updatedAt", "")[:10]})
    return out


def hub_href_to_item(href):
    """https://geodata.ct.gov/datasets/CTDOT::microtransit-service-areas -> ArcGIS item id via a catalog search."""
    m = re.search(r"/datasets/([^:/]+)::([\w-]+)", href or "")
    if not m:
        m2 = re.search(r"/datasets/([0-9a-f]{32})", href or "")
        return m2.group(1) if m2 else None
    title = m.group(2).replace("-", " ")
    d = get_json("https://www.arcgis.com/sharing/rest/search", {"q": f'title:"{title}"', "num": 20, "f": "json"})
    for r in (d or {}).get("results", []):
        if r.get("type") in ("Feature Service", "Map Service", "Web Map"):
            return r["id"]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states")
    ap.add_argument("--skip-states", default="")
    ap.add_argument("--near", type=float, default=2.0, help="miles: pin this close to a polygon counts as a location match")
    ap.add_argument("--max-layers", type=int, default=500)
    ap.add_argument("--bbox", help="xmin,ymin,xmax,ymax (WGS84): only ArcGIS items whose extent intersects it")
    ap.add_argument("--tag", default="", help="suffix for output file names, e.g. 'co' -> harvest_layers_co.csv")
    args = ap.parse_args()
    only = set(args.states.split(",")) if args.states else None
    skip = set(filter(None, args.skip_states.split(",")))
    systems = [s for s in json.load(open(ROOT / "data" / "systems.json"))
               if (only is None or s["state"] in only) and s["state"] not in skip]
    t0 = time.time()

    # 1. Gather candidate items by topic.
    items = {}
    for q in TOPICS:
        for it in arcgis_topic(q, bbox=args.bbox):
            if not BAD.search(it.get("title", "")):
                items.setdefault(it["id"], {**it, "found_by": f"ArcGIS: {q}"})
        for r in socrata_topic(q):
            if BAD.search(r["title"]):
                continue
            iid = hub_href_to_item(r["href"]) if r["href"] else None
            if iid and iid not in items:
                meta = get_json(f"https://www.arcgis.com/sharing/rest/content/items/{iid}", {"f": "json"}) or {}
                if meta.get("type"):
                    items[iid] = {**meta, "found_by": f"Socrata {r['domain']}: {r['title']}"}
        time.sleep(0.3)
    print(f"{len(items)} candidate items after title filtering ({time.time() - t0:.0f}s, {_req} requests)", flush=True)

    # 2. Fetch polygon layers and match each polygon to systems.
    layers_out, matches = [], []
    # Most specific titles first, so --max-layers cuts the generic ones.
    def rank(it):
        t = (it.get("title") or "").lower()
        return (0 if re.search(r"service ?areas?|zones?|boundar", t) else 1,
                0 if re.search(r"micro|on[- _]?demand|flex|demand[- _]response", t) else 1)
    ordered = sorted(items.values(), key=rank)
    for n, it in enumerate(ordered[: args.max_layers], 1):
        try:
            lyrs = V.polygon_layers(it)
        except Exception as e:  # noqa: BLE001
            lyrs = []
        for lu, lname in lyrs[:6]:
            gj, err = V.fetch_features(lu)
            org = V.org_name(it.get("orgId"))
            mod = time.strftime("%Y-%m-%d", time.gmtime((it.get("modified") or 0) / 1000))
            nfeat = len((gj or {}).get("features", []))
            layers_out.append({"Item": f"https://www.arcgis.com/home/item.html?id={it['id']}", "Title": it.get("title"),
                               "Layer": lname, "Layer URL": lu, "Org": org, "Owner": it.get("owner"),
                               "Modified": mod, "Features": nfeat, "Found by": it["found_by"], "Error": err})
            if not gj:
                continue
            for f in gj["features"]:
                rings = V.rings(f.get("geometry"))
                if not rings:
                    continue
                props = f.get("properties") or {}
                label = " ".join(str(v) for k, v in props.items()
                                 if isinstance(v, str) and not k.lower().startswith(("shape", "global", "objectid")))[:200]
                ftoks = tokens(label) | tokens(it.get("title")) | tokens(lname)
                lat0 = rings[0][0][0][1]
                area = V.area_sqmi(rings, lat0)
                for s in systems:
                    if abs(s["lat"] - lat0) > 1.5:  # quick prefilter (~100 mi)
                        continue
                    inside = V.contains(rings, s["lng"], s["lat"])
                    dist = 0.0 if inside else V.nearest_vertex_miles(rings, s["lat"], s["lng"])
                    stoks = tokens(s["name"]) | tokens(s["operator"]) | tokens(s["area"])
                    shared = sorted(ftoks & stoks)
                    if dist > args.near and not (shared and dist < 15):
                        continue
                    name_hit = bool(tokens(s["name"]) & ftoks)
                    score = (3 if inside else 1.5 if dist <= args.near else 0) + (3 if name_hit else 0) + min(len(shared), 3)
                    if score < 3:
                        continue
                    b = s.get("boundary") or {}
                    matches.append({"State": s["state"], "Name": s["name"], "Current boundary": b.get("type", "(none)"),
                                    "Fidelity": b.get("fidelity", ""), "Score": score, "Pin inside": "yes" if inside else "no",
                                    "Miles": round(dist, 1), "Shared words": " ".join(shared[:8]),
                                    "Feature label": label[:120], "Feature sq mi": round(area, 1),
                                    "Layer": f"{it.get('title')} / {lname}", "Org": org, "Modified": mod, "Layer URL": lu,
                                    "Item": f"https://www.arcgis.com/home/item.html?id={it['id']}"})
        if n % 25 == 0:
            print(f"  {n}/{min(len(items), args.max_layers)} items  {time.time() - t0:.0f}s  {len(matches)} matches", flush=True)

    matches.sort(key=lambda m: (m["State"], m["Name"], -m["Score"]))

    def dump(path, data):
        if not data:
            return
        fields = []
        for r in data:
            fields += [k for k in r if k not in fields]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(data)

    OUT_DIR.mkdir(exist_ok=True)
    sfx = f"_{args.tag}" if args.tag else ""
    dump(OUT_DIR / f"harvest_layers{sfx}.csv", layers_out)
    dump(OUT_DIR / f"harvest_matches{sfx}.csv", matches)
    print(f"Done in {time.time() - t0:.0f}s: {len(items)} items, {len(layers_out)} polygon layers, "
          f"{len(matches)} polygon-system matches covering {len({(m['State'], m['Name']) for m in matches})} systems; "
          f"{_req} catalog requests.", flush=True)


if __name__ == "__main__":
    main()
