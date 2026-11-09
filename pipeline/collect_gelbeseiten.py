"""Collect Berlin property management companies from Gelbe Seiten.

Where the data sits: behind the hidden endpoint the "load more" button calls.
How it's read:       call that endpoint, then BeautifulSoup selectors on the HTML it returns.

Uses the site's own "load more" endpoint (/ajaxsuche), which returns 10 results per call.
"""
import base64
import re
import time

import requests
from bs4 import BeautifulSoup

from common import DATA_DIR, write_jsonl

AJAX_URL = "https://www.gelbeseiten.de/ajaxsuche"
TERMS = ["Hausverwaltung", "Immobilienverwaltung", "WEG-Verwaltung"]
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
ADDRESS_RE = re.compile(r"^(?:(.*?),\s*)?(\d{5})\s+Berlin(?:\s*\((.*?)\))?")


def parse_entry(art) -> dict:
    text = lambda sel: (el.get_text(" ", strip=True) if (el := art.select_one(sel)) else None)
    addr = ADDRESS_RE.match(text(".mod-AdresseKompakt__adress-text") or "")
    web = art.select_one("[data-webseitelink]")
    return {
        "name": text("h2.mod-Treffer__name"),
        "street": addr and addr.group(1),
        "postcode": addr and addr.group(2),
        "district": addr and addr.group(3),
        "website": web and base64.b64decode(web["data-webseitelink"]).decode(),
        "phone": text(".mod-TelefonnummerKompakt__phoneNumber"),
        "email": None,
        "source": "gelbeseiten",
        "source_id": art.get("data-realid"),
    }


# Fetch all results for one search term by replaying the site's "load more" button.
# Each request returns at most 10 results, starting at `position` (1, 11, 21, ...).
# A reply with fewer than 10 results (anzahlTreffer < 10) means we've reached the end of the list.
def fetch_term(term: str) -> list[dict]:
    rows, position = [], 1
    while True:
        form = {"WAS": term, "WO": "Berlin", "umkreis": -1, "verwandt": "false",
                "position": position, "anzahl": 10, "sortierung": "relevanz"}
        data = requests.post(AJAX_URL, data=form, headers=HEADERS, timeout=30).json()
        soup = BeautifulSoup(data["html"], "html.parser")
        rows += [parse_entry(a) for a in soup.select("article.mod-Treffer")]
        if data["anzahlTreffer"] < 10:
            return rows
        position += 10
        time.sleep(1)  # be polite


def main() -> None:
    unique = {}
    for term in TERMS:
        rows = fetch_term(term)
        print(f"Gelbe Seiten '{term}': {len(rows)} results")
        unique.update({r["source_id"]: r for r in rows if r["postcode"]})
    write_jsonl(DATA_DIR / "raw_gelbeseiten.jsonl", list(unique.values()))
    print(f"Gelbe Seiten: {len(unique)} unique Berlin companies -> data/raw_gelbeseiten.jsonl")


if __name__ == "__main__":
    main()
