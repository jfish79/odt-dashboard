"""Build the ODT project-summary deck from the NLR PowerPoint template.

Usage:
  python3 scripts/deck/build_deck.py template.pptx out.pptx

`template.pptx` is the NLR .potx re-typed as a presentation: unzip the .potx,
replace "presentationml.template.main+xml" with
"presentationml.presentation.main+xml" in [Content_Types].xml, re-zip.
(python-pptx refuses to open a .potx directly.)

IMPORTANT: docs/ODT-Database-Project-Summary.pptx is hand-edited in PowerPoint
after generation. Do NOT regenerate over it. Extract its text first
(python-pptx), compare with the committed version, and either fold the human
edits into this script or edit the .pptx in place. See NOTES.md "Project deck".
"""
import sys, copy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

SRC = sys.argv[1]
OUT = sys.argv[2]

NAVY = RGBColor(0x00, 0x3A, 0x69)
BLUE = RGBColor(0x00, 0x75, 0xBB)
GOLD = RGBColor(0xDB, 0x97, 0x28)
CLAY = RGBColor(0xD5, 0x7C, 0x5C)
RUST = RGBColor(0x87, 0x2C, 0x15)
SAGE = RGBColor(0x81, 0x9E, 0x7E)
PINE = RGBColor(0x1A, 0x58, 0x4D)
SAND = RGBColor(0xF6, 0xF3, 0xF1)
INK = RGBColor(0x1F, 0x1F, 0x1F)
MID = RGBColor(0x4A, 0x4A, 0x4A)
MUTE = RGBColor(0x6E, 0x6E, 0x6E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xD9, 0xD9, 0xD9)

prs = Presentation(SRC)
# drop the template's 31 sample slides
sldIdLst = prs.slides._sldIdLst
for sldId in list(sldIdLst):
    prs.part.drop_rel(sldId.rId)
    sldIdLst.remove(sldId)

L = {l.name.strip(): l for l in prs.slide_layouts}
def layout(name):
    return L[name]

# ── helpers ────────────────────────────────────────────────────────────────
def ph(slide, idx):
    for p in slide.placeholders:
        if p.placeholder_format.idx == idx:
            return p
    raise KeyError(idx)

