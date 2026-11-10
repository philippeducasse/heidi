"""Build the contact list: named people per company, with a published email where one exists.

Sources, in this order of trust:
  1. the website extraction (names backed by a quote from the company's own Impressum/team page)
  2. the directory listings (contact_name from dedupe.py), used when the site gave no name

Emails were already checked in extract.py: only addresses that literally appear on the site are
kept, so an empty email field means "not published", never "we could not guess it". Generic
mailboxes (info@, kontakt@) are listed on the company row instead, not as a person's address.
LinkedIn is not scraped; we store a search URL so a human can open the profile themselves.
"""
import re
from collections import Counter
from urllib.parse import quote_plus

from common import DATA_DIR, read_jsonl, write_jsonl
from dedupe import domain_key

GENERIC = re.compile(r"^(info|kontakt|office|mail|post|empfang|service|buchhaltung|verwaltung|team)@")
# Most senior first: these are the people who can decide on a metering contract.
SENIORITY = ["geschäftsführ", "inhaber", "vorstand", "prokurist", "leitung", "objektbetreu", "buchhaltung"]


def rank(role):
    role = (role or "").lower()
    return next((i for i, word in enumerate(SENIORITY) if word in role), len(SENIORITY))


def linkedin_search(name, company):
    return "https://www.google.com/search?q=" + quote_plus(f'site:linkedin.com/in "{name}" "{company}"')


def from_site(lead, extracted):
    for c in extracted.get(domain_key(lead["website"]), {}).get("contacts", []):
        email = c.get("email")
        yield {"name": c["value"], "role": c.get("role"), "email": None if email and GENERIC.match(email) else email,
               "evidence_url": c.get("source_url"), "quote": c.get("quote"), "source": "website"}


def from_directory(lead):
    if lead.get("contact_name"):
        yield {"name": lead["contact_name"], "role": None, "email": None,
               "evidence_url": None, "quote": None, "source": "directory (" + ", ".join(lead["sources"]) + ")"}


def contacts_for(lead, extracted):
    people = sorted(from_site(lead, extracted), key=lambda c: rank(c["role"]))
    people = people or list(from_directory(lead))
    return [{"company_id": lead["company_id"], "company_name": lead["name"], "tier": lead["tier"],
             "score": lead["score"], "website": lead["website"], **c,
             "linkedin_search": linkedin_search(c["name"], lead["name"])} for c in people]


def main() -> None:
    extracted = {r["domain"]: r for r in read_jsonl(DATA_DIR / "extracted.jsonl")}
    leads = [r for r in read_jsonl(DATA_DIR / "scored.jsonl") if not r["excluded_reason"]]
    rows = [c for lead in leads for c in contacts_for(lead, extracted)]
    write_jsonl(DATA_DIR / "contacts.jsonl", rows)
    companies = {c["company_id"] for c in rows}
    print(f"{len(rows)} contacts for {len(companies)}/{len(leads)} companies -> data/contacts.jsonl")
    print("by source:", dict(Counter(c["source"] for c in rows)))
    print("with a published personal email:", sum(1 for c in rows if c["email"]))
    print("companies with no named contact at all:", len(leads) - len(companies))


if __name__ == "__main__":
    main()
