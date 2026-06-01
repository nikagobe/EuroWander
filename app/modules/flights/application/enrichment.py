"""
enrichment.py — Enriches FlightOffer legs with airport coordinates and city info.

Collects all unique IATA codes from a list of offers, performs batch
queries against the airports and countries collections, then stamps
lat/lng + city_name + city_freebase_id onto each FlightLeg.
"""

from app.modules.airports.domain.interfaces import AirportRepository
from app.modules.countries.domain.interfaces import CountryRepository
from app.modules.flights.domain.entities import FlightOffer


async def enrich_offers_with_coords(
    offers: list[FlightOffer],
    airport_repo: AirportRepository,
    country_repo: CountryRepository | None = None,
) -> list[FlightOffer]:
    """
    Mutates each FlightLeg in-place with:
      - departure/arrival lat & lng  (from airports collection)
      - departure/arrival city_name + city_freebase_id  (from countries collection)
    Returns the same list.
    """
    # Collect all unique IATA codes across every leg
    iata_codes: set[str] = set()
    for offer in offers:
        for leg in offer.legs:
            if leg.departure_airport:
                iata_codes.add(leg.departure_airport.upper())
            if leg.arrival_airport:
                iata_codes.add(leg.arrival_airport.upper())

    if not iata_codes:
        return offers

    # ── Batch lookup: coordinates ────────────────────────────────────────────
    coord_map: dict[str, tuple[float | None, float | None]] = {}
    for iata in iata_codes:
        airport = await airport_repo.get_by_iata(iata)
        if airport:
            coord_map[iata] = (airport.lat, airport.lng)

    # ── Batch lookup: city info ──────────────────────────────────────────────
    city_map: dict[str, tuple[str, str]] = {}   # iata → (city_name, freebase_id)
    if country_repo is not None:
        for iata in iata_codes:
            city = await country_repo.get_city_by_iata(iata)
            if city:
                city_map[iata] = (city.name, city.freebase_id)

    # ── Stamp onto every leg ─────────────────────────────────────────────────
    for offer in offers:
        for leg in offer.legs:
            dep_iata = leg.departure_airport.upper()
            arr_iata = leg.arrival_airport.upper()

            dep_coords = coord_map.get(dep_iata)
            arr_coords = coord_map.get(arr_iata)
            if dep_coords:
                leg.departure_lat, leg.departure_lng = dep_coords
            if arr_coords:
                leg.arrival_lat, leg.arrival_lng = arr_coords

            dep_city = city_map.get(dep_iata)
            arr_city = city_map.get(arr_iata)
            if dep_city:
                leg.departure_city_name, leg.departure_city_freebase_id = dep_city
            if arr_city:
                leg.arrival_city_name, leg.arrival_city_freebase_id = arr_city

    return offers

