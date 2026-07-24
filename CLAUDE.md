# On-Demand Transit Database

A research inventory of microtransit and demand-response transit deployments
across the US, published as a static dashboard via GitHub Pages.

## What's here

- `ODT_Inventory.csv` — source of truth. One row per system, 20 columns.
- `index.html` — single-file dashboard (Leaflet map, card view, analytics,
  reference tab). Fetches `data/systems.json` and `data/boundaries/*.geojson`
  at runtime — it does not read the CSV directly.
- `scripts/build.py` — reads the CSV, validates it, writes `data/systems.json`,
  `summary.csv`, and `data/boundaries/_index.json`.
- `concerns.csv` — running log of data-quality issues: vendor errors,
  paratransit reclassifications, status discrepancies, dedup notes. Treat this
  as the changelog for anything questionable in the CSV. Add to it, don't
  just fix things silently.
- `legend.csv` — field definitions and valid values. If you're unsure what a
  column means or what values are valid, check here before guessing.
- `source/` — legacy spreadsheet snapshot, kept for provenance only. The CSV
  is authoritative; don't pull data from `source/` to override it.

## Build workflow

```
# edit ODT_Inventory.csv
python3 scripts/build.py          # validates + writes data/systems.json etc.
python3 scripts/build.py --check  # validate only, no files written
git add -A && git commit -m "..." && git push
```

Pages redeploys automatically on push to main. `data/systems.json` and
`data/boundaries/*.geojson` are build *outputs* but must stay committed —
the dashboard fetches them at runtime, they're not intermediate artifacts.

## Scope rules (canonical version lives in index.html's Reference tab)

Quick summary — check the Reference tab in the live dashboard for the full
version before making a judgment call on an edge case:
- Same-day app/phone booking with no fixed schedule → included.
- Demand-response is included if it's flagged with an "Advance" scheduling
  window and open to the general public.
- Excluded: 24+ hour advance-only booking, private/employer/campus-only
  shuttles, permanently discontinued services.
- Planned/pilot services are includable if vendor and funding are confirmed.
- Excluded: strictly paratransit — services restricted to eligibility-certified
  riders (ADA/senior/disability). These are out of scope even though they are
  demand-responsive; the inventory covers general-public on-demand transit only.
  A general-public service that merely prioritizes seniors/disabled riders is
  still included. (Scope change 2026-07: paratransit was previously included as
  its own System Type; all 170 such rows were removed and the type retired.)

## Research heuristics (learned the hard way, don't rediscover)

- **State DOT program-evaluation or toolkit documents are the best source**
  for structured data (vehicle capacity, fleet composition, service area
  size) — much better than press releases. Example: Virginia's DRPT "Rural
  Microtransit Suitability Checklist and Implementation Toolkit" had real
  vehicle specs for two FTA-funded pilots in one PDF; press coverage of the
  same systems had none.
- **A named FTA grant does not imply extractable data exists.** Wilson RIDE
  (NC) has a well-documented AIM grant; exhaustive searching still found no
  vehicle capacity number anywhere. Grant announcements describe funding and
  program goals, not equipment specs.
- **Systems sharing an operator often share undocumented specs** — if one
  system in a cluster (same operator, same regional program) has data the
  others lack, check whether it's actually a shared fleet spec before
  concluding it needs separate research per system.
- Passenger-capacity and service-area-size data is sparse dataset-wide
  (~5% of rows as of last check). Don't build a UI feature around either
  field without checking current coverage first — it moves as the CSV is
  edited.

## Working conventions

- Data enrichment (filling in fields on existing rows) and system discovery
  (finding new systems to add) are different modes of work — don't mix them
  in one sitting without saying which one you're doing.
- Don't silently overwrite a value that conflicts with a newly found source;
  log the discrepancy (in `concerns.csv` or a commit message) instead,
  especially for numbers that might be measuring different things (e.g. a
  core zone vs. a full service zone).
- See `NOTES.md` for open threads and pending items not yet applied to the
  CSV.
