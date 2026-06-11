"""
Helpers for building stable, human-readable flight IDs from offer data,
and for snapshotting both flight and bus offers into trip value-objects.
Lives in application/ because it's business logic (not DB, not HTTP).
"""

import re

from app.modules.trips.domain.entities import (
    SavedBusJourney,
    SavedBusSegment,
    SavedFlight,
    SavedFlightLeg,
)
from app.modules.buses.domain.entities import BusOffer
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


def snapshot_bus(offer: BusOffer) -> SavedBusJourney:
    """Convert a live BusOffer into a SavedBusJourney value-object for storage."""
    segments = [
        SavedBusSegment(
            dep_name=seg.dep_name,
            arr_name=seg.arr_name,
            dep_time=seg.dep_time,
            arr_time=seg.arr_time,
            product_type=seg.product_type,
            product=seg.product,
        )
        for seg in offer.segments
    ]

    # Build a stable ID: "{dep_slug}-{arr_slug}-{date_slug}"
    dep_slug = re.sub(r"\s+", "_", offer.dep_name.lower())[:20]
    arr_slug = re.sub(r"\s+", "_", offer.arr_name.lower())[:20]
    date_slug = re.sub(r"\D", "", offer.dep_time.split("T")[0])[:8]
    journey_id = f"{dep_slug}-{arr_slug}-{date_slug}"

    return SavedBusJourney(
        journey_id=journey_id,
        dep_name=offer.dep_name,
        arr_name=offer.arr_name,
        dep_time=offer.dep_time,
        arr_time=offer.arr_time,
        duration=offer.duration,
        duration_minutes=offer.duration_minutes,
        changeovers=offer.changeovers,
        price=offer.price,
        currency=offer.currency,
        deeplink=offer.deeplink,
        additional_info=offer.additional_info,
        segments=segments,
    )


