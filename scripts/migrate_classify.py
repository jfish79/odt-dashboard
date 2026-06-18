#!/usr/bin/env python3
"""
migrate_classify.py — One-time paratransit reclassification tool

NOT part of the live build pipeline. Kept for provenance and re-import.

This script applies the keyword-based classifier that was originally used
to reclassify 83 supplemental Demand-Response rows as Paratransit during
the June 2026 data import from the CA/CO supplemental JSON files.

The reclassification is now baked into ODT_Inventory.csv as committed data.
Running build.py does NOT re-run this classifier. To apply it to new data,
run this script directly against a CSV.

Usage:
  python3 scripts/migrate_classify.py <input.csv> <output.csv>
"""

import csv
import sys


MARKERS = [
    'ada', 'paratransit', 'senior', 'disabled', 'elderly',
    'older adult', '60+', '62+', '65+', 'eligible', 'specialized',
    'complementary', 'special needs', 'dial-a-ride'
]


def classify_type(row):
    """Return reclassified System Type, or original if no change."""
    sys_type = row.get('System Type', '').strip()
    if sys_type != 'Demand-Response':
        return sys_type

    text = ' '.join([
        row.get('Name', ''),
        row.get('Ridership/Performance Notes', ''),
        row.get('Operator', '')
    ]).lower()

    for marker in MARKERS:
        if marker in text:
            return 'Paratransit'

    name = row.get('Name', '').lower()
    tokens = name.split()
    if 'dar' in tokens or 'dial-a-ride' in name or 'dial a ride' in name:
        return 'Paratransit'

    return 'Demand-Response'


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    inpath, outpath = sys.argv[1], sys.argv[2]
    changed = 0

    with open(inpath, newline='', encoding='utf-8') as fin:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        rows = list(reader)

    for row in rows:
        new_type = classify_type(row)
        if new_type != row.get('System Type', '').strip():
            print(f"  {row['Name']} ({row['State']}): {row['System Type']} → {new_type}")
            row['System Type'] = new_type
            changed += 1

    with open(outpath, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{changed} rows reclassified. Written to {outpath}")


if __name__ == '__main__':
    main()