def no_bullet(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    for tag in ('a:buNone', 'a:buChar', 'a:buAutoNum'):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    pPr.insert(0, etree.SubElement(pPr, qn('a:buNone')))
    pPr.set('marL', '0'); pPr.set('indent', '0')

def bullet(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    for el in pPr.findall(qn('a:buNone')):
        pPr.remove(el)
    pPr.set('marL', str(Inches(0.18))); pPr.set('indent', str(-Inches(0.18)))
    bu = etree.SubElement(pPr, qn('a:buChar')); bu.set('char', '•')

def run(paragraph, text, size=12, bold=False, color=INK, italic=False):
    r = paragraph.add_run(); r.text = text
    f = r.font; f.size = Pt(size); f.bold = bold; f.italic = italic; f.color.rgb = color; f.name = 'Arial'
    return r

def para(tf, text='', size=12, bold=False, color=INK, first=False, space_after=4, bullets=False, italic=False, align=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if bullets: bullet(p)
    else: no_bullet(p)
    p.space_after = Pt(space_after)
    if align: p.alignment = align
    if text: run(p, text, size, bold, color, italic)
    return p

def rich(tf, parts, first=False, space_after=4, bullets=False, size=12):
    """parts = [(text, bold, color)]"""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if bullets: bullet(p)
    else: no_bullet(p)
    p.space_after = Pt(space_after)
    for t, b, c in parts:
        run(p, t, size, b, c)
    return p

def box(slide, x, y, w, h, fill=None, line=None, anchor=MSO_ANCHOR.TOP, margins=(0.12, 0.1, 0.12, 0.1)):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor; tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = [Inches(m) for m in margins]
    if fill is not None:
        tb.fill.solid(); tb.fill.fore_color.rgb = fill
    if line is not None:
        tb.line.color.rgb = line; tb.line.width = Pt(0.75)
    else:
        tb.line.fill.background()
    return tb, tf

def title(slide, text):
    t = slide.shapes.title
    t.text_frame.text = text
    return t

def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

def table(slide, x, y, w, rows, col_widths, header_fill=NAVY, size=10.5, row_h=0.32, first_col_bold=False, zebra=True):
    nrows, ncols = len(rows), len(rows[0])
    shp = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(row_h * nrows))
    tbl = shp.table
    # turn off the template table style banding so our fills rule
    tblPr = tbl._tbl.tblPr
    tblPr.set('firstRow', '0'); tblPr.set('bandRow', '0')
    for i, cw in enumerate(col_widths):
        tbl.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.TOP
            tf = cell.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]; no_bullet(p)
            if r == 0:
                run(p, val, size, True, WHITE)
                cell.fill.solid(); cell.fill.fore_color.rgb = header_fill
            else:
                run(p, val, size, first_col_bold and c == 0, INK)
                cell.fill.solid(); cell.fill.fore_color.rgb = SAND if (zebra and r % 2 == 0) else WHITE
    return tbl

FOOT_Y = 5.18  # keep custom content above the template footer band

# ═════════════════════════════════════════════════════════════════════════
# 1. Cover
s = prs.slides.add_slide(layout('Title Slide - Branded - Dune'))
title(s, 'On-Demand Transit Database')
tf = ph(s, 11).text_frame
tf.text = 'A research inventory of microtransit and demand-response transit across the United States'
p = tf.add_paragraph(); p.text = 'Project summary · September 2026'
notes(s, 'Open with the one-line framing: a research inventory, not an official registry. It exists because no national list of general-public, same-day on-demand transit existed.')

# ═════════════════════════════════════════════════════════════════════════
# 2. At a glance
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'The inventory at a glance')
stats = [('665', 'systems', 'General-public services with a genuine same-day booking option', NAVY),
         ('49 + DC', 'states covered', 'Every state except Alaska has at least one system; California has the most at 94', BLUE),
         ('20', 'fields per system', 'Operator, vendor, booking, fare, hours, fleet, funding, status, coordinates', GOLD)]
x = 0.5
for num, lab, desc, col in stats:
    tb, tf = box(s, x, 1.25, 2.9, 1.95, fill=SAND)
    para(tf, num, 40, True, col, first=True, space_after=0)
    para(tf, lab, 13, True, INK, space_after=6)
    para(tf, desc, 11, False, MID)
    x += 3.05
row2 = [('400', 'Microtransit', PINE), ('265', 'Demand-Response', BLUE), ('659', 'Service-area polygons', RUST), ('26%', 'Fare-free (174 systems)', SAGE)]
x = 0.5
for num, lab, col in row2:
    tb, tf = box(s, x, 3.4, 2.2, 1.0)
    para(tf, num, 26, True, col, first=True, space_after=0)
    para(tf, lab, 11, False, MID)
    x += 2.3
tb, tf = box(s, 0.5, 4.55, 9.0, 0.4)
para(tf, 'Counts as of the 17 September 2026 build. Alaska is the one state with no qualifying system: all three candidates required day-before booking.', 10, False, MUTE, first=True)
notes(s, 'Fare-free is the most audience-friendly number: 174 systems charge nothing, typically funded by municipal or federal grants. Also worth mentioning: every removal, correction and unverified field has a written entry in concerns.csv, 1,063 entries so far, which is the audit trail for the whole inventory.')

