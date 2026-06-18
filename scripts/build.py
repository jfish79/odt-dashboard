#!/usr/bin/env python3
"""
build.py — ODT Database build pipeline

Reads ODT_Inventory.csv and produces:
  - data/systems.json           (consumed by the dashboard at runtime)
  - data/boundaries/_index.json (boundary manifest, from scanning geojson files)
  - summary.csv                 (regenerated from inventory counts)

Usage:
  python3 scripts/build.py              # run from repo root
  python3 scripts/build.py --check      # validate only, don't write files
"""

import csv
import json
import glob
import os
import sys
from collections import Counter
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# ── Column mapping: CSV header → JSON key ──────────────────────────────────
COLUMN_MAP = {
    'Name':                     'name',
    'State':                    'state',
    'Region/Service Area':      'area',
    'Geographic Context':       'geo',
    'Operator':                 'operator',
    'System Type':              'type',
    'Technology Vendor':        'vendor',
    'Booking Method(s)':        'booking',
    'Scheduling Window':        'window',
    'Fare':                     'fare',
    'Service Hours':            'hours',
    'Launch Year':              'year',
    'Funding Source':           'funding',
    'Status/Maturity':          'status',
    'Fleet':                    'fleet',
    'Ridership/Performance Notes': 'notes',
    'Website URL':              'url',
    'Latitude':                 'lat',
    'Longitude':                'lng',
    # 'Source' intentionally excluded — metadata stays in CSV only
}

VALID_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
    'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
    'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
    'TX','UT','VT','VA','WA','WV','WI','WY','DC'
}


def read_inventory(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def validate(rows):
    errors = 0
    warnings = 0
    seen = {}

    for i, row in enumerate(rows, start=2):
        name = row.get('Name', '').strip()
        state = row.get('State', '').strip()
        lat = row.get('Latitude', '').strip()
        lng = row.get('Longitude', '').strip()

        if not name:
            print(f"  ERROR row {i}: missing Name")
            errors += 1
            continue

        if not state:
            print(f"  ERROR row {i} ({name}): missing State")
            errors += 1
        elif state not in VALID_STATES:
            print(f"  ERROR row {i} ({name}): unknown state '{state}'")
            errors += 1

        if not lat or not lng:
            print(f"  ERROR row {i} ({name}/{state}): missing coordinates")
            errors += 1
        else:
            try:
                float(lat); float(lng)
            except ValueError:
                print(f"  ERROR row {i} ({name}/{state}): non-numeric coordinates")
                errors += 1

        key = (name, state)
        if key in seen:
            print(f"  WARN  row {i}: duplicate '{name}/{state}' (first at row {seen[key]})")
            warnings += 1
        seen[key] = i

        sys_type = row.get('System Type', '').strip()
        if sys_type and sys_type not in ('Microtransit', 'Demand-Response', 'Paratransit'):
            print(f"  WARN  row {i} ({name}): unusual System Type '{sys_type}'")
            warnings += 1

    return errors, warnings


def to_json_record(row):
    rec = {}
    for csv_col, json_key in COLUMN_MAP.items():
        val = row.get(csv_col, '').strip()
        if json_key in ('lat', 'lng'):
            try:
                val = round(float(val), 6)
            except (ValueError, TypeError):
                val = 0.0
        rec[json_key] = val
    return rec


def build_systems_json(rows, outpath):
    records = [to_json_record(r) for r in rows]
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=1, ensure_ascii=False)
    return records


def build_summary(rows, outpath):
    types = Counter(r.get('System Type', '').strip() for r in rows)
    states = {r.get('State', '').strip() for r in rows if r.get('State', '').strip()}
    active = sum(1 for r in rows if r.get('Status/Maturity', '').strip().startswith('Active'))

    lines = [
        'ODT Database — Summary',
        f'Total Systems: {len(rows)}  |  States: {len(states)}  |  Updated: {date.today().strftime("%B %Y")}',
        '',
        'Breakdown by Type',
        f'Microtransit: {types.get("Microtransit", 0)}',
        f'Demand-Response (general public): {types.get("Demand-Response", 0)}',
        f'Paratransit (eligibility-restricted): {types.get("Paratransit", 0)}',
        f'Active systems: {active}',
        '',
        'See concerns.csv for data quality issues, vendor errors, and reclassification log.',
    ]
    with open(outpath, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')


def build_boundary_manifest(boundaries_dir):
    states_detail = {}
    for path in sorted(glob.glob(os.path.join(boundaries_dir, '*.geojson'))):
        st = os.path.splitext(os.path.basename(path))[0]
        if st.startswith('_'):
            continue
        with open(path, encoding='utf-8') as f:
            gj = json.load(f)
        feats = gj.get('features', [])
        dates = sorted({feat['properties'].get('updated', '')
                        for feat in feats if feat.get('properties')})
        states_detail[st] = {
            'features': len(feats),
            'updated': dates[-1] if dates else None
        }
    manifest = {'states': sorted(states_detail.keys()), 'detail': states_detail}
    with open(os.path.join(boundaries_dir, '_index.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=1)
    return manifest


def main():
    check_only = '--check' in sys.argv

    inventory_path = os.path.join(ROOT, 'ODT_Inventory.csv')
    systems_path = os.path.join(ROOT, 'data', 'systems.json')
    summary_path = os.path.join(ROOT, 'summary.csv')
    boundaries_dir = os.path.join(ROOT, 'data', 'boundaries')

    if not os.path.exists(inventory_path):
        print(f"ERROR: {inventory_path} not found. Run from the repo root.")
        sys.exit(1)

    print(f"Reading {inventory_path}...")
    rows = read_inventory(inventory_path)
    print(f"  {len(rows)} rows loaded")

    print("Validating...")
    errors, warnings = validate(rows)
    print(f"  {errors} errors, {warnings} warnings")

    if check_only:
        print("\n--check mode: no files written.")
        sys.exit(1 if errors else 0)

    if errors:
        print("\nERRORS found. Fix them before building. Use --check to validate without writing.")
        sys.exit(1)

    print(f"\nWriting {systems_path}...")
    records = build_systems_json(rows, systems_path)
    states = {r['state'] for r in records}
    types = Counter(r['type'] for r in records)
    print(f"  {len(records)} systems across {len(states)} states")
    for t, c in sorted(types.items()):
        print(f"    {t}: {c}")

    print(f"Writing {summary_path}...")
    build_summary(rows, summary_path)

    if os.path.isdir(boundaries_dir):
        print(f"Scanning {boundaries_dir}...")
        manifest = build_boundary_manifest(boundaries_dir)
        print(f"  Boundary states: {manifest['states']}")
    else:
        print(f"  No {boundaries_dir}, skipping boundary manifest.")

    print("\nBuild complete.")


if __name__ == '__main__':
    main()
