# Berlin property management 
## Lead Pipeline

This project is a pipeline designed to retrieve Berlin & Brandenburg hausverwaltung company data, process the data and output a google sheet deliverable. It also includes personal contact info for each lead, when available.

## What a good lead looks like

Heidi sells submetering, so the people worth calling are the ones with a lot of units, in residential management (WEG and Mietverwaltung), not owned by a big listed group, and with a named person we can actually reach.

Also worth noting: Section 5(3) of the Heizkostenverordnung says meters that are not remotely readable have to be retrofitted or replaced by 31 December 2026, and if that is missed tenants may cut their heating cost share by 3 percent. A survey in February 2026 put equipment levels at 58 to 61 percent, so a good part of this list still has to act, and has about seven weeks to do it.

## Sources

4 sources: the VDIV Berlin-Brandenburg member list, Das Örtliche, Gelbe Seiten and OpenStreetMap through the Overpass API. I also tried 11880 but dropped it, Cloudflare blocks the requests after a few calls and the websites are only on the detail pages anyway.

I trust VDIV most because members register themselves, so the names are the real legal names. The directories tend to pad names with category words or list the owner instead of the company, and OSM is crowd sourced and sparse. That order decides which value wins when sources disagree. Heidi is also a VDIV cooperation partner, so membership is a good channel and not just a quality signal.

## Dedupe

The same company shows up in several directories from the sources, so records get merged when they share a website domain, a phone number, or a normalised name inside the same postcode. The matches chain, so if A and B share a phone and B and C share a domain, all three end up as one company. 2188 raw records came out as 1250 companies, and 458 of those are confirmed by more than one source.

## Crawl and extraction

For every company with a website I fetch the homepage, the Impressum, the about page and the team page. Mistral then reads that text and returns the KPIs as JSON.

The important part is that the model has to return a quote for every value. The code then searches for that quote in the pages we actually crawled, and if it is not there the value is marked unverified and nothing downstream uses it. Quotes stitched from several passages are checked part by part, and anything under 15 characters does not count because a short quote matches almost any page.

I preferred this over asking the model for a confidence score, since a confidence score is the model grading itself and there is nothing to check it against. Running the extraction twice would only catch random error, and at temperature 0 there is not much of that, while doubling the cost of the only expensive step.

## Scoring

Points go to units under management (30, the best proxy for meters), employees as a fallback (25), residential management types (25), digital maturity (10), hiring (10), VDIV membership (10), a named decision maker (10) and independence (5). A is 50 and up, B is 30 and up, C below that. The weights are in the sheet so anyone can disagree with them.

Two decisions worth explaining. Own stock owners like Wohnungsunternehmen and Genossenschaften are not excluded, because Heidi lists them as customer segments, they just get a segment label since they buy more slowly and often by tender. Only the large listed groups are excluded, 25 companies in total. And having ista or Techem already is not a disqualifier, Heidi takes over running contracts, so it changes the pitch rather than killing the lead.

The other thing is that a company with no website would score near zero and land in C, which would make it look like a bad lead when really we just know nothing about it. Those are marked unrated instead. That leaves 234 A, 133 B, 123 C and 735 unrated out of 1225.

## Contacts

Names come from the Impressum, which German law requires, so most companies give up a managing director. Emails are only included if they literally appear on the site, no pattern guessing, so an empty field means not published. Generic info@ addresses stay on the company row instead of being passed off as a person. For LinkedIn I store a search URL rather than scraping it.

That gives 1050 contacts across 533 companies, 164 of them with a personal email. Cold B2B email is restricted by UWG section 7 and the personal data falls under GDPR, which is another reason phone is the better channel for this list.

## Validation

The quote check only proves the quote is on the page, not that the value follows from it, so I checked a sample by hand. 30 random companies with a fixed seed, plus the 10 highest scoring ones, since a perfect score on every KPI is where errors would hide. The two groups are reported separately, folding hand picked rows into the headline number would not be a measurement any more.

Accuracy on the random sample: TODO fill in from data/validation.json.

## Limitations

490 of 1225 companies had a website we could read, so everything else is directory data only. Units under management, which carries the most points, is only published by 119 companies, so in practice most size points come from employee counts. The source priority in dedupe is a judgement from looking at listings, not something I measured. And this is Berlin only and a snapshot, with no Handelsregister cross check yet.

## Next

The obvious next step is Handelsregister or Northdata enrichment, which would qualify the 735 unrated companies that have no website. After that, Google reviews as a pain signal, since complaints about late or wrong Nebenkostenabrechnungen are a strong buying trigger. Running it for the rest of Germany is mostly a matter of changing the Overpass boundary and the directory queries, the cost scales with the extraction step. Longer term it should run on a schedule and rescore on what changed, and generate a short call brief per lead from the evidence it already has.

