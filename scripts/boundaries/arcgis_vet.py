#!/usr/bin/env python3
"""Fetch and sanity-check the layers that arcgis_search.py found.

For each candidate in scripts/boundaries/candidates/arcgis_candidates.csv:
  - resolve the item to its polygon layers (a Web Map is unwrapped to its
    operational layers), and look up the publishing organization's name
  - download the features (WGS84 GeoJSON) into scripts/boundaries/cache/arcgis/
  - check location: distance from the polygons to the system's pin, and
    whether the pin falls inside one of them
  - compare area with the polygon currently on the dashboard

Writes scripts/boundaries/candidates/arcgis_vetted.csv. Nothing in
data/boundaries/ changes; a layer that passes still needs a look at its
features (one zone or several? which one is this system?) before it's used.

    python3 scripts/boundaries/arcgis_vet.py
    python3 scripts/boundaries/arcgis_vet.py --tier likely
"""
import argparse
import csv
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CAND = HERE / "candidates" / "arcgis_candidates.csv"
OUT = HERE / "candidates" / "arcgis_vetted.csv"
CACHE = HERE / "cache" / "arcgis"
UA = "odt-inventory-boundary-search/1.0"
NEAR_MILES = 30  # polygons farther than this from the pin are the wrong place
_org_cache = {}


def get_json(url, params=None):
    if not url.startswith(("http://", "https://")):
        return {"error": f"not a web URL: {url[:60]}"}
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return {"error": str(e)}
            time.sleep(2 * (attempt + 1))


def org_name(org_id):
    if not org_id:
        return ""
    if org_id not in _org_cache:
        d = get_json(f"https://www.arcgis.com/sharing/rest/portals/{org_id}", {"f": "json"})
        _org_cache[org_id] = (d or {}).get("name", "")
    return _org_cache[org_id]


def polygon_layers(item):
    """[(layer_url, layer_name)] for the item's polygon layers."""
    out = []
    t, url = item.get("type"), (item.get("url") or "").rstrip("/")
    if t == "Web Map":
        data = get_json(f"https://www.arcgis.com/sharing/rest/content/items/{item['id']}/data", {"f": "json"})
        for ol in (data or {}).get("operationalLayers", []):
            u = (ol.get("url") or "").rstrip("/")
            if not u.startswith(("http://", "https://")):
                continue
            if u.split("/")[-1].isdigit():
                out += [(u, ol.get("title", ""))]
            else:
                out += polygon_layers({"type": "Feature Service", "url": u})
        return out
    if t in ("Feature Service", "Map Service") and url:
        if url.split("/")[-1].isdigit():
            return [(url, item.get("title", ""))]
        svc = get_json(url, {"f": "json"})
        for ly in (svc or {}).get("layers", []):
            if ly.get("geometryType") in (None, "esriGeometryPolygon"):
                out.append((f"{url}/{ly['id']}", ly.get("name", "")))
    return out


def fetch_features(layer_url):
    meta = get_json(layer_url, {"f": "json"})
    if (meta or {}).get("geometryType") not in ("esriGeometryPolygon",):
        return None, (meta or {}).get("geometryType") or (meta or {}).get("error", "no metadata")
    # Screening only: generalize geometry (~50 m) to keep downloads small. The
    # loader (add_agency_layers.py) fetches full-precision geometry.
    gj = get_json(layer_url + "/query", {"where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
                                         "resultRecordCount": 500, "maxAllowableOffset": 0.0005})
    if not gj or "features" not in gj:
        return None, (gj or {}).get("error", "query failed")
    return gj, ""


def rings(geom):
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def area_sqmi(poly_rings, lat0):
    """Planar area on an equirectangular projection; fine for zone-sized shapes."""
    kx, ky = 69.172 * math.cos(math.radians(lat0)), 69.0
    total = 0.0
    for poly in poly_rings:
        for i, ring in enumerate(poly):
            a = 0.0
            for p1, p2 in zip(ring, ring[1:]):  # points may carry a z value
                (x1, y1), (x2, y2) = p1[:2], p2[:2]
                a += (x1 * kx) * (y2 * ky) - (x2 * kx) * (y1 * ky)
            total += abs(a) / 2 * (1 if i == 0 else -1)
    return total


def point_in_ring(x, y, ring):
    inside = False
    for p1, p2 in zip(ring, ring[1:]):
        (x1, y1), (x2, y2) = p1[:2], p2[:2]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def contains(poly_rings, x, y):
    for poly in poly_rings:
        if poly and point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, h) for h in poly[1:]):
            return True
    return False


def miles(lat1, lng1, lat2, lng2):
    dx = (lng2 - lng1) * 69.172 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, (lat2 - lat1) * 69.0)


