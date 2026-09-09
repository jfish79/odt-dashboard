// Service-area boundary workflow (Claude Code Workflow tool script).
//
// Per batch of ~12 CSV rows in one state:
//   1. Draft  (Haiku)  – spec from row text only, run resolver, fix name mismatches
//   2. Audit  (Haiku)  – skeptic: does the spec claim more/less than the row says?
//   3. Fix    (Sonnet) – web research for rows flagged by the resolver or the audit
//   4. Re-audit (Haiku) – only the rows the fix stage touched
//
// args: {
//   scratch: "<dir>",            // has rows/<batch>.json inputs; specs/ and qa/ are written here
//   batches: [{state, batch, n, names:[...]}],
//   skipDraft: false             // true = reuse existing specs/<batch>.json, start at Audit
// }
// Geometry is never produced by an agent: scripts/boundaries/resolve.py turns the
// spec file into GeoJSON deterministically. Merge step is done by hand afterwards:
//   python3 scripts/boundaries/resolve.py --specs data/boundaries/specs/XX.json --qa ...

export const meta = {
  name: 'odt-boundaries',
  description: 'Draft service-area boundary specs per state batch, resolve via Census geometry, audit, web-research the flagged rows',
  phases: [
    { title: 'Draft specs', detail: 'Haiku: spec from row text, run resolver, fix name mismatches', model: 'haiku' },
    { title: 'Audit', detail: 'Haiku skeptic: does each spec match what the row actually says?', model: 'haiku' },
    { title: 'Fix flagged', detail: 'Sonnet: web research for rows flagged by resolver or audit', model: 'sonnet' },
    { title: 'Re-audit', detail: 'Haiku: re-check only the rows the fix stage changed', model: 'haiku' },
  ],
}

const S = args.scratch
const batches = args.batches
const skipDraft = !!args.skipDraft

const RULES = `
SPEC RULES (follow exactly; the resolver is deterministic, your job is only to describe the area in its vocabulary):
- Output file is a JSON list; one object per row; "name" must equal the CSV Name exactly; "state" is the 2-letter state.
- boundary_type choices:
  * "county"   – the service covers one county ("X County", "countywide"). units: [{"layer":"county","name":"Orange"}]
  * "counties" – several named counties, one unit each.
  * "city"     – one incorporated city/village/town, service citywide. units: [{"layer":"place","name":"Wilson"}]
  * "places"   – a list of towns/cities, one unit each, layer "auto" (tries incorporated place, then county subdivision).
  * "cousub"/"cousubs" – New England towns (CT, MA, ME, NH, RI, VT) and township units ("Town of X" in WI/NY/MI/MN, "X Township"). layer "cousub". In WI a "City of X"/"Village of X" is a place; a "Town of X" is a cousub.
  * "tribal"   – a reservation / tribal land. units: [{"layer":"aiannh","name":"Crow"}] (base name, without "Reservation").
  * "buffered" – a municipality PLUS a stated radius around it ("City of X and up to 5 miles outside city limits"). units as for city/places, plus "dilate_km": miles*1.609.
  * "zone_approx" – a zone with NO administrative match but a stated size. Circles of the stated size: radius_km = sqrt(sq_mi*2.59/3.1416) for an area, miles*1.609 for a radius.
      - one zone: "buffer": {"radius_km": R} (centered on the CSV pin) or "buffers": [{"center_unit": {"layer":"place","name":"X"}, "radius_km": R}]
      - several zones, one per named city/county: "buffers": [one entry per zone with its own center_unit and radius]
      - add "units": [the containing city/county units] and "clip_to_units": true so circles never spill outside the municipality.
  * "needs_research" – nothing above applies from the text alone (regions like "South Central IL", "8 zones across the metro", zones named by neighborhoods/corridors/campuses with no size). One-line note on what is missing. NEVER guess county or town lists from memory.
- SIZE BEATS UNIT: if the text gives a zone size (sq mi, radius) that is far smaller than the named city/county, do NOT use the whole unit — use zone_approx circles (with center_unit + clip_to_units). A whole county for a "~20 sq mi zone" is wrong.
- CONTAINING-UNIT PROXY: partial coverage without a stated size ("zone in X", "portions of X", "north side of X", "most of X County", zones named by neighborhoods or boundary streets inside one city) is encoded as the single containing city or county with "fidelity": "approximate" and a note such as "service zone is a subset of city limits (bounded by A Rd, B Blvd)". This is the CORRECT encoding, not an error: the dashboard draws approximate polygons dashed and labels them. Only when the zones are small AND spread across several counties with no sizes does the proxy become misleading; then use "needs_research".
- "needs_research" is the last resort. Prefer, in order: exact units > stated-size circles > containing-unit proxy (approximate) > needs_research.
- Mixed descriptions ("City of Norton; Lee, Scott, and Wise counties"): type of the larger unit set, every unit with its own correct layer.
- "X / Y County" or "X (Y County)" where X is the county seat: county only if the operator is a county agency or the text says county-wide; otherwise the city, fidelity "approximate", say so in the note.
- Names: bare name ("Madison", not "City of Madison"); keep "St." as written. For an ambiguous name add "county": "<County name>" to the unit.
- Always include "confidence" (0-1) and a short "note" for anything approximate or inferred; the note is published in the dashboard popup, so write it for a reader.
`

