"""Collect Berlin property management companies from Das Örtliche.

Where the data sits: a JavaScript variable (handlerData) inside the page.
How it's read:       a regex cuts it out and it's read as JSON. No selectors.

Each results page embeds all listing data in a JavaScript array (`var handlerData = [[...]]`),
which is valid JSON, so we read that instead of parsing the HTML.
"""
import json
import re
import time

import requests

from common import DATA_DIR, write_jsonl

PAGE_URL = "https://www.dasoertliche.de/Themen/{term}/Berlin{suffix}.html"
TERMS = ["Hausverwaltung", "Immobilienverwaltung", "Grundstücksverwaltung"]
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
HANDLER_RE = re.compile(r"var handlerData\s*=\s*(\[\[.*?\]\]);", re.S)
MAX_PAGES = 60  # safety limit (Hausverwaltung has 37 pages)


def to_row(e: list) -> dict:
    # Positions in the handlerData array, worked out by comparing it with the visible page
    return {
        "name": e[14],
        "street": " ".join(filter(None, [e[9], e[10]])) or None,
        "postcode": e[8] or None,
        "website": e[3] or None,
        "phone": e[11] or None,
        "email": e[17] or None,
        "source": "dasoertliche",
        "source_id": e[0],
    }


# Page 1 is "Berlin.html", later pages are "Berlin-Seite-2.html", ...
# Past the last page the site answers 410, which ends the loop.
def fetch_term(term: str) -> list[dict]:
    rows = []
    for page in range(1, MAX_PAGES + 1):
        suffix = "" if page == 1 else f"-Seite-{page}"
        resp = requests.get(PAGE_URL.format(term=term, suffix=suffix), headers=HEADERS, timeout=30)
        match = HANDLER_RE.search(resp.text)
        if resp.status_code != 200 or not match:
            break
        rows += [to_row(e) for e in json.loads(match.group(1)) if e[4] == "Berlin" and e[8]]
        time.sleep(1)  # be polite
    return rows


def main() -> None:
    unique = {}
    for term in TERMS:
        rows = fetch_term(term)
        print(f"Das Örtliche '{term}': {len(rows)} results")
        unique.update({r["source_id"]: r for r in rows})
    write_jsonl(DATA_DIR / "raw_dasoertliche.jsonl", list(unique.values()))
    print(f"Das Örtliche: {len(unique)} unique Berlin companies -> data/raw_dasoertliche.jsonl")


if __name__ == "__main__":
    main()
