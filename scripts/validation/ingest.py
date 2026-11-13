#!/usr/bin/env python3
"""Read a completed validation workbook and list what reviewers found.

Download the shared Google Sheet as .xlsx (File > Download > Microsoft Excel),
then:

    python3 scripts/validation/ingest.py ~/Downloads/ODT-Validation-Workbook.xlsx

Writes to validation/results/ (or --out-dir):
  proposed_changes.csv  one row per Corrected field, compared against the CSV as it is now
  scope_flags.csv       systems with a scope answer of No or Unsure
  boundary_findings.csv systems whose boundary doesn't fully match, or where an agency map was found
  missing_systems.csv   rows from the Missing systems tab
  summary.md            per-state progress and per-field tallies

Nothing here edits ODT_Inventory.csv. Apply changes by hand (or in a Claude
session), rebuild with scripts/build.py, and log each one in concerns.csv
with the reviewer's source, per CLAUDE.md.
"""
import argparse
import csv
import datetime
import sys
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export import (  # noqa: E402  (layout contract lives in export.py)
    BOUNDARY_CHOICES, CHECK_CHOICES, CSV_PATH, FIRST_DATA_ROW, HEADER_ROW, ROOT, STATE_NAMES, columns,
)

CANT_VERIFY = CHECK_CHOICES[2]

DEFAULT_OUT = ROOT / "validation" / "results"


