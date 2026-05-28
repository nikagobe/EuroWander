"""
fetch_airports.py — Downloads airport data from OurAirports (free, open dataset)
and saves it to data/airports/airports.json.

Source: https://ourairports.com/data/
CSV URL: https://davidmegginson.github.io/ourairports-data/airports.csv

Usage:
    python scripts/fetch_airports.py

Filters: only airports with a valid IATA code and type large_airport or medium_airport.
"""

import asyncio
import csv
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from wikidata_helpers import USER_AGENT

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "airports" / "airports.json"

OURAIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# Include large and medium airports that have an IATA code
ALLOWED_TYPES = {"large_airport", "medium_airport"}


async def fetch_airports() -> list[dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT}

    try:
        import ssl as _ssl
        import truststore
        ssl_ctx = truststore.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
        verify: bool | object = ssl_ctx
    except ImportError:
        verify = True

    print("📡 Downloading airports CSV from OurAirports...")

    async with httpx.AsyncClient(verify=verify, timeout=60) as client:
        for attempt in range(3):
            try:
                response = await client.get(OURAIRPORTS_CSV_URL, headers=headers)
                response.raise_for_status()
                csv_text = response.text
                break
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                print(f"  ⚠ Attempt {attempt + 1}/3 failed: {exc}")
                if attempt < 2:
                    await asyncio.sleep(5)
                else:
                    raise

    reader = csv.DictReader(io.StringIO(csv_text))
    airports: list[dict[str, Any]] = []
    seen_iata: set[str] = set()

    for row in reader:
        try:
            airport_type = row.get("type", "").strip()
            iata = row.get("iata_code", "").strip().upper()
            name = row.get("name", "").strip()
            lat = float(row.get("latitude_deg", "") or "nan")
            lng = float(row.get("longitude_deg", "") or "nan")
            country_code = row.get("iso_country", "").strip().upper()
        except (ValueError, KeyError):
            continue

        # Skip if no IATA code, wrong type, or invalid coordinates
        if not iata or airport_type not in ALLOWED_TYPES:
            continue
        if lat != lat or lng != lng:  # NaN check
            continue
        if iata in seen_iata:
            continue
        seen_iata.add(iata)

        # OurAirports uses its own numeric id, not wikidata — use iata as fallback id
        airports.append({
            "wikidata_id": "",  # not available from OurAirports
            "name": name,
            "iata_code": iata,
            "lat": lat,
            "lng": lng,
            "country_code": country_code,
        })

    airports.sort(key=lambda a: (a["country_code"], a["iata_code"]))
    print(f"  ✓ Parsed {len(airports)} airports with IATA codes.")
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