const RESOLVER = (batch) => `python3 /Users/jfish/Documents/GitHub/odt-dashboard/scripts/boundaries/resolve.py --specs ${S}/specs/${batch}.json --dry-run --qa ${S}/qa/${batch}.json`

const ROW_SCHEMA = {
  type: 'object',
  properties: {
    batch: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' },
      boundary_type: { type: 'string' },
      status: { type: 'string', description: 'resolver status: ok | suspect | partial | error | skipped | needs_research' },
      issues: { type: 'array', items: { type: 'string' } },
    }, required: ['name', 'boundary_type', 'status', 'issues'] } },
  },
  required: ['batch', 'rows'],
}

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    batch: { type: 'string' },
    verdicts: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' },
      verdict: { type: 'string', description: 'ok | doubt | wrong' },
      reason: { type: 'string' },
    }, required: ['name', 'verdict', 'reason'] } },
  },
  required: ['batch', 'verdicts'],
}

const rowsFile = (b) => `${S}/rows/${b.batch}.json`
const specFile = (b) => `${S}/specs/${b.batch}.json`
const qaFile = (b) => `${S}/qa/${b.batch}.json`

function draftPrompt(b) {
  return `Draft service-area boundary specs for ${b.n} on-demand transit systems in ${b.state}. Batch id: ${b.batch}.
Read the rows from ${rowsFile(b)} (JSON list: Name, Region/Service Area, Geographic Context, Operator, Website URL, Latitude, Longitude, Ridership/Performance Notes, Fleet). Write the spec file ${specFile(b)}, then run:
  ${RESOLVER(b.batch)}
Read its stdout. For every "unit not found" / "ambiguous unit" issue fix the spec (try layer "cousub" for towns/townships, add a "county" hint, fix spelling, or drop the unit and note it) and re-run; at most 3 rounds. For a "suspect" status (area far off the stated size, or pin far outside), reconsider the shape per the SIZE BEATS UNIT rule. Never delete a row from the file; a row you cannot spec keeps boundary_type "needs_research" with a note. Work from the row text only; no web tools in this stage.
${RULES}
Row names in this batch: ${JSON.stringify(b.names)}
Return one entry per row with the FINAL resolver status and issue strings for that row (copy them from the resolver output / ${qaFile(b)}).`
}

function auditPrompt(b, names) {
  return `Skeptical audit of service-area boundary specs. State: ${b.state}. Read the spec file ${specFile(b)} and the QA file ${qaFile(b)} (status, area_km2, units matched, pin checks), and the rows (Region/Service Area, Operator, Geographic Context, notes) from ${rowsFile(b)}.
For each row listed below decide: does the spec claim MORE or LESS than the text supports? Wrong unit type (whole county where the text says one city; a same-named town elsewhere in the state; a New England town resolved as a CDP)? A whole municipality used where the text states a much smaller zone SIZE in sq mi or a radius (should be zone_approx circles)? A "needs_research" that is avoidable because the text names the units, or because a single containing city/county could stand in with fidelity approximate? A stated "plus N miles" radius that the spec ignored (should be "buffered")? Use area_km2 and pin-outside distance as evidence.
NOT an error: a single containing city or county with "fidelity": "approximate" and a note, used for a zone that has no stated size ("zone in X", "north side of X", zones named by neighborhoods or streets). That is the project's standard proxy; verdict "ok". Judge from the files and row text only; no web tools.
Rows to audit: ${JSON.stringify(names)}
Return one verdict per row: ok / doubt / wrong, with a one-sentence reason.`
}

