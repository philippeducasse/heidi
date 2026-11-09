"""Collect members of VDIV Berlin-Brandenburg (the regional property managers' association).

Where the data sits: ordinary HTML cards, all on one page.
How it's read:       BeautifulSoup selectors.

All ~760 members are on one page as "contact cards". Besides company data, each card names
a contact person, and sometimes their personal email. Membership is also a quality signal.
"""
import re

import requests
from bs4 import BeautifulSoup

from common import DATA_DIR, write_jsonl

MEMBERS_URL = "https://vdiv-bb.de/mitglieder/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
POSTCODE_RE = re.compile(r"\b(\d{5})\b")


def is_berlin(postcode: str | None) -> bool:
    # Berlin postcodes run from 10115 to 14199; the city field has typos ("Berllin"), so use these
    return postcode is not None and 10115 <= int(postcode) <= 14199


def parse_card(card) -> dict:
    text = lambda sel: (el.get_text(" ", strip=True) if (el := card.select_one(sel)) else None)
    city_line = text(".contact-list-address-country-and-state") or ""
    postcode = (m := POSTCODE_RE.search(city_line)) and m.group(1)
    website = card.select_one(".contact-list-custom-field-value a")
    return {
        "name": text(".contact-list-contact-name"),
        "street": text(".contact-list-address-line-1"),
        "postcode": postcode,
        "website": website and website["href"],
        "phone": text(".contact-list-phone a"),
        "email": text(".contact-list-email"),  # entity-obfuscated in HTML; BeautifulSoup decodes it
        "contact_name": text(".contact-list-job-title"),  # the site uses this field for the person
        "source": "vdiv",
        "source_id": card.get("id"),
    }


def main() -> None:
    html = requests.get(MEMBERS_URL, headers=HEADERS, timeout=60).text
    cards = BeautifulSoup(html, "html.parser").select("#all-contacts > li")
    rows = [parse_card(c) for c in cards]
    berlin = [r for r in rows if is_berlin(r["postcode"])]
    write_jsonl(DATA_DIR / "raw_vdiv.jsonl", berlin)
    print(f"VDIV: {len(rows)} members, {len(berlin)} in Berlin -> data/raw_vdiv.jsonl")


if __name__ == "__main__":
    main()
