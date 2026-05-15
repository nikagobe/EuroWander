"""
enrich_seeds.py — Fetches coordinates from Wikidata and writes lat/lng directly
into the JSON seed files under data/cities/.

Run this once (or whenever you add new city data) so that seed_cities.py always
inserts coordinates without needing a separate MongoDB update step.

Usage:
    python scripts/enrich_seeds.py

Options (env vars):
    DRY_RUN=1   Print what would change without writing files.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Allow importing from the scripts/ directory
sys.path.insert(0, str(Path(__file__).parent))
from wikidata_helpers import fetch_all_coordinates

DATA_DIR = Path(__file__).parent.parent / "data" / "cities"
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"


def collect_ids_from_file(data: list[dict]) -> list[str]:
    """Return all non-empty wikidata_ids from a city list."""
    return [
        doc["wikidata_id"].strip()
        for doc in data
        if doc.get("wikidata_id", "").strip()
    ]


def enrich_file(
    data: list[dict],
    coords: dict[str, tuple[float, float]],
) -> tuple[list[dict], int]:
    """
    Write lat/lng into each city dict that has a matching coordinate.
    Returns (enriched_data, count_updated).
    """
    updated = 0
    for doc in data:
        qid = doc.get("wikidata_id", "").strip()
        if qid in coords:
            lat, lng = coords[qid]
            # Only count as updated if value actually changed
            if doc.get("lat") != lat or doc.get("lng") != lng:
                doc["lat"] = lat
                doc["lng"] = lng
                updated += 1
    return data, updated


async def main() -> None:
    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {DATA_DIR}")
        return

    if DRY_RUN:
        print("🔍 DRY RUN — files will NOT be written.\n")

    total_files = len(json_files)
    grand_total_cities = 0
    grand_total_updated = 0

    for file_idx, file_path in enumerate(json_files, start=1):
        print(f"\n[{file_idx}/{total_files}] {file_path.name}")

        with open(file_path, encoding="utf-8") as f:
            data: list[dict] = json.load(f)

        if not data:
            print("  ⚠ Empty file, skipping.")
            continue

        # Collect unique IDs that are missing coordinates (skip already-enriched)
        ids_missing = [
            doc["wikidata_id"].strip()
            for doc in data
            if doc.get("wikidata_id", "").strip()
            and (doc.get("lat") is None or doc.get("lng") is None)
        ]

        already_done = len(data) - len(ids_missing)
        if already_done:
            print(f"  ℹ {already_done}/{len(data)} cities already have coordinates.")

        if not ids_missing:
            print("  ✅ All cities already enriched, skipping API calls.")
            grand_total_cities += len(data)
            continue

        # Deduplicate
        unique_missing = list(dict.fromkeys(ids_missing))
        print(f"  🔎 Fetching coordinates for {len(unique_missing)} cities...")

        coords = await fetch_all_coordinates(unique_missing, label=file_path.stem)

        enriched_data, updated = enrich_file(data, coords)
        grand_total_cities += len(data)
        grand_total_updated += updated

        hit_rate = len(coords) / len(unique_missing) * 100 if unique_missing else 100
        print(f"  📊 {len(coords)}/{len(unique_missing)} IDs matched ({hit_rate:.0f}%), {updated} docs updated.")

        if not DRY_RUN:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=4)
            print(f"  💾 Written → {file_path.name}")

    print(f"\n{'='*60}")
    print(f"✅ Done.")
    print(f"   Files processed : {total_files}")
    print(f"   Cities processed: {grand_total_cities}")
    print(f"   Docs updated    : {grand_total_updated}")
    if DRY_RUN:
        print("   (DRY RUN — no files were written)")


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    elapsed = time.time() - start
    print(f"⏱  Total time: {elapsed:.1f}s")

