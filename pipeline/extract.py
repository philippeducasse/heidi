"""Extract KPIs and contacts from each crawled website with Mistral.

The LLM must back every value with a quote copied from the site. The code then checks that
the quote really is on one of the crawled pages, and records which page (source_url).
Values whose quote can't be found are kept but marked verified=False; later steps ignore them.
Emails are only kept if they literally appear on the site: never guessed.
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from common import DATA_DIR, read_jsonl, write_jsonl
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-small-latest"
PROMPT = (Path(__file__).parent / "prompts" / "extract.txt").read_text(encoding="utf-8")
OUT_PATH = DATA_DIR / "extracted.jsonl"
MAX_RETRIES = 5
WORKERS = 4  # parallel requests; lower this if you keep hitting rate limits
LIMIT = None  # max sites per run, for testing; set to None to process all sites
MIN_QUOTE_CHARS = 15


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def call_mistral(site):
    pages = "\n\n".join(
        f"=== PAGE {name} ({p['url']}) ===\n{p['text']}"
        for name, p in site["pages"].items()
    )
    for attempt in range(MAX_RETRIES):
        resp = requests.post(
            API_URL,
            timeout=120,
            headers={"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}"},
            json={
                "model": MODEL,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": pages},
                ],
            },
        )
        if resp.status_code not in (
            429,
            500,
            502,
            503,
        ):  # 429 = rate limit, 5xx = server busy: wait and retry
            break
        time.sleep(2**attempt * 5)  # 5s, 10s, 20s, 40s, 80s
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])


def find_source(quote, site):
    # URL of the crawled page that contains the quote, or None if it's not on the site (likely hallucinated).
    # Quotes stitched from several passages ("WEG-Verwaltung ... Mietverwaltung") are checked part by part:
    # every part must be on the site, and the URL is the page holding the longest part.
    # Quotes shorter than MIN_QUOTE_CHARS in total don't count: "x" or "2010" would match almost any page.
    parts = [p.strip(" .,;:") for p in re.split(r"\[?(?:\.\.\.|…)\]?", norm(quote))]
    parts = [p for p in parts if p]
    if sum(map(len, parts)) < MIN_QUOTE_CHARS:
        return None
    pages = [(p["url"], norm(p["text"])) for p in site["pages"].values()]
    urls = [next((url for url, text in pages if part in text), None) for part in parts]
    return None if None in urls else urls[parts.index(max(parts, key=len))]


def check(item, site):
    if not isinstance(item, dict) or item.get("value") in (None, "", []):
        return None  # not stated on the site
    url = find_source(item.get("quote"), site)
    return {**item, "source_url": url, "verified": url is not None}


def check_contact(c, site):
    on_site = norm(
        " ".join(p["text"] for p in site["pages"].values())
        + " "
        + " ".join(site["emails"])
    )
    email = (c.get("email") or "").strip().lower()
    c = {
        **c,
        "email": email if email and email in on_site else None,
    }  # drop any email not on the site
    return (
        check({**c, "value": c.get("name")}, site)
        if norm(c.get("name")) in on_site
        else None
    )


def extract(site):
    raw = call_mistral(site)
    fields = {k: check(v, site) for k, v in raw.items() if k != "contacts"}
    contacts = [
        c for c in (check_contact(c, site) for c in raw.get("contacts") or []) if c
    ]
    return {"domain": site["domain"], "fields": fields, "contacts": contacts}


def main() -> None:
    done = {r["domain"] for r in read_jsonl(OUT_PATH)} if OUT_PATH.exists() else set()
    sites = [
        s
        for s in read_jsonl(DATA_DIR / "crawl.jsonl")
        if s["ok"] and s["domain"] not in done
    ][:LIMIT]
    print(f"{len(done)} sites already extracted, {len(sites)} to go")
    failed = 0
    with (
        ThreadPoolExecutor(max_workers=WORKERS) as pool,
        OUT_PATH.open("a", encoding="utf-8") as out,
    ):
        futures = {pool.submit(extract, s): s["domain"] for s in sites}
        for i, future in enumerate(as_completed(futures), start=1):
            try:
                r = future.result()
            except (
                Exception
            ) as e:  # failures are not saved, so the next run retries them
                failed += 1
                print(
                    f"[{i}/{len(sites)}] FAILED {futures[future]}: {type(e).__name__} {e}"[
                        :200
                    ]
                )
                continue
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            ok = sum(1 for v in r["fields"].values() if v and v["verified"])
            print(
                f"[{i}/{len(sites)}] {r['domain']}: {ok} verified fields, {len(r['contacts'])} contacts"
            )
    print(f"done, {failed} failed" + (" (run again to retry them)" if failed else ""))


def recheck() -> None:
    # Re-run the quote and email checks on the saved answers, e.g. after changing find_source.
    # No Mistral calls: it only compares the saved quotes with the current crawl.jsonl.
    sites = {s["domain"]: s for s in read_jsonl(DATA_DIR / "crawl.jsonl")}
    rows = read_jsonl(OUT_PATH)
    count = lambda: sum(1 for r in rows for v in r["fields"].values() if v and v["verified"])
    before = count()
    for r in rows:
        site = sites[r["domain"]]
        r["fields"] = {k: check(v, site) for k, v in r["fields"].items()}
        r["contacts"] = [c for c in (check_contact(c, site) for c in r["contacts"]) if c]
    write_jsonl(OUT_PATH, rows)
    print(f"rechecked {len(rows)} sites: {before} -> {count()} verified values")


if __name__ == "__main__":
    recheck() if "--recheck" in sys.argv else main()
