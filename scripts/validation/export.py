#!/usr/bin/env python3
"""Build the colleague validation workbook from ODT_Inventory.csv.

One tab per state. Each row is one system: the dashboard's current values
(gray, read-only) beside dropdowns and blanks for the reviewer. Upload the
.xlsx to Google Drive (it converts to a Google Sheet, dropdowns included),
share it, and when reviewers are done, download it as .xlsx and run
scripts/validation/ingest.py on it.

    python3 scripts/validation/export.py                 # -> validation/ODT-Validation-Workbook.xlsx
    python3 scripts/validation/export.py -o some/path.xlsx

The column layout here is the contract ingest.py reads. If you change
CORE_FIELDS or SCOPE_QUESTIONS, ingest.py picks the change up by importing
them, but a workbook already sent out keeps its old layout.
"""
import argparse
import csv
import datetime
import subprocess
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "ODT_Inventory.csv"
CONCERNS_PATH = ROOT / "concerns.csv"
DEFAULT_OUT = ROOT / "validation" / "ODT-Validation-Workbook.xlsx"

# Fields reviewers check. Name is the row key, so its dashboard value sits in
# column B and the Name group has only Check + Correct value.
DASHBOARD_URL = "https://jfish79.github.io/odt-dashboard/"
BOUNDARY_DIR = ROOT / "data" / "boundaries"

CORE_FIELDS = [
    "Name",
    "Operator",
    "Technology Vendor",
    "Booking Method(s)",
    "Scheduling Window",
    "Status/Maturity",
    "Fare",
    "Website URL",
]
SCOPE_QUESTIONS = [
    "Still operating?",
    "Open to the general public?",
    "Same-day booking available?",
]
SCOPE_CHOICES = ["Yes", "No", "Unsure"]
CHECK_CHOICES = ["Confirmed", "Corrected", "Couldn't verify"]
BOUNDARY_CHOICES = ["Matches", "Partly matches", "Doesn't match", "No agency map found"]
# Labels match BOUNDARY_COLORS in index.html.
BOUNDARY_LABELS = {
    "gtfs_flex": "Official service area (GTFS-Flex)", "agency_gis": "Agency zone map",
    "city": "City limits (Census)",
    "county": "County (Census)", "counties": "Multi-county (Census)",
    "cousub": "Town/township (Census)", "cousubs": "Towns/townships (Census)",
    "tribal": "Tribal land (Census)", "places": "Town boundaries (Census)",
    "neighborhood_npa": "Neighborhoods (Charlotte NPA)", "census_tracts": "Census tracts",
    "places_constructed": "Constructed from places", "zone_approx": "Approximate zone",
    "zones_approx": "Approximate zone", "buffered": "Municipality + service radius",
}
TAIL_COLUMNS = ["Sources consulted (URLs)", "Notes", "Reviewed by", "Date reviewed"]

# concerns.csv categories that describe a question still open on a live row,
# worth showing the reviewer (a phone call may settle it).
OPEN_QUESTION_CATEGORIES = (
    "Data Gap (needs follow-up)",
    "Unverified Scheduling Window",
    "Scope Question",
    "Scope Question (unverified in data)",
    "Status Change (unverified in data)",
    "Vendor - Low Confidence",
    "Vendor - Weak Label",
    "Unverified program name (placeholder)",
)

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

TITLE_ROW, GROUP_ROW, HEADER_ROW = 1, 2, 3
FIRST_DATA_ROW = 4

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F3A5F")
GROUP_FILL = PatternFill("solid", fgColor="D9E2EC")
DASH_FILL = PatternFill("solid", fgColor="EEF0F2")
PRIORITY_FILL = PatternFill("solid", fgColor="F8E3C8")  # approximate or missing boundary
THIN = Side(style="thin", color="C8CDD3")
GROUP_EDGE = Side(style="medium", color="8696A7")


