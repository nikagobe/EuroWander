"""
Seed script: builds the `countries` collection in MongoDB.

For each European country it stores:
  - name         : canonical country name (matches city "country" field)
  - neighbors    : list of neighboring country names (from neighbors.json)
  - major_cities : curated list of cities with international airports or 500k+
                   population, looked up by name from the existing `cities`
                   collection so we get correct freebase_id / wikidata_id.

Usage:
    python scripts/seed_countries.py

Run AFTER seed_cities.py so the cities collection already exists.
"""

import asyncio
import json
import os
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://admin:secret@localhost:27017/eurowander?authSource=admin",
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "eurowander")
COUNTRIES_COLLECTION = "countries"
CITIES_COLLECTION = "cities"
NEIGHBORS_FILE = Path(__file__).parent.parent / "data" / "countries" / "neighbors.json"
MAJOR_CITIES_FILE = Path(__file__).parent.parent / "data" / "countries" / "major_cities.json"
AIRPORT_CITY_MAP_FILE = Path(__file__).parent.parent / "data" / "countries" / "airport_city_map.json"
FLIXBUS_CITY_MAP_FILE = Path(__file__).parent.parent / "data" / "countries" / "flixbus_city_map.json"


async def seed() -> None:
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    countries_col = db[COUNTRIES_COLLECTION]
    cities_col = db[CITIES_COLLECTION]

    with open(NEIGHBORS_FILE, encoding="utf-8") as f:
        neighbors_map: dict[str, list[str]] = json.load(f)

    with open(MAJOR_CITIES_FILE, encoding="utf-8") as f:
        major_cities_map: dict[str, list[str]] = json.load(f)

    with open(AIRPORT_CITY_MAP_FILE, encoding="utf-8") as f:
        airport_city_map: dict[str, dict[str, list[str]]] = json.load(f)

    with open(FLIXBUS_CITY_MAP_FILE, encoding="utf-8") as f:
        flixbus_city_map: dict[str, dict[str, dict]] = json.load(f)

    await countries_col.drop()
    print("Dropped existing countries collection.")

    country_names: list[str] = await cities_col.distinct("country")
    print(f"Found {len(country_names)} countries in cities collection.")

    documents: list[dict] = []

    for country_raw in sorted(country_names):
        curated_names: list[str] = major_cities_map.get(country_raw, [])
        top_cities: list[dict] = []
        unmatched: list[str] = []

        for city_name in curated_names:
            # Case-insensitive exact match within the country
            cursor = cities_col.find(
                {
                    "country": country_raw,
                    "name": {"$regex": f"^{city_name}$", "$options": "i"},
                },
                {"_id": 0, "wikidata_id": 1, "name": 1, "freebase_id": 1, "description": 1},
            ).sort("wikidata_num", 1).limit(1)
            results = await cursor.to_list(length=1)
            doc = results[0] if results else None
            if doc:
                    # Attach airports from the static map if available
                    country_airports = airport_city_map.get(country_raw, {})
                    airports = country_airports.get(city_name, [])
                    if airports:
                        doc["airports"] = airports
                    # Attach Flixbus IDs from the static map if available
                    flixbus_entry = flixbus_city_map.get(country_raw, {}).get(city_name)
                    if flixbus_entry:
                        doc["flixbus_id"] = flixbus_entry["flixbus_id"]
                        if flixbus_entry.get("flixbus_legacy_id"):
                            doc["flixbus_legacy_id"] = flixbus_entry["flixbus_legacy_id"]
                    top_cities.append(doc)
            else:
                unmatched.append(city_name)

        if unmatched:
            print(f"  ⚠  {country_raw}: could not match — {unmatched}")

        doc = {
            "name": country_raw,
            "neighbors": neighbors_map.get(country_raw, []),
            "major_cities": top_cities,
        }
        documents.append(doc)
        print(f"  ✓ {country_raw}: {len(doc['neighbors'])} neighbors, {len(top_cities)}/{len(curated_names)} major cities matched")

    if documents:
        await countries_col.insert_many(documents)

    await countries_col.create_index("name", unique=True)
    await countries_col.create_index("neighbors")
    print("\nCreated indexes on 'name' and 'neighbors'.")
    print(f"\n✅ Seeding complete. Inserted {len(documents)} country documents.")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

