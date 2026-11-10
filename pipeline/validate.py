"""Spot-check validation: sample rows by hand and report the measured accuracy.

Two modes:
  python validate.py sample   -> data/spotcheck.csv, one row per value to check, with its quote
                                 and source URL. Open it, visit each URL, and fill the "verdict"
                                 column with ok / wrong / unclear.
  python validate.py report   -> reads the filled file back and prints accuracy per field and
                                 overall, and writes data/validation.json for the doc and sheet.

The sample is drawn with a fixed seed, so re-running sample does not shuffle a partly filled
file. Only verified values are sampled: those are the ones that reach the sheet.
"""
import csv
import json
import random
import sys
from collections import Counter

from common import DATA_DIR, read_jsonl

SAMPLE_PATH = DATA_DIR / "spotcheck.csv"
REPORT_PATH = DATA_DIR / "validation.json"
COLUMNS = ["company_id", "company", "field", "value", "source_url", "quote", "verdict", "note"]
SAMPLE_SIZE = 30  # companies, not values: a reviewer checks a whole row at a time
SEED = 20261110


def rows_for(lead):
    for field, (url, quote) in sorted(lead["evidence"].items()):
        yield {"company_id": lead["company_id"], "company": lead["name"], "field": field,
               "value": json.dumps(lead.get(field), ensure_ascii=False), "source_url": url,
               "quote": quote, "verdict": "", "note": ""}


def sample() -> None:
    leads = [r for r in read_jsonl(DATA_DIR / "scored.jsonl") if r["evidence"] and not r["excluded_reason"]]
    picked = random.Random(SEED).sample(leads, min(SAMPLE_SIZE, len(leads)))
    rows = [row for lead in picked for row in rows_for(lead)]
    with SAMPLE_PATH.open("w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel reads the umlauts
        writer = csv.DictWriter(f, COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} values from {len(picked)} of {len(leads)} companies -> {SAMPLE_PATH}")
    print("fill the verdict column with ok / wrong / unclear, then run: python validate.py report")


def report() -> None:
    with SAMPLE_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["verdict"].strip().lower() in ("ok", "wrong", "unclear")]
    counts = Counter(r["verdict"].strip().lower() for r in rows)
    per_field = {field: dict(Counter(r["verdict"].strip().lower() for r in rows if r["field"] == field))
                 for field in sorted({r["field"] for r in rows})}
    accuracy = counts["ok"] / len(rows) if rows else 0.0
    summary = {"companies_checked": len({r["company_id"] for r in rows}), "values_checked": len(rows),
               "accuracy": round(accuracy, 3), "verdicts": dict(counts), "per_field": per_field}
    REPORT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{summary['values_checked']} values from {summary['companies_checked']} companies checked by hand")
    print(f"accuracy: {accuracy:.1%}  {dict(counts)}")
    for field, c in per_field.items():
        n = sum(c.values())
        print(f"  {field:22s} {c.get('ok', 0)}/{n}  {c.get('ok', 0) / n:.0%}")
    print(f"-> {REPORT_PATH}")


if __name__ == "__main__":
    report() if "report" in sys.argv else sample()