# ═════════════════════════════════════════════════════════════════════════
# 3. Definitions
s = prs.slides.add_slide(layout('Simple Slide - Text, 2 columns'))
title(s, 'Key definitions')
tf = ph(s, 12).text_frame; tf.word_wrap = True
para(tf, 'Microtransit', 14, True, PINE, first=True, space_after=2)
para(tf, 'Rides are booked same-day with no fixed route or schedule. Software routes vehicles in real time to pool passengers; pickup is typically within 15–30 minutes. Synonymous with "on-demand transit" in this database.', 11.5, color=MID, space_after=12)
para(tf, 'Demand-Response', 14, True, BLUE, space_after=2)
para(tf, 'Rides are usually scheduled ahead, often by phone, but a same-day request is a real, routinely honored option. Common in rural dial-a-ride programs. Open to the general public.', 11.5, color=MID, space_after=12)
para(tf, 'The typology is about booking model, not vehicle size or branding.', 11, color=MUTE, italic=True)
tf = ph(s, 13).text_frame; tf.word_wrap = True
for head, body in [('Geographic context', 'Urban, Suburban, Rural or Mixed, assigned from the primary service area\'s land use and Census urbanized-area status.'),
                   ('Status', 'Active (plus New, Expanding and Post-Pilot variants), Pilot, or Pilot – Ended. Ended pilots stay in the inventory for the record.'),
                   ('Technology vendor', 'The dispatch and rider-app platform (Via, RideCo, Spare and others), distinct from the operator that runs vehicles and the agency that funds them.'),
                   ('Scheduling window', 'Same-day, Flexible, or Advance. "Advance" means a day-ahead call is the norm but same-day is still honored; systems with no same-day path are out of scope.')]:
    para(tf, head, 12.5, True, NAVY, first=(head == 'Geographic context'), space_after=1)
    para(tf, body, 11, color=MID, space_after=9)
notes(s, 'A rural county dial-a-ride that takes same-day calls is Demand-Response; a Via-powered app service is Microtransit. Full definitions and valid values are on the dashboard Reference tab and in legend.csv.')

# ═════════════════════════════════════════════════════════════════════════
# 4. Scope rules
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'Scope rules')
tb, tf = box(s, 0.5, 1.1, 9.0, 0.4)
para(tf, 'One test decides scope: can a rider book and ride today?', 14, True, NAVY, first=True)
rows = [('Included', 'Excluded'),
        ('Same-day app or phone booking with no fixed schedule, even with a short same-day lead time (e.g. two hours). Advance booking may be preferred or the norm.',
         'No same-day option at all: booking required by a cutoff on a day before the trip ("by 4pm the day before", "24-hour advance", "next-day only").'),
        ('Open to the general public, even if seniors or riders with disabilities are prioritized.',
         'Paratransit restricted to eligibility-certified riders (ADA, senior or disability certification required).'),
        ('Publicly accessible services, even if privately sponsored.',
         'Employer, apartment, campus-only or closed-loop shuttles.'),
        ('Planned or pilot services with a confirmed vendor and funding.',
         'Services that have permanently ceased operations.')]
table(s, 0.5, 1.55, 9.0, rows, [4.5, 4.5], size=10.5, row_h=0.5)
tb, tf = box(s, 0.5, 4.5, 9.0, 0.6)
para(tf, 'Two scope rulings reshaped the inventory: retiring paratransit as a type (July 2026, 170 rows removed) and clarifying the same-day test (August 2026, 215 rows removed after a source check of every advance-booking row).', 10.5, color=MID, first=True)
notes(s, 'The August ruling was the "spirit of the rule": the test is same-day capability, not a literal hour count. A "call by 4:30pm the day before" policy is out even though that can be under 24 hours.')

