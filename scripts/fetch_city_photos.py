"""
Fetch image filenames AND pre-resolved thumbnail URLs from Wikidata for MAJOR CITIES only.

Reads data/countries/major_cities.json to know which cities to populate.
Queries Wikidata P18 (image) and P948 (banner) for those ~200 cities,
then resolves the actual Wikimedia thumbnail URL via the imageinfo API
and stores both the raw filename and the thumbnail URL in MongoDB.

Usage:
    python -m scripts.fetch_city_photos

Requires: httpx, motor
"""

import asyncio
import json
import urllib.parse
from pathlib import Path

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

MAJOR_CITIES_PATH = Path(__file__).parent.parent / "data" / "countries" / "major_cities.json"

_WIKI_UA = "EuroWander/1.0 (travel app; contact@eurowander.dev)"


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


async def resolve_thumbnail_urls(
    session: httpx.AsyncClient, filenames: list[str], width: int = 800
) -> dict[str, str]:
    """
    Batch-resolve Wikimedia Commons filenames to actual thumbnail URLs
    via the MediaWiki imageinfo API (up to 50 titles per request).

    Returns a dict mapping filename -> thumbnail URL.
    """
    if not filenames:
        return {}

    titles = "|".join(f"File:{fn.replace(' ', '_')}" for fn in filenames)
    resp = await session.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": titles,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": str(width),
            "format": "json",
        },
        timeout=30.0,
    )
    data = resp.json()
    result: dict[str, str] = {}

    for page in data.get("query", {}).get("pages", {}).values():
        title = page.get("title", "")
        # Strip "File:" prefix and restore spaces
        fn = title.removeprefix("File:").replace("_", " ")
        for ii in page.get("imageinfo", []):
            thumb = ii.get("thumburl", "")
            if thumb:
                result[fn] = thumb
                break

    return result


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

    # Find major cities in DB that don't have an image_url yet
    cursor = collection.find(
        {
            "name": {"$in": list(all_major_names)},
            "wikidata_id": {"$exists": True, "$ne": ""},
            "$or": [
                {"image_url": {"$exists": False}},
                {"image_url": ""},
            ],
        },
        {"wikidata_id": 1, "name": 1, "image_filename": 1},
    )
    cities = await cursor.to_list(length=None)
    print(f"Found {len(cities)} major cities without resolved photo URLs in DB")

    if not cities:
        print("All major cities already have photo URLs!")
        return

    # Process in batches of 50
    batch_size = 50
    updated = 0

    async with httpx.AsyncClient(
        verify=False,
        headers={"User-Agent": _WIKI_UA},
    ) as session:
        for i in range(0, len(cities), batch_size):
            batch = cities[i : i + batch_size]
            qid_map = {doc["wikidata_id"]: doc for doc in batch}
            qids = list(qid_map.keys())

            # Step 1: Fetch filenames from Wikidata for cities that don't have them
            cities_needing_filenames = [
                qid for qid, doc in qid_map.items()
                if not doc.get("image_filename")
            ]
            if cities_needing_filenames:
                try:
                    wikidata_results = await fetch_wikidata_images(session, cities_needing_filenames)
                    for qid, filenames in wikidata_results.items():
                        doc = qid_map[qid]
                        await collection.update_one({"_id": doc["_id"]}, {"$set": filenames})
                        doc.update(filenames)  # update in-memory for step 2
                except Exception as e:
                    print(f"  Error fetching Wikidata batch {i}: {e}")
                    continue

            # Step 2: Resolve thumbnail URLs for all filenames in this batch
            filename_to_doc: dict[str, dict] = {}
            for doc in batch:
                fn = doc.get("image_filename", "")
                if fn:
                    filename_to_doc[fn] = doc

            if filename_to_doc:
                try:
                    thumb_urls = await resolve_thumbnail_urls(
                        session, list(filename_to_doc.keys())
                    )
                    for fn, thumb_url in thumb_urls.items():
                        doc = filename_to_doc[fn]
                        await collection.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"image_url": thumb_url}},
                        )
                        updated += 1
                except Exception as e:
                    print(f"  Error resolving thumbnails batch {i}: {e}")
                    continue

            batch_names = [doc["name"] for doc in batch]
            print(f"  Batch {i // batch_size + 1}: resolved {len(thumb_urls) if filename_to_doc else 0}/{len(batch)} "
                  f"({', '.join(batch_names[:5])}{'...' if len(batch_names) > 5 else ''})")
            await asyncio.sleep(1.0)  # be nice to Wikimedia API

    print(f"\nDone! Updated {updated} major cities with resolved thumbnail URLs.")


if __name__ == "__main__":
    asyncio.run(main())



