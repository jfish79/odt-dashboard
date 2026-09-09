#!/usr/bin/env python3
"""
Boundary resolver: turns JSON "boundary specs" into service-area GeoJSON.

A spec names the administrative units (Census counties / places / county
subdivisions / tracts) or an approximate buffer that best represents one
system's service area. This script fetches the matching Census cartographic
boundary geometries (2023, 1:500k), dissolves them, and writes GeoJSON
features in the same property schema as data/boundaries/NC.geojson.

The LLM legwork only ever produces specs; geometry is always deterministic
and reproducible from the spec + Census files.

Usage:
  python3 scripts/boundaries/resolve.py --specs data/boundaries/specs/VA.json \
      --out data/boundaries/VA.geojson [--qa qa.json] [--merge]

  --merge   keep existing features in --out whose name is not in the specs
            (lets several batches / re-runs accumulate into one state file)
  --qa      write a QA report (unresolved units, pin-in-polygon checks, area
            sanity) as JSON; a summary is always printed to stdout
  --dry-run resolve and report, write nothing

Spec format (one JSON list per file):
  {
    "name": "Orange County MOD",          # must match the CSV Name exactly
    "state": "NC",
    "boundary_type": "county",            # see BOUNDARY_TYPES below
    "units": [                            # admin units to union (not for buffer/tracts)
      {"layer": "county", "name": "Orange"},
      {"layer": "place",  "name": "Wilson"},                 # incorporated place or CDP
      {"layer": "cousub", "name": "Madison", "county": "New Haven"},  # town/township (MCD)
      {"layer": "auto",   "name": "Guilford"},               # tries place, then cousub
      {"layer": "aiannh", "name": "Crow"}                    # federal reservation / tribal land
    ],
    "tract_geoids": ["37063001001", ...], # for boundary_type census_tracts
    "buffer": {"lat": 36.1, "lon": -79.9, "radius_km": 5},   # for zone_approx (single circle)
    "buffers": [                          # zone_approx: several circles, e.g. one per named zone
      {"center_unit": {"layer": "place", "name": "Virginia Beach"}, "radius_km": 3.5},
      {"lat": 37.0, "lon": -76.4, "radius_km": 2.2}
    ],
    "clip_to_units": true,                # zone_approx: clip the circles to the union of "units"
    "dilate_km": 8,                       # boundary_type "buffered": units + this radius around them
                                          #   ("City of X plus 5 miles" -> place X, dilate_km 8)
    "fidelity": "exact" | "approximate",  # optional; defaulted from boundary_type
    "source": "Census TIGER county",      # optional; defaulted from boundary_type
    "note": "free text provenance / caveat", # optional, kept in properties
    "confidence": 0.9,                    # optional, LLM self-rating, kept in properties
    "skip": true                          # optional: no boundary producible; row listed in QA only
  }
"""

import argparse
import csv
import io
import json
import math
import os
import re
import sys
import urllib.request
import zipfile
from collections import defaultdict

import shapefile  # pyshp
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon
from shapely.ops import unary_union

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
CB_YEAR = '2023'
CB_BASE = f'https://www2.census.gov/geo/tiger/GENZ{CB_YEAR}/shp/'

STATE_FIPS = {
    'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09', 'DE': '10',
    'DC': '11', 'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19',
    'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27',
    'MS': '28', 'MO': '29', 'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34', 'NM': '35',
    'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39', 'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44',
    'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53',
    'WV': '54', 'WI': '55', 'WY': '56', 'PR': '72',
}

# boundary_type -> (default source, default fidelity). Must stay in sync with
# BOUNDARY_COLORS in index.html.
BOUNDARY_TYPES = {
    'city':               ('Census TIGER place', 'exact'),
    'places':             ('Census TIGER place', 'exact'),
    'county':             ('Census TIGER county', 'exact'),
    'counties':           ('Census TIGER county', 'exact'),
    'cousub':             ('Census TIGER county subdivision', 'exact'),
    'cousubs':            ('Census TIGER county subdivision', 'exact'),
    'tribal':             ('Census TIGER AIANNH area', 'exact'),
    'census_tracts':      ('Census TIGER tract', 'exact'),
    'places_constructed': ('Census TIGER place (constructed)', 'approximate'),
    'zone_approx':        ('Manual approximation', 'approximate'),
    'buffered':           ('Census TIGER unit + service radius', 'approximate'),
}