# ═════════════════════════════════════════════════════════════════════════
# 5. Timeline
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'Methodology timeline')
steps = [('Before June 2026', 'Manual NC collection', 'North Carolina systems researched and entered by hand, one agency at a time, with service areas digitized manually. The model for every later row.', SAGE),
         ('June 2026', 'Seed inventory', '241 systems in 24 states from the NC work, an existing spreadsheet, and supplemental California and Colorado lists.', MUTE),
         ('July 2026', 'Expand to 50 states', 'Nine research batches covered the 27 uncovered states, then a high-recall deep sweep of every state in three waves, reading state DOT provider rosters against the CSV.', BLUE),
         ('July 2026', 'Retire paratransit', '170 eligibility-restricted rows removed after a keyword classifier plus row-by-row checks. Scope narrowed to general-public service only.', CLAY),
         ('August 2026', 'Same-day sweep', 'Every advance-booking row re-checked against a primary source in 17 parallel state batches: 215 removed, about 40 corrected and kept, 64 flagged for follow-up.', GOLD),
         ('September 2026', 'Service-area boundaries', 'Polygons for 659 of 665 systems in 12 staged batches; nine replaced with agencies\' own GTFS-Flex geofences.', PINE)]
x = 0.5; w = 1.5
for when, head, desc, col in steps:
    bar = s.shapes.add_shape(1, Inches(x), Inches(1.2), Inches(w - 0.1), Inches(0.06))
    bar.fill.solid(); bar.fill.fore_color.rgb = col; bar.line.fill.background()
    tb, tf = box(s, x, 1.3, w - 0.1, 2.6, margins=(0.02, 0.06, 0.06, 0.04))
    para(tf, when.upper(), 8, True, col, first=True, space_after=2)
    para(tf, head, 11.5, True, INK, space_after=4)
    para(tf, desc, 9, color=MID)
    x += w
tb, tf = box(s, 0.5, 3.7, 9.0, 0.95, fill=SAND, anchor=MSO_ANCHOR.MIDDLE)
rich(tf, [('Row count over time   ', True, INK), ('241 → 394 → 597 → 724 → 880 → ', False, MID), ('665', True, INK)], first=True, size=13, space_after=2)
para(tf, 'The count peaks before each scope pass; the final number is smaller than the peak because the rules tightened.', 10, color=MUTE)
notes(s, 'Growth was not monotonic. Two-thirds of the work after July was verification and removal, not discovery.')

# ═════════════════════════════════════════════════════════════════════════
# 6. Pipeline
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'How a system gets in')
steps = [('1', 'Discover', 'Read what the CSV already has for a state, then search state DOT §5311 and §5310 provider rosters, NTD profiles, press releases and local news coverage for what is missing.'),
         ('2', 'Verify against a primary source', 'Agency or operator page first. News articles sometimes provide information that is not supported by operators.'),
         ('3', 'Log every decision', 'Each add, removal, correction and unverified field gets a concerns.csv entry with a citation. Nothing is fixed silently.'),
         ('4', 'Build and publish', 'A build script validates the CSV, derives clean categories from free text, and writes the JSON the dashboard reads. Push to GitHub Pages.')]
x = 0.5; w = 2.18
for n, head, desc in steps:
    tb, tf = box(s, x, 1.2, w - 0.12, 2.35, fill=SAND)
    para(tf, n, 26, True, BLUE, first=True, space_after=2)
    para(tf, head, 12, True, INK, space_after=4)
    para(tf, desc, 9.5, color=MID)
    x += w + 0.08
for i, (head, desc) in enumerate([('Verify before removal', 'A row leaves only after a primary source confirms it fails a rule. Rows where no source states a policy are kept and flagged, not removed on a guess.'),
                                  ('Integrity check after every sweep', 'Every logged removal is cross-referenced against the live CSV. This caught two research batches whose results were read but never applied.')]):
    tb, tf = box(s, 0.5 + i * 4.6, 3.75, 4.4, 1.3)
    para(tf, head, 12, True, RUST, first=True, space_after=2)
    para(tf, desc, 10, color=MID)
notes(s, 'The verify-before-removal rule came from a real mistake: a bulk-imported Arizona row described a service as senior-only; the city\'s own page showed a general-public TNC-subsidy program with same-day booking.')

