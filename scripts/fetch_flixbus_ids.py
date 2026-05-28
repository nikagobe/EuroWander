"""
Script: fetch_flixbus_ids.py

For every major city in the `countries` collection, calls the Flixbus
autocomplete API to find the city's Flixbus UUID and stores it back into
MongoDB as `flixbus_id` on the city sub-document.

Usage:
    python scripts/fetch_flixbus_ids.py

Rate-limiting: 1 request per second (adjustable via DELAY_SECONDS).
Run AFTER seed_countries.py.
"""

import asyncio
import os
import ssl
from pathlib import Path

import certifi
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://admin:secret@localhost:27017/eurowander?authSource=admin",
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "eurowander")
COUNTRIES_COLLECTION = "countries"

FLIXBUS_AUTOCOMPLETE_URL = (
    "https://global.api.flixbus.com/search/autocomplete/cities"
)

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://www.flixbus.com",
    "referer": "https://www.flixbus.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
    ),
}

# Delay between requests to avoid hammering the API (seconds)
DELAY_SECONDS: float = 1.2

# Minimum score threshold – results below this are skipped
MIN_SCORE: float = 10.0


def _best_match(city_name: str, results: list[dict]) -> dict | None:
    """
    Pick the best Flixbus city match from autocomplete results.

    Strategy:
    1. Filter to results where `name` matches city_name (case-insensitive).
    2. Among those, take the one with the highest score.
    3. If no exact name match exists, fall back to the top-scored result
       with score >= MIN_SCORE.
    """
    if not results:
        return None

    name_lower = city_name.lower()

    exact: list[dict] = [
        r for r in results if r.get("name", "").lower() == name_lower
    ]
    pool = exact if exact else results

    best = max(pool, key=lambda r: r.get("score", 0.0))
    if best.get("score", 0.0) < MIN_SCORE:
        return None
    return best


async def fetch_flixbus_id(
    client: httpx.AsyncClient, city_name: str
) -> tuple[str | None, str | None]:
    """
    Returns (flixbus_uuid, flixbus_legacy_id) or (None, None) on failure.
    """
    params = {
        "q": city_name,
        "lang": "en_US",
        "country": "us",
        "flixbus_cities_only": "false",
        "is_train_only": "false",
        "stations": "true",
    }
    try:
        resp = await client.get(
            FLIXBUS_AUTOCOMPLETE_URL, params=params, headers=HEADERS, timeout=10.0
        )
        resp.raise_for_status()
        data: list[dict] = resp.json()
        match = _best_match(city_name, data)
        if match:
            return match.get("id"), str(match.get("legacy_id")) if match.get("legacy_id") else None
        return None, None
    except Exception as exc:
        print(f"    ⚠  HTTP error for '{city_name}': {exc}")
        return None, None


async def main() -> None:
    # Build SSL context that accepts corporate/self-signed certs
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client_mongo = AsyncIOMotorClient(MONGODB_URI)
    db = client_mongo[DATABASE_NAME]
    col = db[COUNTRIES_COLLECTION]

    countries = await col.find({}, {"name": 1, "major_cities": 1}).to_list(length=None)

    # Build a de-duplicated list of (city_name, [(country_name, city_index)])
    # so we only call the API once per unique city name.
    city_index: dict[str, list[tuple[str, int]]] = {}
    for country_doc in countries:
        for idx, city in enumerate(country_doc.get("major_cities", [])):
            name: str = city.get("name", "")
            if name:
                city_index.setdefault(name, []).append((country_doc["name"], idx))

    unique_cities = list(city_index.keys())
    print(f"Found {len(unique_cities)} unique major cities to look up.\n")

    results_cache: dict[str, tuple[str | None, str | None]] = {}

    async with httpx.AsyncClient(verify=False) as http:
        for i, city_name in enumerate(unique_cities, 1):
            print(f"[{i}/{len(unique_cities)}] Looking up: {city_name} ...", end=" ")
            flixbus_id, legacy_id = await fetch_flixbus_id(http, city_name)
            results_cache[city_name] = (flixbus_id, legacy_id)
            if flixbus_id:
                print(f"✓  id={flixbus_id}  legacy={legacy_id}")
            else:
                print("✗  no match")
            await asyncio.sleep(DELAY_SECONDS)

    # Write results back to MongoDB
    print("\nUpdating MongoDB...")
    updated_cities = 0
    for country_doc in countries:
        cities: list[dict] = country_doc.get("major_cities", [])
        changed = False
        for city in cities:
            name = city.get("name", "")
            flixbus_id, legacy_id = results_cache.get(name, (None, None))
            if flixbus_id:
                city["flixbus_id"] = flixbus_id
                if legacy_id:
                    city["flixbus_legacy_id"] = legacy_id
                changed = True
                updated_cities += 1

        if changed:
            await col.update_one(
                {"name": country_doc["name"]},
                {"$set": {"major_cities": cities}},
            )
            print(f"  ✓ Updated {country_doc['name']}")

    print(f"\n✅ Done. Updated {updated_cities} city entries with Flixbus IDs.")
    client_mongo.close()


if __name__ == "__main__":
    asyncio.run(main())

