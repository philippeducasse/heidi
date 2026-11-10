"""Static text for the documentation tabs of the workbook (KPI definitions and methodology).

Kept apart from export.py so the code stays short and the wording can be edited without
touching logic. Each KPI row: name, what it means, where it comes from, points.
"""
from score import LISTED_GROUPS

KPI_HEADERS = ["KPI", "Why it matters to Heidi", "Where the value comes from", "Max points"]
KPI_ROWS = [
    ["units_managed", "Best proxy for revenue: more units means more meters to install and read.",
     "Company website (Impressum, 'Über uns', service pages), extracted by LLM with a verbatim quote.",
     "30 (>=2000: 30, >=500: 20, >=100: 10, below: 5)"],
    ["employees", "Size signal and fallback when the unit count is not published.",
     "Company website (team pages, 'Über uns').", "25, only if units_managed is missing (>=15: 25, >=5: 15, below: 5)"],
    ["management_types", "WEG and Mietverwaltung manage residential property under the HeizkostenV, so they are "
     "the core buyers. "
     "Pure Gewerbe or SEV is a weaker fit.", "Company website (service descriptions).",
     "25 if WEG or Miet, 10 if only other types"],
    ["software_or_portal", "Digital maturity: a company already running Casavi, Immoware24, DOMUS or a tenant portal "
     "is easier to integrate with and more open to a new metering workflow.", "Company website (portal links, footer).", "10"],
    ["hiring", "Growth signal: an open vacancy means the company is expanding and has budget.",
     "Company website (Karriere / Stellenangebote pages).", "10"],
    ["vdiv_member", "Membership in the VDIV Berlin-Brandenburg means a professional manager, reachable through the "
     "association and its events.", "VDIV member directory.", "10"],
    ["decision_maker", "A named Geschäftsführer or contact makes the lead actionable instead of a company mailbox.",
     "Impressum (legally required in Germany) or directory listing.", "10"],
    ["independent", "Groups such as Vonovia or Deutsche Wohnen do metering in-house or through central tenders, "
     "so an independent manager is the better target.", "Company website (parent company mentions).",
     "5 if no parent company is stated"],
    ["metering_provider", "Shows whether the company would have to switch away from ista, Techem, Brunata or Minol. "
     "Not scored, but it drives the sales pitch.", "Company website (billing info, FAQ).", "0 (context only)"],
]
SCORING_NOTES = [
    ["Total", "Sum of the points above, capped by design at 100."],
    ["Tier A", "score >= 50 - contact first."],
    ["Tier B", "score >= 30 - second wave."],
    ["Tier C", "score < 30 - mostly small or thinly documented companies."],
    ["Excluded", "Not a lead at all; see the Excluded tab for the reason. These rows get no tier."],
    ["Segment", "Verwalter / Wohnungsunternehmen / Wohnungsunternehmen (kommunal) / Genossenschaft. This is the "
     "sales motion, not the quality: own-stock owners are customers of Heidi too (they are named as segments on "
     "heidisystems.com), but they decide more slowly and municipal ones usually run a tender. Sort by it to split "
     "the quick wins from the long game."],
    ["Unverified values", "A value is only scored if the LLM's quote was found character-for-character on the "
     "crawled page. Anything else is treated as missing, so a missing value never earns points."],
    ["Timing", "Section 5(3) HeizkostenV: meters that are not remotely readable and were installed up to "
     "1 Dec 2021 must be retrofitted or replaced by 31 Dec 2026 - they then have to be readable without entering "
     "the flat, connectable to a smart-meter gateway and interoperable (section 5(2) and (5)). "
     "The duty is the building owner's, and the property manager procures it for them. "
     "If it is missed, tenants may cut their heating-cost share by 3 percent (section 12(1)). "
     "A Feb 2026 manager survey put equipment levels at only 58-61 percent, so most of this list still has to act."],
]
METHOD_HEADERS = ["Step", "What happens", "Script"]
METHOD_ROWS = [
    ["1. Collect", "OpenStreetMap Overpass (office=property_management plus name matches inside Berlin), "
     "Gelbe Seiten, Das Oertliche and the VDIV Berlin-Brandenburg member list. "
     "11880 was dropped: Cloudflare blocks automated requests.", "collect_*.py"],
    ["2. Dedupe", "Records are merged when they share a website domain, a phone number, or a normalised name in the "
     "same postcode. Matches chain, so A-B by phone and B-C by domain give one company. "
     "The 'sources' column shows how many directories confirm a company.", "dedupe.py"],
    ["3. Crawl", "Homepage plus Impressum, 'Ueber uns' and team pages of each website.", "crawl.py"],
    ["4. Extract", "Mistral (mistral-small-latest, temperature 0, JSON output) reads the crawled text and returns one "
     "value plus a verbatim quote per KPI. The code then searches that quote in the crawled pages; if it is not "
     "found the value is marked unverified and ignored. This is the guard against hallucinated numbers.", "extract.py"],
    ["5. Score", "Points per KPI as described in the 'KPI definitions' tab, then a tier.", "score.py"],
    ["6. Contacts", "Names from the Impressum (required by German law). Emails only if they literally appear on the "
     "site: no pattern guessing. LinkedIn is not scraped, only a search URL is provided.", "contacts.py"],
    ["7. Export", "This workbook.", "export.py"],
    ["8. Publish", "The .xlsx is imported into Google Sheets and shared read-only with anyone who has the link. "
     "The file is a snapshot: re-running the pipeline produces a new file, it does not edit this sheet.", "manual, see README.md"],
]
PUBLISH_STEPS = """Publishing the workbook as a Google Sheet (manual, ~2 minutes):
  1. drive.google.com -> New -> File upload -> data/heidi_berlin_property_managers.xlsx
  2. Right-click the uploaded file -> Open with -> Google Sheets
     (this creates a real Sheet next to the .xlsx; the .xlsx itself stays as an attachment)
  3. File -> Share -> Share with others -> General access: "Anyone with the link", role "Viewer"
  4. Copy link, and check it in a private browser window before sending it.
Column widths, the frozen header, the autofilter and the tier colours all survive the import."""
LEGAL_NOTE = ("Legal note: cold B2B email in Germany is restricted by UWG SS 7 (prior consent or a clear prior "
              "business relationship is normally required); phone calls to businesses need presumed consent. "
              "All personal data here is published by the companies themselves and processed under GDPR Art. 6(1)(f); "
              "people can object at any time. Use this list for research and for a first call, not for bulk mailing.")
SOURCE_NOTE = ("All values come from public sources. Every KPI value in the Leads tab has a source URL next to it, "
               "and the underlying quote is stored in data/extracted.jsonl. Values without a verified quote are "
               "left empty on purpose.")
EXCLUSION_NOTE = ("Only two things get a company excluded: its website shows it is not a property manager at all, "
                  "or it is one of the large listed residential groups that meter in-house or tender centrally - "
                  "matched on: " + LISTED_GROUPS.pattern + ". "
                  "Own-stock owners (Wohnungsunternehmen, municipal companies, Genossenschaften) are NOT excluded: "
                  "heidisystems.com names them as customer segments. They stay in the Leads tab with their segment "
                  "marked, because they buy on a longer cycle and often through a tender.")
VALIDATION_NOTE = ("Measured accuracy: {values_checked} values across {companies_checked} randomly sampled companies "
                   "were re-checked by hand against the source page: {accuracy_pct} correct ({verdicts}). "
                   "The sample and the per-value verdicts are in data/spotcheck.csv.")
VALIDATION_MISSING = ("Measured accuracy: not yet available - run 'python validate.py sample', fill in the verdict "
                      "column, then 'python validate.py report' and rebuild this workbook.")