# ═════════════════════════════════════════════════════════════════════════
# 7. Sources
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'Sources consulted')
rows = [('Source type', 'Examples', 'What it gave us'),
        ('Agency and operator websites', 'City, county, transit-agency and tribal pages; rider handbooks; Via/RideCo/Spare-branded booking pages', 'Primary source for scope calls, booking method, hours, fares, status'),
        ('State DOT program documents', 'Virginia DRPT rural microtransit toolkit; MDOT ConnectMS regional map; state §5311/§5310 provider rosters; WI Legislative Fiscal Bureau paper 43', 'Best structured data on fleets and service areas; discovery of rural systems'),
        ('Federal Transit Administration', 'National Transit Database agency profiles; AIM and IMI grant announcements', 'Confirms general-public rural status, vehicles in service, funding; grants rarely give specs'),
        ('Press and vendor releases', 'Local news, agency press releases, vendor case studies', 'Launch dates, pilot outcomes, vendor identity'),
        ('Open transit data', 'Mobility Database GTFS catalog; Trillium-hosted GTFS-Flex feeds (locations.geojson)', 'Nine agency-published service-area geofences; booking-rule cross-checks'),
        ('Census Bureau', 'TIGER/Line cartographic boundary files, 2023, 1:500k (places, county subdivisions, counties, AIANNH areas)', 'Proxy polygons for 650 systems; urbanized-area context'),
        ('Secondary signals, used with caution', 'App-store package names (e.g. com.ridewithvia...), Wikipedia, cached snapshots', 'Vendor inference, flagged as unconfirmed in the log')]
table(s, 0.5, 1.15, 9.0, rows, [2.2, 4.0, 2.8], size=9, row_h=0.44, first_col_bold=True)
tb, tf = box(s, 0.5, 4.72, 9.0, 0.4)
para(tf, 'Rule of thumb learned early: a state DOT evaluation document beats ten press releases for structured fields.', 10, color=MUTE, italic=True, first=True)
notes(s, 'Mention the Virginia DRPT toolkit example: one PDF had real vehicle specs for two FTA-funded pilots that no news coverage contained. On vendors: Via is the most frequently identified platform, named outright on 134 systems, but the vendor is unrecorded for half the inventory, so quote counts, not market share.')

# ═════════════════════════════════════════════════════════════════════════
# 8. Agents
s = prs.slides.add_slide(layout('Simple Slide – 3 text boxes'))
title(s, 'Use of AI agents')
tf = ph(s, 10).text_frame; tf.word_wrap = True
para(tf, 'Claude Code sessions ran the repetitive research in parallel batches and drafted candidate rows and boundary specs; every scope rule and every borderline call stayed with a person, and every agent action left a logged, reversible trail.', 11, color=MID, first=True)
cols = [(17, 'What agents did', ['State-by-state discovery sweeps in parallel batches (up to 17 at once), each returning candidate rows with citations', 'Source re-checks of every advance-booking row during the same-day sweep', 'Drafting a boundary spec per system, then auditing and researching flagged ones', 'Matching all 665 rows against GTFS feed catalogs and inspecting feed contents']),
        (18, 'What stayed with a human', ['Every scope ruling: the same-day test, paratransit retirement, tribal-community services as general public, TNC fare-subsidy programs as systems', 'Borderline rows, one at a time rather than in batches', 'North Carolina boundaries, drawn by hand, and review of low-confidence proxies', 'Deciding when a sweep is done: small stages, one commit per stage, re-audit']),
        (19, 'Guardrails and lessons', ['Agents never remove a row on the row\'s own text; a primary source must confirm the failure', 'Every agent-added row carries a Data Gap entry listing the fields it could not confirm', 'A name-matched GTFS feed is not enough: five geofences were rejected because they belonged to a paratransit route on the same feed'])]
for idx, head, items in cols:
    tf = ph(s, idx).text_frame; tf.word_wrap = True
    para(tf, head, 12, True, NAVY, first=True, space_after=4)
    for it in items:
        para(tf, it, 9.5, color=MID, bullets=True, space_after=3)
notes(s, 'Be candid that agents also made mistakes: one batch misread the advance-booking rule and included seven Texas systems it should have flagged; that is what prompted the explicit policy ruling. The process is designed so mistakes are logged and reversible.')

