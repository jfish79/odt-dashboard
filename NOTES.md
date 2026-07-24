# Notes — pending items, open threads

Working scratchpad for things that came up in research/chat but haven't been
applied to the CSV yet, or aren't resolved. Clear items out once they're
actually committed — this file should reflect *current* open items, not be
a permanent log (that's what `concerns.csv` and git history are for).

## Full 50-state deep sweep — wave 3 follow-ups (2026-07-24)

Wave 3 (AZ/CA/FL, CT/NC/CO, OK/IL/MA, TX/GA — 5 research passes; TX/GA
required one retry after an API failure) covered the last 11 states not yet
given the high-recall deep-sweep treatment. Wave 3 is now **complete**: took
the CSV from 597 to 724 rows (128 adds, 1 rename/update, 1 removal). Every
added row has a `Data Gap (new-state research)` entry in `concerns.csv`;
only the systemic/borderline items are listed here.

- **TX and GA were both dramatically under-covered going in** (11 rows
  each) — the deep sweep found 34 new TX systems and 18 new GA systems,
  nearly tripling/doubling their counts respectively. GA's research agent
  also surfaced **~40 additional named county systems** from the Georgia
  Transit Association's statewide roster that plausibly fit the same
  general-public rural demand-response pattern but were NOT individually
  verified this pass (listed by name in the agent's report, not
  reproduced here) — good candidate for a dedicated targeted follow-up
  rather than a broad re-sweep: Wilcox, Cook, Americus, Pierce, Haralson,
  Taylor, Cedartown, Murray, Habersham, Bleckley, Conyers, Taliaferro,
  River Valley Regional Transit (16-county), Lumpkin, Paulding, Dawson,
  Douglas/Coffee, Clay, Heard, Glascock, Greene, Hart, Banks, Wilkinson,
  Walker, Lincoln, Jefferson, Morgan, Macon, Bryan, Catoosa, Crawford,
  Hancock (name suggests possible senior-restriction, check eligibility),
  Talbot, McDuffie, Tift, Dade, Dooly, Wilkes, Burke counties.
- **TX 24-hour-advance policy question, affects ~7 systems**: several
  added TX rural systems (Panhandle Transit, PTS, Valley Metro/LRGVDC,
  Alamo Regional Transit, GoBus/ETCOG, both TRAX systems, HOTCOG) are
  24-hour-advance-minimum general-public demand-response. The research
  agent read CLAUDE.md's "24+ hour advance-only booking" exclusion as
  targeting paratransit-only services specifically (per the fuller
  Reference-tab wording), not general-public advance-window service, and
  included these on that reading. Worth confirming this as an explicit
  single policy call rather than per-row, since it recurs constantly in
  rural demand-response research.
- **TX name collision, handled**: two unrelated systems are both branded
  "TRAX" — one run by Ark-Tex COG (NE Texas), one by Permian Basin RTD
  (West Texas). Both added, disambiguated in the CSV `Name` field as
  "TRAX (Ark-Tex COG)" / "TRAX (Permian Basin RTD)".
- **TX TNC-subsidy programs, category-level scope question not yet
  resolved**: Cedar Park Microtransit Pilot, Uber Kyle ($3.14 flat fare),
  and Pfetch a Ride (Pflugerville) are all subsidized-TNC-voucher programs
  (city pays down an Uber/Lyft-style fare rather than running its own
  fleet/app). None added pending one category-level ruling on whether
  fare-subsidy-on-a-commercial-TNC counts as an in-scope "system" the way
  a city-run microtransit app does — resolving it once would settle all
  three at once plus any future finds of the same model.
- **TX borderline, not added**: CARR/City and Rural Rides (Central Texas
  RTD) — primary purpose is job/training access, general public served
  only "space-available," reads as not truly general-public; SaGO (San
  Antonio) — free electric shuttle but privately/ad-funded, not a public
  transit agency, scope-fit unresolved; Gulf Coast Transit District "Ride
  the Wave" (Galveston/League City/Texas City/Brazoria) — partial detail
  only, worth a direct follow-up; CVTGoNow (Colorado Valley Transit) — launch
  announcement removed from site, phone-arranged fare card argues against
  same-day app model; BTD Micro-Transit (Liberty/Dayton/Ames) — funding not
  confirmed, fails pilot-inclusion rule; El Aguila Rural Transit (Webb
  County) — booking window never confirmed; SETRPC — scheduling window
  unresolved; Plano Rides, Collin County Transit/McKinney UTD, GoGeo
  (Georgetown), Cletran — all read as 65+/disabled/income-gated or have
  conflicting eligibility sources, excluded on current information.
- **GA borderline, not added**: Statesboro Area Transit (SAT) — deviated
  fixed-route requiring pickup within 1/4 mile of an existing route, needs
  a human call on whether that counts as demand-response under this
  database's fixed-schedule exclusion; Troup Transit and Warner Robins
  Transit — general-public eligibility not fully confirmed in a primary
  source (Warner Robins also has an unusual private-operator model).
- **GA existing-row updates flagged, not new rows**: CobbLinc Go's North
  Cobb/Acworth-Kennesaw expansion ($3.84M funding) and MARTA Reach's
  expansion to Alpharetta/North Fulton CID both look like additional zones
  of already-listed systems (CobbLinc Go, MARTA Reach) rather than new
  systems — their `Region/Service Area` fields should be updated once
  confirmed, not duplicated as new rows.
- **REAL Flash (TX) added as a separate row from existing "REAL Microtransit
  (Rockport/Fulton)"** — same operator/brand (Rural Economic Assistance
  League), disjoint zone (Beeville/Alice/Rancho Alegre vs. Rockport/Fulton).
  Flagged in concerns.csv for a human merge-vs-keep-separate decision,
  following the same open question as DCTA GoZone/GoZone Frisco.
