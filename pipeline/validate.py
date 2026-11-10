"""Spot-check validation: sample rows by hand and report the measured accuracy.

Two modes:
  python validate.py sample   -> data/spotcheck.csv, one row per value to check, with its quote
                                 and source URL. Open it, visit each URL, and fill the "verdict"
                                 column with ok / wrong / unclear.
  python validate.py report   -> reads the filled file back and prints accuracy per field and
                                 overall, and writes data/validation.json for the doc and sheet.

Two groups are sampled, and the "sample" column says which is which:
  random  - 30 companies drawn with a fixed seed. This is the UNBIASED number and the one to
            quote as "the accuracy of the sheet".
  top     - the highest-scoring companies. They are the ones a salesperson calls first, and a
            perfect score on every KPI is exactly where extraction errors would hide, so they
            are checked deliberately. Their accuracy is reported SEPARATELY: mixing a
            hand-picked group into the headline number would not be a measurement any more.

The seed is fixed, so re-running sample does not reshuffle a partly filled file. Only verified
values are sampled: those are the ones that reach the sheet.
"""
import csv
import json
import random
import sys
from collections import Counter

from common import DATA_DIR, read_jsonl

SAMPLE_PATH = DATA_DIR / "spotcheck.csv"
REPORT_PATH = DATA_DIR / "validation.json"
COLUMNS = ["sample", "company_id", "company", "score", "field", "value", "source_url", "quote", "verdict", "note"]
SAMPLE_SIZE = 30  # companies, not values: a reviewer checks a whole row at a time
TOP_N = 10  # highest-scoring companies, checked on purpose rather than by chance
SEED = 20261110


def rows_for(lead, group):
    for field, (url, quote) in sorted(lead["evidence"].items()):
        yield {"sample": group, "company_id": lead["company_id"], "company": lead["name"],
               "score": lead["score"], "field": field,
               "value": json.dumps(lead.get(field), ensure_ascii=False), "source_url": url,
               "quote": quote, "verdict": "", "note": ""}


def filled_verdicts():
    if not SAMPLE_PATH.exists():
        return 0
    with SAMPLE_PATH.open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for r in csv.DictReader(f) if r.get("verdict", "").strip())


def sample() -> None:
    if (done := filled_verdicts()) and "--force" not in sys.argv:
        print(f"{SAMPLE_PATH} already has {done} verdicts filled in. Not overwriting that work.")
        print("Use --force to redraw the sample from scratch.")
        return
    leads = [r for r in read_jsonl(DATA_DIR / "scored.jsonl") if r["evidence"] and not r["excluded_reason"]]
    top = sorted(leads, key=lambda r: -r["score"])[:TOP_N]
    rest = [r for r in leads if r["company_id"] not in {t["company_id"] for t in top}]
    picked = random.Random(SEED).sample(rest, min(SAMPLE_SIZE, len(rest)))
    rows = ([row for lead in top for row in rows_for(lead, "top")]
            + [row for lead in picked for row in rows_for(lead, "random")])
    with SAMPLE_PATH.open("w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel reads the umlauts
        writer = csv.DictWriter(f, COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} values to check -> {SAMPLE_PATH}")
    print(f"  top:    {len(top)} highest-scoring companies (scores "
          f"{top[-1]['score']}-{top[0]['score']}), checked on purpose")
    print(f"  random: {len(picked)} of {len(rest)} other companies, fixed seed - the headline number")
    print("fill the verdict column with ok / wrong / unclear, then run: python validate.py report")


def report() -> None:
    with SAMPLE_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["verdict"].strip().lower() in ("ok", "wrong", "unclear")]
    if not rows:
        # Never write a 0% result from an unfilled file: export.py would print it as a measured fact.
        print(f"no verdicts filled in yet in {SAMPLE_PATH} - nothing to report.")
        print("open it, put ok / wrong / unclear in the verdict column, then run this again.")
        return
    def stats(subset):
        c = Counter(r["verdict"].strip().lower() for r in subset)
        return {"companies": len({r["company_id"] for r in subset}), "values": len(subset),
                "accuracy": round(c["ok"] / len(subset), 3) if subset else None, "verdicts": dict(c)}

    random_rows = [r for r in rows if r.get("sample") != "top"]
    per_field = {field: dict(Counter(r["verdict"].strip().lower() for r in random_rows if r["field"] == field))
                 for field in sorted({r["field"] for r in random_rows})}
    # Headline = the random sample only. The top rows are hand-picked, so folding them in would
    # turn a measurement into a flattering average.
    summary = {"headline_random_sample": stats(random_rows),
               "top_scoring_sample": stats([r for r in rows if r.get("sample") == "top"]),
               "all_checked": stats(rows), "per_field_random": per_field}
    REPORT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    for label, key in [("random (headline)", "headline_random_sample"), ("top-scoring", "top_scoring_sample")]:
        s = summary[key]
        acc = f"{s['accuracy']:.1%}" if s["accuracy"] is not None else "not checked"
        print(f"{label:18s} {s['values']:3d} values / {s['companies']:2d} companies  accuracy {acc}  {s['verdicts']}")
    for field, c in per_field.items():
        n = sum(c.values())
        print(f"  {field:22s} {c.get('ok', 0)}/{n}  {c.get('ok', 0) / n:.0%}")
    print(f"-> {REPORT_PATH}")


if __name__ == "__main__":
    report() if "report" in sys.argv else sample()
