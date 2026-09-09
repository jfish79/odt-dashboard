# Notes — pending items, open threads

## Service-area boundary pipeline (started 2026-09-09)

Goal: a boundary polygon for every row, NC-style, in `data/boundaries/{ST}.geojson`.
Method: `scripts/boundaries/` — an agent workflow drafts a JSON "spec" per row
(which Census units / stated zone size), `resolve.py` builds the geometry from
Census cartographic boundary files, `merge.py` promotes batch output into the
committed `data/boundaries/specs/{ST}.json` + GeoJSON. Specs are the durable
record; re-running the resolver regenerates the GeoJSON.

Staging: 12 small stages (batch lists in the session scratchpad, one commit +
push per stage on `state-expansion`). Progress:
- Pilot VA + WI: done (54/55). Open: **GRTC LINK** (six named zones across four
  counties, no sizes; needs a human to trace GRTC's zone map).
- Stage 1 (NC gaps, AL, AR, DC, DE, HI, ID, IN, KY, LA): done 2026-09-09, 51/51.
- Stage 2 (MD, ME, MO, MS, NE, NH, NJ, NV): done 2026-09-09. Worth a human
  glance: **Delta Rides** and **SMART** (MS) county lists were read by the
  research agent off MDOT's ConnectMS regional map PDF (20 of 21 and 12 of
  13 counties, confidence 0.7 / 0.65) — verify against the map.
- Stage 3 (RI, SC, UT, WV, WY): done 2026-09-09. Follow-up: **UTA On Demand**
  (UT) is drawn as the union of the nine North Utah County municipalities it
  names, marked approximate; UTA's five other zones (South Davis, SLC
  Westside/South, Tooele, Provo/Orem) have no polygon — needs UTA's zone maps.
- Stage 4 (CT, MA, VT): done 2026-09-09.
- Stage 5 (NY, PA, OH, MI): done 2026-09-09.
- Stage 6 (FL, GA): done 2026-09-09. Open: **MARTA Reach** (GA) — 12 named
  zones across Fulton/DeKalb/Clayton with no sizes; needs MARTA's zone maps.
- Stage 7 (TN, TX): done 2026-09-09.
- Stage 8 (CA): launched 2026-09-09.

Follow-up list (rows left as `needs_research`, or approximate proxies worth a
human look) is visible in the spec files: search for `"needs_research"` and
`"fidelity": "approximate"` with confidence <= 0.5.

NC housekeeping: NC.geojson still carries three features for rows removed in
the scope sweep (KARTS, Tar River Transit RGP, YVEDDI GOTransit); the NC merge
in stage 1 drops them.

