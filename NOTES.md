# Notes — pending items, open threads

Working scratchpad for things that came up in research/chat but haven't been
applied to the CSV yet, or aren't resolved. Clear items out once they're
actually committed — this file should reflect *current* open items, not be
a permanent log (that's what `concerns.csv` and git history are for).

## Pending CSV updates (found, not yet applied)

- **Bay Transit Express (VA)** — `Fleet` currently "Not specified". Found: 3
  vehicles — Ford E450, Ford Transit 350, Ford Transit van (6 seats). Source:
  Virginia DRPT "Rural Microtransit Suitability Checklist and Implementation
  Toolkit."
- **METGo! (VA)** — `Fleet` currently "Not specified". Found: 4 Ford vans,
  each 7-ambulatory-passenger capacity. Same DRPT source as above.
  - Note: that source also states the service area is "~15 sq mi"; the CSV
    currently has "~11 sq mi core." Possibly core-zone vs. full-zone rather
    than a real conflict — don't overwrite silently, note both if updating.

## Dead ends (don't re-research)

- **El Cajon Microtransit (CA)** — no public vehicle capacity number exists.
  Checked city site, Via press release, three news outlets. All describe
  fleet only as "one small electric vehicle," no seat count anywhere.
- **Mid-City GO (CA)** — same result. Fleet described qualitatively ("a
  large van and a handicap accessible vehicle"), no seat count published.

## Open threads

- **NCDOT toolkit check** — Virginia's DRPT publishes a program-evaluation
  document that covers multiple systems at once (see CLAUDE.md). NC already
  leads the dataset in system count, partly attributed to NCDOT programs
  (per the dashboard's own analytics note). Worth checking whether NCDOT has
  published something similar — could both enrich existing NC rows and
  surface new systems in one pass.
- **FTA AIM/IMI award lists as a discovery source** — these are public and
  might surface systems not yet in the inventory, not just enrich existing
  ones. Not yet systematically checked.
- **Vendor data quality on supplemental CA/CO entries** — flagged in
  `concerns.csv` as unverified (4/4 checked were wrong). If enrichment work
  touches these rows, don't trust the `Technology Vendor` field without
  independent verification.

## State expansion sweep — follow-ups (added 2026-07-23)

Sweep added 168 systems across the 27 previously-uncovered jurisdictions,
bringing coverage to all 50 states + DC. Full per-row detail is in
`concerns.csv` (168 `Data Gap (new-state research)` rows, one per added
system — every added row has at least one unverified field). Only the
*open decisions* are listed here.

### Thin states — likely under-researched, not genuinely sparse

Each was capped at ~8 web fetches per research agent, which is too tight for
states whose systems are dispersed rather than clustered in one metro. Worth
a dedicated higher-recall discovery pass (more fetches + more search angles,
e.g. state DOT §5311 rural provider lists and regional transit districts):

- **NM (1 system)** — only ABQ RIDE Connect. Almost certainly missing Santa Fe,
  Las Cruces, and the regional RTDs.
- **MS (1 system)** — only Coast Transit paratransit.
- **ND (2 systems)** — likely missing Bismarck CAT and Grand Forks CAT.
- **TN (5 systems)** — moderate, but light for the state's size.

### Rows added on inference, not direct verification

All four are real agencies, but the source site blocked automated fetches, so
no field is source-confirmed. Re-verify against a live source before relying
on these rows:

- **RTC Paratransit (NV)** — rtcsnv.com returned 403 twice.
- **CARTA OnDemand (SC)** — site 502, cited article 403, sub-page 404.
- **KRT Paratransit (WV)** — *name is a placeholder*; "Care-A-Van" branding
  appears only in secondary sources and could not be confirmed.
- **TTA Paratransit (WV)** — *name is a placeholder*; tta-wv.com is bot-gated,
  and Wikipedia lists "paratransit" only generically.

### Scope questions needing a call

- **Transport DC (DC)** — it's a DACL taxi *fare subsidy* for MetroAccess-certified
  riders, not an agency-operated demand-response service. Does a fare-subsidy
  program belong in the inventory as a distinct system? Its `Scheduling Window`
  was also unpublished and inferred as "Same-day."
- **Access AT — listed under both NH and VT** — Advance Transit is a genuinely
  bi-state Upper Valley service, recorded once per state (consistent with the
  existing RideKC precedent). Real, but **don't double-count** it in totals.
- **GET My Ride (NV)** — `Scheduling Window` unpublished; set to "Advance" per
  rural dial-a-ride convention. Inclusion is unaffected either way, but verify
  against the rider handbook.
- **Two OK rows** (Red River Public Transportation Service, Southwest Transit)
  have **approximate county-derived centroids**, not sourced coordinates.
