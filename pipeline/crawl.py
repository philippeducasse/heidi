"""Crawl each company's website: the homepage plus its Impressum, about and team pages.

Saves the visible text of each page (input for the Mistral extraction step) and any mailto:
addresses. Also records whether the site is reachable at all (part of the validation).
Results are keyed by website domain and appended as each site finishes, so an interrupted
run resumes where it stopped. To redo a site, delete its line from data/crawl.jsonl.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from common import DATA_DIR, read_jsonl
from dedupe import domain_key

OUT_PATH = DATA_DIR / "crawl.jsonl"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
# Page type -> words to look for in a link's text or URL. The first matching link per type is used.
PAGE_TYPES = {"impressum": ["impressum", "imprint"],
              "about": ["über uns", "ueber-uns", "uber-uns", "about", "unternehmen", "philosophie"],
              "team": ["team", "ansprechpartner", "mitarbeiter"]}
MAX_CHARS = 8000  # per page, to keep the Mistral prompt small


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")  # from bytes, so the page's own charset is used
    mails = {a["href"][7:].split("?")[0].strip().lower() for a in soup.select('a[href^="mailto:"]')}
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return resp.url, soup, re.sub(r"\s+", " ", soup.get_text(" ")).strip()[:MAX_CHARS], mails


def find_links(soup, base_url):
    links = {}
    for a in soup.select("a[href]"):
        url = urldefrag(urljoin(base_url, a["href"])).url  # "/#team" -> the homepage itself
        label = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
        if urlparse(url).netloc == urlparse(base_url).netloc and url != base_url:  # own site, new page
            for page_type, words in PAGE_TYPES.items():
                if page_type not in links and any(w in label for w in words):
                    links[page_type] = url
    return links


def crawl(domain, website):
    result = {"domain": domain, "website": website, "ok": False, "pages": {}, "emails": []}
    try:
        url, soup, text, mails = fetch(website if website.startswith("http") else "http://" + website)
        result.update(ok=True, pages={"home": {"url": url, "text": text}})
        for page_type, link in find_links(soup, url).items():
            try:  # a broken subpage shouldn't lose the rest of the site
                page_url, _, page_text, page_mails = fetch(link)
                result["pages"][page_type] = {"url": page_url, "text": page_text}
                mails |= page_mails
            except Exception:
                pass
        result["emails"] = sorted(mails)
    except Exception as e:
        result["error"] = type(e).__name__  # e.g. ConnectionError, SSLError, HTTPError
    return result


def main() -> None:
    done = {r["domain"] for r in read_jsonl(OUT_PATH)} if OUT_PATH.exists() else set()
    sites = {}  # domain -> website URL (several companies can share one domain)
    for c in read_jsonl(DATA_DIR / "companies.jsonl"):
        if (d := domain_key(c["website"])) and d not in done:
            sites.setdefault(d, c["website"])
    print(f"{len(done)} domains already crawled, {len(sites)} to go")
    with ThreadPoolExecutor(max_workers=16) as pool, OUT_PATH.open("a", encoding="utf-8") as out:
        futures = [pool.submit(crawl, d, url) for d, url in sites.items()]
        for i, future in enumerate(as_completed(futures), start=1):
            out.write(json.dumps(r := future.result(), ensure_ascii=False) + "\n")
            out.flush()  # so a crash or Ctrl+C keeps every finished site
            print(f"[{i}/{len(sites)}] {'ok' if r['ok'] else r['error']} {r['domain']}: {', '.join(r['pages'])}")


if __name__ == "__main__":
    main()

