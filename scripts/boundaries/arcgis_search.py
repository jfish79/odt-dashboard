#!/usr/bin/env python3
"""Search ArcGIS Online for agency-published service-area layers.

Many agencies publish their microtransit zone map as a public ArcGIS Online
layer (e.g. COTA's "COTA Plus Zones Current (Public View)") even when there is
no GTFS-Flex feed. This script searches ArcGIS Online's public catalog for each
row whose polygon is approximate or missing, and writes the candidate layers to
a CSV for vetting. It does not touch data/boundaries/.

    python3 scripts/boundaries/arcgis_search.py --skip-states CO,OH
    python3 scripts/boundaries/arcgis_search.py --states FL,GA --all-fidelity

Output: scripts/boundaries/candidates/arcgis_candidates.csv (one row per
system x candidate layer, best first) and arcgis_summary.csv (one row per
system searched, with its best score).

Scores are a triage aid, not a verdict. Before using a layer, check that its
owner is the agency (or its operator/vendor), that it is the current zone and
not a proposal or an old snapshot, and that it matches the row's service-area
text. The Sept 2026 GTFS-Flex scan rejected 5 name matches that turned out to
be a different route on the same feed.
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

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "candidates"
SEARCH = "https://www.arcgis.com/sharing/rest/search"
UA = "odt-inventory-boundary-search/1.0"
TYPES = ['Feature Service', 'Map Service', 'Web Map', 'GeoJson', 'Shapefile', 'KML']

# Words that say a layer is a zone/boundary, and words that say it's something else.
ZONE_WORDS = re.compile(r"\b(zones?|service ?areas?|boundar(y|ies)|microtransit|micro-transit|on[- ]?demand|"
                        r"geofences?|coverage|flex)\b", re.I)
BAD_WORDS = re.compile(r"\b(candidates?|proposed|proposals?|recommend\w*|draft|future|scenarios?|demographic\w*|"
                       r"stops?|lines|routes?|survey|outreach|analysis|study|test|copy|old|archive|ridership|"
                       r"trips?|heat ?map|potential|options?|alternatives?|equity|suitability|feedback|comments?|"
                       r"concepts?|prelim\w*|planning|boardings?|average|daily|limits|projects?|improvements?|nextgen|redesign)\b", re.I)
# Tokens too generic to identify a system on their own.
GENERIC = {"the", "of", "and", "on", "demand", "ondemand", "on-demand", "transit", "transportation", "service",
           "services", "microtransit", "ride", "rides", "connect", "area", "city", "county", "authority",
           "regional", "public", "flex", "go", "via", "zone", "zones", "app", "a", "to", "in", "for", "by",
           "metro", "bus", "system", "district", "mobility", "shuttle", "pilot", "program", "dial", "dart"}


def tokens(s):
    return [t for t in re.findall(r"[a-z0-9]+", s.lower()) if len(t) > 1]


def distinctive(s):
    return [t for t in tokens(s) if t not in GENERIC]


def short_name(name):
    """'Call-N-Ride (Greeley-Evans Transit)' -> 'Call-N-Ride'."""
    return re.sub(r"\s*\(.*?\)\s*", " ", name).strip()


def search(q, num=50):
    type_q = " OR ".join(f'type:"{t}"' for t in TYPES)
    params = {"q": f"({q}) AND ({type_q})", "num": num, "f": "json"}
    url = SEARCH + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("results", [])
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                print(f"  search failed ({e}): {q}", file=sys.stderr)
                return []
            time.sleep(2 * (attempt + 1))


def score(item, row):
    text = " ".join([item.get("title") or "", " ".join(item.get("tags") or []), item.get("snippet") or ""])
    tt = set(tokens(text))
    title = item.get("title") or ""
    name_tok = set(distinctive(short_name(row["name"])))
    op_tok = set(distinctive(row["operator"]))
    place_tok = set(distinctive(row["area"]))
    s, why = 0.0, []
    if name_tok:
        hit = len(name_tok & tt) / len(name_tok)
        s += 4 * hit
        if hit:
            why.append(f"name {hit:.0%}")
    if op_tok:
        hit = len(op_tok & tt) / len(op_tok)
        s += 2 * hit
        if hit >= 0.5:
            why.append("operator")
    if place_tok & tt:
        s += 1
        why.append("place")
    if ZONE_WORDS.search(text):
        s += 1.5
        why.append("zone word")
    bad = BAD_WORDS.findall(title)
    if bad:
        s -= 2.5
        why.append("flag: " + ",".join(sorted({b if isinstance(b, str) else b[0] for b in bad})).lower())
    if re.search(r"current|public view|adopted|existing|official", title, re.I):
        s += 0.5
    if item.get("type") == "Feature Service":
        s += 0.5
    likely = bool(name_tok) and len(name_tok & tt) / len(name_tok) >= 0.5 and ZONE_WORDS.search(text) and not bad
    return round(s, 2), "; ".join(why), "likely" if likely else "possible"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states", help="comma-separated states to search (default: all)")
    ap.add_argument("--skip-states", default="", help="comma-separated states to leave out")
    ap.add_argument("--all-fidelity", action="store_true", help="also search rows whose polygon is exact")
    ap.add_argument("--min-score", type=float, default=3.0, help="drop candidates scoring below this")
    ap.add_argument("--per-system", type=int, default=5, help="keep at most this many candidates per system")
    ap.add_argument("--tag", default="", help="suffix for output file names, e.g. 'oh' -> arcgis_candidates_oh.csv")
    args = ap.parse_args()

    systems = json.load(open(ROOT / "data" / "systems.json"))
    only = set(args.states.split(",")) if args.states else None
    skip = set(filter(None, args.skip_states.split(",")))
    rows = [s for s in systems
            if (only is None or s["state"] in only) and s["state"] not in skip
            and (args.all_fidelity or not s.get("boundary") or s["boundary"].get("fidelity") == "approximate")]
    print(f"Searching ArcGIS Online for {len(rows)} systems")

    OUT_DIR.mkdir(exist_ok=True)
    cand_rows, summary = [], []
    for n, row in enumerate(rows, 1):
        sn = short_name(row["name"])
        queries = [f'"{sn}"']
        if row["operator"] and row["operator"] != "Not specified":
            op = short_name(row["operator"])
            queries.append(f'"{op}" AND (microtransit OR zone OR zones OR "on demand" OR "service area")')
        seen = {}
        for q in queries:
            for it in search(q):
                if it["id"] in seen:
                    continue
                sc, why, tier = score(it, row)
                seen[it["id"]] = (sc, why, q, it, tier)
            time.sleep(0.3)
        ranked = sorted(seen.values(), key=lambda x: (x[4] != "likely", -x[0]))
        kept = [x for x in ranked if x[0] >= args.min_score][: args.per_system]
        b = row.get("boundary") or {}
        summary.append({"State": row["state"], "Name": row["name"], "Current boundary": b.get("type", "(none)"),
                        "Fidelity": b.get("fidelity", ""), "Results": len(seen), "Candidates": len(kept),
                        "Likely": sum(1 for x in kept if x[4] == "likely"),
                        "Best score": kept[0][0] if kept else "", "Best title": kept[0][3].get("title") if kept else ""})
        for sc, why, q, it, tier in kept:
            mod = it.get("modified")
            cand_rows.append({
                "State": row["state"], "Name": row["name"], "Operator": row["operator"],
                "Service area (CSV)": row["area"], "Current boundary": b.get("type", "(none)"),
                "Tier": tier, "Score": sc, "Why": why, "Title": it.get("title"), "Type": it.get("type"),
                "Owner": it.get("owner"),
                "Modified": time.strftime("%Y-%m-%d", time.gmtime(mod / 1000)) if mod else "",
                "Item": f"https://www.arcgis.com/home/item.html?id={it['id']}",
                "Service URL": it.get("url") or "", "Query": q,
            })
        if n % 20 == 0 or n == len(rows):
            print(f"  {n}/{len(rows)} searched, {sum(1 for s in summary if s['Candidates'])} with candidates")

    def dump(path, data):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            if not data:
                fh.write("")
                return
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    sfx = f"_{args.tag}" if args.tag else ""
    dump(OUT_DIR / f"arcgis_candidates{sfx}.csv", cand_rows)
    dump(OUT_DIR / f"arcgis_summary{sfx}.csv", summary)
    print(f"{sum(1 for s in summary if s['Likely'])} of {len(summary)} systems have a likely match, "
          f"{sum(1 for s in summary if s['Candidates'])} have at least one candidate; "
          f"{len(cand_rows)} candidate layers. Wrote {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