# LSAD codes that are NOT incorporated municipalities (CDPs etc.)
CDP_LSADS = {'57'}
NAME_PREFIX = re.compile(r'^(city|town|village|borough|township|charter township|'
                         r'municipality|cdp) of\s+', re.I)
NAME_SUFFIX = re.compile(r'\s+(city|town|village|borough|township|charter township|'
                         r'cdp|county|parish|municipality)$', re.I)


def norm(name):
    s = name.strip()
    s = NAME_PREFIX.sub('', s)
    s = NAME_SUFFIX.sub('', s)
    s = s.replace('St. ', 'Saint ').replace('St ', 'Saint ').replace('Ste. ', 'Sainte ')
    s = re.sub(r'[\'’.\-]', '', s)
    return re.sub(r'\s+', ' ', s).strip().lower()


# ── Census file access ────────────────────────────────────────────────────

def _fetch(fname):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, fname)
    if not os.path.exists(path):
        url = CB_BASE + fname
        print(f'  downloading {url}')
        tmp = f'{path}.part{os.getpid()}'
        urllib.request.urlretrieve(url, tmp)
        os.replace(tmp, path)  # atomic: parallel runs never see a partial zip
    return path


def _read_zip(path):
    z = zipfile.ZipFile(path)
    shp = [n for n in z.namelist() if n.endswith('.shp')][0]
    base = shp[:-4]
    return shapefile.Reader(shp=io.BytesIO(z.read(shp)),
                            dbf=io.BytesIO(z.read(base + '.dbf')),
                            shx=io.BytesIO(z.read(base + '.shx')))


class Layers:
    """Lazy per-state index of Census units, keyed by normalized name."""

    def __init__(self):
        self._county = None      # fips -> list of unit dicts
        self._aiannh = None
        self._state = {}         # (fips, layer) -> {normname: [units]}

    @staticmethod
    def _units(reader, fields):
        out = []
        for sr in reader.iterShapeRecords():
            rec = dict(zip(fields, sr.record))
            rec['_geom'] = shape(sr.shape.__geo_interface__)
            out.append(rec)
        return out

    def county(self, fips):
        if self._county is None:
            r = _read_zip(_fetch(f'cb_{CB_YEAR}_us_county_500k.zip'))
            fields = [f[0] for f in r.fields[1:]]
            self._county = defaultdict(list)
            for u in self._units(r, fields):
                self._county[u['STATEFP']].append(u)
        return self._county.get(fips, [])

    def aiannh(self, fips):
        if self._aiannh is None:
            r = _read_zip(_fetch(f'cb_{CB_YEAR}_us_aiannh_500k.zip'))
            fields = [f[0] for f in r.fields[1:]]
            self._aiannh = self._units(r, fields)
        # AIANNH areas are national (no STATEFP); filter by the state's counties
        cg = unary_union([c['_geom'] for c in self.county(fips)])
        return [u for u in self._aiannh if u['_geom'].intersects(cg)]

    def layer(self, fips, layer):
        key = (fips, layer)
        if key not in self._state:
            if layer == 'county':
                units = self.county(fips)
            elif layer == 'aiannh':
                units = self.aiannh(fips)
            else:
                r = _read_zip(_fetch(f'cb_{CB_YEAR}_{fips}_{layer}_500k.zip'))
                fields = [f[0] for f in r.fields[1:]]
                units = self._units(r, fields)
            idx = defaultdict(list)
            for u in units:
                idx[norm(u['NAME'])].append(u)
                if layer == 'aiannh':
                    short = re.sub(r'\s+(Reservation|Indian Reservation|Off-Reservation Trust Land|Trust Land|Rancheria|Pueblo|Colony|Community|Indian Community|Nation)\b.*$', '', u['NAME'], flags=re.I)
                    if norm(short) != norm(u['NAME']):
                        idx[norm(short)].append(u)
            self._state[key] = idx
        return self._state[key]

    def find(self, fips, layer, name, county=None):
        """Return (matches, tried_layers). matches is a list of unit dicts."""
        layers = ['place', 'cousub'] if layer == 'auto' else [layer]
        tried = []
        for ly in layers:
            tried.append(ly)
            cands = list(self.layer(fips, ly).get(norm(name), []))
            if not cands:
                continue
            if county:
                cn = norm(county)
                cty = [c for c in self.county(fips) if norm(c['NAME']) == cn]
                if ly == 'cousub':
                    cands = [c for c in cands if any(c['COUNTYFP'] == k['COUNTYFP'] for k in cty)]
                elif cty:
                    cg = unary_union([k['_geom'] for k in cty])
                    cands = [c for c in cands if c['_geom'].representative_point().within(cg)]
            if ly == 'place' and len(cands) > 1:
                inc = [c for c in cands if c.get('LSAD') not in CDP_LSADS]
                if len(inc) == 1:
                    cands = inc
            if cands:
                return cands, tried
        return [], tried


