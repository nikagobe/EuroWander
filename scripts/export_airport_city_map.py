"""
Script: export_airport_city_map.py

Reads the current airport–city matchings from MongoDB and writes them
to data/countries/airport_city_map.json so they can be committed and
re-applied by seed_countries.py on a fresh database.

Usage:
    python scripts/export_airport_city_map.py
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

OUT_FILE = Path(__file__).parent.parent / "data" / "countries" / "airport_city_map.json"


async def main() -> None:
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]

    countries = await db["countries"].find(
        {}, {"name": 1, "major_cities": 1}
    ).to_list(length=None)

    result: dict[str, dict[str, list[str]]] = {}
    for country in countries:
        cities: dict[str, list[str]] = {}
        for city in country.get("major_cities", []):
            airports: list[str] = city.get("airports", [])
            if airports:
                cities[city["name"]] = airports
        if cities:
            result[country["name"]] = cities

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    total = sum(len(v) for v in result.values())
    print(f"✅ Exported {total} city→airport mappings to {OUT_FILE}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

