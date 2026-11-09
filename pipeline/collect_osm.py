"""Collect Berlin property management companies from OpenStreetMap (Overpass API)."""
import requests

from common import DATA_DIR, USER_AGENT, write_jsonl

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NAME_PATTERN = "Hausverwalt|Immobilienverwalt|WEG-Verwalt|Grundstücksverwalt|Objektverwalt"
QUERY = f"""
[out:json][timeout:180];
area["name"="Berlin"]["boundary"="administrative"]["admin_level"="4"]->.berlin;
(
  nwr["office"="property_management"](area.berlin);
  nwr["name"~"{NAME_PATTERN}",i](area.berlin);
);
out center tags;
"""


def to_row(el: dict) -> dict:
    t = el.get("tags", {})
    street = " ".join(filter(None, [t.get("addr:street"), t.get("addr:housenumber")]))
    return {
        "name": t.get("name"),
        "street": street or None,
        "postcode": t.get("addr:postcode"),
        "website": t.get("website") or t.get("contact:website"),
        "phone": t.get("phone") or t.get("contact:phone"),
        "email": t.get("email") or t.get("contact:email"),
        "source": "osm",
        "source_id": f"{el['type']}/{el['id']}",
    }


def main() -> None:
    resp = requests.post(OVERPASS_URL, data={"data": QUERY},
                         headers={"User-Agent": USER_AGENT}, timeout=200)
    resp.raise_for_status()
    rows = [to_row(el) for el in resp.json()["elements"]]
    rows = [r for r in rows if r["name"]]
    write_jsonl(DATA_DIR / "raw_osm.jsonl", rows)
    print(f"OSM: {len(rows)} companies -> data/raw_osm.jsonl")


if __name__ == "__main__":
    main()
