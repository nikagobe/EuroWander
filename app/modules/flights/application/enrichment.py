"""
enrichment.py — Enriches FlightOffer legs with airport coordinates.

Collects all unique IATA codes from a list of offers, performs a single
batch query against the airports collection, then stamps lat/lng onto
each FlightLeg.  Pure application logic — no FastAPI or HTTP concerns.
"""

from app.modules.airports.domain.interfaces import AirportRepository
from app.modules.flights.domain.entities import FlightOffer


async def enrich_offers_with_coords(
    offers: list[FlightOffer],
    airport_repo: AirportRepository,
) -> list[FlightOffer]:
    """
    Mutates each FlightLeg in-place with departure/arrival lat & lng
    looked up from the airports collection.  Returns the same list.
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

    # Single batch lookup
    coord_map: dict[str, tuple[float | None, float | None]] = {}
    for iata in iata_codes:
        airport = await airport_repo.get_by_iata(iata)
        if airport:
            coord_map[iata] = (airport.lat, airport.lng)

    # Stamp coordinates onto every leg
    for offer in offers:
        for leg in offer.legs:
            dep = coord_map.get(leg.departure_airport.upper())
            arr = coord_map.get(leg.arrival_airport.upper())
            if dep:
                leg.departure_lat, leg.departure_lng = dep
            if arr:
                leg.arrival_lat, leg.arrival_lng = arr

    return offers


