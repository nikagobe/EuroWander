"""
Real SerpApi client — calls the Google Flights engine via SerpApi.
Docs: https://serpapi.com/google-flights-api

departure_id / arrival_id are freebase IDs (e.g. "/m/05qtj") taken directly
from the `freebase_id` field stored on every City document.
"""

import httpx

from app.modules.flights.domain.entities import FlightLeg, FlightOffer
from app.modules.flights.domain.interfaces import FlightSearchProvider

_BASE_URL = "https://serpapi.com/search"


class SerpApiFlightClient(FlightSearchProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(
        self,
        origin: str,           # freebase_id, e.g. "/m/05qtj"
        destination: str,      # freebase_id, e.g. "/m/01f62"
        outbound_date: str,    # YYYY-MM-DD
        return_date: str | None,
        adults: int,
    ) -> list[FlightOffer]:
        params: dict[str, str | int] = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": outbound_date,
            "currency": "EUR",
            "hl": "en",
            "gl": "us",
            "deep_search": "true",
            "adults": adults,
            "api_key": self._api_key,
        }
        if return_date:
            params["return_date"] = return_date
            params["type"] = "1"   # round-trip
        else:
            params["type"] = "2"   # one-way

        # Use the OS certificate store so corporate SSL-inspection proxies are trusted.
        # Falls back to httpx default if truststore is not installed.
        try:
            import ssl as _ssl
            import truststore
            ssl_ctx = truststore.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
            verify: bool | object = ssl_ctx
        except ImportError:
            verify = True  # default httpx behaviour

        async with httpx.AsyncClient(timeout=20, verify=verify) as client:
            response = await client.get(_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        return _parse_serpapi_response(data)


def _parse_serpapi_response(data: dict) -> list[FlightOffer]:
    """Parse a SerpApi Google Flights JSON response into domain FlightOffer objects."""
    offers: list[FlightOffer] = []

    # SerpApi splits results into best_flights and other_flights
    raw_groups: list[dict] = data.get("best_flights", []) + data.get("other_flights", [])

    for group in raw_groups:
        raw_legs: list[dict] = group.get("flights", [])
        legs = [_parse_leg(leg) for leg in raw_legs]

        offers.append(
            FlightOffer(
                price=float(group.get("price", 0)),
                currency=data.get("search_parameters", {}).get("currency", "EUR"),
                total_duration_minutes=group.get("total_duration", 0),
                legs=legs,
                stops=max(0, len(legs) - 1),
                airline_logo=group.get("airline_logo", ""),
                booking_token=group.get("booking_token", ""),
                source="serpapi",
            )
        )

    return offers


def _parse_leg(raw: dict) -> FlightLeg:
    dep = raw.get("departure_airport", {})
    arr = raw.get("arrival_airport", {})
    return FlightLeg(
        flight_number=raw.get("flight_number", ""),
        airline=raw.get("airline", ""),
        airline_logo=raw.get("airline_logo", ""),
        airplane=raw.get("airplane", ""),
        departure_airport=dep.get("id", ""),
        departure_airport_name=dep.get("name", ""),
        arrival_airport=arr.get("id", ""),
        arrival_airport_name=arr.get("name", ""),
        departure_time=dep.get("time", ""),
        arrival_time=arr.get("time", ""),
        duration_minutes=raw.get("duration", 0),
        is_overnight=raw.get("overnight", False),
        travel_class=raw.get("travel_class", "Economy"),
        legroom=raw.get("legroom", ""),
    )

