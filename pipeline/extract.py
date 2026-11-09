"""Extract KPIs and contacts from each crawled website with Mistral.

The LLM must back every value with a quote copied from the site. The code then checks that
the quote really is on one of the crawled pages, and records which page (source_url).
Values whose quote can't be found are kept but marked verified=False; later steps ignore them.
Emails are only kept if they literally appear on the site: never guessed.
"""
import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-small-latest"
PROMPT = (Path(__file__).parent / "prompts" / "extract.txt").read_text(encoding="utf-8")


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def call_mistral(site):
    pages = "\n\n".join(f"=== PAGE {name} ({p['url']}) ===\n{p['text']}" for name, p in site["pages"].items())
    resp = requests.post(API_URL, timeout=120, headers={"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}"},
                         json={"model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
                               "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": pages}]})
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])


def find_source(quote, site):
    # URL of the crawled page that contains the quote, or None if it's on no page (likely hallucinated)
    q = norm(quote)
    return next((p["url"] for p in site["pages"].values() if q and q in norm(p["text"])), None)


def check(item, site):
    if not isinstance(item, dict) or item.get("value") in (None, "", []):
        return None  # not stated on the site
    url = find_source(item.get("quote"), site)
    return {**item, "source_url": url, "verified": url is not None}


def check_contact(c, site):
    on_site = norm(" ".join(p["text"] for p in site["pages"].values()) + " " + " ".join(site["emails"]))
    email = (c.get("email") or "").strip().lower()
    c = {**c, "email": email if email and email in on_site else None}  # drop any email not on the site
    return check({**c, "value": c.get("name")}, site) if norm(c.get("name")) in on_site else None


def extract(site):
    raw = call_mistral(site)
    fields = {k: check(v, site) for k, v in raw.items() if k != "contacts"}
    contacts = [c for c in (check_contact(c, site) for c in raw.get("contacts") or []) if c]
    return {"domain": site["domain"], "fields": fields, "contacts": contacts}
