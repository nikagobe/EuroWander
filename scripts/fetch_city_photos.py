"""
Fetch image filenames from Wikidata for MAJOR CITIES only.

Reads data/countries/major_cities.json to know which cities to populate.
Queries Wikidata P18 (image) and P948 (banner) for those ~200 cities,
stores the raw filenames in MongoDB. The API builds URLs dynamically.

For non-major cities, the Flutter frontend will query Wikidata directly
when it encounters a null photo_url in the city response.

Usage:
    python -m scripts.fetch_city_photos

Requires: httpx, motor
"""

import asyncio
import json
from pathlib import Path

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

MAJOR_CITIES_PATH = Path(__file__).parent.parent / "data" / "countries" / "major_cities.json"


async def fetch_wikidata_images(
    session: httpx.AsyncClient, qids: list[str]
) -> dict[str, dict[str, str]]:
    """Batch-fetch P18 (image) and P948 (banner) for up to 50 Wikidata entities."""
    ids_str = "|".join(qids)
    resp = await session.get(
        "https://www.wikidata.org/w/api.php",
        params={
            "action": "wbgetentities",
            "ids": ids_str,
            "props": "claims",
            "format": "json",
        },
        timeout=30.0,
    )
    data = resp.json()
    results: dict[str, dict[str, str]] = {}

    for qid in qids:
        entity = data.get("entities", {}).get(qid, {})
        claims = entity.get("claims", {})
        info: dict[str, str] = {}

        # P18 = main image
        p18 = claims.get("P18", [])
        if p18:
            filename = p18[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
            if filename:
                info["image_filename"] = filename

        # P948 = page banner
        p948 = claims.get("P948", [])
        if p948:
            filename = p948[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
            if filename:
                info["banner_filename"] = filename

        if info:
            results[qid] = info

    return results


async def main() -> None:
    # Load major city names
    with open(MAJOR_CITIES_PATH, encoding="utf-8") as f:
        major_cities_by_country: dict[str, list[str]] = json.load(f)

    # Flatten to a set of city names for fast lookup
    all_major_names: set[str] = set()
    for cities in major_cities_by_country.values():
        all_major_names.update(cities)

    print(f"Major cities to process: {len(all_major_names)}")

    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.database_name]
    collection = db["cities"]

    # Find major cities in DB that don't have an image_filename yet
    cursor = collection.find(
        {
            "name": {"$in": list(all_major_names)},
            "image_filename": {"$exists": False},
            "wikidata_id": {"$exists": True, "$ne": ""},
        },
        {"wikidata_id": 1, "name": 1},
    )
    cities = await cursor.to_list(length=None)
    print(f"Found {len(cities)} major cities without photos in DB")

    if not cities:
        print("All major cities already have photos!")
        return

    # Process in batches of 50
    batch_size = 50
    updated = 0

    async with httpx.AsyncClient(
        verify=False,
        headers={"User-Agent": "EuroWander/1.0 (travel app; contact@eurowander.dev)"},
    ) as session:
        for i in range(0, len(cities), batch_size):
            batch = cities[i : i + batch_size]
            qid_map = {doc["wikidata_id"]: doc["_id"] for doc in batch}
            qids = list(qid_map.keys())

            try:
                results = await fetch_wikidata_images(session, qids)
            except Exception as e:
                print(f"  Error on batch {i}: {e}")
                continue

            for qid, filenames in results.items():
                doc_id = qid_map[qid]
                await collection.update_one({"_id": doc_id}, {"$set": filenames})
                updated += 1

            batch_names = [doc["name"] for doc in batch]
            print(f"  Batch {i // batch_size + 1}: {len(results)}/{len(batch)} "
                  f"({', '.join(batch_names[:5])}{'...' if len(batch_names) > 5 else ''})")
            await asyncio.sleep(0.5)

    print(f"\nDone! Updated {updated} major cities with image filenames.")


if __name__ == "__main__":
    asyncio.run(main())



