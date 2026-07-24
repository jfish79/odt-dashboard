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

## Full 50-state deep sweep — wave 2 follow-ups (2026-07-24)

Wave 2 (TN/OH/LA, WY/WA/AL, IN/MO/NE, VT/MN/PA, VA/NJ/ME, SC/IA/MT) took the
CSV from 478 to 597 rows. Build validates clean, all 51 jurisdictions still
covered. 11 states remain for wave 3: AZ, CA, FL, CT, NC, CO, OK, IL, MA, TX,
GA (roughly ordered by current count, largest last). Systemic/high-value
items surfaced this wave:

- **HIGH PRIORITY eligibility conflicts** (operator's own pages disagree on
  who can ride — needs a human call, not another automated fetch): **MO
  CGCTA** (Cape Girardeau), **NE Fremont Transit Program**, **LA Plaquemines
  Parish Transit**, **TN ETHRA Public Transit**, **MT Fort Belknap Transit**
  and **Northern Cheyenne Transit** (weak-sourced, not just ambiguous —
  eligibility inferred by analogy to other MT tribal systems, not
  independently confirmed).
- **CARTA OnDemand (SC) resolved** — this was an old open item (prior
  passes couldn't reach ridecarta.com at all, 502/403/404). Now confirmed
  directly: it's senior 60+/Tel-A-Ride-only, correctly out of scope. Closes
  that NOTES.md thread from the original state-expansion sweep.
- **Large provider directories only partially sampled** — good targets for
  a dedicated future pass rather than general rotation: **AL** (~26 more
  ALDOT 5311 rural county providers beyond the 4 added, per ALTRANS'
  directory), **MO** (MoDOT rural 5311 subrecipients beyond OATS/SMTS not
  enumerated one-by-one), **NE** (~49 rural agencies statewide per NDOT,
  only a subset checked), **OH** (Athens, Licking, Marion counties
  unchecked).
- **Confirm-soon pilots**: LA's Lafayette Transit System microtransit pilot
  (funding confirmed, vendor not yet, targeting Jul/Aug 2026 launch); ME's
  RTP Harrison pilot ($99,576 grant announced Sep 2025, launch unconfirmed).
- Minor scope-classification flags for a human to weigh in on: **IA
  CorridorRides** (general public except within 3/4 mile of fixed routes in
  Linn/Johnson counties, which is ADA-restricted there — mixed eligibility
  by geography); **PA LANtaFlex** (typed Demand-Response/Advance here vs.
  PennDOT's own "Microtransit" grouping); **IN MCPT** (typed
  Microtransit/Same-day despite phone-only booking).
- **WY DoGo Public Transportation** (Douglas/Converse County) — looked
  promising (general public, advance booking) but only sourced via a Yellow
  Pages aggregator, never the operator directly; deliberately left out per
  project sourcing rules, worth a direct follow-up look.

## Full 50-state deep sweep — wave 1 follow-ups (2026-07-24)

Wave 1 (KY/MD/MS/WV done earlier, then SD/NY/UT, AK/DE/HI, ID/ND/NM, RI/DC/WI,
OR/MI/AR, KS/NH/NV in parallel) took the CSV from 397 to 478 rows. Build
validates clean. Per-row unverified fields are logged in `concerns.csv` as
usual; the items below are the *systemic* ones worth surfacing here:

- **WI shared-ride taxi program (Wis. Stat. 85.20) is a large untapped
  source.** Only 5 of a plausibly 20-40+ eligible WI cities were checked
  (Fond du Lac, Wisconsin Rapids, Waupun, Medford, Viroqua-Westby). Brown
  Cab Service and Passenger Transit Inc. alone list ~10 more WI cities
  under the same model, not yet individually verified. Worth a dedicated
  WI-only follow-up pass rather than folding into general rotation.
- **Several states hit a shared WebSearch budget cap mid-sweep** (parallel
  sub-forks within one agent draw from the same quota) and are confirmed
  incomplete, not exhaustively covered: **NM** (Rio Metro, Farmington,
  Silver City, Gallup, Grants/Cibola, Roswell/Pecos Trails, non-Navajo
  tribal transit unchecked — treat NM's count as a floor), **NY** (~15-18
  rural counties across the North Country, Finger Lakes, Mohawk Valley,
  Central NY unchecked), **NH** (Concord Area Transit, Advance Transit
  non-ADA options unchecked), **ID** (Kootenai County/Coeur d'Alene
  unchecked), **ND** (~30 other §5311 rural subrecipients unchecked), **OR**
  (Coos, Douglas, Josephine, Umatilla counties unchecked), **MI** (~10 of
  MDOT's ~15 rural "Advancing Rural Mobility" providers unchecked).
- **DC's old "Transport DC" concern entries are now stale/orphaned** — that
  system was already correctly removed in the paratransit purge before
  this wave started; the older concerns.csv rows referencing it as a live
  scope question were left in place per convention but no longer apply.
- Notable borderline single-row calls needing a human look (full detail in
  concerns.csv): HI's MEO Rural Shopping Shuttle (two county sources give
  conflicting eligibility language — needs a phone call, 808-877-7651);
  ND's Standing Rock Public Transit (eligibility sourced only from a
  secondary aggregator); MI's Charlevoix County Transit (no eligibility
  language found either way); OR's Sunset Empire microtransit pilot
  (marked Pilot - Ended but language is ambiguous about relaunch); NY's
  Circuit Rockaways (grant-funding may have lapsed, current status
  unconfirmed) and RTS On Demand (conflicting vendor signals — Via-style
  URL pattern vs. a TRC/Pingo press release for the same rollout).

## Paratransit scope change — cleanup follow-ups (2026-07-24)

Uncommitted in the working tree as of 2026-07-24: all 170 `Paratransit`-typed
rows removed from the CSV (see CLAUDE.md scope rules for the decision). Build
re-run clean. Two things this broke, both open:

- **WV dropped to zero systems** — its only 3 rows were all Paratransit.
  Discovery research in progress to find real candidates (2026-07-24); a
  genuine zero is an acceptable outcome, not a bug to force-fix.
- **index.html Reference tab is now stale** — still documents "Paratransit"
  as a live System Type (definitions grid, filter dropdown option, and the
  "Paratransit reclassification" data-quality note don't mention the later
  full retirement). `legend.csv` also still lists Paratransit under
  Geographic Context Values (a pre-existing misplacement, unrelated to this
  change). Needs a documentation pass before committing.
- Footer stat "241 systems across 24 states" (index.html) is stale
  independent of this change — needs updating regardless.

## Full 50-state review — scope decision (2026-07-24)

Only 3 states (KY, MD, MS) have had the high-recall "deep sweep" treatment
(deep sweep batch 1, commit c9db30d) since the original low-recall state
expansion sweep (batches 1-9, ~8 fetches/agent cap). The paratransit purge
above additionally thinned many states that weren't previously flagged —
11 states/DC now sit at exactly 1 system, 9 more at 2.

Decision: **don't limit the re-pass to currently-thin states.** A low count
isn't itself evidence a state needs more research (some states may
genuinely have few qualifying systems), and a high count doesn't prove a
state is *fully* covered either — the only way to know is to actually run
the deep-sweep method (read what's in the CSV per state, search state DOT
§5311/5310 provider lists for what's missing) against every state, not just
the ones that look sparse. Plan: batch 2+ of the deep sweep should cover
all 50 states + DC systematically, not by first flagging "thin" ones.

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
