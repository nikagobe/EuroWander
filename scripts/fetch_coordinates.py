"""
fetch_coordinates.py — One-time script to enrich all city documents in MongoDB
with latitude/longitude coordinates fetched from the Wikidata SPARQL endpoint.

Usage:
    python scripts/fetch_coordinates.py

Requirements (already in project):
    pip install motor httpx

What it does:
    1. Reads all unique wikidata_ids from the 'cities' collection.
    2. Queries Wikidata SPARQL in batches of 200 IDs at a time.
    3. Bulk-updates every matching document with { lat, lng } fields.
    4. Prints a summary at the end.

After running this script, re-index if needed:
    The script does NOT re-seed — it only adds coordinates to existing docs.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

sys.path.insert(0, str(Path(__file__).parent))
from wikidata_helpers import fetch_all_coordinates

# ── Config ────────────────────────────────────────────────────────────────────

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://admin:secret@localhost:27017/eurowander?authSource=admin",
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "eurowander")
COLLECTION_NAME = "cities"
MONGO_WRITE_BATCH_SIZE = 500


# ── MongoDB helpers ───────────────────────────────────────────────────────────

async def get_all_wikidata_ids(collection: AsyncIOMotorCollection) -> list[str]:
    """Return every unique wikidata_id present in the collection."""
    ids: list[str] = []
    async for doc in collection.find({}, {"wikidata_id": 1, "_id": 0}):
        wid = doc.get("wikidata_id", "").strip()
        if wid:
            ids.append(wid)
    return ids


async def bulk_update_coordinates(
    collection: AsyncIOMotorCollection,
    coords: dict[str, tuple[float, float]],
) -> int:
    """
    Write coordinates back to MongoDB in batches.
    Returns total number of documents modified.
    """
    from pymongo import UpdateMany

    total_modified = 0
    ops: list[Any] = []

    async def flush() -> None:
        nonlocal total_modified
        if ops:
            result = await collection.bulk_write(ops, ordered=False)
            total_modified += result.modified_count
            ops.clear()

    for qid, (lat, lng) in coords.items():
        ops.append(
            UpdateMany(
                {"wikidata_id": qid},
                {"$set": {"lat": lat, "lng": lng}},
            )
        )
        if len(ops) >= MONGO_WRITE_BATCH_SIZE:
            await flush()

    await flush()
    return total_modified


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    client = AsyncIOMotorClient(MONGODB_URI)
    collection = client[DATABASE_NAME][COLLECTION_NAME]

    print("🔍 Reading wikidata_ids from MongoDB...")
    all_ids = await get_all_wikidata_ids(collection)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_ids: list[str] = []
    for wid in all_ids:
        if wid not in seen:
            seen.add(wid)
            unique_ids.append(wid)

    print(f"   Found {len(unique_ids)} unique wikidata_ids.\n")

    print("📡 Fetching coordinates from Wikidata...")
    all_coords = await fetch_all_coordinates(unique_ids)

    print(f"\n📊 Total cities with coordinates: {len(all_coords)} / {len(unique_ids)}")
    print(f"   Cities without coordinates:    {len(unique_ids) - len(all_coords)}\n")

    # Write back to MongoDB
    print("💾 Writing coordinates to MongoDB...")
    total_updated = await bulk_update_coordinates(collection, all_coords)

    # Create a 2dsphere index for future geo queries
    await collection.create_index([("location", "2dsphere")], sparse=True)

    # Also store as GeoJSON point for proper geo indexing (optional, future-proof)
    print("🗺  Building GeoJSON location field for 2dsphere index...")
    await collection.update_many(
        {"lat": {"$exists": True}, "lng": {"$exists": True}},
        [
            {
                "$set": {
                    "location": {
                        "type": "Point",
                        "coordinates": ["$lng", "$lat"],   # GeoJSON is [lng, lat]
                    }
                }
            }
        ],
    )

    print(f"\n✅ Done! Updated {total_updated} documents with lat/lng coordinates.")
    client.close()


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    elapsed = time.time() - start
    print(f"⏱  Total time: {elapsed:.1f}s")




