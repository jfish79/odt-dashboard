"""November 2026 update of the project deck: latest boundary work + validation.

    python3 scripts/deck/update_deck_2026_11.py [out.pptx] [--before IMG --after IMG]

Edits a COPY of the user's hand-edited docs/ODT-Database-Project-Summary.pptx in
place with python-pptx (see NOTES.md "Project deck": never regenerate over it).
Numbers come from data/systems.json and data/validation.json at run time, so
rerun after a rebuild. Writes docs/ODT-Database-Project-Summary-2026-11.pptx
by default; the source deck is never modified.
"""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "ODT-Database-Project-Summary.pptx"

NAVY = RGBColor(0x00, 0x3A, 0x69)
BLUE = RGBColor(0x00, 0x75, 0xBB)
GOLD = RGBColor(0xDB, 0x97, 0x28)
RUST = RGBColor(0x87, 0x2C, 0x15)
BRICK = RGBColor(0xA3, 0x3A, 0x1F)  # chart-only: RUST is too dark for the lightness band
PINE = RGBColor(0x1A, 0x58, 0x4D)
SAND = RGBColor(0xF6, 0xF3, 0xF1)
INK = RGBColor(0x1F, 0x1F, 0x1F)
MID = RGBColor(0x4A, 0x4A, 0x4A)
MUTE = RGBColor(0x6E, 0x6E, 0x6E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xD9, 0xD9, 0xD9)

BUILD_DATE = "19 November 2026"


# ── helpers (same conventions as build_deck.py) ───────────────────────────
def no_bullet(p):
    pPr = p._p.get_or_add_pPr()
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    pPr.insert(0, etree.SubElement(pPr, qn("a:buNone")))
    pPr.set("marL", "0")
    pPr.set("indent", "0")


def run(p, text, size=12, bold=False, color=INK):
    r = p.add_run()
    r.text = text
    f = r.font
    f.size, f.bold, f.name = Pt(size), bold, "Arial"
    f.color.rgb = color
    return r


def para(tf, text="", size=12, bold=False, color=INK, first=False, space_after=4):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    no_bullet(p)
    p.space_after = Pt(space_after)
    if text:
        run(p, text, size, bold, color)
    return p