def nearest_vertex_miles(poly_rings, lat, lng):
    best = float("inf")
    for poly in poly_rings:
        for pt in poly[0][:: max(1, len(poly[0]) // 200)]:
            best = min(best, miles(lat, lng, pt[1], pt[0]))
    return best


def current_area(state, name):
    p = ROOT / "data" / "boundaries" / f"{state}.geojson"
    if not p.exists():
        return None
    for f in json.load(open(p))["features"]:
        if f["properties"].get("name") == name:
            r = rings(f["geometry"])
            lat0 = r[0][0][0][1] if r else 40
            return area_sqmi(r, lat0)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", choices=["likely", "all"], default="all")
    ap.add_argument("--tag", default="", help="read/write the files arcgis_search.py wrote with the same --tag")
    args = ap.parse_args()
    global CAND, OUT
    if args.tag:
        CAND = CAND.with_name(f"arcgis_candidates_{args.tag}.csv")
        OUT = OUT.with_name(f"arcgis_vetted_{args.tag}.csv")
    systems = {(s["state"], s["name"]): s for s in json.load(open(ROOT / "data" / "systems.json"))}
    cands = list(csv.DictReader(open(CAND, newline="", encoding="utf-8")))
    if args.tier == "likely":
        cands = [c for c in cands if c["Tier"] == "likely"]
    CACHE.mkdir(parents=True, exist_ok=True)
    out = []
    print(f"Vetting {len(cands)} candidate items")
    for n, c in enumerate(cands, 1):
        try:
            vet_one(c, systems, out)
        except Exception as e:  # noqa: BLE001  one bad item shouldn't stop the run
            out.append({**c, "Check": f"error: {e}"[:200]})
        if n % 25 == 0 or n == len(cands):
            print(f"  {n}/{len(cands)}")
    write(out)


def vet_one(c, systems, out):
    sys_row = systems[(c["State"], c["Name"])]
    item_id = c["Item"].split("id=")[-1]
    item = get_json(f"https://www.arcgis.com/sharing/rest/content/items/{item_id}", {"f": "json"}) or {}
    org = org_name(item.get("orgId"))
    cur = current_area(c["State"], c["Name"])
    layers = polygon_layers(item) if "error" not in item else []
    if not layers:
        out.append({**c, "Org": org, "Layer": "", "Layer URL": "", "Features": 0, "Area sq mi": "",
                    "Current area sq mi": round(cur, 1) if cur else "", "Area ratio": "",
                    "Pin inside": "", "Miles to pin": "", "Check": "no polygon layer",
                    "Feature names": "", "Cached": ""})
    for layer_url, layer_name in layers[:6]:
        gj, err = fetch_features(layer_url)
        row = {**c, "Org": org, "Layer": layer_name, "Layer URL": layer_url,
               "Current area sq mi": round(cur, 1) if cur else ""}
        if gj is None:
            out.append({**row, "Features": 0, "Area sq mi": "", "Area ratio": "", "Pin inside": "",
                        "Miles to pin": "", "Check": f"skipped: {err}", "Feature names": "", "Cached": ""})
            continue
        feats = [f for f in gj["features"] if rings(f.get("geometry"))]
        allr = [p for f in feats for p in rings(f["geometry"])]
        lat, lng = sys_row["lat"], sys_row["lng"]
        area = area_sqmi(allr, lat) if allr else 0
        inside = contains(allr, lng, lat) if allr else False
        dist = 0.0 if inside else (nearest_vertex_miles(allr, lat, lng) if allr else float("inf"))
        # Feature labels help pick the right zone in a multi-zone layer.
        label_keys = [k for k in (feats[0]["properties"] if feats else {}) if
                      any(w in k.lower() for w in ("name", "zone", "label", "title", "area", "service"))]
        names = sorted({str(f["properties"].get(label_keys[0])) for f in feats})[:12] if label_keys else []
        check = "ok"
        if not feats:
            check = "no features"
        elif dist > NEAR_MILES:
            check = f"wrong place ({dist:.0f} mi from pin)"
        elif cur and area and not (0.05 <= area / cur <= 3):
            check = "area very different"
        cache = CACHE / f"{item_id}_{layer_url.split('/')[-1]}.geojson"
        cache.write_text(json.dumps(gj), encoding="utf-8")
        out.append({**row, "Features": len(feats), "Area sq mi": round(area, 1),
                    "Area ratio": round(area / cur, 2) if cur and area else "",
                    "Pin inside": "yes" if inside else "no", "Miles to pin": round(dist, 1),
                    "Check": check, "Feature names": " | ".join(names),
                    "Cached": str(cache.relative_to(ROOT))})



def write(out):
    fields = []
    for r in out:
        fields += [k for k in r if k not in fields]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    ok = {(r["State"], r["Name"]) for r in out if r["Check"] == "ok"}
    print(f"{len(ok)} systems have at least one layer that passes location/area checks. Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
