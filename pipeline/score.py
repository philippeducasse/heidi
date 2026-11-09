"""Score each company as a lead for Heidi: points per KPI, a total (0-100) and a tier (A/B/C).

Inputs: companies.jsonl (directories), crawl.jsonl (website reachable?) and extracted.jsonl
(website facts). Only verified values are used, so every point can be traced to a quote and URL.
Companies that are not potential customers get an exclusion reason instead of a tier.

Points (max 100): size 30, core market 25, digital 10, growth 10, VDIV member 10,
named decision maker 10, independent 5. Tiers: A >= 50, B >= 30, C below.
"""
import re
from collections import Counter

from common import DATA_DIR, read_jsonl, write_jsonl
from dedupe import domain_key

# Municipal housing companies, listed landlords and cooperatives manage their own stock and buy
# metering through large central tenders: not leads for Heidi.
OWN_STOCK = re.compile(r"(?-i:\be\.?G\b)|genossenschaft|wohnungsbaugesellschaft|degewo|gewobag|howoge|gesobau"
                       r"|stadt ?und ?land|\bwbm\b|berlinovo|vonovia|deutsche wohnen|covivio|heimstaden|grand city", re.I)
KPI_FIELDS = ["is_property_manager", "management_types", "units_managed", "employees", "founded_year",
              "parent_company", "software_or_portal", "metering_provider", "hiring", "managing_directors"]


def verified(fields, key):
    return fields[key]["value"] if fields.get(key) and fields[key]["verified"] else None


def size_points(units, employees):
    # Units managed is the best proxy for meters (= revenue); employees is the fallback.
    # Not published: no points, but no penalty either.
    if units:
        return 30 if units >= 2000 else 20 if units >= 500 else 10 if units >= 100 else 5
    return (25 if employees >= 15 else 15 if employees >= 5 else 5) if employees else 0


def score(c, f):
    types = set(verified(f, "management_types") or [])
    return {"size": size_points(verified(f, "units_managed"), verified(f, "employees")),
            "core_market": 25 if types & {"WEG", "Miet"} else 10 if types else 0,  # residential = HKVO metering
            "digital": 10 if verified(f, "software_or_portal") else 0,
            "growth": 10 if verified(f, "hiring") is True else 0,
            "vdiv_member": 10 if "vdiv" in c["sources"] else 0,
            "decision_maker": 10 if verified(f, "managing_directors") or c["contact_name"] else 0,
            "independent": 0 if verified(f, "parent_company") else 5}


def exclusion(c, f, domain):
    if OWN_STOCK.search(f"{c['name']} {verified(f, 'legal_name') or ''} {domain or ''}"):
        return "Own-stock landlord or cooperative (central metering tenders)"
    if verified(f, "is_property_manager") is False:
        return f"Website shows it is not a property manager: \"{f['is_property_manager']['quote'][:120]}\""


def build(c, crawl, extracted):
    domain = domain_key(c["website"])
    f = extracted.get(domain, {}).get("fields", {})
    points, reason = score(c, f), exclusion(c, f, domain)
    total = sum(points.values())
    return {**c, "name": verified(f, "legal_name") or c["name"], "directory_name": c["name"],
            "website_ok": bool(crawl.get(domain, {}).get("ok")) and any(f.values()),
            **{k: verified(f, k) for k in KPI_FIELDS},
            "evidence": {k: [v["source_url"], v["quote"]] for k, v in f.items() if v and v["verified"]},
            "points": points, "score": total, "excluded_reason": reason,
            "tier": None if reason else "A" if total >= 50 else "B" if total >= 30 else "C"}


def main() -> None:
    crawl = {s["domain"]: s for s in read_jsonl(DATA_DIR / "crawl.jsonl")}
    extracted = {r["domain"]: r for r in read_jsonl(DATA_DIR / "extracted.jsonl")}
    leads = sorted((build(c, crawl, extracted) for c in read_jsonl(DATA_DIR / "companies.jsonl")),
                   key=lambda r: -r["score"])
    write_jsonl(DATA_DIR / "scored.jsonl", leads)
    print("tiers:", dict(Counter(r["tier"] or "excluded" for r in leads)), "-> data/scored.jsonl")
    for r in [r for r in leads if r["tier"]][:10]:
        print(f"  {r['score']:3d} {r['tier']}  {r['name']}  {r['points']}")


if __name__ == "__main__":
    main()
