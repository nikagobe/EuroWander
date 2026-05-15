"""
Helpers for building stable, human-readable flight IDs from offer data.
Lives in application/ because it's business logic (not DB, not HTTP).
"""

import re

from app.modules.trips.domain.entities import SavedFlight, SavedFlightLeg
from app.modules.flights.domain.entities import FlightOffer


def build_flight_id(offer: FlightOffer) -> str:
    """
    Build a stable ID from the first leg of a flight offer:
      "{dep_airport}-{arr_airport}-{YYYYMMDD}-{flight_number_slug}"

    Example: "CDG-BCN-20260615-VY8243"
    """
    if not offer.legs:
        raise ValueError("Cannot build flight_id: offer has no legs.")

    first = offer.legs[0]
    last  = offer.legs[-1]

    # Extract date part from departure_time ("2026-06-15 10:15" → "20260615")
    date_slug = re.sub(r"\D", "", first.departure_time.split(" ")[0])[:8]

    # Sanitise flight number: "VY 8243" → "VY8243"
    fn_slug = re.sub(r"\s+", "", first.flight_number).upper()

    return f"{first.departure_airport}-{last.arrival_airport}-{date_slug}-{fn_slug}"


def snapshot_flight(offer: FlightOffer) -> SavedFlight:
    """Convert a live FlightOffer into a SavedFlight value-object for storage."""
    legs = [
        SavedFlightLeg(
            flight_number=leg.flight_number,
            airline=leg.airline,
            airline_logo=leg.airline_logo,
            airplane=leg.airplane,
            departure_airport=leg.departure_airport,
            departure_airport_name=leg.departure_airport_name,
            arrival_airport=leg.arrival_airport,
            arrival_airport_name=leg.arrival_airport_name,
            departure_time=leg.departure_time,
            arrival_time=leg.arrival_time,
            duration_minutes=leg.duration_minutes,
            travel_class=leg.travel_class,
            legroom=leg.legroom,
            is_overnight=leg.is_overnight,
        )
        for leg in offer.legs
    ]
    return SavedFlight(
        flight_id=build_flight_id(offer),
        price=offer.price,
        currency=offer.currency,
        total_duration_minutes=offer.total_duration_minutes,
        stops=offer.stops,
        airline_logo=offer.airline_logo,
        booking_token=offer.booking_token,
        legs=legs,
    )