# ═════════════════════════════════════════════════════════════════════════
# 9. Boundaries
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'Service-area boundaries')
tb, tf = box(s, 0.5, 1.15, 4.3, 3.95)
para(tf, 'Almost no agency publishes a downloadable service area, so each polygon is built from the best available geography, and its popup says what it was built from and whether it is exact or approximate.', 10.5, color=MID, first=True, space_after=8)
para(tf, 'Sources, in order of preference', 11, True, NAVY, space_after=3)
for i, t in enumerate(['The agency\'s own GTFS-Flex geofence, where one exists', 'Census cartographic boundaries matched to the described area: city, town, county, tribal land', 'Charlotte neighborhood areas and Census tracts for a few NC zones', 'A circle of the agency-stated size when only a size is published'], 1):
    para(tf, f'{i}.  {t}', 10, color=MID, space_after=3)
para(tf, 'Every choice is recorded in a per-state spec file, so the GeoJSON regenerates deterministically. Six multi-zone systems still have no polygon because their zones are named only by neighborhood.', 9.5, color=MUTE, space_after=0)
rows = [('Boundary type', 'Accuracy', 'Systems'),
        ('Agency GTFS-Flex geofence', 'Exact', '9'), ('City limits', 'High', '217'), ('County / multi-county', 'High', '183'),
        ('Town boundaries', 'Good', '184'), ('Tribal land', 'Good', '17'), ('Municipality + stated radius', 'Moderate', '13'),
        ('Neighborhoods / tracts', 'Moderate', '4'), ('Stated-size circle', 'Low', '32')]
tbl = table(s, 5.1, 1.15, 4.4, rows, [2.4, 1.1, 0.9], size=10, row_h=0.36)
for r in range(len(rows)):
    tbl.cell(r, 2).text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
tb, tf = box(s, 5.1, 4.5, 4.4, 0.5)
para(tf, 'Census TIGER/Line cartographic boundary files, 2023 vintage, 1:500k. Counts from the 17 September 2026 build.', 8.5, color=MUTE, first=True)
notes(s, '421 polygons are exact administrative units, 238 are labeled approximate. A county polygon for a county-wide dial-a-ride is accurate; a circle for "about 12 square miles" shows scale, not shape.')

# ═════════════════════════════════════════════════════════════════════════
# 10. Completeness (native bar chart)
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'Data gaps by field')
fields = [('Vehicle count', 8), ('Fleet description', 42), ('Technology vendor', 54), ('Launch year', 57), ('Funding source', 59),
          ('Service hours', 69), ('Fare', 81), ('Website', 87), ('Scheduling window', 93), ('Booking method', 99)]