Working scratchpad for things that came up in research/chat but haven't been
applied to the CSV yet, or aren't resolved. Clear items out once they're
actually committed — this file should reflect *current* open items, not be
a permanent log (that's what `concerns.csv` and git history are for).

## AZ "Paratransit"-batch review, session paused mid-thread (2026-08-21)

**Not yet committed to git** — CSV/build changes are made locally but this
session stopped before a commit. Next session should review the working
tree diff, commit if it looks right, then continue.

Started because a routine "next steps" check found 9 AZ rows literally named
"___ Paratransit" that survived the 2026-07-24 paratransit purge (the purge
apparently filtered on `System Type == "Paratransit"`, but these 9 all have
`System Type = Demand-Response` despite Fleet-field text openly describing
ADA/eligibility restriction). That's when it became clear the whole AZ
"New addition on  July 1" batch (a synthetic-looking bulk add, many blank
`Source` fields) has unreliable Fleet/Ridership-Notes text — don't trust it
without checking a primary source first (this batch is a **different**
issue from the already-fixed Website-URL/Ridership-Notes column swap noted
below).

**Done and logged in concerns.csv (all rebuilt clean, 891 → 880 rows):**
- Removed 9 rows literally named "___ Paratransit" (Valley Metro, Mountain
  Line, CAT, Vista Transit, Bisbee Bus, KART, BATS, Four Seasons Connection,
  Page Express) — each individually checked, each had `Scheduling Window:
  Advance` + a Fleet field explicitly stating ADA/eligible-riders
  restriction.
- Removed **East Valley Dial-a-Ride** (AZ) — confirmed via Valley Metro's
  own site: this *is* their ADA Paratransit program, requiring in-person
  Mobility Center certification. Same program as the removed Valley Metro
  Paratransit row, just the East Valley branding.
- Removed **Salt River Transit** (AZ) — otherwise general-public and
  ADA-*accessible* (not restricted) per srpmic-nsn.gov, but requires 24-hour
  advance notice. Removed under the new 24hr+ policy call, see below. This
  is the row that surfaced the policy question.
- Corrected (not removed) **Tolleson Dial-a-Ride → renamed "Tolleson Micro
  Transit Program"** — the CSV's "Strictly a senior and medical/grocery
  trip shuttle" text was simply wrong. Confirmed via
  tolleson.az.gov/762/Tolleson-Micro-Transit-Program: general public,
  Uber/Lyft TNC-subsidy model ($15 city subsidy per ride), same-day app
  booking. **This also resolves the TX TNC-subsidy scope question below**
  (Cedar Park, Uber Kyle, Pfetch a Ride) — user's ruling: a city fare-subsidy
  on a commercial TNC app *does* count as an in-scope system, same as a
  city-run microtransit app. Those 3 TX rows can now be added on that basis
  in a future pass.

**AZ batch follow-ups — RESOLVED (2026-08-27), during the 24hr-advance-policy
sweep below:**
- **CART Dial-a-Ride (Casa Grande)** — confirmed: CART is the separate
  fixed-route regional bus; the demand-response service is branded CG LINK,
  general public, same-day best-effort. Renamed and corrected.
- **Glendale Dial-A-Ride (AZ)** — confirmed via ridewithvia.com/news and
  yourvalley.net (glendaleaz.gov itself still 403s): replaced by Glendale
  OnBoard, a same-day Via-operated curb-to-curb service. Renamed and
  corrected.
- San Carlos Apache Nnee Transit, YCAT OnCall, Benson Area Transit (BAT)
  Dial-a-Ride, and Coolidge Transit Dial-a-Ride were all checked and
  removed under the confirmed 24hr-advance policy (each required booking a
  day or more ahead, no same-day option found).
- **Still unconfirmed**: Wickenburg Dial-a-Ride, Havasu Mobility, Beeline
  Bus Dial-a-Ride — no primary source found stating a booking policy either
  way despite a real search attempt; logged as Data Gap entries in
  concerns.csv, left in scope. Needs a direct phone call, not further web
  search.

### 24-hour-advance-booking policy — SWEEP COMPLETE (2026-08-27)

**User ruling (2026-08-21): a confirmed 24-hour-plus advance booking
requirement is a definite disqualifier, full stop — regardless of
general-public eligibility.** This resolves the "TX 24-hour-advance policy
question" thread further down this file as well.

**Threshold clarified 2026-08-27 ("spirit-of-the-rule" ruling):** the test
is whether a rider can book AND ride same-day at all (even with a short
intraday lead time, e.g. "2-hour advance"), not the literal hour count.
Any requirement to call by some cutoff on a day *before* the trip (e.g.
"by 4:30pm the day before," "24hr," "next-day," "noon cutoff day-before")
disqualifies, regardless of whether that's technically 12, 16, or 24 actual
hours. Systems where same-day is a real accepted option — even if advance
booking is preferred/encouraged, or a short same-day lead time is required —
stay in scope.

This directly contradicts the *current* text in CLAUDE.md's scope rules
("Demand-response is included if it's flagged with an 'Advance' scheduling
window and open to the general public") and index.html's Reference-tab
definition of the "Demand-Response" System Type ("Rides are booked in
advance (typically the prior day or further out)... Open to the general
public"). Both need to be rewritten to match the new ruling — **hold off on
editing them until the data audit below is complete**, so the docs and the
data don't fall out of sync in the meantime.

**Triage done 2026-08-27** (mechanical text classification of all 880 rows'
`Scheduling Window` values, no removals yet):

- **KEEP, no action (~29 rows)** — value starts with `Same-day`/`Flexible`
  as the primary category (advance is an optional extra), or states an
  intraday lead time only (`2-hour`, `1-hour`, `30 min`, etc.). Confirmed
  same-day-capable from the text alone; not part of this sweep.
- **DISQUALIFY_TEXT queue (~90 rows after removing same-day-led false
  positives)** — existing text already states an unconditional prior-day
  cutoff with no same-day exception language (e.g. `Advance (24hr)`,
  `Advance (day-before)`, `Advance (by 4pm day-before)`). Candidates for
  removal, but each still needs a **light-touch source re-check** before
  removing per the verify-before-removal rule (bulk-batch text has been
  wrong before — see the Tolleson correction above) — heavier re-check for
  blank-`Source`/synthetic-looking batches, lighter for well-cited
  deep-sweep rows. Grouped by state for batch verification (mirrors the
  existing deep-sweep batch structure): **GA is by far the largest cluster
  at ~41 rows** (matches the "rural GA counties" pass flagged as
  systemically affected), then CA (~16), TX (~14), WI (~9, excluding the
  ambiguous shared-ride-taxi ones below), IL (6), CO (4), CT (2), NM (2),
  AZ (1), OK (1).
  - **Done (2026-08-27):** AR (5) + IL/OK (7) + CO (4) = 16 rows verified.
    13 removed (NATS, NEAT, SEAT, WTS / Boone County Transit, Fulton County
    Rural Transit, Kendall Area Transit/TransVAC, BPART, Call to Connect
    RMTD, White Eagle Transit / All Points Transit, Outback Express, MoCo
    Public Transportation — all logged in concerns.csv with citations). 2
    corrected and KEPT after the source showed same-day is actually accepted
    (CIPT — "24hr suggested, not required"; CADC/SCAT — "72hr requested,"
    not a hard requirement). 1 flagged unconfirmed, not removed (Call-N-Ride
    Greeley-Evans — site restructured, no live general-public DR page found;
    needs a phone check, may have folded into ADA paratransit). Rebuilt
    clean: 880 → 867 rows.
  - **Done (2026-08-27, round 2):** GA (36) + CA (11) + TX (14) + WI (9) = 70
    rows verified, plus the AMBIGUOUS queue (18 rows) verified in the same
    pass. 60 rows removed total this round, all logged in concerns.csv with
    citations. 14 corrected and KEPT after the source showed same-day is
    genuinely accepted (Ridgerunner/Corcoran/Sage Stage/Desert Roadrunner
    CA; Wilkes County GA; Fond du Lac/Door County/Oneida/Ozaukee/Washington
    County/Waupaca County WI; Harris County Transit Plus/SCRPT/SWART TX;
    Lake Mills/Tehachapi/Kern Regional/Dixon Readi-Ride from the ambiguous
    queue). 1 removed as a judgment call on self-contradicting source text
    (Kenosha County LINK — flagged medium-confidence in concerns.csv).
    ~10 rows left genuinely unconfirmed and NOT removed (Colusa County
    Transit CA, Waupun/Medford/Wisconsin Rapids/Viroqua-Westby WI, Jackson
    County/Taylor County GA, Shafter/Taft Area CA) — each needs a direct
    phone call, not a web search, to resolve; logged individually in
    concerns.csv as Data Gap entries. Rebuilt clean: 867 → 807 rows.
    **DISQUALIFY_TEXT and AMBIGUOUS queues are now fully worked. Only the
    BARE `Advance` queue (248 rows) remains — not yet started.**
  - Several rows in this queue had hedge language worth extra care during
    verification, not a rubber-stamp removal: "same-day if capacity
    allows/accommodated/possible/honored," "occasional same-day," "24hr or
    ASAP," "preferred/encouraged" rather than "required," and genuinely
    mixed-zone policies (e.g. Door County WI: one zone same-day-capable,
    other zones 24hr — resolved with a per-zone note, not a single
    keep/remove verdict for the whole row; Wilkes County GA similarly kept
    on a real same-day carve-out for city riders specifically).
- **BARE `Advance` queue — DONE (2026-08-27).** All 248 rows checked against
  a primary source, in 17 parallel state-batch research passes (ND, AZ, OK,
  MT, IA, SC, SD+MI, TN+IL, CO+OH, CA+NE, WY+NY, IN+ME, MD+ID+MO, NH+MS+OR,
  WA+NC+AK, LA+AL+GA+TX, and a 10-state misc batch). 148 removed (logged
  individually in concerns.csv with citations), ~40 corrected and KEPT after
  the source showed same-day is genuinely accepted (Scheduling Window
  updated from bare `Advance` to a confirmed detail), ~54 left genuinely
  UNCONFIRMED — no source (official site, aggregator, cached snapshot)
  stated a policy either way after a real search attempt. Those ~54 are not
  a residual TODO to keep chasing by web search; each is logged in
  concerns.csv as a Data Gap needing an actual phone call, which is out of
  scope for this pass.

**Sweep-wide total (2026-08-27, all four queues — DISQUALIFY_TEXT, KEEP_TEXT,
AMBIGUOUS, BARE): 880 → 665 rows (215 removed).** One state (AK) dropped to
zero — all 3 of its rows required 24hr+ prior-day booking with no same-day
option found. Treated as a genuine outcome per the WV precedent above, not
forced back up. A handful of AZ rows also got name/brand corrections
discovered along the way (Glendale Dial-A-Ride → Glendale OnBoard; CART
Dial-a-Ride → CG LINK, resolving the open item from the 2026-08-21 AZ-batch
thread above) — same pattern as the Tolleson correction: bulk-batch Fleet
text claiming ADA/senior restriction wasn't corroborated by the current
source and was cleared, not carried forward.

One process note for next time: two of the 17 parallel research batches'
results (SD+MI, TN+IL) got read but not applied to the CSV in the first
pass — caught by a post-sweep integrity check (cross-referencing every
concerns.csv "Scope Removal" entry's system name against the live CSV) and
fixed. That check also caught one single-row name-mismatch (removal script
used "BitterRoot Bus (Ravalli County)," the CSV's actual Name was just
"BitterRoot Bus"). Worth re-running that same integrity check after any
future multi-batch sweep before considering it done.

**Still open, lower priority:**
1. Update CLAUDE.md's scope-rules section and index.html's Reference-tab
   System Type definitions to state the spirit-of-the-rule threshold plainly
   and drop the contradictory carve-in language — the docs still describe
   the old "Advance window + general public = included" rule.
2. Given the scale (Demand-Response fell from 467 to 265 rows in this
   sweep, well under half its pre-sweep size), reconsider whether
   "Demand-Response" survives as a meaningful System Type afterward, or
   whether it should be redefined/renamed now that same-day-only systems
   are the norm for what's left.
3. The ~54 UNCONFIRMED bare-Advance rows and the ~10 UNCONFIRMED rows from
   the earlier DISQUALIFY_TEXT/AMBIGUOUS queues (Colusa County CA, Waupun/
   Medford WI, etc.) are all individually logged in concerns.csv as Data Gap
   entries needing a phone call — a good candidate for a dedicated future
   session if someone wants to work the phones, not a web-research task.

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
  general-public rural demand-response pattern.
  **Batch 1 of that follow-up (15 checked, 2026-07-24): 14 confirmed and
  added** (Wilcox, Cook, Americus/Sumter, Pierce, Haralson, Taylor,
  Cedartown/Polk, Murray, Habersham, Bleckley, Taliaferro, Lumpkin,
  Paulding, Dawson counties) — **Conyers/Rockdale County excluded**, still
  in planning stage (a Nov 2023 transit development plan recommends
  microtransit but no vendor/launch date confirmed as of this check; fails
  the pilot-inclusion rule, re-check in a future pass).
  **Batch 2 (15 checked, 2026-07-24): 12 confirmed and added** (Clay,
  Heard, Glascock, Greene, Hart, Banks, Wilkinson, Walker, Lincoln,
  Jefferson, Morgan, Macon/Oglethorpe counties — note Macon County here is
  distinct from the existing "MTA Rapid Transit" Macon-Bibb row). **3
  excluded/duplicate**: River Valley Regional Transit (a 16-county
  planning/coordinating body, not itself a rider-facing system — its
  member counties are already covered individually via METRA, RMS-operated
  systems, or newly-added rows); Douglas/Coffee County Rideshare (Coffee
  County is already covered by the existing "Southern Georgia Regional
  Transit" row); Bryan County (already covered by the existing "Coastal
  Regional Coaches" row). Lincoln County Transit's data is notably thinner
  than the rest of this batch (no live county webpage found, sourced only
  from an FTA NTD profile) — worth a dedicated re-check.
  **Batch 3 (final, 10 checked, 2026-07-24): all 10 confirmed and added**
  (Catoosa, Crawford, Hancock, Talbot, McDuffie, Tift/"Tift Lift", Dade,
  Dooly, Wilkes, Burke counties). Hancock County was double-checked for
  the possible senior-restriction the "Hancock County Senior Center /
  Transit" combined naming suggested — FTA NTD classifies it as "Rural
  General Public Transit" across three profile years (2014/2016/2019)
  and the county's own page states no eligibility restriction; confirmed
  general-public despite sharing office space with the senior center.
  **GA's county-roster follow-up thread is now closed** — all ~40
  originally-flagged leads have been checked across 3 batches (36
  confirmed and added, 4 excluded as duplicates/still-planning).
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
- **GA existing-row updates — resolved**. CobbLinc Go's `Region/Service
  Area` updated to note its North Cobb/Acworth-Kennesaw expansion ($3.84M
  funding confirmed 2026, launch date unconfirmed). MARTA Reach's existing
  12-zone list already included "North Fulton" — the Alpharetta/North
  Fulton CID expansion noted in wave 3 appears to be within that
  already-listed zone, not a new one, so no edit was needed there.
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
- **CA under-coverage — substantially addressed (2026-07-24), roster
  question resolved as a permanent dead-end.** A dedicated Caltrans/CalACT
  follow-up added 35 more CA systems (LA County, a 6-city Kern County
  cluster, SLO/Santa Barbara, Central Valley, Solano Delta towns, rural
  Sierra/far-north counties, Calaveras County, 3 tribal systems). Neither
  the Caltrans §5311/§5310 BlackCat system nor the CalACT member directory
  was ever obtained as a public document across three separate passes —
  both are login-gated with no public roster page. **Stop trying this
  route without actual login credentials.** Instead, this pass found and
  recommends a public substitute for future state sweeps: the FTA
  National Transit Database "Service by Agency" dataset, queryable with
  no auth at `https://data.transportation.gov/resource/6y83-7vuw.json`
  (filter `?max_state=XX`) — it returned 313 named CA agencies and is
  federal, current, and machine-readable, though it only captures
  agencies that file NTD reports (a blind spot for tiny
  volunteer-run/purely-locally-funded services).
  Open items from this pass:
  - **Tehachapi Dial-A-Ride vs. Kern Regional Transit Dial-A-Ride
    network** — both added as separate rows, but they share a phone
    number and hosting domain; may be the same underlying service.
    Flagged in concerns.csv, not resolved.
  - **GoMonrovia's vendor** recorded as Lyft (confirmed this pass); a
    secondary source elsewhere describes Via — unresolved whether there
    was an earlier Via phase.
  - Several fields need a direct spot-check before being treated as
    final: Lodi GrapeLine's $7 fare (single search snippet), Dixon
    Readi-Ride's ~8-vehicle fleet count (2022 planning doc, may be
    stale), Claremont Dial-a-Ride's conflicting reported hours, Avalon
    COAST's truncated funding-source citation.
  - **The 6 previously-unresearched NTD entities — checked, all
    out-of-scope (2026-07-24)**: Foothill Transit (fixed-route), Access
    Services (LA County's ADA paratransit broker), Paratransit Inc./
    Sacramento (SacRT's ADA contractor), CalVans (statewide vanpool JPA,
    not demand-response), Easy Lift Transportation/Goleta (ADA/disability-
    restricted Dial-A-Ride), Attentive Transportation LLC/Sacramento
    (private NEMT, medical-trip-purpose-restricted, not general-public
    transit). None added. The 313-agency NTD list overall was still only
    triaged by name/city-size judgment for the ~55 sent to research, not
    exhaustively — a future pass could still find more among the
    untouched majority, but the specific flagged leads are now resolved.
  - **LA County DPW's ~8 named shuttle programs — checked, out of scope
    as a category (2026-07-24)**: all still active in 2026 (confirmed via
    the current LA County Public Works shuttles page), but every one is a
    fixed-route shuttle with a published timed schedule, not demand-
    response — not folded into Metro Micro, just genuinely fixed-route.
    Their absence from 2024 NTD data appears to be a reporting artifact,
    not a service change. Thread closed, no further per-program checks
    needed.
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
- **Douglas County, CO — "Link on Demand" — resolved (2026-07-24)**.
  Confirmed and applied: Parker/Stonegate expansion is live (Apr 2026);
  Castle Rock ($1.9M contract, approved Jul 14 2026) goes live Jul 31
  2026 — not yet live as of this update. Row's `Region/Service Area` and
  `Ridership/Performance Notes` updated. The row's name still says
  "(Lone Tree)" though its service area has outgrown that single city —
  a rename (e.g. to "Link on Demand (Douglas County)") may be warranted
  once Castle Rock actually goes live; left as a human judgment call.
- **Mountain Valley Transit (CO) — re-checked, still not added**. Status
  is genuinely mixed, not a clean discontinuation: Antonito-Alamosa
  resumed Apr 1 2026, but all other San Luis Valley routes remain paused
  since Feb 2 2026 due to funding cuts, and the former Buena Vista-Salida
  leg is no longer MVT at all (absorbed by CDOT's Bustang service, Jan
  2026). Recommend against adding until status stabilizes further; if
  added later, scope narrowly to the Antonito-Alamosa corridor only.
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
- **IL borderline items — mostly resolved (2026-07-24)**. Pace On
  Demand's 11-zone list confirmed still current via pacebus.com, zero
  changes — the zone-split-into-11-rows question remains an open human
  decision, not re-litigated. TransVAC/Kendall Area Transit confirmed
  general-public (capacity/priority gating only, not an eligibility gate)
  — added as "Kendall Area Transit (KAT) / TransVAC." Bond County Transit
  confirmed directly ("ANYONE OF ANY AGE IS ELIGIBLE TO RIDE!") — added.
  BPART confirmed directly via ridebpart.org — added as "Bureau-Putnam
  Area Rural Transit (BPART)." Knox County/Galesburg **still not
  finalized** — Galesburg council approved its side ~Jul 20 2026, county
  board vote is scheduled Jul 29 2026 (not yet occurred), no vendor named
  yet; re-check after that date. **RMTD "Call to Connect" — resolved
  (2026-07-24)**: it was never Rock Island — "RMTD" is Rockford Mass
  Transit District. It's a point-deviation/flex connector in Machesney
  Park (Winnebago County) bridging RMTD's fixed-route service to a few
  destinations, Advance (24hr) booking, standard fixed-route fare.
  Added as "Call to Connect (RMTD)." Confidence on general-public
  eligibility is moderate-high (textually distinguished from RMTD's
  separate ADA paratransit section across three fetches) but not
  phone-verified — call 815-961-2230 if higher certainty is needed. The
  existing "RIM Rural Transit" row (the actual Rock Island/Mercer county
  operator) still has a few "Not specified" fields a prior pass could
  fill in (hours Mon-Fri 8:00-4:30, explicit 60+ no-duration-requirement
  eligibility) — unrelated enrichment opportunity, not yet applied.
- **OK tribal systems — re-checked, mostly still unclear (2026-07-24)**.
  **Citizen Potawatomi Nation Transit resolved: eligibility-gated, out of
  scope** (per CPN's own criteria — enrolled members 18+, or other Native
  American applicants who are 60+/meet an income limit/live in tribal
  jurisdiction; not general-public). The other 4 remain genuinely
  unresolved even after a direct-source check: Cheyenne and Arapaho
  Tribal Transit's DR component (describes eligibility by trip purpose,
  never by rider category) and Otoe-Missouria Tribe Transit (leans
  tribal-member-focused per program description) stay unclear; Muscogee
  (Creek) Nation Transit has an unconfirmed secondary-source claim of
  general-public eligibility, not found on any official page. **Comanche
  Nation Transit is the strongest lead** — a non-official source (Lawton
  MPO) describes it as open to both tribal and non-tribal members
  covering Lawton/Fort Sill/Cache/Apache/Elgin/Fletcher/Cyril, but the
  operator's own page 404'd; retry at comanchenation.com/general-services/page/transit.
- **FL borderline — Gainesville RTS Mobility on Demand added, Bayway
  confirmed excluded (2026-07-24)**. Mobility on Demand (Gainesville
  RTS): the "clinic/social-service" framing turned out to be
  equity-marketing emphasis, not a booking restriction — riders can go to
  any destination within the East Gainesville MOD zone, no eligibility
  gate found. Added. Bayway On Demand/Flex (Bay County): confirmed
  eligibility-gated via the operator's own application criteria (60+,
  below poverty line, or disability, with a 21-day application process;
  site explicitly states "not available to the general public") —
  correctly excluded. Still open: Babcock Ranch AV shuttle (likely
  private-community/school shuttle) and the Lake County Facebook post
  describing a "free on-demand" service (likely a TD-program rebrand) —
  neither re-checked this pass.
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

- **WI shared-ride taxi program (Wis. Stat. 85.20) — resolved (2026-07-24)**.
  Found the authoritative roster: WI Legislative Fiscal Bureau
  Informational Paper 43 ("Transit Assistance," Jan 2025), Appendix I,
  itemizes all 46 CY2024 state-aid shared-ride-taxi systems. Of those, 4
  were already in the CSV, 39 were added as new rows, and 3 were confirmed
  discontinued (Clark County, Rhinelander, Waupaca — all ended their
  contracts Dec 2024–Dec 2025; logged in concerns.csv as `Status Change`).
  This closes the original open item — Brown Cab's and Passenger Transit's
  full city lists are now independently confirmed via the LFB roster.
  Remaining loose ends from this pass:
  - **Waupaca County's 2026 replacement program** (Feonix – Mobility
    Rising, county-wide, launched after the old Brown Cab contract ended)
    postdates the LFB roster and was NOT researched — good next targeted
    follow-up.
  - The roster only covers systems that received CY2024 WisDOT 85.20 aid;
    any purely locally-funded shared-ride-taxi system, or one launched in
    2025/2026, wouldn't appear on it — a structural gap, not a shortcut.
  - 5 official city pages returned errors during fetch (Tomah, Whitewater,
    Hartford, Ripon, Waupaca) — those rows relied on operator sites/news
    coverage rather than a primary city source; worth a manual re-check.
  - Several fare/operator discrepancies were found and logged per-row in
    concerns.csv rather than silently resolved (Chippewa Falls, Fort
    Atkinson, and Whitewater fare figures; Ozaukee County operator
    identity — STS vs. GoRiteway, possibly confused with neighboring
    Washington County's 2026 changeover; Plover's operator, mid-transition
    as of Jan 2026 and unnamed in sources found).
- **Several states hit a shared WebSearch budget cap mid-sweep** (parallel
  sub-forks within one agent draw from the same quota) and were confirmed
  incomplete, not exhaustively covered. Re-sweep in progress (2026-07-24),
  state by state:
  - **NH — checked, closed, 0 added.** Concord Area Transit's only
    demand-response is ADA Paratransit (certified-only) and Concord
    Senior Transit (60+ only) — both hard eligibility gates. Advance
    Transit's only demand-response is Access AT, ADA-certification
    required. No general-public service found for either operator.
  - **ID — checked, closed, 0 added.** Kootenai County/Coeur d'Alene:
    Citylink North's Ring-a-Ride is restricted to 65+ with a mobility
    challenge; Citylink South's (Coeur d'Alene Tribe) demand-response is
    ADA-only within 3/4 mile of its fixed route. No general-public
    service found.
  - **NM — checked, 6 added, mostly closed (2026-07-25).** Rio Metro
    Valencia County Dial-A-Ride, Rockin' 66 Express (Cibola County/
    Grants), Po'Pay Messenger (Ohkay Owingeh Pueblo), plus (added in a
    follow-up pass) Roswell Dial-a-Ride and Pueblo of Isleta Dial-a-Ride
    (Rio Metro) — the latter two resolve what were previously conflicting/
    unconfirmed eligibility signals. Rio Rancho Dial-a-Ride, Farmington's
    Red Apple Transit Dial-A-Ride, Silver City's Corre Caminos Silver
    Route, and Gallup Express were checked and confirmed out of scope
    (ADA/senior-restricted or route-deviation-only, not standalone
    demand-response). **Corre Cantinas (Silver City/Grant County) added
    but flagged as a genuine scope edge case** — a weekend-night
    DWI-prevention "safe ride home" service, not general mobility transit
    by original purpose, but it satisfies the database's literal
    eligibility-based scope rules (open to the public, no certification,
    same-day dispatch). CLAUDE.md doesn't address purpose-restricted
    services — needs a human policy call, comparable to the TX TNC-subsidy
    question below. **Non-Navajo NM tribal transit re-checked
    (2026-07-25), genuinely no service found for 6 of 7**: Jicarilla
    Apache, Taos, Tesuque, and Santa Clara are served only by NCRTD fixed
    routes (no standalone tribal demand-response); Mescalero Apache
    contracts to Ztrans (Otero County) but booking/eligibility type
    unconfirmed; Sandia Pueblo's transportation program is medical/
    elder-restricted, excluded. **Santa Ana Pueblo remains the one
    genuinely promising unresolved lead** — a secondary DOL/FTA filing
    says beneficiaries include "the tribe and other general public," but
    the tribe's own transportation pages show only school-transportation
    content; worth one more direct call (Transportation Manager David
    Griego) if revisited.
  - **NY — fully checked and closed, 3 added.** Identified 17 genuine
    candidate-gap counties across the North Country, Finger Lakes,
    Mohawk Valley, and Central NY. Batch 1 added Schoharie County Public
    Transportation's Demand Response service and excluded 10 with a clear
    reason each (St. Lawrence/Jefferson: fixed-route feeders only; Essex:
    no demand-response beyond Medicaid NEMT; Yates: contracted dial-a-ride
    discontinued 12/31/2025, no successor yet; Herkimer: age-60+
    restricted; Fulton/Montgomery: route-deviation + application-gated
    paratransit only; Madison: county's own page says "currently
    unavailable"; Cayuga: only disability-certified paratransit + age-60+
    rideshare voucher; Chenango: restarted service is fixed-route +
    route-deviation only). Applied the existing Franklin County CSV
    precedent consistently throughout: route-deviation (up to 3/4 mile
    off a fixed route) and fixed-route-feeder services don't count as
    standalone demand-response, even when a county's own site loosely
    calls them "demand response." Batch 2 resolved the remaining 6:
    added Clinton County (CCPT Rural Zone/Dial-A-Ride — confirmed
    general-public; the earlier Michigan-area-code lead was an unrelated
    system, correctly discarded) and Steuben County (confirmed
    general-public via regional mobility management site — note a
    same-named agency exists in Steuben County, Indiana, don't confuse
    them); excluded Hamilton (no transit department exists at all, one
    of only two NY counties with no county highway system either),
    Lewis (confirmed route-deviation; also caught that
    lewiscountytransit.org/dartt was actually Lewis County, *Washington*
    — a bad domain match, not NY at all), Cortland (confirmed
    route-deviation), and Otsego ("OCBS" was entirely a Michigan system
    in Gaylord, MI — another bad cross-state lead, discarded; the real NY
    Otsego Express is the already-excluded route-deviation service).
    NY's rural-county thread is now fully closed.
  - **ND — batch 1 checked, 17 added, 9 remain.** Combined the Dakota
    Transit Association membership list with ND Community Action
    Partnership's statewide transit resource guide to reconstruct
    NDDOT's roster (~34 programs, matching NDDOT's own "approximately 34
    bus programs" figure — no flat directory page exists). 4 already in
    CSV (Souris Basin, Standing Rock, NW Dakota, Wildrose). 4 excluded as
    urban fixed-route (Bis-Man/Bismarck-Mandan, Cities Area Transit/Grand
    Forks, Fargo MATBUS, Minot City Transit). Added 17 general-public
    demand-response systems: Benson County, Cavalier County, Dickey
    County, Dickinson, Golden Valley/Billings County, Hazen, James River
    (Jamestown), Kenmare Wheels & Meals, Kidder Emmons (Steele), Nutrition
    United/Can-Do Transportation (Rolla), Pembina County, South Central
    Transit Network (Valley City), Southwest Public Transit (Bowman),
    Valley Senior Services' rural-county service only (its separate
    Fargo-Moorhead metro Senior Ride Service reads senior-restricted, not
    added), Walsh County, West River Transit, Devils Lake Transit. Three
    of these (Golden Valley/Billings, Nutrition United/Can-Do, Devils
    Lake) lean on the CAP-ND brochure's blanket "open to the public"
    statement rather than first-party language — flagged as second-tier
    confidence in concerns.csv. **Batch 2 (final) resolved the remaining
    9, adding 4.** The Rolette County/Turtle Mountain cluster of 5 names
    turned out to be 3 real systems: Rolette County Transit (Nutrition
    United Inc., non-reservation Rolette County — distinct from that same
    nonprofit's Towner County "Can-Do" service) and Turtle Mountain
    Transit (= "Turtle Mountain Tribal Transit," one system under two
    names, confirmed via matching phone numbers and a single FTA NTD ID)
    were both added; Royal Coach Transportation was confirmed defunct
    (involuntarily dissolved 2018) and excluded. Also added Spirit Lake
    Transit (Fort Totten — a genuinely separate tribe/reservation, not
    part of the Turtle Mountain cluster) and Trenton Indian Service Area
    Aging Program (Williams County). Eddy County, Glen Ullin, and Nelson
    County were NOT added as new rows — each turned out to be the same
    operator as an existing row, serving an area that row's Region field
    hadn't documented. Two existing rows were corrected as a result:
    "Nutrition United Transit (Can-Do Transportation)" had mislabeled
    Rolla (the Rolette County seat) as being in Towner County — fixed;
    "South Central Transit Network" was missing Nelson County from its
    county list despite serving it — added. **ND's thread, and the whole
    7-state re-sweep, is now fully closed.**
  - **OR — fully checked and closed, 2 added.** CoosGO (Coos County/
    Bandon) and UPTD Dial-A-Ride (Douglas County) — both confirmed
    general-public directly on the operator's own site, with same-operator
    ADA/senior-certified paratransit siblings (CoosLIFT, UPTD ParaTransit)
    correctly excluded. Josephine County's app-based "Transit On Demand"
    evening service is confirmed discontinued per JCT's own current
    alerts page. Umatilla County's Kayak Public Transit demand-response is
    certification-gated ADA paratransit. **WORC Taxi Voucher Program —
    re-checked (2026-07-25), confirmed excluded**: WORC stands for
    "Workforce," not a general community program — confirmed via
    hermiston.gov's own page that it's explicitly employment-restricted
    (proof of current employment required, intended exclusively for work
    commutes) and is a subsidized third-party taxi-voucher scheme
    (Hermiston Taxi Company), not an agency-operated demand-response
    system. The earlier "reads general-public" summary was incorrect.
  - **MI — fully checked and closed, 16 added total.** The MDOT
    "Advancing Rural Mobility Program" roster turned out larger than
    estimated: 23 agencies total (4 pilot + 19 expansion partners), not
    ~15. 6 were already in the CSV (Benzie, Wexford/WexExpress,
    Charlevoix, Roscommon, Battle Creek/BCGo, Marquette/MarqTran).
    Batch 1 added Blugo (Clinton Transit), I-Ride (Isabella County),
    I-DART (Ionia), The Interurban (Saugatuck/Douglas); excluded Blue
    Water Area Transit (60+/ADA-card gated). Batch 2 added the remaining
    11 county/township providers (Antrim, Arenac, Clare, Crawford,
    Gladwin, Iosco, Kalkaska, Manistee, Ogemaw, Thunder Bay, Yates
    Township) plus Straits Regional Ride, whose flex-route-vs-
    demand-response classification question was resolved by checking
    FTA's National Transit Database — it's officially classified
    Demand-Response (not Deviated Fixed Route) across all filed years.
    All 23 roster agencies are now accounted for; MI's thread is closed.
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

## Paratransit scope change — cleanup follow-ups — RESOLVED (checked 2026-08-21)

All items below turned out to already be fixed in a later commit; nothing
open here. Confirmed 2026-08-21: WV sits at 3 rows (real candidates were
found in the Wave 1 low-recall sweep). index.html's Reference tab already
documents the July 2026 retirement in its System Type section, and
`legend.csv` no longer mentions Paratransit at all. The footer stat computes
dynamically from `systems.length`/state count at load time, so it was never
actually hardcoded/stale. Leaving this note only so a future pass doesn't
waste time re-checking it — safe to delete next edit.

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

### Thin states — RESOLVED via later deep-sweep passes (checked 2026-08-21)

All four caught up since this was written: NM is now 8 systems (NM/OR
coverage-gap sweep), ND is now 25 (ND coverage gap batches 1-2), TN is now
16 (Wave 2 deep sweep), MS is now 4. Safe to delete next edit.

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
