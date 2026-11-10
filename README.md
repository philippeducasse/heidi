# Heidi Leads — Berlin property management companies

A small Python pipeline that builds a qualified lead list of Berlin property managers
(Hausverwaltungen) for Heidi Systems, from public sources, with a source URL behind every value.

```
collect_* → dedupe → crawl → extract (LLM) → score → contacts → export → Google Sheet
```

The deliverable is `data/heidi_berlin_property_managers.xlsx`, published as a Google Sheet.

## Setup

```bash
uv sync
echo "MISTRAL_API_KEY=..." > .env
```

## Running the pipeline

Each step reads the previous step's file from `data/` and writes its own, so steps can be
re-run individually. Run them from the `pipeline/` folder:

| # | Command | Writes | Notes |
|---|---|---|---|
| 1 | `python collect_osm.py` | `raw_osm.jsonl` | OpenStreetMap Overpass, Berlin boundary |
| 2 | `python collect_gelbeseiten.py` | `raw_gelbeseiten.jsonl` | |
| 3 | `python collect_dasoertliche.py` | `raw_dasoertliche.jsonl` | |
| 4 | `python collect_vdiv.py` | `raw_vdiv.jsonl` | VDIV Berlin-Brandenburg members |
| 5 | `python dedupe.py` | `companies.jsonl` | merges all `raw_*.jsonl` |
| 6 | `python crawl.py` | `crawl.jsonl` | homepage, Impressum, about, team; slow |
| 7 | `python extract.py` | `extracted.jsonl` | Mistral; resumable, costs money |
| 8 | `python score.py` | `scored.jsonl` | points, tier, exclusions |
| 9 | `python contacts.py` | `contacts.jsonl` | Impressum names, published emails only |
| 10 | `python export.py` | `heidi_berlin_property_managers.xlsx` | the five-tab workbook |

`extract.py` appends as it goes and skips domains already done, so it is safe to interrupt and
restart. `python extract.py --recheck` re-verifies the saved quotes without calling the API.

## Publishing as a Google Sheet

1. drive.google.com → **New → File upload** → `data/heidi_berlin_property_managers.xlsx`
2. Right-click the file → **Open with → Google Sheets**
3. **File → Share → General access: "Anyone with the link", Viewer**
4. Copy the link and open it in a private window to confirm it is reachable.

Formatting (frozen header, autofilter, column widths, tier colours) survives the import.
The sheet is a snapshot: re-running the pipeline creates a new file rather than updating it.

## What makes a value trustworthy

The LLM must return a verbatim quote for every value. `extract.py` then searches that quote in
the crawled pages; if it is not found, the value is marked unverified and no later step uses it.
A missing value therefore never earns points, and every filled cell in the Leads tab has a
source URL next to it.

Emails are only kept when they literally appear on the company's own site. No pattern guessing,
no email-finding services. Cold B2B email in Germany is restricted by UWG § 7 and the personal
data here falls under GDPR Art. 6(1)(f) — see the legal note on the Contacts tab.

## Data files

`data/` is gitignored: it holds intermediate JSONL, the workbook, and nothing that cannot be
rebuilt by re-running the pipeline.
