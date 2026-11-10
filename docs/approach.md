---
marp: true
paginate: true
title: Berlin property managers — lead pipeline for Heidi Systems
---

<!--
Format: Marp deck. Render with `npx @marp-team/marp-cli@latest docs/approach.md --pdf`,
or paste each slide into Google Slides (slides are separated by `---`).

Two TODOs remain: the measured accuracy and the Google Sheet link.
-->

# Berlin property managers
### A lead pipeline for Heidi Systems

Philippe · AI Agent Builder case · 10 November 2026

**Deliverable:** 1,225 qualified companies, 1,050 named contacts, every value traceable to a source URL.
**What was actually built:** the pipeline that produces that sheet, re-runnable in a day.

---

## 1. Goal, and what makes a lead good

**Heidi sells submetering** — heat and water meters, readings, and the annual
Heizkostenabrechnung. The buyer is the **property manager (Hausverwaltung)** who decides for
dozens of buildings at once.

A good lead is therefore:

| | |
|---|---|
| **Big** | Units under management ≈ number of meters ≈ revenue |
| **In the regulated core** | WEG and Mietverwaltung manage residential property under the HeizkostenV |
| **Independent** | Not a listed group — those meter in-house or tender centrally |
| **Reachable** | A named Geschäftsführer, not an `info@` mailbox |
| **Under time pressure** | See below |

> **The hook: 31 December 2026 — seven weeks away.**
> **§ 5 Abs. 3 HeizkostenV:** meters that are not remotely readable and were installed up to
> 1 Dec 2021 must be **retrofitted or replaced** by then — and must end up readable without
> entering the flat, connectable to a smart-meter gateway, and interoperable (§ 5 Abs. 2 and 5).
> Miss it and **tenants may cut their heating-cost share by 3 %** (§ 12 Abs. 1).
> A **February 2026 manager survey put equipment levels at only 58–61 %.**

*Note: the legal duty is the **building owner's**, not the manager's — but the manager
specifies, procures and coordinates it. That is who Heidi has to convince.*

---

## 2. The pipeline

```
 collect_osm ─┐
 gelbeseiten ─┤
 dasoertliche ├─→ dedupe ─→ crawl ─→ extract ─→ score ─→ contacts ─→ export ─→ Google Sheet
 vdiv ────────┘   (union-   (4 pages  (Mistral +  (points,  (Impressum   (5 tabs)
                   find)     per site)  quote      tier)     names)
                                        check)
                                           └──→ validate (30-company hand check)
```

**Ten standalone steps, each writing a JSONL file.** Why files and not one program:

- **Cost asymmetry.** Crawling and LLM extraction are slow, flaky and cost money; everything
  else is cheap and pure. The file boundary sits exactly between them.
- **Resumable.** `extract.py` appends per site and skips what's done — safe to interrupt.
- **Cheap iteration.** Re-scoring all companies is a sub-second loop, no network, no cost.
- **Auditable.** Any cell walks backwards: sheet → `scored` → `extracted` (quote + URL) → `crawl`.

---

## 3. Sources and tools

| Source | What it gives | Trust |
|---|---|---|
| **VDIV Berlin-Brandenburg** | Members, self-registered legal names | highest — and it's a KPI || **Das Örtliche** | Address, phone | names sometimes abbreviated |
| **Gelbe Seiten** | Address, phone, website | often lists the owner, not the firm |
| **OpenStreetMap (Overpass)** | `office=property_management` in Berlin | crowd-sourced, sparse |
| ~~11880~~ | — | **dropped:** Cloudflare 403 + captcha, websites only on detail pages |

**No Google Places key, no Hunter/Apollo, no paid data.** OSM replaces Places; contacts come
from the legally mandatory Impressum.

**Tools:** Python, `requests` + BeautifulSoup, **Mistral `mistral-small-latest`** (temperature 0,
JSON mode) for extraction, `openpyxl` for the workbook.

**Dedupe:** one company = one row. Merge on website domain, phone, or normalised name within a
postcode; matches chain through union-find. The `sources` column shows how many directories
confirm each company.

---

## 4. KPIs and scoring

Weights are **derived from the regulation and from what drives Heidi's revenue**, and are
printed openly in the sheet's "KPI definitions" tab.