cd = CategoryChartData(); cd.categories = [f for f, _ in fields]; cd.add_series('Share of systems with a value (%)', [v for _, v in fields])
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.4), Inches(1.1), Inches(5.6), Inches(3.95), cd)
ch = gf.chart
ch.has_legend = False; ch.has_title = False
ch.font.size = Pt(10); ch.font.name = 'Arial'; ch.font.color.rgb = MID
plot = ch.plots[0]; plot.gap_width = 55; plot.has_data_labels = True
dl = plot.data_labels; dl.font.size = Pt(9.5); dl.font.color.rgb = INK; dl.number_format = '0"%"'; dl.number_format_is_linked = False; dl.position = XL_LABEL_POSITION.OUTSIDE_END
ser = plot.series[0]; ser.format.fill.solid(); ser.format.fill.fore_color.rgb = BLUE
va = ch.value_axis; va.maximum_scale = 100; va.minimum_scale = 0; va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = LINE; va.tick_labels.font.size = Pt(9); va.tick_labels.font.color.rgb = MUTE; va.format.line.fill.background()
va.tick_labels.number_format = '0"%"'; va.tick_labels.number_format_is_linked = False
ca = ch.category_axis; ca.tick_labels.font.size = Pt(10); ca.format.line.color.rgb = LINE; ca.has_major_gridlines = False
tb, tf = box(s, 6.2, 1.15, 3.3, 1.75, fill=SAND)
para(tf, 'Why the gaps skew rural', 11.5, True, NAVY, first=True, space_after=3)
para(tf, 'Legacy dial-a-ride programs rarely publish a launch date, vendor or fleet. Missing values cluster in Demand-Response rows: 192 of 265 have no launch year.', 9.5, color=MID)
tb, tf = box(s, 6.2, 3.05, 3.3, 1.75, fill=SAND)
para(tf, 'Read the charts accordingly', 11.5, True, NAVY, first=True, space_after=3)
para(tf, 'The dashboard\'s fleet-propulsion and accessibility charts count keyword mentions in the Fleet and Notes fields, not fleet audits. "Not mentioned" is a gap in the source, not evidence of absence.', 9.5, color=MID)
tb, tf = box(s, 0.5, 4.95, 9.0, 0.3)
para(tf, 'Share of 665 systems with a value other than "Not specified", 17 September 2026 build.', 8.5, color=MUTE, first=True)
notes(s, 'The bar lengths are the share of rows with any value, not the share verified. Fare is 81% present, but about a fifth of those are "same as bus fare" or "varies" rather than a dollar amount.')

# ═════════════════════════════════════════════════════════════════════════
# 11. Gaps
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'Known gaps')
items = [('Scheduling policy unconfirmed for 64 rows', 'No web source states whether same-day is honored. Kept in scope and logged; each needs direct follow-up with the operator, not another web search.', RUST),
         ('Supplemental CA/CO vendor field is unreliable', 'Four of four "Via" labels checked were wrong. Vendors on those rows are unverified unless independently confirmed.', RUST),
         ('Coordinates are centroids, not zone centers', 'Many pins sit on a city hall or county seat. Fine nationally; the polygon, where present, is the better guide when zoomed in.', GOLD),
         ('Multi-zone systems lack polygons or show one zone', 'Six large systems (e.g. MARTA Reach, LA Metro Micro) have no polygon; a few GTFS-Flex geofences cover only the zones the feed includes.', GOLD),
         ('Two vendor conflicts unresolved', 'Rows where an official site and a vendor press release disagree (e.g. RTS On Demand) show as "Not specified" until resolved.', MUTE),
         ('Discovery sources not yet exhausted', 'FTA AIM/IMI award lists and NCDOT program documents are unchecked; Texas TNC fare-subsidy programs are ruled in scope but not yet added.', MUTE)]
for i, (head, desc, col) in enumerate(items):
    cx = 0.5 + (i % 2) * 4.6; cy = 1.15 + (i // 2) * 1.3
    tb, tf = box(s, cx, cy, 4.4, 1.2, fill=SAND)
    para(tf, head, 11, True, col, first=True, space_after=2)
    para(tf, desc, 9.5, color=MID)
tb, tf = box(s, 0.5, 5.0, 9.0, 0.3)
para(tf, 'All items are tracked in concerns.csv and NOTES.md in the repository.', 8.5, color=MUTE, first=True)
notes(s, 'If asked "how confident are you overall": high for existence and general-public status of each row; moderate for scheduling policy on the rural demand-response rows; low for fleet and vendor details on bulk-imported rows.')

# ═════════════════════════════════════════════════════════════════════════
# 12. Assumptions
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'Key assumptions')
rows = [('Question', 'Ruling applied'),
        ('Is "advance preferred" the same as "advance required"?', 'No. A system stays in if same-day is genuinely honored, even when a day-ahead call is encouraged or earns a discount.'),
        ('Tribal transit open only to reservation residents', 'Counted as general public for that community, not as eligibility-restricted paratransit.'),
        ('City subsidy on Uber or Lyft rides, no agency fleet', 'Counts as a system: the rider experience is same-day app booking funded by the public.'),
        ('A pilot that has ended', 'Kept with status "Pilot – Ended" for the record; permanently discontinued regular services are removed.'),
        ('One service operating in two states', 'Listed once per state (e.g. Advance Transit in NH and VT); do not double-count in national totals.'),
        ('Messy free text in vendor, status and year fields', 'The build derives normalized categories for filters and charts; the researcher\'s original wording stays on each card.'),
        ('A state with few or zero rows after a scope pass', 'Treated as a genuine outcome, not forced back up; Alaska currently has none.')]