- **CRIS Rural Transit (IL) removed** — reported dissolved 2026-01-02 after
  IDOT froze funding over an accounting issue; not independently
  reconfirmed beyond the research pass that surfaced it. See `concerns.csv`
  (`Status Change`). Re-add if service has actually resumed.
- **WeRIDE Peoria (AZ) renamed/updated to "Peoria Transit On-Demand"** —
  City of Peoria's WeRIDE pilot ended and was replaced April 2026;
  vendor/funding for the new service unconfirmed.
- **Website URL / Ridership Notes column swap — fixed dataset-wide
  (2026-07-24)**. Turned out to be much bigger than the single WeRIDE
  Peoria row: 123 rows across AZ/CT/FL/GA/IL/MA had Website URL and
  Ridership/Performance Notes swapped, not limited to the "New addition
  on July 1/July 7" batches (83 of the 123 have a blank Source field).
  Fixed mechanically (no research needed). The `Fleet` column on many of
  these same rows still holds a general description rather than real
  fleet specs — left untouched since some mix in genuine fleet mentions;
  still worth a closer human pass per `concerns.csv`.
- **CA appears significantly under-built relative to its real microtransit
  footprint** — 25 new candidates found in one pass (vs. 3-9 for other wave
  3 states), and the research agent flagged this explicitly. Caltrans'
  §5311/§5310 subrecipient roster and the CalACT member directory were
  never successfully pulled as itemized lists (only program-description
  pages) — flagged as the single highest-value next source for CA
  specifically.
- **NC's NCDOT MEE-NC grant cohort — resolved (2026-07-24)**. Full
  program name is "Mobility for Everyone, Everywhere in NC" (MEE NC), an
  11-community cohort. Follow-up research confirmed all 11 already
  correspond to an existing CSV row (Kerr Area Regional Transit/KARTS,
  Johnston Quick Ride/JCATS, McDowell Express, Go Randolph/RCATS, ACTA
  Microtransit, Wilson RIDE, Local Link, Buzzline, RideMICRO/Castle Hayne,
  Salisbury Connect, Tar River Transit RGP) — zero new rows needed. Along
  the way: enriched the existing **Buzzline** row with newly-available
  confirmed data (launch Nov 12 2025, $5 fare, weekday-from-6am hours,
  more specific MEE-NC funding source). **Wilson RIDE**'s funding source
  may be incomplete (original AIM grant vs. MEE-NC continuation funding)
  but wasn't confirmed well enough to edit. **Tar River Transit/Rocky
  Mount** is MEE-NC-funded but has NOT launched a distinct same-day
  on-demand product yet (existing row is the legacy advance-booking RGP
  service, unaffected) — don't add a second Tar River row without a
  direct launch confirmation.