# ── Geometry helpers ──────────────────────────────────────────────────────

def circle(lat, lon, radius_km, n=72):
    dlat = radius_km / 111.32
    dlon = radius_km / (111.32 * math.cos(math.radians(lat)))
    pts = [(lon + dlon * math.cos(2 * math.pi * i / n),
            lat + dlat * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return Polygon(pts)


def area_km2(geom):
    # equal-area-ish approximation adequate for sanity checks
    c = geom.centroid
    kx = 111.32 * math.cos(math.radians(c.y))
    ky = 111.32
    from shapely.affinity import scale
    return scale(geom, xfact=kx, yfact=ky, origin=(0, 0)).area


def round_geom(geom, nd=5):
    return json.loads(json.dumps(mapping(geom)), parse_float=lambda x: round(float(x), nd))


def clean(geom):
    if not geom.is_valid:
        geom = geom.buffer(0)
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        return geom
    # GeometryCollection etc: keep polygonal parts
    polys = [g for g in getattr(geom, 'geoms', []) if isinstance(g, (Polygon, MultiPolygon))]
    return unary_union(polys) if polys else geom


# ── Resolution ────────────────────────────────────────────────────────────

def load_pins(state):
    pins = {}
    p = os.path.join(ROOT, 'ODT_Inventory.csv')
    with open(p, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['State'] != state:
                continue
            try:
                pins[r['Name']] = (float(r['Latitude']), float(r['Longitude']), r['Region/Service Area'])
            except ValueError:
                pins[r['Name']] = (None, None, r['Region/Service Area'])
    return pins


SQMI = re.compile(r'(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(?:\d+(?:\.\d+)?)?\s*(?:sq(?:uare)?\.?\s*mi|sq\.?\s*mile|square mile)', re.I)
RADIUS = re.compile(r'(\d+(?:\.\d+)?)\s*-?\s*mile\s+radius', re.I)


def resolve_one(spec, layers, pins, updated):
    name = spec['name']
    st = spec['state']
    fips = STATE_FIPS[st]
    bt = spec.get('boundary_type')
    qa = {'name': name, 'state': st, 'boundary_type': bt, 'status': 'ok', 'issues': []}
    if name not in pins:
        qa['issues'].append(f'name not in CSV for {st}: {name!r}')
    if spec.get('skip') or bt in (None, 'none', 'needs_research'):
        qa['status'] = 'skipped'
        qa['issues'].append(spec.get('note', 'no boundary spec'))
        return None, qa
    if bt not in BOUNDARY_TYPES:
        qa['status'] = 'error'
        qa['issues'].append(f'unknown boundary_type {bt!r}')
        return None, qa

    parts, matched_units = [], []

    def resolve_units(units):
        out = []
        for u in units:
            layer = u.get('layer', 'auto')
            cands, tried = layers.find(fips, layer, u['name'], u.get('county'))
            if not cands:
                qa['issues'].append(f'unit not found: {u["name"]!r} (layers tried: {tried})')
                continue
            if len(cands) > 1:
                desc = ', '.join(f"{c.get('NAMELSAD', c['NAME'])}[{c['GEOID']}]" for c in cands)
                qa['issues'].append(f'ambiguous unit {u["name"]!r}: {desc} — add "county" hint or pick GEOID')
                continue
            out.append(cands[0])
        return out

    if bt == 'zone_approx':
        blist = spec.get('buffers') or ([spec['buffer']] if spec.get('buffer') else [{}])
        for b in blist:
            lat, lon = b.get('lat'), b.get('lon')
            label = None
            if b.get('center_unit'):
                cu = resolve_units([b['center_unit']])
                if not cu:
                    continue
                c = cu[0]['_geom'].representative_point()
                lat, lon = c.y, c.x
                label = cu[0].get('NAMELSAD') or cu[0]['NAME']
            if lat is None or lon is None:
                lat, lon = pins.get(name, (None, None, ''))[:2]
            r = b.get('radius_km')
            if lat is None or r is None:
                qa['issues'].append('zone_approx buffer needs radius_km and a lat/lon, center_unit, or CSV pin')
                continue
            parts.append(circle(lat, lon, r))
            matched_units.append(f'buffer {r} km @ ' + (label or f'{lat:.4f},{lon:.4f}'))
        if not parts:
            qa['status'] = 'error'
            return None, qa
        if spec.get('clip_to_units') and spec.get('units'):
            clip_units = resolve_units(spec['units'])
            if clip_units:
                cg = unary_union([u['_geom'] for u in clip_units])
                parts = [unary_union(parts).intersection(cg)]
                matched_units.append('clipped to ' + '; '.join(u.get('NAMELSAD') or u['NAME'] for u in clip_units))
    elif bt == 'census_tracts':
        idx = layers.layer(fips, 'tract')
        want = set(spec.get('tract_geoids') or [])
        if not want:
            qa['status'] = 'error'
            qa['issues'].append('census_tracts needs tract_geoids')
            return None, qa
        found = {u['GEOID']: u for us in idx.values() for u in us if u['GEOID'] in want}
        missing = sorted(want - set(found))
        if missing:
            qa['issues'].append(f'tract GEOIDs not found: {missing}')
        parts.extend(u['_geom'] for u in found.values())
        matched_units.extend(sorted(found))
    else:
        for c in resolve_units(spec.get('units') or []):
            parts.append(c['_geom'])
            matched_units.append(c.get('NAMELSAD') or c['NAME'])
        if not spec.get('units'):
            qa['issues'].append('no units listed')
        dil = spec.get('dilate_km')
        if bt == 'buffered' and not dil:
            qa['issues'].append('boundary_type buffered needs dilate_km')
        if dil and parts:
            lat = unary_union(parts).centroid.y
            # buffer in degrees, corrected for longitude shrink: scale, buffer, unscale
            from shapely.affinity import scale
            kx = math.cos(math.radians(lat))
            g = scale(unary_union(parts), xfact=kx, yfact=1, origin=(0, 0))
            g = g.buffer(dil / 111.32, resolution=8)
            parts = [scale(g, xfact=1 / kx, yfact=1, origin=(0, 0))]
            matched_units.append(f'+{dil} km radius')

    if not parts:
        qa['status'] = 'error'
        return None, qa
    if any('not found' in i or 'ambiguous' in i for i in qa['issues']):
        qa['status'] = 'partial'

    geom = clean(unary_union(parts))
    qa['area_km2'] = round(area_km2(geom), 1)
    qa['units'] = matched_units

    # pin check
    lat, lon, area_text = pins.get(name, (None, None, ''))
    if lat is not None:
        pt = Point(lon, lat)
        if not geom.contains(pt):
            d = geom.distance(pt) * 111.32
            qa['pin_outside_km'] = round(d, 1)
            if d > 3:
                qa['issues'].append(f'CSV pin is {d:.1f} km outside the polygon')
            if d > 15 and qa['status'] == 'ok':
                qa['status'] = 'suspect'
    # stated-size check
    m = SQMI.search(area_text or '')
    if m:
        stated = float(m.group(1)) * 2.58999
        qa['stated_km2'] = round(stated, 1)
        ratio = qa['area_km2'] / stated if stated else None
        if ratio and (ratio > 4 or ratio < 0.25):
            qa['issues'].append(f'polygon {qa["area_km2"]} km2 vs stated ~{stated:.0f} km2 (x{ratio:.1f})')
            if qa['status'] == 'ok':
                qa['status'] = 'suspect'

    src, fid = BOUNDARY_TYPES[bt]
    props = {
        'name': name,
        'boundary_type': bt,
        'source': spec.get('source') or src,
        'fidelity': spec.get('fidelity') or fid,
        'updated': updated,
        'units': '; '.join(matched_units),
    }
    if spec.get('note'):
        props['note'] = spec['note']
    if spec.get('confidence') is not None:
        props['confidence'] = spec['confidence']
    feat = {'type': 'Feature', 'properties': props, 'geometry': round_geom(geom)}
    return feat, qa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--specs', required=True, nargs='+')
    ap.add_argument('--out')
    ap.add_argument('--qa')
    ap.add_argument('--merge', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--updated', default=None, help='YYYY-MM stamp; default = today')
    a = ap.parse_args()

    from datetime import date
    updated = a.updated or date.today().strftime('%Y-%m')

    specs = []
    for p in a.specs:
        with open(p, encoding='utf-8') as f:
            data = json.load(f)
        specs.extend(data if isinstance(data, list) else data.get('specs', []))
    states = {s['state'] for s in specs}
    if len(states) != 1:
        sys.exit(f'specs must cover exactly one state, got {sorted(states)}')
    state = states.pop()
    if not a.out and not a.dry_run:
        a.out = os.path.join(ROOT, 'data', 'boundaries', f'{state}.geojson')

    layers = Layers()
    pins = load_pins(state)
    feats, report = [], []
    for s in specs:
        s.setdefault('state', state)
        try:
            feat, qa = resolve_one(s, layers, pins, updated)
        except Exception as e:  # keep going; report
            feat, qa = None, {'name': s.get('name'), 'state': state, 'status': 'error',
                              'issues': [f'exception: {e!r}']}
        report.append(qa)
        if feat:
            feats.append(feat)

    if a.merge and a.out and os.path.exists(a.out):
        with open(a.out, encoding='utf-8') as f:
            existing = json.load(f).get('features', [])
        spec_names = {s['name'] for s in specs}
        keep = [f for f in existing if f['properties']['name'] not in spec_names]
        feats = keep + feats
    feats.sort(key=lambda f: f['properties']['name'].lower())

    # summary
    counts = defaultdict(int)
    for q in report:
        counts[q['status']] += 1
    print(f'{state}: {len(feats)} features written' if not a.dry_run else f'{state}: dry run, {len(feats)} features')
    print('  status:', dict(counts))
    for q in report:
        if q['issues']:
            print(f'  [{q["status"]}] {q["name"]}: ' + ' | '.join(q['issues']))
    if not a.dry_run:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump({'type': 'FeatureCollection', 'features': feats}, f, separators=(',', ':'))
        print(f'  wrote {a.out} ({os.path.getsize(a.out)//1024} KB)')
    if a.qa:
        with open(a.qa, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=1)
        print(f'  wrote {a.qa}')
    coverage = os.path.join(ROOT, 'ODT_Inventory.csv')
    print(f'  CSV rows for {state}: {len(pins)}; with boundary: {len(feats)}')


if __name__ == '__main__':
    main()