table(s, 0.5, 1.15, 9.0, rows, [3.3, 5.7], size=10, row_h=0.46, first_col_bold=True)
notes(s, 'These are the calls most likely to be questioned by a transit audience. Each was made once, written down, and applied uniformly, which matters more than whether every reviewer would make the same call.')

# ═════════════════════════════════════════════════════════════════════════
# 13. Dashboard
s = prs.slides.add_slide(layout('Simple Slide - No text box'))
title(s, 'The dashboard')
views = [('Cards', 'Every system with its operator, vendor, fare and launch year; expand for booking, hours, funding, fleet and notes, then open full details.'),
         ('Map', 'Pins colored by geographic context, type, status, vendor or state; service-area polygons appear when a state is selected; a year slider animates growth.'),
         ('Analytics', 'Growth over time, geography, fares, vendors, states, status, fleet propulsion, accessibility and fleet size, all recomputed for the current filter.'),
         ('Reference', 'Scope rules, field definitions, boundary sources and the data-quality history, so a reader can judge each number.')]
x = 0.5; w = 2.18
for head, desc in views:
    tb, tf = box(s, x, 1.2, w - 0.12, 2.15, fill=SAND)
    para(tf, head, 15, True, NAVY, first=True, space_after=5)
    para(tf, desc, 9.5, color=MID)
    x += w + 0.08
tb, tf = box(s, 0.5, 3.6, 9.0, 1.0, fill=NAVY, anchor=MSO_ANCHOR.MIDDLE)
rich(tf, [('Filters   ', True, WHITE), ('Search · State · Type · Geographic context · Status · Vendor · Launch year. They apply to Cards, Map and Analytics at once, so "rural demand-response in Wisconsin launched before 2010" is three clicks.', False, WHITE)], first=True, size=10.5)
tb, tf = box(s, 0.5, 4.75, 9.0, 0.35)
para(tf, 'Static site on GitHub Pages: jfish79.github.io/odt-dashboard. The CSV is the source of truth; a build script regenerates everything the page reads.', 9, color=MUTE, first=True)
notes(s, 'If demoing live: start on the Map with Geographic Context coloring, select one state to show polygons, play the growth slider, then switch to Analytics to show the charts follow the filter.')

# ═════════════════════════════════════════════════════════════════════════
# 14. Close
s = prs.slides.add_slide(layout('1_End Slide - Simple with Text'))
title(s, 'Questions?')
ph(s, 11).text_frame.text = 'jfish79.github.io/odt-dashboard'
tf = ph(s, 57).text_frame; tf.word_wrap = True
for i, (head, body) in enumerate([('Use it', 'Data is CC BY 4.0; code is MIT. Cite as "On-Demand Transit Database". Verify hours and fares with the agency before travel planning.'),
                                  ('Improve it', 'Operator follow-up on the 64 unconfirmed scheduling policies; agency zone maps for the six unmapped systems; FTA award lists as a discovery source.'),
                                  ('Correct it', 'Edit the CSV, log the reason in concerns.csv, run the build, push. Errors and omissions: contact the research team.')]):
    para(tf, head, 12, True, NAVY, first=(i == 0), space_after=2)
    para(tf, body, 10, color=MID, space_after=10)
notes(s, 'Close on the invitation: corrections from agencies are the fastest way to raise confidence on the rural rows.')

prs.save(OUT)
print('saved', OUT, len(prs.slides), 'slides')
