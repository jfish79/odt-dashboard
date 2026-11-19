#!/usr/bin/env python3
"""Load agency-published zone maps into data/boundaries/{ST}.geojson.

scripts/boundaries/agency_layers.json is the durable record: for each system,
the map it comes from (an ArcGIS layer via "layer_url", a KML/KMZ file such
as a Google My Maps export via "kml_url", a GeoJSON file via "geojson_url",
or several of these via "urls"), which features (zones) to keep, and
a note on why. Entries with "hold": true are skipped unless named with --only
(used for findings waiting on a review, e.g. Ohio). This script fetches each layer, unions the chosen zones into one
(Multi)Polygon, and writes it as boundary_type "agency_gis" (fidelity exact),
replacing that system's existing polygon. It also removes the system's entry
from data/boundaries/specs/{ST}.json, the same way the GTFS-Flex polygons were
added, so a later resolve.py --merge run doesn't overwrite it.

    python3 scripts/boundaries/add_agency_layers.py              # all entries not on hold
    python3 scripts/boundaries/add_agency_layers.py --only "SMART Flex"
    python3 scripts/build.py                                     # afterwards

Candidates come from arcgis_search.py / arcgis_vet.py; see NOTES.md.
"""
import argparse
import datetime
import io
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from resolve import round_geom  # noqa: E402

CONFIG = HERE / "agency_layers.json"
UA = "odt-inventory-boundary-search/1.0"


KML = "{http://www.opengis.net/kml/2.2}"


def fetch_kml(url):
    """KML or KMZ -> GeoJSON-like dict; each Placemark polygon becomes a feature
    with properties {"name": <placemark name>, "folder": <folder name>}."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    if raw[:2] == b"PK":  # KMZ
        z = zipfile.ZipFile(io.BytesIO(raw))
        raw = z.read(next(n for n in z.namelist() if n.lower().endswith(".kml")))
    root = ET.fromstring(raw)
    feats = []

    def walk(node, folder):
        for child in node:
            tag = child.tag.replace(KML, "")
            if tag in ("Folder", "Document"):
                nm = child.find(KML + "name")
                walk(child, nm.text.strip() if nm is not None and nm.text else folder)
            elif tag == "Placemark":
                nm = child.find(KML + "name")
                for pg in child.iter(KML + "Polygon"):
                    def ring(el):
                        pts = [tuple(map(float, p.split(",")[:2])) for p in el.text.split()]
                        return pts
                    outer = ring(pg.find(f"{KML}outerBoundaryIs//{KML}coordinates"))
                    holes = [ring(c) for c in pg.findall(f"{KML}innerBoundaryIs//{KML}coordinates")]
                    feats.append({"type": "Feature",
                                  "properties": {"name": (nm.text or "").strip() if nm is not None else "",
                                                 "folder": folder},
                                  "geometry": Polygon(outer, holes).__geo_interface__})
    walk(root, "")
    return {"type": "FeatureCollection", "features": feats}


def fetch_geojson(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        gj = json.load(r)
    if "features" not in gj:
        raise RuntimeError(f"no features in {url}")
    return gj


def fetch(e):
    """One source ("kml_url", "geojson_url" or ArcGIS "layer_url"), or several
    ("urls": list of those URLs, kind inferred from the extension); features merged."""
    urls = e.get("urls")
    if urls:
        feats = []
        for u in urls:
            low = u.lower().split("?")[0]
            src = fetch_kml(u) if low.endswith((".kml", ".kmz")) or "maps/d/kml" in u else \
                fetch_geojson(u) if low.endswith(".geojson") else fetch_arcgis(u)
            feats += src["features"]
        return {"type": "FeatureCollection", "features": feats}
    if e.get("kml_url"):
        return fetch_kml(e["kml_url"])
    if e.get("geojson_url"):
        return fetch_geojson(e["geojson_url"])
    return fetch_arcgis(e["layer_url"])


def fetch_arcgis(layer_url):
    q = urllib.parse.urlencode({"where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
                                "resultRecordCount": 500})
    req = urllib.request.Request(f"{layer_url}/query?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        gj = json.load(r)
    if "features" not in gj:
        raise RuntimeError(f"no features from {layer_url}: {gj.get('error')}")
    return gj


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", help="system name to (re)load; repeatable (overrides hold)")
    args = ap.parse_args()
    entries = json.load(open(CONFIG, encoding="utf-8"))
    if args.only:
        entries = [e for e in entries if e["name"] in args.only]
    else:
        held = [e["name"] for e in entries if e.get("hold")]
        entries = [e for e in entries if not e.get("hold")]
        if held:
            print(f"Skipping {len(held)} entries on hold: {', '.join(held)}")
    today = datetime.date.today()
    by_state = {}
    for e in entries:
        by_state.setdefault(e["state"], []).append(e)

    for st, es in sorted(by_state.items()):
        gpath = ROOT / "data" / "boundaries" / f"{st}.geojson"
        spath = ROOT / "data" / "boundaries" / "specs" / f"{st}.json"
        gj = json.load(open(gpath, encoding="utf-8"))
        specs = json.load(open(spath, encoding="utf-8")) if spath.exists() else None
        # keep each spec file's existing escaping (some have \u escapes, some raw UTF-8)
        spec_text = spath.read_text(encoding="utf-8") if spath.exists() else ""
        spec_ascii = all(ord(ch) < 128 for ch in spec_text)
        spec_nl = spec_text.endswith("\n")
        for e in es:
            src = fetch(e)
            feats = [f for f in src["features"] if f.get("geometry")]
            if e.get("include"):
                feats = [f for f in feats if str(f["properties"].get(e["field"], "")).strip() in e["include"]]
            if not feats:
                sys.exit(f"{st} {e['name']}: no features left after filtering")
            zones = sorted({str(f["properties"].get(e["field"], "")).strip() for f in feats} - {"", "None"})
            geom = unary_union([shape(f["geometry"]).buffer(0) for f in feats])
            feature = {
                "type": "Feature",
                "properties": {
                    "name": e["name"],
                    "boundary_type": "agency_gis",
                    "source": f"Agency zone map ({e.get('platform', 'ArcGIS Online')})",
                    "fidelity": "exact",
                    "updated": today.strftime("%Y-%m"),
                    "units": f"{e['title']} / {e['layer']}" + (f": {', '.join(zones)}" if zones else ""),
                    "note": (f"{e['note']} Layer published by {e['publisher']}, last modified {e['modified']} "
                             f"({e['item']}). Fetched {today.isoformat()}."),
                    "confidence": 0.9,
                },
                "geometry": round_geom(geom),
            }
            idx = [i for i, f in enumerate(gj["features"]) if f["properties"].get("name") == e["name"]]
            replaced = bool(idx)
            if idx:  # replace in place so the file diff shows only this system
                gj["features"][idx[0]] = feature
                for i in reversed(idx[1:]):
                    del gj["features"][i]
            else:
                gj["features"].append(feature)
            if specs is not None:
                specs = [s for s in specs if s.get("name") != e["name"]]
            print(f"{st} {e['name']}: {len(feats)} feature(s) {zones or ''} -> agency_gis"
                  f" ({'replaced existing polygon' if replaced else 'new polygon'})")
        with open(gpath, "w", encoding="utf-8") as fh:
            json.dump(gj, fh, separators=(",", ":"))  # same format as resolve.py / merge.py
        if specs is not None:
            with open(spath, "w", encoding="utf-8") as fh:
                json.dump(specs, fh, indent=1, ensure_ascii=spec_ascii)
                if spec_nl:
                    fh.write("\n")


if __name__ == "__main__":
    main()
