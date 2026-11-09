"""Merge the raw_*.jsonl files from all collectors into one list of unique companies.

Two records are the same company if they share a website domain, a phone number, or a
normalised name within the same postcode. Matches chain (union-find): if A matches B by
phone and B matches C by domain, A, B and C all end up in one group.
"""
import re
from collections import Counter

from common import DATA_DIR, read_jsonl, write_jsonl

# When sources disagree, the first one in this list wins. This order is a judgement from a few
# listings seen while building the collectors, not a measurement:
#   vdiv:         names read like the companies' own legal names
#   dasoertliche: names sometimes padded with category words or abbreviated ("Hausverwaltg.")
#   gelbeseiten:  often lists the owner's name instead of the company ("Dehmel Klaus-Ulrich")
#   osm:          crowd-sourced, sparse, sometimes brand names only
# Placeholder: the Impressum data from the crawler (step 6) should override all of these.
SOURCE_PRIORITY = ["vdiv", "dasoertliche", "gelbeseiten", "osm"]
# Domains shared by many unrelated businesses: they can't identify a company
SHARED_DOMAINS = {"facebook.com", "google.com", "immobilienscout24.de", "t-online.de", "gmx.de", "web.de"}
LEGAL_FORMS = r"\b(gmbh|mbh|co|kg|ohg|ug|ag|gbr|haftungsbeschränkt|und)\b"
FIELDS = ["name", "street", "postcode", "district", "website", "phone", "contact_name"]


def domain_key(url):
    # "https://www.plurahi.de/" and "http://plurahi.de" both become "plurahi.de"
    host = re.sub(r"^https?://", "", (url or "").strip().lower()).split("/")[0].removeprefix("www.")
    return host if host and host not in SHARED_DOMAINS else None


def phone_key(phone):
    # "+49 30 6807353", "030 6807353" and "(030) 6807353" all become "0306807353"
    digits = re.sub(r"\D", "", phone or "")
    digits = re.sub(r"^(00)?49", "0", digits) if (phone or "").strip().startswith(("+", "00")) else digits
    return digits if len(digits) >= 7 else None


def name_key(name):
    # "Kleiß Hausverwaltung GmbH" and "Hausverwaltung Kleiß" give the same key
    words = re.sub(LEGAL_FORMS, " ", re.sub(r"[^\wäöüß ]", " ", (name or "").lower())).split()
    return " ".join(sorted(w for w in words if len(w) > 1)) or None


def group(rows):
    parent = list(range(len(rows)))  # union-find: each record points towards its group's root
    find = lambda i: i if parent[i] == i else find(parent[i])
    first_seen = {}  # key -> index of the first record that had it
    for i, r in enumerate(rows):
        for key in [("web", domain_key(r.get("website"))), ("tel", phone_key(r.get("phone"))),
                    ("name", r.get("postcode"), name_key(r.get("name")))]:
            if None not in key:
                parent[find(i)] = find(first_seen.setdefault(key, i))
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(find(i), []).append(r)
    return list(groups.values())


def merge(records, idx):
    records = sorted(records, key=lambda r: SOURCE_PRIORITY.index(r["source"]))
    return {
        "company_id": f"C{idx:04d}",
        **{f: next((r[f] for r in records if r.get(f)), None) for f in FIELDS},
        "emails": sorted({r["email"].strip().lower() for r in records if r.get("email")}),
        "sources": sorted({r["source"] for r in records}, key=SOURCE_PRIORITY.index),
        "source_ids": [f"{r['source']}:{r['source_id']}" for r in records],
    }


def main() -> None:
    rows = [r for path in sorted(DATA_DIR.glob("raw_*.jsonl")) for r in read_jsonl(path)]
    companies = [merge(g, i) for i, g in enumerate(group(rows), start=1)]
    write_jsonl(DATA_DIR / "companies.jsonl", companies)
    print(f"{len(rows)} raw records -> {len(companies)} unique companies -> data/companies.jsonl")
    print("by number of sources:", dict(sorted(Counter(len(c["sources"]) for c in companies).items())))
    print("largest groups (check these for wrong merges):")
    for c in sorted(companies, key=lambda c: -len(c["source_ids"]))[:10]:
        print(f"  {len(c['source_ids']):3d} records  {c['name']}  ({c['website']})")


if __name__ == "__main__":
    main()
