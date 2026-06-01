"""
Script: export_flixbus_ids.py

Reads the current Flixbus IDs from MongoDB and writes them to
data/countries/flixbus_city_map.json so they can be re-applied
by seed_countries.py on a fresh database.

Usage:
    python scripts/export_flixbus_ids.py
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

OUT_FILE = Path(__file__).parent.parent / "data" / "countries" / "flixbus_city_map.json"


async def main() -> None:
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]

    countries = await db["countries"].find(
        {}, {"name": 1, "major_cities": 1}
    ).to_list(length=None)

    result: dict[str, dict[str, dict]] = {}
    for country in countries:
        cities: dict[str, dict] = {}
        for city in country.get("major_cities", []):
            flixbus_id = city.get("flixbus_id")
            if flixbus_id:
                entry: dict = {"flixbus_id": flixbus_id}
                if city.get("flixbus_legacy_id"):
                    entry["flixbus_legacy_id"] = city["flixbus_legacy_id"]
                cities[city["name"]] = entry
        if cities:
            result[country["name"]] = cities

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    total = sum(len(v) for v in result.values())
    print(f"✅ Exported {total} city→flixbus_id mappings to {OUT_FILE}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