def box(slide, x, y, w, h, fill=None, margins=(0.12, 0.1, 0.12, 0.1), anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = [Inches(m) for m in margins]
    if fill is not None:
        tb.fill.solid()
        tb.fill.fore_color.rgb = fill
    tb.line.fill.background()
    return tb, tf


def shape(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(name)


def replace(sh, old, new):
    """Replace text inside a single run, keeping its formatting."""
    frames = [sh.text_frame] if sh.has_text_frame else []
    if sh.has_table:
        frames = [c.text_frame for r in sh.table.rows for c in r.cells]
    for tf in frames:
        for p in tf.paragraphs:
            for r in p.runs:
                if old in r.text:
                    r.text = r.text.replace(old, new)
                    return
    raise ValueError(f"{old!r} not found in {sh.name}")


def set_para(p, text):
    """Put `text` in the paragraph's first run and drop the other runs."""
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def next_id(slide):
    return max(int(el.get("id")) for el in slide.shapes._spTree.iter(qn("p:cNvPr"))) + 1


def clone(slide, sh):
    el = copy.deepcopy(sh._element)
    slide.shapes._spTree.append(el)
    el.find(".//" + qn("p:cNvPr")).set("id", str(next_id(slide)))
    return slide.shapes[-1]


def move_slide(prs, slide, index):
    lst = prs.slides._sldIdLst
    for el in lst:
        if prs.part.related_part(el.get(qn("r:id"))) is slide.part:
            lst.remove(el)
            lst.insert(index, el)
            return


def new_slide(prs, title, after_index):
    lay = {l.name.strip(): l for l in prs.slide_layouts}["Simple Slide - No text box"]
    s = prs.slides.add_slide(lay)
    s.shapes.title.text_frame.text = title
    move_slide(prs, s, after_index)
    return s


def card(slide, x, y, w, h, head, body, head_color=INK, num=None, num_color=BLUE, head_size=12, body_size=9.5):
    _, tf = box(slide, x, y, w, h, fill=SAND)
    first = True
    if num is not None:
        para(tf, num, 26, True, num_color, first=True, space_after=2)
        first = False
    para(tf, head, head_size, True, head_color, first=first, space_after=4)
    para(tf, body, body_size, False, MID, space_after=0)
    return tf


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ── numbers ───────────────────────────────────────────────────────────────
def stats():
    S = json.load(open(ROOT / "data" / "systems.json"))
    V = json.load(open(ROOT / "data" / "validation.json"))
    bt = Counter((s.get("boundary") or {}).get("type") for s in S)
    n = {"systems": len(S), "poly": sum(1 for s in S if s.get("boundary")), "bt": bt,
         "none": [s["name"] for s in S if not s.get("boundary")]}
    n["agency"] = bt["agency_gis"]
    n["gtfs"] = bt["gtfs_flex"]
    n["census"] = n["poly"] - n["agency"] - n["gtfs"]
    n["exact_proxy"] = bt["city"] + bt["places"] + bt["county"] + bt["counties"] + bt["cousubs"] + bt["cousub"]
    R = V["reviews"]
    n["reviewed"] = len(R)
    n["states_reviewed"] = Counter(r["state"] for r in R)
    n["by"] = Counter((r["state"], r["by"]) for r in R)
    checks = Counter()
    per_field = {f: Counter() for f in V["fields"]}
    for r in R:
        for f, x in r["checks"].items():
            checks[x or "Not checked"] += 1
            per_field[f][x or "Not checked"] += 1
    n["checks"], n["per_field"], n["fields"] = checks, per_field, V["fields"]
    n["boundary"] = Counter(r["boundary"] or "Not checked" for r in R)
    F = V["findings"]
    n["corr_types"] = Counter(f.get("type") for f in F if f["kind"] == "field")
    n["scope_flags"] = [f for f in F if f["kind"] == "scope"]
    n["read"] = V["read"]
    n["applied"] = sum(1 for f in F if f["kind"] == "field" and f.get("status") == "applied")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(ROOT / "docs" / "ODT-Database-Project-Summary-2026-11.pptx"))
    ap.add_argument("--before", help="map screenshot: Census proxy polygon")
    ap.add_argument("--after", help="map screenshot: agency zone map")
    ap.add_argument("--example", default="", help="caption for the before/after pair")
    args = ap.parse_args()
    n = stats()
    prs = Presentation(SRC)
    sl = list(prs.slides)  # original order, 0-based

    # Slide 3: inventory at a glance
    s = sl[2]
    replace(shape(s, "TextBox 7"), "659", str(n["poly"]))
    replace(shape(s, "TextBox 9"), "17 September 2026", BUILD_DATE)

    # Slide 5: timeline, add a seventh step
    s = sl[4]
    rect = clone(s, shape(s, "Rectangle 12"))
    rect.fill.fore_color.rgb = NAVY
    tb = clone(s, shape(s, "TextBox 13"))
    ps = tb.text_frame.paragraphs
    set_para(ps[0], "NOVEMBER 2026")
    for r in ps[0].runs:
        r.font.color.rgb = NAVY
    set_para(ps[1], "Validation and zone maps")
    set_para(ps[2], f"Colleagues re-checked {n['reviewed']} systems in two states; agency-published zone maps "
                    f"replace Census stand-ins for {n['agency']} systems.")
    pairs = [(f"Rectangle {2 * i + 2}", f"TextBox {2 * i + 3}") for i in range(6)]
    items = [(shape(s, a), shape(s, b)) for a, b in pairs] + [(rect, tb)]
    w, step = 1.2, 1.3
    for i, (r_, t_) in enumerate(items):
        x = Inches(0.5 + i * step)
        r_.left, r_.width = x, Inches(w)
        t_.left, t_.width = x, Inches(w)
        t_.height = Inches(2.35)

    # Slide 7: sources table, add the regional/state GIS row
    s = sl[6]
    tblshape = next(sh for sh in s.shapes if sh.has_table)
    replace(tblshape, "Proxy polygons for 650 systems", f"Proxy polygons for {n['census']} systems")
    tbl = tblshape.table
    tr = copy.deepcopy(tbl._tbl.tr_lst[5])  # after "Open transit data"
    tbl._tbl.tr_lst[5].addnext(tr)
    texts = ["Agency and regional GIS portals",
             "ArcGIS Online; maps embedded on agency pages (Google My Maps, KML); state DOT and MPO layers "
             "(CTDOT, MassDOT, Virginia DRPT, NCTCOG, H-GAC, PSRC)",
             f"Agency-drawn zone polygons for {n['agency']} systems"]
    for c, t in zip(tbl.rows[6].cells, texts):
        set_para(c.text_frame.paragraphs[0], t)
    for i, row in enumerate(tbl.rows):
        row.height = Inches(0.40)

    # Slide 9: service-area boundaries
    s = sl[8]
    tb = shape(s, "TextBox 2")
    ps = tb.text_frame.paragraphs
    set_para(ps[2], "1.  The agency's own zone: a GTFS-Flex geofence, or a map the agency, state DOT or MPO "
                    "publishes (ArcGIS, Google My Maps, KML)")
    k = len(n["none"])
    set_para(ps[7], f"{k} system{'s' if k != 1 else ''} still {'have' if k != 1 else 'has'} no polygon because "
                    "their zones are named only by neighborhood.")
    tblshape = next(sh for sh in s.shapes if sh.has_table)
    tbl = tblshape.table
    tr = copy.deepcopy(tbl._tbl.tr_lst[1])
    tbl._tbl.tr_lst[1].addnext(tr)
    bt = n["bt"]
    rows = [("Agency GTFS-Flex geofence", "Exact", bt["gtfs_flex"]),
            ("Agency zone map", "Exact", bt["agency_gis"]),
            ("City limits", "High", bt["city"]),
            ("County / multi-county", "High", bt["county"] + bt["counties"]),
            ("Town boundaries", "Good", bt["places"] + bt["cousubs"] + bt["cousub"]),
            ("Tribal land", "Good", bt["tribal"]),
            ("Municipality + stated radius", "Moderate", bt["buffered"]),
            ("Neighborhoods / tracts", "Moderate", bt["census_tracts"] + bt["neighborhood_npa"]),
            ("Stated-size circle", "Low", bt["zone_approx"])]
    assert sum(r[2] for r in rows) == n["poly"], (sum(r[2] for r in rows), n["poly"])
    for i, (a, b, c) in enumerate(rows, start=1):
        cells = tbl.rows[i].cells
        for cell, t in zip(cells, (a, b, str(c))):
            set_para(cell.text_frame.paragraphs[0], t)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else SAND
    for row in tbl.rows:
        row.height = Inches(0.32)
    replace(shape(s, "TextBox 4"), "17 September 2026", BUILD_DATE)

    # Slide 11: known gaps, the multi-zone card
    s = sl[10]
    ps = shape(s, "TextBox 5").text_frame.paragraphs
    set_para(ps[0], "Many polygons are still Census stand-ins")
    set_para(ps[1], f"{n['census']} systems use a city, town or county outline that can overstate a smaller zone; "
                    f"{k} have no polygon. Each needs an agency zone map.")

    # Slide 13: dashboard, five cards with the Validation tab
    s = sl[12]
    cards = [shape(s, f"TextBox {i}") for i in (2, 3, 4, 5)]
    vt = clone(s, cards[3])
    ps = vt.text_frame.paragraphs
    set_para(ps[0], "Validation")
    set_para(ps[1], "Review progress by state, proposed corrections with sources, scope flags and boundary "
                    "findings, refreshed as reviews come in.")
    for i, c in enumerate(cards + [vt]):
        c.left, c.width = Inches(0.5 + i * 1.83), Inches(1.68)

    # New slide after 9: boundary refinement
    s = new_slide(prs, "Finding agency zone maps", 9)
    _, tf = box(s, 0.5, 1.05, 9.0, 0.45)
    para(tf, "A city or county outline is exact as geography but often too large for the service. "
             "In November we searched for the zones agencies draw themselves.", 11, False, MID, first=True)
    steps = [("1", "Search the ArcGIS catalog", "Each system's name and operator searched in ArcGIS Online; every "
                                                 "polygon layer checked for location and size against the current one."),
             ("2", "Scan agency web pages", "Each system's page and its map links read for embedded ArcGIS maps, "
                                            "Google My Maps, KML and GeoJSON files."),
             ("3", "Harvest regional layers", "State DOTs and MPOs often publish one layer for many systems: CTDOT, "
                                              "MassDOT, Virginia DRPT, NCTCOG, H-GAC, PSRC, Tahoe RPA.")]
    have_imgs = args.before and args.after
    if have_imgs:
        for i, (num, head, body) in enumerate(steps):
            card(s, 0.5, 1.6 + i * 0.9, 4.3, 0.82, f"{num}.  {head}", body, head_size=11, body_size=9)
        iw, ih = 2.15, 2.15 / 1.38
        s.shapes.add_picture(args.before, Inches(5.15), Inches(1.6), Inches(iw), Inches(ih))
        s.shapes.add_picture(args.after, Inches(7.4), Inches(1.6), Inches(iw), Inches(ih))
        for x, cap in ((5.15, "Before: Census city outline"), (7.4, "After: agency zone map")):
            _, tf = box(s, x, 1.62 + ih, iw, 0.28, margins=(0, 0.02, 0, 0))
            para(tf, cap, 9, True, INK, first=True, space_after=0)
        if args.example:
            _, tf = box(s, 5.15, 1.9 + ih, 4.35, 0.5, margins=(0, 0, 0, 0))
            para(tf, args.example, 8.5, False, MUTE, first=True, space_after=0)
        y, h = 4.35, 0.8
    else:
        for i, (num, head, body) in enumerate(steps):
            card(s, 0.5 + i * 3.05, 1.6, 2.9, 1.75, head, body, num=num)
        y, h = 3.55, 0.95
    _, tf = box(s, 0.5, y, 9.0, h, fill=None)
    p = para(tf, "", first=True, space_after=3)
    run(p, f"Agency-drawn polygons: {n['gtfs']} in September  \u2192  {n['gtfs'] + n['agency']} now.   ", 13, True, INK)
    para(tf, "Machine time is seconds per system; review is the cost, about 15 minutes per 25 systems, because most "
             "layers need zones matched to rows and paratransit or proposed zones dropped.", 10, False, MUTE, space_after=0)
    notes(s, "Prompted by the validation: reviewers kept marking city-limits polygons as 'partly matches'. "
             "'Exact' in our popups meant an exact administrative unit, not the exact service zone; of 15 exact rows "
             "reviewers checked, 10 matched the agency map. Example: Stamford's microtransit zone is about 5 square "
             "miles; the city polygon was 39. Colorado and Ohio were left out while their reviews were open. Layers "
             "still waiting on a decision: an NC State compilation of NC zones and three Arizona layers.")

    # New slide after the zone-map slide: before/after pairs
    pairs = [("Denver Connector", "denver_connector",
              "Census city outline, 155 sq mi", "Denver's three published zones, 18 sq mi",
              "Source: City and County of Denver, Connector Areas 2025."),
             ("Houston Community Connector", "houston_cc",
              "Census city outline, 673 sq mi", "Five neighborhood zones, 13 sq mi",
              "Source: H-GAC regional microtransit layer, Sept 2026.")]
    img = ROOT / "docs" / "img"
    if all((img / f"{k}_{w}.jpg").exists() for _, k, *_ in pairs for w in ("before", "after")):
        s = new_slide(prs, "Before and after", 10)
        iw, ih = 2.3, 2.3 / 1.38
        for r, (label, key, cap_b, cap_a, src) in enumerate(pairs):
            y = 1.1 + r * 2.0
            _, tf = box(s, 0.5, y + 0.2, 2.9, ih)
            para(tf, label, 12.5, True, INK, first=True, space_after=4)
            para(tf, cap_b, 9.5, False, MID, space_after=1)
            para(tf, "\u2193", 11, True, BLUE, space_after=1)
            para(tf, cap_a, 9.5, True, PINE, space_after=6)
            para(tf, src, 8, False, MUTE, space_after=0)
            for c, (w, cap) in enumerate((("before", "Before"), ("after", "After"))):
                x = 4.0 + c * (iw + 0.2)
                _, tf = box(s, x, y, iw, 0.22, margins=(0, 0, 0, 0))
                para(tf, cap.upper(), 8, True, MUTE, first=True, space_after=0)
                pic = s.shapes.add_picture(str(img / f"{key}_{w}.jpg"), Inches(x), Inches(y + 0.22), Inches(iw), Inches(ih))
                pic.line.color.rgb = LINE
                pic.line.width = Pt(0.75)
        notes(s, "Denver Connector is the example that started the zone-map pass: the dashboard drew all of Denver "
                 "for a service that runs in three neighborhood zones. Both 'after' maps come from public layers the "
                 "city or regional council publishes; the 'before' maps show the Census city outline with the "
                 "dashboard popup open. Map scales differ between before and after.")
        shift = 1
    else:
        shift = 0

    # New slides after known gaps: validation method + findings
    # (original 11 is now at index 11 because one slide was inserted before it)
    s = new_slide(prs, "Colleague validation", 12 + shift)
    _, tf = box(s, 0.5, 1.05, 9.0, 0.45)
    para(tf, "Colleagues re-check rows against agency sources, one state at a time, in a shared workbook.",
         11, False, MID, first=True)
    steps = [("1", "Shared review workbook", "One tab per state, generated from the CSV. Each row opens that system "
                                             "on the dashboard map."),
             ("2", "Scope questions", "Still operating? Open to the general public? Same-day booking available?"),
             ("3", "Eight fields and the boundary", "Name, operator, vendor, booking, scheduling window, status, fare, "
                                                    "website: Confirmed, Corrected (with a source) or Couldn't verify. "
                                                    "Boundary compared with any agency map."),
             ("4", "Ingest, then publish", "A script reads the workbook into the dashboard's Validation tab. Clear "
                                           "corrections are applied and logged; the workbook is kept as the first-pass record.")]
    for i, (num, head, body) in enumerate(steps):
        _, tf = box(s, 0.5, 1.55 + i * 0.86, 5.6, 0.8, fill=SAND)
        p = para(tf, "", first=True, space_after=2)
        run(p, f"{num}   ", 12, True, BLUE)
        run(p, head, 11.5, True, INK)
        para(tf, body, 9.5, False, MID, space_after=0)
    _, tf = box(s, 6.4, 1.6, 3.1, 3.24, fill=None)
    tf.margin_left = Inches(0.2)
    para(tf, str(n["reviewed"]), 40, True, NAVY, first=True, space_after=0)
    para(tf, "systems reviewed", 13, True, INK, space_after=8)
    sr = n["states_reviewed"]
    names = {"CO": "Colorado", "OH": "Ohio"}
    for st, cnt in sr.most_common():
        who = Counter({b: c for (s_, b), c in n["by"].items() if s_ == st}).most_common(1)[0][0]
        who = "independent reviewer" if who == "independent" else "project team"
        para(tf, f"{names.get(st, st)}: {cnt} systems, {who}", 10.5, False, MID, space_after=3)
    para(tf, "More states are assigned. Reviews are tagged independent or project team; the public tab shows no "
             "names.", 9.5, False, MUTE, space_after=0)
    notes(s, "The workbook is a Google Sheet built by scripts/validation/export.py; ingest.py reads it back into "
             "data/validation.json, which the dashboard's Validation tab displays. Proposed corrections are held "
             "until a larger set of reviews is in, so the CSV hasn't changed yet. Every applied change will get a "
             "concerns.csv entry with the reviewer's source.")

    s = new_slide(prs, "What reviewers found", 13 + shift)
    order = ["Confirmed", "Corrected", "Couldn't verify", "Not checked"]
    colors = [BLUE, GOLD, BRICK, LINE]
    fields = list(reversed(n["fields"]))  # bar charts draw bottom-up
    label = {"Booking Method(s)": "Booking method", "Technology Vendor": "Vendor", "Status/Maturity": "Status",
             "Scheduling Window": "Scheduling window", "Website URL": "Website"}
    cd = CategoryChartData()
    cd.categories = [label.get(f, f) for f in fields]
    for o in order:
        cd.add_series(o, [n["per_field"][f][o] for f in fields])
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, Inches(0.4), Inches(1.05), Inches(5.6), Inches(3.75), cd)
    ch = gf.chart
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(9)
    ch.legend.font.color.rgb = MID
    plot = ch.plots[0]
    plot.gap_width = 45
    plot.overlap = 100
    for se, c in zip(plot.series, colors):
        se.format.fill.solid()
        se.format.fill.fore_color.rgb = c
        se.format.line.color.rgb = WHITE
        se.format.line.width = Pt(1)
    for se in list(plot.series)[1:3]:  # direct labels on the small segments
        dls = se.data_labels
        for i, v in enumerate(se.values):  # no label on segments too thin to hold one
            if v is not None and v < 2:
                dl = etree.SubElement(dls._element, qn("c:dLbl"))
                etree.SubElement(dl, qn("c:idx")).set("val", str(i))
                etree.SubElement(dl, qn("c:delete")).set("val", "1")
                dls._element.insert(0, dl)
        se.data_labels.show_value = True
        se.data_labels.font.size = Pt(8)
        se.data_labels.font.bold = True
        se.data_labels.font.color.rgb = WHITE
        se.data_labels.position = XL_LABEL_POSITION.CENTER
    va = ch.value_axis
    va.minimum_scale = 0
    va.maximum_scale = n["reviewed"]
    va.major_unit = 5
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = LINE
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(8)
    va.tick_labels.font.color.rgb = MUTE
    ca = ch.category_axis
    ca.tick_labels.font.size = Pt(9)
    ca.tick_labels.font.color.rgb = INK
    ca.format.line.color.rgb = LINE
    c = n["checks"]
    total = sum(c.values())
    cant, dont = c["Couldn't verify"], n["boundary"]["Doesn't match"]
    ct = n["corr_types"]
    b = n["boundary"]
    callouts = [
        (f"{round(100 * c['Confirmed'] / total)}% of field checks confirmed",
         f"{c['Confirmed']} of {total} checks; {c['Corrected']} corrected, {cant} "
         f"couldn't be verified, {c['Not checked']} left blank."),
        ("Corrections mostly add detail",
         f"{ct['gap']} filled a 'Not specified', {ct['refinement']} refined a value, {ct['cosmetic']} trimmed a name; "
         f"{ct['unclassified']} await a decision."),
        (f"{len(n['scope_flags'])} scope flags",
         "Call-N-Ride (Greeley) may lack same-day booking; Via Mobility (Weld County) eligibility is unclear."),
        (f"Boundaries: {b['Matches']} of {n['reviewed']} match",
         f"{b['Partly matches']} partly, {dont} don't, {b['No agency map found']} "
         "had no agency map. City-limit stand-ins were the usual gap."),
    ]
    for i, (head, body) in enumerate(callouts):
        _, tf = box(s, 6.2, 1.1 + i * 0.93, 3.3, 0.86, fill=SAND)
        para(tf, head, 11, True, RUST if i == 2 else INK, first=True, space_after=2)
        para(tf, body, 9, False, MID, space_after=0)
    _, tf = box(s, 0.5, 4.93, 9.0, 0.3, margins=(0.12, 0, 0.12, 0))
    para(tf, f"Field checks per system ({n['reviewed']} systems). Reviews read {n['read']}; "
             f"{n['applied']} of {sum(ct.values())} applied to the CSV so far.", 8.5, False, MUTE, first=True, space_after=0)
    notes(s, "Lesson for the next round: Scheduling Window. Three Ohio rows read 'Same-day' where the agency says "
             "to call well ahead and same-day only 'may' be available, or booking is phone-only. Those stay in scope "
             "(same-day is a real option) but the value should be 'Flexible'. The reviewer guide will get a line on "
             "this, and blanks will mean 'not checked'. The two scope flags are held, not removed: verify before "
             "removal applies to reviewer findings too.")

    # Level of effort, before questions and next steps
    from pptx.enum.shapes import MSO_SHAPE
    s = new_slide(prs, "Level of effort", len(prs.slides) - 1)
    levels = {1: "Low", 2: "Medium", 3: "High", 4: "Extra high"}
    rows = [
        ("Identifying systems", 3, "Nine state research batches, then a three-wave sweep of every state against state DOT "
                                   "provider rosters; 880 rows at the peak."),
        ("Verifying scope rules", 4, "Every advance-booking row re-checked against a primary source (215 removed); 170 "
                                     "paratransit rows retired; borderline calls made one at a time by a person."),
        ("Creating the dashboard", 2, "One web page with map, cards, analytics, reference and validation views, built and "
                                      "revised in short iterations."),
        ("GitHub management", 1, "A build script checks the CSV and regenerates the data files; a push republishes the site."),
        ("Finding boundaries", 2, "Census outlines matched to each row's described area for 659 systems, in 12 staged "
                                  "batches; mostly automated."),
        ("Refining boundaries", 3, f"Searching agency, MPO and state DOT layers is quick; checking each match takes about "
                                   f"15 minutes per 25 systems, and {n['census']} systems are still on Census outlines."),
        ("Colleague validation", 2, "About a state per reviewer; reading results back is automated, applying them needs "
                                    "judgment."),
    ]
    y0, rh = 1.12, 0.5
    for c, (x, w, t) in enumerate(((0.5, 2.3, "Task"), (2.9, 2.2, "Effort"), (5.2, 4.3, "Why"))):
        _, tf = box(s, x, y0, w, 0.28, margins=(0.1, 0, 0.05, 0))
        para(tf, t.upper(), 8, True, MUTE, first=True, space_after=0)
    for i, (task, lvl, why) in enumerate(rows):
        y = y0 + 0.3 + i * rh
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(y), Inches(9.0), Inches(rh - 0.06))
        bg.fill.solid()
        bg.fill.fore_color.rgb = SAND if i % 2 == 0 else WHITE
        bg.line.fill.background()
        bg.shadow.inherit = False
        _, tf = box(s, 0.5, y, 2.3, rh - 0.06, anchor=MSO_ANCHOR.MIDDLE, margins=(0.1, 0, 0.05, 0))
        para(tf, task, 11, True, INK, first=True, space_after=0)
        for k in range(4):
            seg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(2.95 + k * 0.29), Inches(y + (rh - 0.06) / 2 - 0.07),
                                     Inches(0.25), Inches(0.14))
            seg.fill.solid()
            seg.fill.fore_color.rgb = NAVY if k < lvl else LINE
            seg.line.fill.background()
            seg.shadow.inherit = False
        _, tf = box(s, 4.1, y, 1.05, rh - 0.06, anchor=MSO_ANCHOR.MIDDLE, margins=(0.02, 0, 0.02, 0))
        para(tf, levels[lvl], 10, True, NAVY, first=True, space_after=0)
        _, tf = box(s, 5.2, y, 4.3, rh - 0.06, anchor=MSO_ANCHOR.MIDDLE, margins=(0.1, 0, 0.1, 0))
        para(tf, why, 8.5, False, MID, first=True, space_after=0)
    _, tf = box(s, 0.5, y0 + 0.32 + len(rows) * rh, 9.0, 0.3, margins=(0.1, 0, 0.1, 0))
    para(tf, "Relative ratings judged from the project log, not timed. Agent batches shortened the research time; "
             "they did not shorten review.", 8.5, False, MUTE, first=True, space_after=0)
    notes(s, "Scope verification was the biggest effort because every removal needed a primary source and the rules "
             "were refined twice (paratransit in July, the same-day test in August). Refining boundaries is the "
             "largest remaining effort: machine search costs seconds per system, but most matches need zones reconciled "
             "with the CSV or paratransit and proposed zones dropped.")

    # Questions and next steps, just before the closing slide
    s = new_slide(prs, "Questions and next steps", len(prs.slides) - 1)
    cols = [("Questions for the group", [
                ("Research uses", "Where could the inventory support research: service design, rural access, "
                                  "vendor and fare trends, or links to NTD ridership?"),
                ("Fleet data", "Vehicle counts exist for about 8% of systems. Ideas for getting them: NTD vehicle "
                               "inventories, state DOT grant files, operator surveys?"),
                ("Partners and reviewers", "Who should review or co-maintain it: state DOTs, transit associations, "
                                           "researchers, agencies themselves?")]),
            ("Next steps", [
                ("Permanent hosting", "Move the dashboard and data from a personal GitHub Pages site to a permanent home."),
                ("Additional validation", "Review more states, with clearer guidance on the Scheduling Window field."),
                ("Sharing results externally", "Publish the dataset with a citation and a way for agencies to send corrections."),
                ("Collaboration", "Shared upkeep with partners: new systems, status changes and agency zone maps.")])]
    for c, (head, items) in enumerate(cols):
        x = 0.5 + c * 4.65
        _, tf = box(s, x, 1.1, 4.35, 0.4, margins=(0, 0, 0, 0))
        para(tf, head, 14, True, NAVY, first=True, space_after=0)
        hgt = 3.45 / len(items)
        for i, (t, b) in enumerate(items):
            _, tf = box(s, x, 1.55 + i * hgt, 4.35, hgt - 0.1, fill=SAND)
            para(tf, t, 11.5, True, RUST if c == 0 else INK, first=True, space_after=2)
            para(tf, b, 9.5, False, MID, space_after=0)
    notes(s, "Questions are open prompts for discussion. Fleet: vehicle count is the sparsest field (about 8% of "
             "rows); NTD covers only reporting agencies, so rural demand-response would still need another source.")

    def after_title(title):
        for i, sl_ in enumerate(prs.slides):
            if sl_.shapes.title is not None and sl_.shapes.title.text_frame.text.strip() == title:
                return i + 1
        raise KeyError(title)

    # State sweeps in depth, after the timeline
    s = new_slide(prs, "State sweeps in depth", after_title("Methodology timeline"))
    stages = [
        ("Seed inventory (June)", "The NC work as a template, an existing spreadsheet, and California and Colorado lists.",
         "241"),
        ("State expansion: 9 batches", "Three missing states per batch until all 50 + DC had rows; each agent was capped "
                                       "at about 8 page fetches, so this pass was shallow.", "394"),
        ("Deep sweep: 3 waves", "Every state again, told to assume it was under-covered and work through state DOT and "
                                "transit-association rosters. Wave 1 +81, wave 2 +119, wave 3 +127.", "724"),
        ("Targeted follow-ups", "States that ran out of search budget, and leads the waves flagged: GA county roster "
                                "+36, ND +21, MI +16, NM +4, NY +3, OR +2; NH and ID +0.", "889"),
        ("Same-day scope sweep (August)", "Every advance-booking row checked against a primary source.", "665"),
    ]
    for i, (h_, b_, r_) in enumerate(stages):
        _, tf = box(s, 0.5, 1.15 + i * 0.7, 4.6, 0.62, fill=SAND, anchor=MSO_ANCHOR.MIDDLE, margins=(0.12, 0.04, 0.1, 0.04))
        para(tf, h_, 10.5, True, INK, first=True, space_after=1)
        para(tf, b_, 8.5, False, MID, space_after=0)
        _, tf = box(s, 5.15, 1.15 + i * 0.7, 0.95, 0.62, anchor=MSO_ANCHOR.MIDDLE, margins=(0.05, 0, 0.05, 0))
        para(tf, r_, 15, True, RUST if i == len(stages) - 1 else NAVY, first=True, space_after=0)
        _, tf = box(s, 5.15, 1.15 + i * 0.7 + 0.42, 0.95, 0.2, margins=(0.05, 0, 0.05, 0))
        para(tf, "rows", 7.5, False, MUTE, first=True, space_after=0)
    side = [("Why re-sweeps were needed", "The first pass stopped early: with a small fetch cap, agents quit after "
                                          "the obvious finds. The deep sweep re-ran every state with an explicit push "
                                          "to keep going. Then parallel agents exhausted a shared search budget (200 "
                                          "searches) mid-wave; those states were flagged and re-run on their own."),
            ("Why three waves", "About six state groups ran in parallel per wave, each wave committed and "
                                "cross-checked before the next. The largest states (TX, GA, CA, FL) went last."),
            ("What the later passes added", "Rural demand-response found through state rosters: 39 Wisconsin "
                                            "shared-ride taxis from one fiscal bureau paper; Texas 11 rows to 45, Georgia "
                                            "11 to 29. NH and ID adding nothing showed coverage had saturated.")]
    yy = 1.15
    for h_, b_ in side:
        hh = 1.25 if h_.startswith("Why re") else 0.95
        _, tf = box(s, 6.35, yy, 3.15, hh, fill=None, margins=(0.1, 0.02, 0.05, 0.02))
        para(tf, h_, 11, True, NAVY, first=True, space_after=2)
        para(tf, b_, 8.5, False, MID, space_after=0)
        yy += hh + 0.12
    _, tf = box(s, 0.5, 4.72, 9.0, 0.3, margins=(0.1, 0, 0.1, 0))
    para(tf, "Row counts after each stage. The paratransit retirement (170 rows) ran alongside the deep sweep, so the "
             "stages don't sum exactly.", 8.5, False, MUTE, first=True, space_after=0)
    notes(s, "The expansion batches were breadth-first: get every state on the board. The deep sweep was "
             "recall-first: assume each state is under-covered and read the authoritative roster. Most of the large "
             "gains came from a single roster document per state, which is why state DOT and association lists are "
             "now the first stop for discovery. On the re-sweeps: the first-pass agents weren't wrong so much as "
             "shallow; they stopped once they had a plausible list. Asking for recall explicitly, and logging which "
             "states hit the search budget, is what made the second pass worth running.")

    # Boundary selection and refinement in depth, after the boundary slide
    s = new_slide(prs, "Boundaries in depth", after_title("Service-area boundaries"))
    cols = [("September: a polygon for every row", [
                ("Draft a spec", "An agent reads each row's service area and picks the Census units, or a circle of "
                                 "the stated size."),
                ("Build and check", "A script builds the polygon and compares its area with any stated size; "
                                    "mismatches are flagged."),
                ("Audit and fix", "A second agent reviews each spec; flagged rows are fixed or left for research. "
                                  "659 of 665 drawn in 12 staged batches."),
                ("Rule learned", "Size beats unit: early drafts picked whole counties for small zones.")]),
            ("November: swap stand-ins for agency zones", [
                ("Screen", "Keep layers whose polygons sit near the system and are a plausible size; skip "
                           "non-transit layers by name."),
                ("Review each match", "Pick the right features; drop paratransit, proposed and coming-soon zones; "
                                      "compare the zone list with the CSV and log differences."),
                ("Check the source", "Prefer the agency, then the state DOT or MPO; hold layers with an unknown "
                                     "publisher or unclear status."),
                ("Load and cite", "Union the zones; the popup names the layer, publisher, date and link.")])]
    for c, (head, items) in enumerate(cols):
        x = 0.5 + c * 4.65
        _, tf = box(s, x, 1.08, 4.35, 0.35, margins=(0, 0, 0, 0))
        para(tf, head, 12.5, True, NAVY, first=True, space_after=0)
        for i, (t, b) in enumerate(items):
            _, tf = box(s, x, 1.5 + i * 0.8, 4.35, 0.72, fill=SAND if not t.startswith("Rule") else None,
                        anchor=MSO_ANCHOR.MIDDLE)
            para(tf, t, 10.5, True, RUST if t.startswith("Rule") else INK, first=True, space_after=1)
            para(tf, b, 8.5, False, MID, space_after=0)
    _, tf = box(s, 0.5, 4.75, 9.0, 0.3, margins=(0.1, 0, 0.1, 0))
    para(tf, "Rejected along the way: whole-agency districts, simple buffers and preliminary plan layers.",
         8.5, False, MUTE, first=True, space_after=0)
    notes(s, "Preference order for a row's polygon: exact administrative units, then a stated-size circle, then a "
             "containing-unit proxy, then 'needs research'. In November the agency's own zone map moved to the top. "
             "Examples of holds: Putnam On-Demand (the county's latest layer marks its zone PROPOSED), Erie Bee "
             "(publisher can't be identified), Catch Connect (five zones in the layer, two in the CSV).")

    prs.save(args.out)
    print(f"wrote {args.out}: {len(prs.slides)} slides; polygons {n['poly']} "
          f"(agency {n['agency']}, gtfs {n['gtfs']}, none {len(n['none'])}: {n['none']})")


if __name__ == "__main__":
    main()