- **"GoRaleigh MicroLink" vs. "Go Wake Forest" (NC) — resolved,
  genuinely distinct**. Confirmed different operators (City of Raleigh
  vs. Town of Wake Forest), vendors, fares, hours, and fleets — GoRaleigh
  MicroLink's Rolesville zone only connects into Wake Forest as a
  destination, while Go Wake Forest is the town's own town-wide
  Via-operated system (replaced the old "Wake Forest Loop" fixed route,
  Oct 2024). Added "Go Wake Forest" as a new row.
- **Douglas County, CO — "Link on Demand" service-area update, not a new
  row**: the existing Lone Tree row's Via-powered service has since
  expanded into Parker (Apr 2026) and Castle Rock (launching Jul 2026,
  $1.99M contract). Not added as new rows; existing row's `Region/Service
  Area` field should be updated once confirmed.
- **Mountain Valley Transit (CO)** — San Luis Valley routes reportedly
  paused since April 2026 due to funding cuts. Not added (status too
  uncertain to confirm as currently operating); re-check before adding.
- **Broken Arrow Transit microtransit pilot (OK) — resolved, same system**.
  Confirmed MTTA rebranded to "MetroLink Tulsa" in 2024 (same legal
  entity); Broken Arrow's pilot runs on the same GoPass app under that
  agency. Folded Broken Arrow's confirmed zone details (20 sq mi, $500K
  CMAQ grant, 4 Mustang Mach-E + 1 accessible van, zone-specific fare/
  hours) into the existing "MTTA On-Demand Microtransit (GoPass App)"
  row rather than creating a duplicate.
- **CT dedup risks — resolved, both genuinely distinct**. "WRTD
  Dial-A-Ride" (9-town district, Ecolane, Advance window, $3.00) is a
  separate legacy product from same-day "WRTD Link" (2-town, Via) —
  added as a new row. "River Valley Transit Dial-A-Ride" (16-town
  Estuary district, Ecolane, Advance window, $3.50, curb-to-curb ¾-mile-
  beyond-fixed-routes model) is likewise a separate legacy product from
  the operator's same-day TransLoc-based branded zones (XtraMile x3,
  River HOP) — added as a new row. Both pair with a separate official
  ADA Paratransit rider's guide at the same operator, but the Dial-A-Ride
  products themselves are confirmed general-public/no-application-required.
- **IL borderline items not added**: Pace On Demand's 11 named zones
  (existing single CSV row) — question of whether to split by zone, not
  resolved; TransVAC/Kendall Area Transit (gating reads restrictive);
  RMTD "Call to Connect" and Bond County Transit (thin/secondary sourcing
  only); Knox County/Galesburg expansion (funding vote not finalized, no
  vendor — excluded per pilot rule); BPART (Bureau-Putnam; existence
  confirmed, details never extracted).
- **Eligibility-unclear tribal systems not added (OK)**: Cheyenne and
  Arapaho Tribal Transit's demand-response component, Otoe-Missouria Tribe
  Transit, Muscogee (Creek) Nation Transit, Comanche Nation Transit,
  Citizen Potawatomi Nation Transit — general-public framing found but not
  confirmed strongly enough this pass.
- **FL borderline, not added**: Gainesville RTS Mobility on Demand (framed
  around clinic/social-service destinations, general trip-taking
  unconfirmed); Bayway On Demand/Flex (Bay County, reads TD-eligibility
  gated); Babcock Ranch AV shuttle (likely private-community/school
  shuttle); a Lake County Facebook post describing a "free on-demand"
  service, likely a TD-program rebrand, unconfirmed as distinct.
- **Coverage still incomplete even in the 3 completed sweeps** — notably:
  AZ (Nogales/Santa Cruz County, Apache County towns, unincorporated
  Maricopa fringe cities); FL (FDOT's full CTC directory never pulled,
  Panhandle counties beyond Bay/Escambia, North Central rural counties);
  IL (Grundy, Will beyond West Joliet, Kane beyond Ride in Kane, DuPage
  beyond Ride DuPage, Cook south suburbs beyond Lansing); MA (MassDOT/FTA
  §5310/5311 rosters returned fetch errors, relied on secondary press;
  other MAPC subregions unchecked); NC (Outer Banks/far-eastern counties,
  Sandhills, southwestern mountain counties, the 16 NC COGs' pages);
  CO (southeast counties, San Luis Valley county-by-county, western slope,
  Denver-metro exurban fringe, Custer County — unresolved lead "Carry Me to
  Town").

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
