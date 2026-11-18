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

and data/validation.json, which the dashboard's Validation tab reads. That file
is public (GitHub Pages), so it carries no reviewer names: each review is marked
"independent" or "project" (pass --self NAME for the project team's own names,
as typed in the Reviewed by column). Commit it after each ingest.

Manual calls live in scripts/validation/tags.csv (State, Name, Field, Type,
Status, Note): what kind of correction a change is when it can't be inferred
(error / cosmetic / ...), and whether a finding is resolved. Field is a core
field name, "Scope" or "Service area boundary".

Nothing here edits ODT_Inventory.csv. Apply changes by hand (or in a Claude
session), rebuild with scripts/build.py, and log each one in concerns.csv
with the reviewer's source, per CLAUDE.md.
"""
import argparse
import csv
import datetime
import json
import re
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
DEFAULT_JSON = ROOT / "data" / "validation.json"
TAGS_PATH = Path(__file__).resolve().parent / "tags.csv"

# Correction types. Inferred where possible, otherwise set in tags.csv.
FIELD_TYPES = {"gap", "refinement", "cosmetic", "error", "not_error"}
BOUNDARY_TYPES = {"method_question", "proxy_ok", "redraw", "needs_agency_map"}
STATUSES = {"open", "applied", "declined", "removed", "kept", "resolved"}
EMPTY_VALUES = {"", "not specified", "unknown", "n/a", "none"}


def infer_type(exported, proposed):
    """gap: we had nothing; refinement: the new value keeps ours and adds to it."""
    e, p = exported.strip().lower(), proposed.strip().lower()
    if e in EMPTY_VALUES:
        return "gap"
    if p and e in p:
        return "refinement"
    return None  # needs a call in tags.csv


def load_tags():
    tags = {}
    if not TAGS_PATH.exists():
        return tags
    with open(TAGS_PATH, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = (r["State"].strip(), r["Name"].strip(), r["Field"].strip())
            t, st = r.get("Type", "").strip(), r.get("Status", "").strip()
            if t and t not in FIELD_TYPES | BOUNDARY_TYPES:
                sys.exit(f"tags.csv: unknown Type {t!r} for {key}")
            if st and st not in STATUSES:
                sys.exit(f"tags.csv: unknown Status {st!r} for {key}")
            tags[key] = {"type": t, "status": st, "note": r.get("Note", "").strip()}
    return tags


def split_urls(s):
    return [u for u in (x.strip() for x in s.replace(";", " ").replace(",", " ").split()) if u.startswith("http")]


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
    ap.add_argument("--json", type=Path, default=DEFAULT_JSON, help="dashboard data file (default data/validation.json)")
    ap.add_argument("--no-json", action="store_true", help="don't write the dashboard data file")
    ap.add_argument("--self", dest="self_names", action="append", default=[], metavar="NAME",
                    help="a project-team reviewer name, as typed in Reviewed by (repeatable)")
    args = ap.parse_args()
    self_names = {n.strip().lower() for n in args.self_names}
    tags = load_tags()
    used_tags = set()
    reviews, pub_findings = [], []
    reviewer_kinds = defaultdict(set)

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
            by = "project" if who.strip().lower() in self_names else "independent"
            reviewer_kinds[by].add(who.strip().lower() or "(unnamed)")
            reviews.append({
                "state": st, "id": rid, "name": name, "by": by, "date": when,
                "scope": {q: scope[q] for q in scope_qs},
                "checks": {f: checks[f] for f in check_fields},
                "boundary": b_check,
            })
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
                tg = tags.get((st, name, "Scope"), {})
                if tg:
                    used_tags.add((st, name, "Scope"))
                pub_findings.append({
                    "kind": "scope", "state": st, "id": rid, "name": name, "by": by, "date": when,
                    "answers": {q: scope[q] for q in scope_qs},
                    "status": tg.get("status") or ("removed" if row_live is None else "open"),
                    "sources": split_urls(sources), "notes": notes, "call": tg.get("note", ""),
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
                tg = tags.get((st, name, f), {})
                if tg:
                    used_tags.add((st, name, f))
                applied = bool(row_live) and proposed and now.strip().lower() == proposed.strip().lower()
                pub_findings.append({
                    "kind": "field", "state": st, "id": rid, "name": name, "by": by, "date": when,
                    "field": f, "from": exported, "to": proposed,
                    "type": tg.get("type") or infer_type(exported, proposed) or "unclassified",
                    "status": tg.get("status") or ("applied" if applied else "open"),
                    "sources": split_urls(sources), "notes": notes, "call": tg.get("note", ""),
                    "flag": "; ".join(notes_flag),
                })
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
                key = (st, name, "Service area boundary")
                tg = tags.get(key, {})
                if tg:
                    used_tags.add(key)
                pub_findings.append({
                    "kind": "boundary", "state": st, "id": rid, "name": name, "by": by, "date": when,
                    "check": b_check, "on_dashboard": get(vals, "bdash", None),
                    "agency_map": b_map, "difference": b_diff,
                    "type": tg.get("type") or "", "status": tg.get("status") or "open",
                    "sources": split_urls(sources), "notes": notes, "call": tg.get("note", ""),
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

    for key in sorted(set(tags) - used_tags):
        problems.append(f"tags.csv row {key} matched no finding in this workbook (renamed, or the answer changed?)")
    if not args.no_json:
        out = {
            "read": datetime.date.today().isoformat(),
            "total_systems": total,
            "states": {st: t for st, (_, t) in sorted(progress.items())},
            "reviewers": {k: len(v) for k, v in reviewer_kinds.items()},
            "fields": check_fields,
            "scope_questions": scope_qs,
            "reviews": reviews,
            "findings": pub_findings,
            "missing": [{"state": m.get("State", ""), "name": m.get("System name", ""),
                         "operator": m.get("Operator", ""), "url": m.get("Website URL", ""),
                         "why": m.get("Why it looks in scope", ""), "date": m.get("Date", "")} for m in missing],
        }
        # Notes are free text; drop any reviewer's name (full or first) before publishing.
        names = sorted({n for ns in reviewer_kinds.values() for n in ns if n != "(unnamed)"}, key=len, reverse=True)
        tokens = names + sorted({n.split()[0] for n in names if len(n.split()[0]) >= 3}, key=len, reverse=True)
        def scrub(t):
            for n in tokens:
                t = re.sub(r"\b" + re.escape(n) + r"\b", "[reviewer]", t, flags=re.I)
            return t
        for f in out["findings"]:
            f["notes"] = scrub(f["notes"])
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if not self_names:
            print("Note: no --self given, so every review is counted as independent.")

    print(f"{done}/{total} systems reviewed; {len(changes)} proposed corrections, "
          f"{len(flags)} scope flags, {len(boundaries)} boundary findings, {len(missing)} missing systems.")
    for p in problems:
        print("WARNING:", p)
    print(f"Wrote results to {args.out_dir}" + ("" if args.no_json else f" and {args.json.relative_to(ROOT) if args.json.is_relative_to(ROOT) else args.json}"))


if __name__ == "__main__":
    main()
