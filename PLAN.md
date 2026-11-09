# Heidi Systems Case – Plan

**Role:** AI Agent Builder
**Deadline:** Tuesday, 10 November 2026, 18:00 (Berlin time)
**Deliverables:** Google Sheet (preferred) or Excel file, plus an approach presentation or doc. All links must be accessible to anyone with the link.

---

## Guiding idea

The role is **AI Agent Builder**, so the list itself matters less than the pipeline that produces it and how it is explained. Build something repeatable rather than a list collected by hand.

```
Collect → Dedupe → Enrich (crawl + LLM extraction) → Score → Export to Google Sheet
                                                        ↓
                                              Approach doc (Task 3)
```

A small Python pipeline in this folder produces the whole sheet, and the doc describes that pipeline.

---

## Task 1: Collect Berlin property management companies

**Target:** 500–1,500 companies

Use several sources so they can be cross-checked:

- **OpenStreetMap (Overpass API)**: free replacement for Google Places (no key available). Query `office=property_management` plus names containing "Hausverwaltung" / "Immobilienverwaltung" / "WEG-Verwaltung" within Berlin.
- **Directories**: VDIV Berlin-Brandenburg member list, Gelbe Seiten, 11880, Das Örtliche, ImmoScout24's property manager directory.
- **Registers**: Northdata or Handelsregister for legal form, founding year, managing directors and size signals.

**Dedupe:**
1. Match on website domain.
2. Then match on phone number.
3. Then use a fuzzy name match.

Keep a `sources` column so the sheet shows which companies more than one source confirms.

---

## Task 2: Qualifying KPIs

Choose KPIs a metering provider would actually care about:

| KPI | Why it matters to Heidi |
|---|---|
| **Units under management** | The best proxy for revenue, since more units means more meters. Websites often state it ("über 3.000 Einheiten"). |
| **Management type** (WEG / Miet / SEV / Gewerbe) | Residential WEG and rental management fall under the Heizkostenverordnung, so these are the core buyers. |
| **Employees** | A size signal and a fallback when the unit count isn't published. |
| **Independent vs. group-owned** | Groups like Vonovia or Deutsche Wohnen handle metering in-house, so they're worth excluding. |
| **Digital maturity** | Tenant portal, software used (Casavi, Immoware24, DOMUS, Karthago). This shows how well Heidi would integrate. |
| **Current metering provider** (ista, Techem, Brunata, Minol), if visible | Shows whether they'd need to switch from an incumbent. |
| **Pain signals** | Google reviews complaining about late or wrong Nebenkostenabrechnungen. |
| **Growth signals** | Open job postings, recent founding, acquisitions. |
| **Lead score + tier (A/B/C)** | A weighted mix of the above, with the weights shown openly in the sheet. |
| **Confidence + source URL** per data point | Lets the reader check where each value came from. |

**Timing hook:** under the HKVO, all heat and water meters must be remotely readable by **31 Dec 2026**, which is seven weeks away. That deadline is a strong reason for these companies to act now, so use it in both the scoring and the doc.

---

## Bonus: Contact persons

- **Impressum pages**: German law requires them to name the managing director (Geschäftsführer), so we get a named person for almost every company.
- **Email**: only personal addresses published on the company's own site. If none is found, the email field stays empty (no guessing).
- **LinkedIn**: search `site:linkedin.com/in "<Firma>" Geschäftsführer`.
- **Legal note:** German law (UWG §7) restricts cold B2B email, and personal data falls under the GDPR. Mention both in the doc.

---

## Validation

- An LLM pulls the data out of each crawled website as structured output. It must quote the text it relied on and give the source URL. Any value without that evidence is left empty.
- Check that each website is live, and match companies against the Handelsregister.
- Spot-check a random sample of about 30 rows by hand and **report the accuracy found** in the doc.

---

## Sheet layout

Five tabs:

1. **Leads**: the main table.
2. **KPI definitions & scoring weights**
3. **Contacts**
4. **Excluded (with reason)**
5. **Methodology/Sources**

---

## Task 3: Approach doc (5–7 slides)

1. Goal and how a good lead is defined
2. The pipeline diagram
3. Sources and tools
4. KPI rationale and scoring
5. Validation and accuracy numbers
6. Limitations and next steps, e.g. running it for all of Germany, a CRM sync, or a recurring agent that keeps the list fresh

---

## Timeline

| When | What |
|---|---|
| **Mon 9 Nov (today)** | Collection and dedupe, then crawling and LLM enrichment |
| **Tue 10 Nov, morning** | Scoring, contacts and spot-check validation |
| **Tue 10 Nov, early afternoon** | Build the sheet, write the doc, send with a buffer before 18:00 |

---

## Decisions (answered)

1. **API access:** no Google Places key. LLM = **Mistral** (own key). No budget for email-finding tools.
2. **Scope:** build the full pipeline here, **slowly**: batches of max 50 lines of code (docs/config excluded), with a review by Philippe after each batch.
3. **Language:** all deliverables in **English**.

### What changes because of this

- **Collection without Google Places:** use **OpenStreetMap (Overpass API, free)** with `office=property_management` and name matches on "Hausverwaltung" / "Immobilienverwaltung" inside Berlin's boundary. Then add scraped directories (Gelbe Seiten, 11880, Das Örtliche) and the VDIV Berlin-Brandenburg member list.
- **LLM:** Mistral chat API with JSON output (`mistral-small-latest` for bulk extraction to keep costs low).
- **Contacts without Hunter/Apollo:**
  - Names of managing directors from the **Impressum** (legally required).
  - Personal emails found directly on the site (team pages, Impressum, vCards). If none is found, leave the email empty. No pattern guessing.
  - LinkedIn: build a search URL per contact rather than scraping LinkedIn (scraping it breaks their terms).

## Build order (batches of max 50 lines of code)

1. Project setup + OSM Overpass collector
2. Directory collectors (one per batch)
3. Dedupe
4. Website crawler (homepage, Impressum, about/team pages)
5. Mistral extraction with evidence quotes
6. Scoring + tiers
7. Contacts (Impressum names, personal emails published on the site)
8. Export to Excel (5 tabs), then upload to Google Sheets
9. Spot-check validation
10. Approach doc