def columns():
    """Ordered column spec: (group, header, kind, field).

    kind: id | dash | open | scope | check | correct | bdash | blink | bcheck | binput | tail
    """
    cols = [
        ("System", "ID", "id", None),
        ("System", "Name (dashboard)", "dash", "Name"),
        ("System", "Region / service area", "dash", "Region/Service Area"),
        ("System", "Open question in our log", "open", None),
    ]
    for q in SCOPE_QUESTIONS:
        cols.append(("Scope check", q, "scope", q))
    for f in CORE_FIELDS:
        if f != "Name":
            cols.append((f, "Dashboard value", "dash", f))
        cols.append((f, "Check", "check", f))
        cols.append((f, "Correct value", "correct", f))
    cols += [
        ("Service area boundary", "Boundary on dashboard", "bdash", None),
        ("Service area boundary", "View on map", "blink", None),
        ("Service area boundary", "Check", "bcheck", None),
        ("Service area boundary", "Agency map (URL or description)", "binput", "Agency map"),
        ("Service area boundary", "What's different", "binput", "What's different"),
    ]
    for t in TAIL_COLUMNS:
        cols.append(("Your review", t, "tail", t))
    return cols


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_open_questions():
    out = {}
    with open(CONCERNS_PATH, newline="", encoding="utf-8") as fh:
        for c in csv.DictReader(fh):
            if c["Category"].strip() in OPEN_QUESTION_CATEGORIES:
                key = (c["System Name"], c["State"])
                out.setdefault(key, []).append(c["Detail"].strip())
    return out


def load_boundaries():
    """(name, state) -> (description, needs_attention) from data/boundaries/*.geojson."""
    import json
    out = {}
    for path in sorted(BOUNDARY_DIR.glob("*.geojson")):
        st = path.stem
        for feat in json.loads(path.read_text(encoding="utf-8")).get("features", []):
            p = feat.get("properties", {})
            approx = p.get("fidelity") == "approximate" or "approx" in (p.get("boundary_type") or "")
            label = BOUNDARY_LABELS.get(p.get("boundary_type"), p.get("boundary_type") or "Unknown type")
            parts = [f"{'Approximate' if approx else 'Exact'}: {label}."]
            if p.get("units"):
                parts.append(f"Built from {p['units']}.")
            if p.get("note"):
                parts.append(p["note"].rstrip(".") + ".")
            out[(p.get("name"), st)] = (" ".join(parts), approx)
    return out


def map_link(st, name):
    from urllib.parse import quote
    return f"{DASHBOARD_URL}#system={st}/{quote(name, safe='')}"


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def font(**kw):
    return Font(name=FONT, **kw)


