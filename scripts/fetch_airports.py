"""
fetch_airports.py — Fetches all international airports from Wikidata
and saves them to data/airports/airports.json.

Usage:
    python scripts/fetch_airports.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from wikidata_helpers import USER_AGENT

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "airports" / "airports.json"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT DISTINCT ?airport ?name ?iata ?lat ?lng ?countryCode WHERE {
  ?airport wdt:P31 wd:Q1248784 .
  ?airport wdt:P238 ?iata .
  ?airport wdt:P625 ?coord .
  ?airport wdt:P17  ?country .
  ?country wdt:P297 ?countryCode .
  ?airport rdfs:label ?name .
  FILTER(LANG(?name) = "en")
  BIND(geof:latitude(?coord)  AS ?lat)
  BIND(geof:longitude(?coord) AS ?lng)
}
ORDER BY ?countryCode ?iata
"""


async def fetch_airports() -> list[dict[str, Any]]:
    params = {"query": SPARQL_QUERY, "format": "json"}
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }

    try:
        import ssl as _ssl
        import truststore
        ssl_ctx = truststore.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
        verify: bool | object = ssl_ctx
    except ImportError:
        verify = True

    print("📡 Querying Wikidata for international airports (this may take 30-60s)...")

    async with httpx.AsyncClient(verify=verify, timeout=120) as client:
        for attempt in range(3):
            try:
                response = await client.get(SPARQL_ENDPOINT, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                break
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                print(f"  ⚠ Attempt {attempt + 1}/3 failed: {exc}")
                if attempt < 2:
                    await asyncio.sleep(10)
                else:
                    raise

    bindings = data.get("results", {}).get("bindings", [])
    print(f"  ✓ Received {len(bindings)} results from Wikidata.")

    airports: list[dict[str, Any]] = []
    seen_iata: set[str] = set()

    for b in bindings:
        try:
            wikidata_id = b["airport"]["value"].split("/")[-1]
            iata = b["iata"]["value"].strip().upper()
            name = b["name"]["value"].strip()
            lat = float(b["lat"]["value"])
            lng = float(b["lng"]["value"])
            country_code = b["countryCode"]["value"].strip().upper()
        except (KeyError, ValueError):
            continue

        if iata in seen_iata:
            continue
        seen_iata.add(iata)

        airports.append({
            "wikidata_id": wikidata_id,
            "name": name,
            "iata_code": iata,
            "lat": lat,
            "lng": lng,
            "country_code": country_code,
        })

    airports.sort(key=lambda a: (a["country_code"], a["iata_code"]))
    return airports


async def main() -> None:
    airports = await fetch_airports()

    print(f"\n📊 Unique airports found: {len(airports)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(airports, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved → {OUTPUT_PATH}")
    print("\nSample records:")
    for ap in airports[:5]:
        print(f"  {ap['iata_code']}  {ap['name']}  ({ap['country_code']})  [{ap['lat']:.4f}, {ap['lng']:.4f}]")


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    print(f"⏱  Total time: {time.time() - start:.1f}s")

