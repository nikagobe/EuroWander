"""
Script: match_airports_to_cities.py

For every major city in the `countries` collection:
  1. Looks up the city's coordinates from the `cities` collection.
  2. Finds all airports in the same country (by country_code).
  3. Matches airports within MAX_DISTANCE_KM OR whose name contains the city name.
  4. Stores a list of matched IATA codes as `airports` on each major-city sub-document.

Usage:
    python scripts/match_airports_to_cities.py

Run AFTER seed_countries.py and seed_airports.py.
"""

import asyncio
import json
import math
import os
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://admin:secret@localhost:27017/eurowander?authSource=admin",
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "eurowander")

# Airports closer than this to the city centre are always included
MAX_DISTANCE_KM: float = 80.0

# Country name (as stored in MongoDB) → ISO 3166-1 alpha-2 code
COUNTRY_CODE_MAP: dict[str, str] = {
    "Albania": "AL",
    "Andorra": "AD",
    "Austria": "AT",
    "Belarus": "BY",
    "Belgium": "BE",
    "Bosnia_and_Herzegovina": "BA",
    "Bulgaria": "BG",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech_Republic": "CZ",
    "Denmark": "DK",
    "Estonia": "EE",
    "Finland": "FI",
    "France": "FR",
    "Georgia": "GE",
    "Germany": "DE",
    "Greece": "GR",
    "Hungary": "HU",
    "Iceland": "IS",
    "Ireland": "IE",
    "Italy": "IT",
    "Kazakhstan": "KZ",
    "Kosovo": "XK",
    "Latvia": "LV",
    "Liechtenstein": "LI",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Malta": "MT",
    "Moldova": "MD",
    "Monaco": "MC",
    "Montenegro": "ME",
    "Netherlands": "NL",
    "North_Macedonia": "MK",
    "Northern_Cyprus": "CY",
    "Norway": "NO",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Russia": "RU",
    "San_Marino": "SM",
    "Serbia": "RS",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Spain": "ES",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Ukraine": "UA",
    "United_Kingdom": "GB",
    "Vatican_City": "VA",
}

AIRPORTS_FILE = (
    Path(__file__).parent.parent / "data" / "airports" / "airports.json"
)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


async def main() -> None:
    # ── Load airports from file ──────────────────────────────────────────────
    with open(AIRPORTS_FILE, encoding="utf-8") as f:
        all_airports: list[dict] = json.load(f)

    # Index by country_code for fast lookup
    airports_by_country: dict[str, list[dict]] = {}
    for ap in all_airports:
        cc = ap.get("country_code", "")
        if cc:
            airports_by_country.setdefault(cc, []).append(ap)

    print(f"Loaded {len(all_airports)} airports across {len(airports_by_country)} countries.\n")

    # ── Connect to MongoDB ───────────────────────────────────────────────────
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    countries_col = db["countries"]
    cities_col = db["cities"]

    countries = await countries_col.find({}, {"name": 1, "major_cities": 1}).to_list(length=None)

    total_matched = 0

    for country_doc in countries:
        country_name: str = country_doc["name"]
        country_code = COUNTRY_CODE_MAP.get(country_name)
        if not country_code:
            print(f"  ⚠  No country_code mapping for '{country_name}' — skipping")
            continue

        country_airports = airports_by_country.get(country_code, [])
        # Some small countries share airports with neighbours — also include adjacent codes
        # e.g. Liechtenstein uses Swiss airports (CH), Monaco uses French (FR)
        extra_codes: dict[str, list[str]] = {
            "Liechtenstein": ["CH"],
            "Monaco": ["FR"],
            "San_Marino": ["IT"],
            "Vatican_City": ["IT"],
            "Andorra": ["ES", "FR"],
        }
        for extra_cc in extra_codes.get(country_name, []):
            country_airports = country_airports + airports_by_country.get(extra_cc, [])

        major_cities: list[dict] = country_doc.get("major_cities", [])
        changed = False

        for city in major_cities:
            city_name: str = city.get("name", "")
            city_name_lower = city_name.lower()

            # ── Get city coordinates from cities collection ──────────────────
            cursor = cities_col.find(
                {
                    "country": country_name,
                    "name": {"$regex": f"^{city_name}$", "$options": "i"},
                    "lat": {"$exists": True},
                    "lng": {"$exists": True},
                },
                {"lat": 1, "lng": 1},
            ).sort("wikidata_num", 1).limit(1)
            results = await cursor.to_list(length=1)
            city_coords = results[0] if results else None

            matched_iatas: list[str] = []

            for ap in country_airports:
                iata: str = ap.get("iata_code", "")
                if not iata:
                    continue

                ap_name_lower = ap.get("name", "").lower()
                ap_lat = ap.get("lat")
                ap_lng = ap.get("lng")

                # Match 1: airport name contains city name
                name_match = city_name_lower in ap_name_lower

                # Match 2: proximity (only if city has coordinates)
                proximity_match = False
                if city_coords and ap_lat is not None and ap_lng is not None:
                    dist = _haversine_km(
                        city_coords["lat"], city_coords["lng"],
                        ap_lat, ap_lng,
                    )
                    proximity_match = dist <= MAX_DISTANCE_KM

                if name_match or proximity_match:
                    matched_iatas.append(iata)

            # Deduplicate preserving order
            seen: set[str] = set()
            unique_iatas: list[str] = []
            for iata in matched_iatas:
                if iata not in seen:
                    seen.add(iata)
                    unique_iatas.append(iata)

            if unique_iatas:
                city["airports"] = unique_iatas
                changed = True
                print(f"  ✓ {country_name} / {city_name}: {unique_iatas}")
            else:
                print(f"  ✗ {country_name} / {city_name}: no airports matched")

            total_matched += len(unique_iatas)

        if changed:
            await countries_col.update_one(
                {"name": country_name},
                {"$set": {"major_cities": major_cities}},
            )

    print(f"\n✅ Done. Matched {total_matched} airport–city links across all major cities.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