def write_instructions(ws, n_rows, n_states, snapshot):
    ws.sheet_properties.tabColor = "1F3A5F"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 100
    wrap = Alignment(wrap_text=True, vertical="top")

    lines = [
        ("title", "ODT inventory review: how to check your state"),
        ("text", f"The dashboard lists {n_rows} on-demand transit systems in {n_states} states and DC. "
                 "Each tab after Assignments holds one state. For every system, check the dashboard's "
                 "values and its service-area boundary against current primary sources and record what "
                 "you find. Plan on about 10 minutes per system."),
        ("text", snapshot),
        ("blank", ""),
        ("head", "Steps for each system"),
        ("kv", "1. Find a source", "Start from the website in the Website URL column, then the agency's own site, "
               "the app's App Store or Google Play listing, board or council documents, and state DOT reports. "
               "Press releases and news stories are fine for launch facts but check their date."),
        ("kv", "2. Scope check", "Answer the three scope questions (Yes / No / Unsure). If any answer is No, "
               "explain why in Notes, paste the source, and skip the field checks for that system."),
        ("kv", "3. Field checks", "For each field, pick Confirmed, Corrected or Couldn't verify from the dropdown. "
               "For Corrected, type the right value in that field's Correct value column."),
        ("kv", "4. Boundary check", "Click Open map to see the system's service area on the dashboard, then compare "
               "it with the agency's own service-area map (usually on the service's web page or in the app). Pick a "
               "result from the Check dropdown, paste the agency map's URL in Agency map, and describe any difference "
               "in What's different. See \"Boundary check\" below."),
        ("kv", "5. Sources", "Paste the URLs you used in Sources consulted, one per line (Ctrl+Enter or "
               "Cmd+Enter for a new line in a cell). A source is required for every Corrected value and every "
               "scope answer of No."),
        ("kv", "6. Sign off", "Put your name in Reviewed by and the date in Date reviewed. Use Notes for "
               "anything else worth knowing, such as a new zone, a fare change coming soon, or a phone call you made."),
        ("blank", ""),
        ("head", "What the check choices mean"),
        ("kv", "Confirmed", "A current source agrees with the dashboard value."),
        ("kv", "Corrected", "A source shows a different value, or the dashboard says \"Not specified\" and you found "
               "the real value. Enter it in Correct value."),
        ("kv", "Couldn't verify", "You looked and found nothing that settles it either way. Leave Correct value blank."),
        ("blank", ""),
        ("head", "Boundary check"),
        ("kv", "What's on the map", "Each dashboard boundary was drawn from the service's published description, using "
               "official lines such as city limits, counties or towns. \"Exact\" means the polygon follows such a line, "
               "not that the line is the right one. \"Approximate\" means a stand-in, such as a circle of the stated size "
               "or a whole city for a zone that covers only part of it. Orange cells mark approximate boundaries and "
               "systems with none drawn; those are the most likely to be wrong."),
        ("kv", "Matches", "Covers the same area as the agency's map, give or take small differences at the edges."),
        ("kv", "Partly matches", "Right place, but noticeably bigger or smaller, or a zone is missing or extra."),
        ("kv", "Doesn't match", "Wrong place or a very different shape."),
        ("kv", "No agency map found", "Neither the agency site nor the app shows the service area. Use What's different "
               "for any written description you did find, such as \"anywhere within Smith County\"."),
        ("kv", "Agency map", "Paste the map's URL even when the boundary matches. A link to the agency's map (a PDF, an "
               "image or an interactive map) is what lets us redraw an approximate boundary later."),
        ("blank", ""),
        ("head", "Scope rules (from the dashboard's Reference tab)"),
        ("kv", "In scope", "Same-day app or phone booking with no fixed schedule, even if a short same-day lead time "
               "(such as two hours) is required. Demand-response counts when advance booking is preferred or the "
               "norm, as long as a same-day request is a real, routinely honored option. Open to the general public, "
               "even if the service prioritizes seniors or riders with disabilities. Planned or pilot services count "
               "if the vendor and funding are confirmed."),
        ("kv", "Out of scope", "No same-day option: booking required by a cutoff on a day before the trip (\"by 4pm the "
               "day before\", \"24-hour advance\", \"next-day only\"). Paratransit restricted to eligibility-certified "
               "riders (ADA, senior or disability certification required). Private, employer or campus-only shuttles. "
               "Permanently discontinued services."),
        ("blank", ""),
        ("head", "Fields"),
        ("kv", "Name", "The name the agency uses for the service today. If it was renamed, enter the new name and "
               "mention the old one in Notes."),
        ("kv", "Operator", "The agency, city, county or organization that runs or sponsors the service."),
        ("kv", "Technology Vendor", "The software platform used for booking and dispatch, such as Via, RideCo, Spare, "
               "TransLoc, Freebee, Circuit or Ecolane. \"In-house\" if the agency built its own. The developer name "
               "on the app's store listing is often the quickest clue."),
        ("kv", "Booking Method(s)", "How riders book: App, Phone, Online (website). List all that apply, for example "
               "\"App, Phone\"."),
        ("kv", "Scheduling Window", "Same-day: booked and ridden the same day. Advance: booking ahead is the norm but "
               "same-day is still possible. Flexible: both are offered. Note any required lead time, for example "
               "\"Same-day (1-hour minimum)\"."),
        ("kv", "Status/Maturity", "Active, Active - New (launched in the last 6 months or so), Active - Expanding, "
               "Active - Post Pilot, Pilot, Pilot - Ended. A service that has shut down permanently is a scope No, "
               "not a status change."),
        ("kv", "Fare", "The standard one-way adult fare, for example \"$2.00\" or \"Free\". Mention reduced fares briefly "
               "if the source lists them."),
        ("kv", "Website URL", "The service's own page if it has one, otherwise the operator's page about it."),
        ("blank", ""),
        ("head", "Please don't"),
        ("kv", "Edit gray cells", "Gray columns show what the dashboard says now. Leave them as they are, even when "
               "they're wrong; put the fix in Correct value."),
        ("kv", "Add or move columns", "Adding rows of notes below the table is fine. Inserting, deleting or reordering "
               "columns breaks the script that reads the results."),
        ("kv", "Add new systems here", "If you find a system the dashboard is missing, add it on the Missing systems tab "
               "(last tab), not in the state tab."),
        ("blank", ""),
        ("head", "Example of a finished row"),
        ("kv", "Scope check", "Still operating? Yes. Open to the general public? Yes. Same-day booking available? Yes."),
        ("kv", "Technology Vendor", "Dashboard value: Not specified. Check: Corrected. Correct value: Via."),
        ("kv", "Fare", "Dashboard value: $1.50. Check: Corrected. Correct value: $2.00 (raised July 2026)."),
        ("kv", "Other fields", "Check: Confirmed."),
        ("kv", "Boundary", "Check: Partly matches. Agency map: https://www.exampletransit.org/ondemand/zone-map.pdf. "
               "What's different: zone also covers the hospital and college east of the city limits."),
        ("kv", "Sources consulted", "https://www.exampletransit.org/ondemand\nApp Store listing \"Example On-Demand\" "
               "(developer: Via Transportation)"),
    ]
    r = 1
    for kind, *vals in lines:
        if kind == "title":
            ws.cell(r, 1, vals[0]).font = font(bold=True, size=16)
        elif kind == "head":
            c = ws.cell(r, 1, vals[0])
            c.font = font(bold=True, size=12, color="FFFFFF")
            for col in (1, 2):
                ws.cell(r, col).fill = HEADER_FILL
        elif kind == "text":
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
            c = ws.cell(r, 1, vals[0])
            c.font = font(size=11)
            c.alignment = wrap
            ws.row_dimensions[r].height = 30
        elif kind == "kv":
            a = ws.cell(r, 1, vals[0])
            a.font = font(bold=True, size=10)
            a.alignment = wrap
            b = ws.cell(r, 2, vals[1])
            b.font = font(size=10)
            b.alignment = wrap
            # Rough height so wrapped text isn't cut off in Excel; Sheets refits on its own.
            est_lines = max(1, sum(len(p) // 95 + 1 for p in vals[1].split("\n")))
            ws.row_dimensions[r].height = 14 * est_lines + 4
        r += 1
    ws.freeze_panes = "A2"


def write_assignments(ws, states):
    ws.sheet_properties.tabColor = "1F3A5F"
    headers = ["State", "State name", "Systems", "Approximate or missing boundaries", "Reviewer(s)",
               "Systems with a scope answer", "Share done", "Notes"]
    widths = [8, 22, 10, 16, 26, 16, 12, 50]
    ws.cell(1, 1, "Assignments").font = font(bold=True, size=16)
    ws.cell(2, 1, "Write reviewer names in column E. Counts update as reviewers fill in their tabs. "
                  "Small states can share one reviewer; a large state like CA can be split by giving "
                  "each person a range of rows and using the Reviewed by column.").font = font(size=10, italic=True)
    hr = 4
    for i, (h, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(hr, i, h)
        c.font = font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[hr].height = 30

    name_col = 2  # column B on state tabs holds the system name
    scope_col = 1 + [k for _, _, k, _ in columns()].index("scope")  # first scope question
    bdash_col = 1 + [k for _, _, k, _ in columns()].index("bdash")
    nl, sl, bl = get_column_letter(name_col), get_column_letter(scope_col), get_column_letter(bdash_col)
    r = hr + 1
    for st in states:
        tab = f"'{st}'"
        ws.cell(r, 1, st)
        ws.cell(r, 2, STATE_NAMES.get(st, st))
        ws.cell(r, 3, f"=COUNTA({tab}!{nl}{FIRST_DATA_ROW}:{nl}1000)")
        brng = f"{tab}!{bl}{FIRST_DATA_ROW}:{bl}1000"
        ws.cell(r, 4, f'=COUNTIF({brng},"Approximate*")+COUNTIF({brng},"No boundary*")')
        ws.cell(r, 6, f"=COUNTA({tab}!{sl}{FIRST_DATA_ROW}:{sl}1000)")
        ws.cell(r, 7, f"=IF(C{r}=0,0,F{r}/C{r})").number_format = "0%"
        for col in range(1, 9):
            ws.cell(r, col).font = font(size=10)
            ws.cell(r, col).border = Border(bottom=THIN)
        r += 1
    last = r - 1
    ws.cell(r, 2, "Total").font = font(bold=True)
    ws.cell(r, 3, f"=SUM(C{hr + 1}:C{last})").font = font(bold=True)
    ws.cell(r, 4, f"=SUM(D{hr + 1}:D{last})").font = font(bold=True)
    ws.cell(r, 6, f"=SUM(F{hr + 1}:F{last})").font = font(bold=True)
    c = ws.cell(r, 7, f"=IF(C{r}=0,0,F{r}/C{r})")
    c.font = font(bold=True)
    c.number_format = "0%"
    ws.freeze_panes = ws.cell(hr + 1, 1)


def write_state(ws, st, rows, open_q, bounds, snapshot):
    cols = columns()
    ncol = len(cols)
    title = f"{STATE_NAMES.get(st, st)} ({st})"
    t = ws.cell(TITLE_ROW, 1, title)
    t.font = font(bold=True, size=14)
    legend = ws.cell(TITLE_ROW, 3, "Gray cells: what the dashboard shows now (don't edit). White cells: your review. "
                                   "Orange boundary cells: approximate or missing boundary, most likely to need a fix. "
                                   "Instructions are on the first tab.")
    legend.font = font(size=10, italic=True, color="44505C")

    # Group header row (merged over each group) and column headers.
    start = 1
    for i in range(1, ncol + 2):
        group = cols[i - 1][0] if i <= ncol else None
        prev = cols[start - 1][0]
        if group != prev:
            if i - 1 > start:
                ws.merge_cells(start_row=GROUP_ROW, start_column=start, end_row=GROUP_ROW, end_column=i - 1)
            c = ws.cell(GROUP_ROW, start, prev)
            c.font = font(bold=True, size=10, color="1F3A5F")
            c.alignment = Alignment(horizontal="center", vertical="center")
            for j in range(start, i):
                ws.cell(GROUP_ROW, j).fill = GROUP_FILL
                ws.cell(GROUP_ROW, j).border = Border(left=GROUP_EDGE if j == start else None)
            start = i
    for i, (group, header, kind, field) in enumerate(cols, start=1):
        c = ws.cell(HEADER_ROW, i, header)
        c.font = font(bold=True, size=10, color="FFFFFF")
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        width = {"id": 8, "dash": 24, "open": 30, "scope": 13, "check": 15, "correct": 22, "tail": 22,
                 "bdash": 34, "blink": 12, "bcheck": 17, "binput": 28}[kind]
        if header == "Name (dashboard)":
            width = 30
        if header == "Notes" or header.startswith("Sources"):
            width = 34
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[HEADER_ROW].height = 32
    ws.cell(HEADER_ROW, 1).comment = Comment(snapshot, "ODT export")

    for n, row in enumerate(rows, start=1):
        r = FIRST_DATA_ROW + n - 1
        for i, (group, header, kind, field) in enumerate(cols, start=1):
            c = ws.cell(r, i)
            c.font = font(size=10)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = Border(bottom=THIN, left=GROUP_EDGE if (i == 1 or cols[i - 2][0] != group) else None)
            if kind == "id":
                c.value = f"{st}-{n:02d}"
                c.fill = DASH_FILL
            elif kind == "dash":
                c.value = row.get(field, "")
                c.fill = DASH_FILL
                if field == "Website URL" and c.value.startswith("http"):
                    c.hyperlink = c.value
                    c.font = font(size=10, color="1155CC", underline="single")
            elif kind == "open":
                c.value = "\n".join(open_q.get((row["Name"], st), []))
                c.fill = DASH_FILL
            elif kind == "bdash":
                desc, approx = bounds.get((row["Name"], st), ("No boundary drawn yet.", True))
                c.value = desc
                c.fill = PRIORITY_FILL if approx else DASH_FILL
            elif kind == "blink":
                c.value = "Open map"
                c.hyperlink = map_link(st, row["Name"])
                c.fill = DASH_FILL
                c.font = font(size=10, color="1155CC", underline="single")

    last_row = FIRST_DATA_ROW + len(rows) - 1
    if rows:
        scope_dv = DataValidation(type="list", formula1='"' + ",".join(SCOPE_CHOICES) + '"', allow_blank=True)
        check_dv = DataValidation(type="list", formula1='"' + ",".join(CHECK_CHOICES) + '"', allow_blank=True)
        bound_dv = DataValidation(type="list", formula1='"' + ",".join(BOUNDARY_CHOICES) + '"', allow_blank=True)
        scope_dv.error = check_dv.error = bound_dv.error = "Pick a value from the list."
        ws.add_data_validation(scope_dv)
        ws.add_data_validation(check_dv)
        ws.add_data_validation(bound_dv)
        green = PatternFill("solid", fgColor="D8EFD9")
        amber = PatternFill("solid", fgColor="FBE3C2")
        red = PatternFill("solid", fgColor="F6CFCF")
        grey = PatternFill("solid", fgColor="E3E3E3")
        yellow = PatternFill("solid", fgColor="FFF59D")
        for i, (group, header, kind, field) in enumerate(cols, start=1):
            L = get_column_letter(i)
            rng = f"{L}{FIRST_DATA_ROW}:{L}{last_row}"
            if kind == "scope":
                scope_dv.add(rng)
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Yes"'], fill=green))
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"No"'], fill=red))
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Unsure"'], fill=amber))
            elif kind == "check":
                check_dv.add(rng)
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Confirmed"'], fill=green))
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Corrected"'], fill=amber))
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Couldn\'t verify"'], fill=grey))
            elif kind == "bcheck":
                bound_dv.add(rng)
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Matches"'], fill=green))
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Partly matches"'], fill=amber))
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Doesn\'t match"'], fill=red))
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"No agency map found"'], fill=grey))
            elif kind == "correct":
                # Highlight a Corrected check that still has no correct value.
                chk = get_column_letter(i - 1)
                ws.conditional_formatting.add(
                    rng,
                    FormulaRule(formula=[f'AND(${chk}{FIRST_DATA_ROW}="Corrected",LEN({L}{FIRST_DATA_ROW})=0)'],
                                fill=yellow),
                )
    ws.freeze_panes = ws.cell(FIRST_DATA_ROW, 3)  # keep ID + Name visible while scrolling right