| KPI | Points | Rationale |
|---|---|---|
| Units managed | **30** | Best proxy for meters, i.e. revenue |
| Employees | 25 | Fallback when units aren't published |
| Management type (WEG / Miet) | **25** | HeizkostenV applies to residential — the compulsory buyers |
| Digital maturity (Casavi, portal) | 10 | Easier integration, more open to new workflow |
| Hiring | 10 | Growth and budget signal |
| VDIV member | 10 | **Heidi is a VDIV Kooperationspartner** — a warm channel, not a cold list |
| Named decision maker | 10 | Makes the lead actionable |
| Independent | 5 | Groups meter in-house |
| *Current metering provider* | *0* | *Not scored — it shapes the pitch (switch vs. greenfield)* |

**Tiers:** A ≥ 50 (234) · B ≥ 30 (133) · C below (123) · **Unrated (735)** — no website data, so
the score would say nothing. Those keep phone and address and stay callable; they are not C.

**Segment, not exclusion.** heidisystems.com names *Wohnungsunternehmen* and *Asset Manager &
Fonds* as customer segments, so own-stock owners stay in the list, tagged
**Verwalter / Wohnungsunternehmen / kommunal / Genossenschaft** — they buy on a longer cycle,
often via tender. **Only the large listed groups are excluded** (Vonovia, Deutsche Wohnen,
Covivio, Heimstaden, Grand City): they meter in-house or tender centrally.

**Not a disqualifier:** an incumbent (ista, Techem, Brunata, Minol) is a *target*, not a dead
end — Heidi takes over existing meters even while the old contract runs.

---

## 5. Validation — two layers

**Layer 1 — machine, on 100% of values.** The LLM must return a **verbatim quote** for every
value. The code then searches that quote in the crawled pages. Not found → `verified=False` →
every later step ignores it.

- Stitched quotes are checked **part by part**; quotes under 15 characters don't count.
- Better than a self-reported confidence score (uncalibrated, unfalsifiable) and cheaper than
  running extraction twice (temperature 0 — little randomness to catch, systematic errors repeat).

**Layer 2 — human, on a sample.** Quote verification proves *provenance*, not *inference*: the
quote is on the page, but does the value follow from it? `validate.py` draws **30 random
companies** (fixed seed) and exports every value with its quote and URL for a hand check.

> **Measured accuracy: TODO — fill from data/validation.json after the spot-check.**

**Coverage:** 490 of 1,225 companies had a website we could read and verify; 735 are unrated for
lack of website data; only 119 publish a unit count, so most size points come from employees.

---

## 6. Limitations and next steps

**Limitations — stated, not hidden**
- **Coverage is honest, not complete.** No unit count on the site → no points, so small firms are
  under-scored because they publish less, not because they're worse leads.
- **Dedupe source priority is a judgement, not a measurement.** Chained matching can over-merge
  via a shared serviced-office phone; under-merge is likelier for firms with no website.
- **Berlin only, a snapshot, no Handelsregister cross-check yet.**
- **Contacts are deliberately thin** — emails only where published. UWG § 7 and GDPR Art. 6(1)(f)
  make **phone the better channel** for this list anyway.

**Next — days**
Handelsregister enrichment · Google reviews as a **pain signal** (late or wrong
Nebenkostenabrechnung is the sharpest buying trigger there is) · re-rank sources from measured
disagreement.

**Next — scale**
All of Germany: only the Overpass boundary and directory queries are Berlin-specific; cost scales
with the LLM step · CRM sync with score and evidence URLs attached.

**Next — make it an agent (the actual role)**
Scheduled re-crawl that watches for *change* — a new vacancy, a new portal, a lost metering
provider — and re-scores on the delta · per-lead call brief generated from the evidence: what they
manage, what they use today, what § 5 Abs. 3 HeizkostenV means for them before 31 Dec 2026.

<!-- Sources: § 5, § 12 HeizkostenV, gesetze-im-internet.de/heizkostenv (Stand 16.10.2023);
     equipment-level survey Feb 2026 reported via PresseBox, 19.09.2026. -->


---

## Thank you

**Sheet:** TODO — paste the share link (anyone with the link, Viewer)
**Code:** 13 scripts, ~950 lines — `README.md` explains every step and how to re-run it.

One rule holds the whole thing together:

> **Every value is either traceable to a source, or it isn't there.**

<!-- Render: npx @marp-team/marp-cli@latest docs/approach.md --pdf -->

---

<!--
STILL TO FILL IN
  Measured accuracy (slide 5)    -> data/validation.json, after filling data/spotcheck.csv
  Google Sheet link (last slide) -> after the manual import
-->
