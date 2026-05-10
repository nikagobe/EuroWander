"""
Seed script: reads all JSON files from data/cities/ and uploads them to MongoDB.

Usage:
    python scripts/seed_cities.py
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
COLLECTION_NAME = "cities"
DATA_DIR = Path(__file__).parent.parent / "data" / "cities"
BATCH_SIZE = 1000  # insert in batches to avoid memory issues


async def seed() -> None:
    client = AsyncIOMotorClient(MONGODB_URI)
    collection = client[DATABASE_NAME][COLLECTION_NAME]

    # Drop existing data so re-running the script gives a clean state
    await collection.drop()
    print("Dropped existing cities collection.")

    json_files = list(DATA_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {DATA_DIR}")
        return

    total_inserted = 0

    for file_path in json_files:
        print(f"Processing {file_path.name}...")

        with open(file_path, encoding="utf-8") as f:
            data: list[dict] = json.load(f)

        # Tag each document with the country file it came from
        country_name = file_path.stem  # e.g. "greece" from "greece.json"
        for doc in data:
            doc["country"] = country_name
            # Extract numeric part of wikidata_id (e.g. "Q90" → 90) for sorting
            wikidata_id: str = doc.get("wikidata_id", "Q0")
            try:
                doc["wikidata_num"] = int(wikidata_id.lstrip("Q"))
            except ValueError:
                doc["wikidata_num"] = 0

        # Insert in batches
        for i in range(0, len(data), BATCH_SIZE):
            batch = data[i : i + BATCH_SIZE]
            await collection.insert_many(batch)

        total_inserted += len(data)
        print(f"  ✓ Inserted {len(data)} cities from {file_path.name}")

    # Regular index on "name" for fast regex prefix queries
    await collection.create_index("name")
    # Index on wikidata_num for sorting by city size
    await collection.create_index("wikidata_num")
    # Create a regular index on "country" for filtering
    await collection.create_index("country")
    print("\nCreated indexes on 'name', 'wikidata_num' and 'country'.")

    print(f"\n✅ Seeding complete. Total cities inserted: {total_inserted}")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