function fixPrompt(b, flagged) {
  return `Fix service-area boundary specs that failed automated checks. State: ${b.state}. Spec file: ${specFile(b)} — edit ONLY the entries for the rows listed below; leave every other entry byte-for-byte untouched. Row data (Region/Service Area, Operator, Website URL, pin, notes) is in ${rowsFile(b)}.
For each row: first re-read the row text against the SPEC RULES (many flags are fixable from the text: a stated zone size -> zone_approx circles with center_unit + clip_to_units; "plus 5 miles" -> buffered; "most of X County" -> county with fidelity approximate). If the text is not enough, fetch the Website URL (WebFetch) and WebSearch for "<system name> service area" / "<name> zone map" / the operator's site, looking for: municipalities or counties served, a zone size in square miles or a radius, or a boundary described by towns/roads. Rewrite the row's spec, then run:
  ${RESOLVER(b.batch)}
and re-run once more if a unit name failed. Put the URL you relied on in the spec "note". If no size or unit list is public but the zone sits inside one city or one county, keep that containing unit with "fidelity": "approximate" and put what you learned (boundary streets, URL) in the note — do not downgrade to needs_research. Use "needs_research" only when you cannot even name a single containing municipality or county (or the zones are small and spread over several counties); then record in the note what you checked (URLs) and what the site says, so a human can follow up. Never invent unit lists.
${RULES}
ROWS TO FIX: ${JSON.stringify(flagged)}
Return one entry per fixed row with its FINAL resolver status and issues.`
}

const results = await pipeline(
  batches,
  async (b) => {
    if (skipDraft) return { batch: b.batch, rows: [], reused: true }
    return agent(draftPrompt(b), { label: `draft:${b.batch}`, phase: 'Draft specs', model: 'haiku', schema: ROW_SCHEMA })
  },
  async (draft, b) => {
    if (!draft) return null
    const audit = await agent(auditPrompt(b, b.names), { label: `audit:${b.batch}`, phase: 'Audit', model: 'haiku', schema: AUDIT_SCHEMA })
    return { draft, audit }
  },
  async (prev, b) => {
    if (!prev) return null
    const { draft, audit } = prev
    const byName = {}
    for (const r of draft.rows) byName[r.name] = { name: r.name, resolver_status: r.status, resolver_issues: r.issues, audit: 'ok', audit_reason: '' }
    for (const v of (audit ? audit.verdicts : [])) {
      byName[v.name] = byName[v.name] || { name: v.name, resolver_status: 'unknown', resolver_issues: [], audit: 'ok', audit_reason: '' }
      byName[v.name].audit = v.verdict
      byName[v.name].audit_reason = v.reason
    }
    const flagged = Object.values(byName).filter(r =>
      (r.resolver_status && !['ok', 'unknown'].includes(r.resolver_status)) || r.audit !== 'ok')
    log(`${b.batch}: ${b.n - flagged.length}/${b.n} clean; ${flagged.length} flagged for research`)
    if (!flagged.length) return { batch: b.batch, state: b.state, draft, audit, fix: null, reaudit: null, flagged: [] }
    const fix = await agent(fixPrompt(b, flagged), { label: `fix:${b.batch}`, phase: 'Fix flagged', model: 'sonnet', schema: ROW_SCHEMA })
    const fixedNames = fix ? fix.rows.map(r => r.name) : flagged.map(r => r.name)
    const reaudit = await agent(auditPrompt(b, fixedNames), { label: `reaudit:${b.batch}`, phase: 'Re-audit', model: 'haiku', schema: AUDIT_SCHEMA })
    return { batch: b.batch, state: b.state, draft, audit, fix, reaudit, flagged: flagged.map(r => r.name) }
  },
)

return results.filter(Boolean)