def text(v):
    if v is None:
        return ""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook", type=Path)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        live = {(r["Name"], r["State"]): r for r in csv.DictReader(fh)}

    wb = load_workbook(args.workbook, data_only=True)
    cols = columns()
    expected_headers = [h for _, h, _, _ in cols]
    idx = {}  # (kind, field) -> 0-based column index
    for i, (_, _, kind, field) in enumerate(cols):
        idx[(kind, field)] = i
    scope_qs = [f for _, _, k, f in cols if k == "scope"]
    check_fields = [f for _, _, k, f in cols if k == "check"]
    get = lambda vals, kind, field: text(vals[idx[(kind, field)]]) if idx[(kind, field)] < len(vals) else ""

    changes, flags, problems, boundaries = [], [], [], []
    progress = {}
    tallies = defaultdict(Counter)

    state_tabs = [ws for ws in wb.worksheets if ws.title in STATE_NAMES]
    for ws in state_tabs:
        st = ws.title
        headers = [text(c.value) for c in ws[HEADER_ROW]][: len(expected_headers)]
        if headers != expected_headers:
            problems.append(f"{st}: column headers don't match the export layout; tab skipped. "
                            "Someone may have inserted or moved a column.")
            continue
        total = reviewed = 0
        for vals in ws.iter_rows(min_row=FIRST_DATA_ROW, values_only=True):
            name = get(vals, "dash", "Name")
            if not name:
                continue
            total += 1
            scope = {q: get(vals, "scope", q) for q in scope_qs}
            checks = {f: get(vals, "check", f) for f in check_fields}
            b_check = get(vals, "bcheck", None)
            b_map = get(vals, "binput", "Agency map")
            b_diff = get(vals, "binput", "What's different")
            if not any(scope.values()) and not any(checks.values()) and not (b_check or b_map or b_diff):
                continue
            reviewed += 1
            rid = get(vals, "id", None)
            who = get(vals, "tail", "Reviewed by")
            when = get(vals, "tail", "Date reviewed")
            sources = get(vals, "tail", "Sources consulted (URLs)")
            notes = get(vals, "tail", "Notes")
            row_live = live.get((name, st))
            if row_live is None:
                problems.append(f"{st} {rid} {name!r}: no longer in ODT_Inventory.csv under this name "
                                "(renamed or removed since export). Match by hand.")

            for q, a in scope.items():
                tallies[q][a or "(blank)"] += 1
            bad = {q: a for q, a in scope.items() if a in ("No", "Unsure")}
            if bad:
                flags.append({
                    "State": st, "ID": rid, "Name": name,
                    **{q: scope[q] for q in scope_qs},
                    "Reviewer": who, "Date": when, "Sources": sources, "Notes": notes,
                    "Flag": "" if sources or "No" not in bad.values() else "No source given for a No answer",
                })

            for f in check_fields:
                verdict = checks[f]
                tallies[f][verdict or "(blank)"] += 1
                if verdict != "Corrected":
                    continue
                proposed = get(vals, "correct", f)
                exported = name if f == "Name" else get(vals, "dash", f)
                now = row_live.get(f, "") if row_live else ""
                notes_flag = []
                if not proposed:
                    notes_flag.append("Marked Corrected but no correct value given")
                if not sources:
                    notes_flag.append("No source given")
                if row_live and now != exported:
                    notes_flag.append("CSV value changed since export")
                if proposed and proposed == now:
                    notes_flag.append("Already matches CSV")
                changes.append({
                    "State": st, "ID": rid, "Name": name, "Field": f,
                    "Dashboard value at export": exported, "CSV value now": now,
                    "Proposed value": proposed, "Reviewer": who, "Date": when,
                    "Sources": sources, "Notes": notes, "Flag": "; ".join(notes_flag),
                })
            tallies["Service area boundary"][b_check or "(blank)"] += 1
            if (b_check and b_check != "Matches") or b_map or b_diff:
                boundaries.append({
                    "State": st, "ID": rid, "Name": name,
                    "Boundary on dashboard": get(vals, "bdash", None),
                    "Check": b_check, "Agency map": b_map, "What's different": b_diff,
                    "Reviewer": who, "Date": when, "Notes": notes,
                })
        progress[st] = (reviewed, total)

    missing = []
    if "Missing systems" in wb.sheetnames:
        ms = wb["Missing systems"]
        hdr = [text(c.value) for c in ms[3]]
        for vals in ms.iter_rows(min_row=4, values_only=True):
            row = {h: text(v) for h, v in zip(hdr, vals) if h}
            if row.get("System name"):
                missing.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    def dump(name, rows, fields):
        with open(args.out_dir / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    dump("proposed_changes.csv", changes,
         ["State", "ID", "Name", "Field", "Dashboard value at export", "CSV value now", "Proposed value",
          "Reviewer", "Date", "Sources", "Notes", "Flag"])
    dump("scope_flags.csv", flags,
         ["State", "ID", "Name", *scope_qs, "Reviewer", "Date", "Sources", "Notes", "Flag"])
    dump("boundary_findings.csv", boundaries,
         ["State", "ID", "Name", "Boundary on dashboard", "Check", "Agency map", "What's different",
          "Reviewer", "Date", "Notes"])
    dump("missing_systems.csv", missing,
         ["State", "System name", "Operator", "Website URL", "Why it looks in scope", "Added by", "Date"])

    done = sum(r for r, _ in progress.values())
    total = sum(t for _, t in progress.values())
    md = [f"# Validation results from {args.workbook.name}", "",
          f"Read {datetime.date.today().isoformat()}. {done} of {total} systems have at least one answer.", "",
          f"- Proposed field corrections: {len(changes)} "
          f"({sum(1 for c in changes if c['Flag'])} need a look, see the Flag column)",
          f"- Systems flagged on scope (No or Unsure): {len(flags)}",
          f"- Boundary findings (not a full match, or an agency map supplied): {len(boundaries)}",
          f"- Missing systems suggested: {len(missing)}", ""]
    if problems:
        md += ["## Problems reading the workbook", ""] + [f"- {p}" for p in problems] + [""]
    md += ["## Answers by field", "", "| Field | Confirmed / Yes | Corrected / No | Couldn't verify / Unsure | Blank |",
           "|---|---|---|---|---|"]
    for q in scope_qs:
        t = tallies[q]
        md.append(f"| {q} | {t['Yes']} | {t['No']} | {t['Unsure']} | {t['(blank)']} |")
    for f in check_fields:
        t = tallies[f]
        md.append(f"| {f} | {t['Confirmed']} | {t['Corrected']} | {t[CANT_VERIFY]} | {t['(blank)']} |")
    t = tallies["Service area boundary"]
    md += ["", "| Boundary | Matches | Partly matches | Doesn't match | No agency map found | Blank |",
           "|---|---|---|---|---|---|",
           f"| Service area boundary | {t['Matches']} | {t['Partly matches']} | {t[BOUNDARY_CHOICES[2]]} "
           f"| {t['No agency map found']} | {t['(blank)']} |"]
    md += ["", "## Progress by state", "", "| State | Reviewed | Systems |", "|---|---|---|"]
    for st, (r, t) in sorted(progress.items()):
        md.append(f"| {st} | {r} | {t} |")
    (args.out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"{done}/{total} systems reviewed; {len(changes)} proposed corrections, "
          f"{len(flags)} scope flags, {len(boundaries)} boundary findings, {len(missing)} missing systems.")
    for p in problems:
        print("WARNING:", p)
    print(f"Wrote results to {args.out_dir}")


if __name__ == "__main__":
    main()
