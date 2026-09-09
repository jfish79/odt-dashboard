#!/usr/bin/env python3
"""
Promote workflow batch specs into the committed per-state spec + GeoJSON.

  python3 scripts/boundaries/merge.py --scratch <dir> --states VA WI [--updated 2026-09]

For each state:
  1. concatenates <scratch>/specs/<ST>.b*.json into data/boundaries/specs/<ST>.json
     (later batches win on duplicate names; existing committed specs are kept
     for names not present in the batches)
  2. runs resolve.py -> data/boundaries/<ST>.geojson, dropping any feature whose
     name is no longer in ODT_Inventory.csv (orphans are reported)
  3. prints a coverage line and every non-ok QA status

Committed spec files are the durable, human-editable record of *why* each
polygon looks the way it does; re-running resolve.py on them regenerates the
GeoJSON exactly.
"""
import argparse
import csv
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SPECS = os.path.join(ROOT, 'data', 'boundaries', 'specs')
OUT = os.path.join(ROOT, 'data', 'boundaries')
RESOLVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resolve.py')


def csv_names(state):
    with open(os.path.join(ROOT, 'ODT_Inventory.csv'), encoding='utf-8') as f:
        return {r['Name'] for r in csv.DictReader(f) if r['State'] == state}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scratch', required=True)
    ap.add_argument('--states', nargs='+', required=True)
    ap.add_argument('--updated')
    a = ap.parse_args()
    os.makedirs(SPECS, exist_ok=True)

    for st in a.states:
        names = csv_names(st)
        spec_path = os.path.join(SPECS, f'{st}.json')
        merged = {}
        if os.path.exists(spec_path):
            with open(spec_path, encoding='utf-8') as f:
                for s in json.load(f):
                    merged[s['name']] = s
        files = sorted(glob.glob(os.path.join(a.scratch, 'specs', f'{st}.b*.json')),
                       key=lambda p: int(p.rsplit('.b', 1)[1].split('.')[0]))
        for p in files:
            with open(p, encoding='utf-8') as f:
                for s in json.load(f):
                    s['state'] = st
                    merged[s['name']] = s
        dropped = [n for n in merged if n not in names]
        for n in dropped:
            del merged[n]
        specs = sorted(merged.values(), key=lambda s: s['name'].lower())
        with open(spec_path, 'w', encoding='utf-8') as f:
            json.dump(specs, f, indent=1, ensure_ascii=False)

        geo_path = os.path.join(OUT, f'{st}.geojson')
        # existing features for names without a spec are kept only if still in the CSV
        keep = []
        if os.path.exists(geo_path):
            with open(geo_path, encoding='utf-8') as f:
                for feat in json.load(f).get('features', []):
                    n = feat['properties'].get('name')
                    if n in names and n not in merged:
                        keep.append(feat)
                    elif n not in names:
                        dropped.append(n)
        qa_path = os.path.join(a.scratch, 'qa', f'{st}.merged.json')
        cmd = [sys.executable, RESOLVE, '--specs', spec_path, '--out', geo_path, '--qa', qa_path]
        if a.updated:
            cmd += ['--updated', a.updated]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(r.stdout, r.stderr)
            sys.exit(f'resolve failed for {st}')
        if keep:
            with open(geo_path, encoding='utf-8') as f:
                gj = json.load(f)
            have = {x['properties']['name'] for x in gj['features']}
            gj['features'] += [k for k in keep if k['properties']['name'] not in have]
            gj['features'].sort(key=lambda x: x['properties']['name'].lower())
            with open(geo_path, 'w', encoding='utf-8') as f:
                json.dump(gj, f, separators=(',', ':'))
        with open(geo_path, encoding='utf-8') as f:
            nfeat = len(json.load(f)['features'])
        with open(qa_path, encoding='utf-8') as f:
            qa = json.load(f)
        bad = [q for q in qa if q['status'] != 'ok']
        print(f'{st}: {nfeat}/{len(names)} rows have a boundary; specs={len(specs)}; '
              f'{len(bad)} non-ok; dropped stale: {sorted(set(dropped)) or "none"}')
        for q in bad:
            print(f'   [{q["status"]}] {q["name"]}: ' + ' | '.join(q['issues'])[:200])


if __name__ == '__main__':
    main()
