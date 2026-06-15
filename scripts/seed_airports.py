"""
seed_airports.py — Loads data/airports/airports.json into MongoDB.

Usage:
    python scripts/seed_airports.py

Run fetch_airports.py first if the JSON file does not exist yet.
"""

import asyncio
import json
import os
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://eurowander-app:S3VcK7oBKm32vVJM@cluster0.cjwhina.mongodb.net/?appName=Cluster0",
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "eurowander")
COLLECTION_NAME = "airports"
DATA_PATH = Path(__file__).parent.parent / "data" / "airports" / "airports.json"


async def seed() -> None:
    if not DATA_PATH.exists():
        print(f"❌ File not found: {DATA_PATH}")
        print("   Run  python scripts/fetch_airports.py  first.")
        return

    with open(DATA_PATH, encoding="utf-8") as f:
        airports: list[dict] = json.load(f)

    if not airports:
        print("❌ airports.json is empty.")
        return

    client = AsyncIOMotorClient(MONGODB_URI)
    collection = client[DATABASE_NAME][COLLECTION_NAME]

    await collection.drop()
    print(f"Dropped existing '{COLLECTION_NAME}' collection.")

    await collection.insert_many(airports)
    print(f"✓ Inserted {len(airports)} airports.")

    # Indexes
    await collection.create_index("iata_code", unique=True)
    await collection.create_index("wikidata_id")
    await collection.create_index("country_code")
    await collection.create_index([("location", "2dsphere")], sparse=True)


    print("✓ Created indexes (iata_code, wikidata_id, country_code, 2dsphere).")
    print(f"\n✅ Done. {len(airports)} airports seeded.")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