def write_missing(ws):
    ws.sheet_properties.tabColor = "8696A7"
    ws.cell(1, 1, "Missing systems").font = font(bold=True, size=14)
    ws.cell(2, 1, "Found an in-scope system the dashboard doesn't list? Add it here, one row per system.").font = \
        font(size=10, italic=True)
    headers = ["State", "System name", "Operator", "Website URL", "Why it looks in scope", "Added by", "Date"]
    widths = [8, 30, 26, 34, 50, 18, 12]
    for i, (h, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(3, i, h)
        c.font = font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A4"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = load_rows()
    open_q = load_open_questions()
    bounds = load_boundaries()
    by_state = {}
    for row in rows:
        by_state.setdefault(row["State"], []).append(row)
    states = sorted(by_state)
    for st in states:
        by_state[st].sort(key=lambda r: r["Name"].lower())

    snapshot = (f"Dashboard values exported from ODT_Inventory.csv at commit {git_commit()} "
                f"on {datetime.date.today().isoformat()}.")
    n_states = len([s for s in states if s != "DC"])

    wb = Workbook()
    write_instructions(wb.active, len(rows), n_states, snapshot)
    wb.active.title = "How to review"
    write_assignments(wb.create_sheet("Assignments"), states)
    for st in states:
        write_state(wb.create_sheet(st), st, by_state[st], open_q, bounds, snapshot)
    write_missing(wb.create_sheet("Missing systems"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.out)
    n_open = sum(1 for r in rows if (r["Name"], r["State"]) in open_q)
    print(f"Wrote {args.out} ({len(rows)} systems, {len(states)} state tabs, "
          f"{n_open} rows with an open question from concerns.csv)")


if __name__ == "__main__":
    main()
