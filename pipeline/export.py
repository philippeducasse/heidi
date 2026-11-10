"""Write the five-tab workbook that is the deliverable: Leads, KPI definitions, Contacts,
Excluded and Methodology.

Every KPI column is followed by a <field>_source column holding the URL of the page the value
was taken from, so any row can be checked by hand. Empty means: not stated on the website.
The tab texts live in sheet_text.py.
"""
import json

import sheet_text as T
from common import DATA_DIR, read_jsonl
from contacts import COLUMNS as CONTACT_COLUMNS
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from score import KPI_FIELDS, UNRATED
from validate import REPORT_PATH as VALIDATION_PATH

OUT_PATH = DATA_DIR / "heidi_berlin_property_managers.xlsx"
BASE = ["company_id", "name", "segment", "website", "phone", "street", "postcode", "district"]
TAIL = ["sources", "website_ok", "emails", "directory_name"]
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
TIER_FILL = {"A": "C6EFCE", "B": "FFEB9C", "C": "F2F2F2", UNRATED: "DDEBF7"}


def cell(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return "" if value is None else value if isinstance(value, (int, float, str)) else str(value)


def lead_row(r):
    values = {k: r.get(k) for k in BASE}
    for field in KPI_FIELDS:
        values[field] = r.get(field)
        values[f"{field}_source"] = (r["evidence"].get(field) or [None])[0]
    return {**values, **{k: r.get(k) for k in TAIL},
            **{f"pts_{k}": v for k, v in r["points"].items()}, "score": r["score"], "tier": r["tier"]}


def sheet(wb, title, rows, headers=None, note=None, widths=60):
    ws = wb.create_sheet(title)
    if note:
        ws.append([note])
        ws.cell(1, 1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[1].height = 45
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers or rows[0]), 2))
    if headers:
        ws.append(headers)
        for c in ws[ws.max_row]:
            c.font, c.fill, c.alignment = Font(bold=True, color="FFFFFF"), HEADER_FILL, Alignment(wrap_text=True)
        ws.auto_filter.ref = f"A{ws.max_row}:{get_column_letter(len(headers))}{ws.max_row + len(rows)}"
        ws.freeze_panes = f"C{ws.max_row + 1}"  # a string: ws.cell() here would insert an empty row
    for row in rows:
        ws.append([cell(v) for v in (row.values() if isinstance(row, dict) else row)])
    for i in range(1, (len(headers or rows[0]) if headers or rows else 1) + 1):
        ws.column_dimensions[get_column_letter(i)].width = min(widths, max(
            12, *(len(str(c.value or "")) + 2 for c in ws[get_column_letter(i)])))
    return ws


def validation_note():
    # Accuracy measured by hand in validate.py; absent until someone has filled the spot-check file.
    if not VALIDATION_PATH.exists():
        return T.VALIDATION_MISSING
    v = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
    head, top = v["headline_random_sample"], v["top_scoring_sample"]
    pct = lambda s: f"{s['accuracy']:.0%}" if s["accuracy"] is not None else "not checked"
    return T.VALIDATION_NOTE.format(values=head["values"], companies=head["companies"],
                                    accuracy_pct=pct(head), verdicts=head["verdicts"],
                                    top_values=top["values"], top_pct=pct(top))


def main() -> None:
    scored = read_jsonl(DATA_DIR / "scored.jsonl")
    leads = [lead_row(r) for r in scored if not r["excluded_reason"]]
    wb = Workbook()
    wb.remove(wb.active)
    ws = sheet(wb, "Leads", leads, list(leads[0]), note=T.SOURCE_NOTE, widths=40)
    tier_col = get_column_letter(len(leads[0]))
    for row in range(ws.max_row - len(leads) + 1, ws.max_row + 1):  # colour the tier cell so A/B/C are visible at a glance
        if fill := TIER_FILL.get(ws[f"{tier_col}{row}"].value):
            ws[f"{tier_col}{row}"].fill = PatternFill("solid", fgColor=fill)
    sheet(wb, "KPI definitions", T.KPI_ROWS + [[]] + T.SCORING_NOTES, T.KPI_HEADERS, widths=70)
    contacts = read_jsonl(DATA_DIR / "contacts.jsonl")
    sheet(wb, "Contacts", contacts, list(contacts[0]) if contacts else CONTACT_COLUMNS,
          note=T.LEGAL_NOTE, widths=45)
    excluded = [[r["company_id"], r["name"], r["website"], ", ".join(r["sources"]), r["excluded_reason"]]
                for r in scored if r["excluded_reason"]]
    sheet(wb, "Excluded", excluded, ["company_id", "name", "website", "sources", "reason"],
          note=T.EXCLUSION_NOTE, widths=60)
    sheet(wb, "Methodology", T.METHOD_ROWS, T.METHOD_HEADERS, note=validation_note(), widths=90)
    wb.save(OUT_PATH)
    print(f"{len(leads)} leads, {len(contacts)} contacts, {len(excluded)} excluded -> {OUT_PATH}")
    print("\n" + T.PUBLISH_STEPS)


if __name__ == "__main__":
    main()
