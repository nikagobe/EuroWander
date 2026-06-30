"""
Real SerpApi client — calls the Google Flights engine via SerpApi.
Docs: https://serpapi.com/google-flights-api

departure_id / arrival_id are freebase IDs (e.g. "/m/05qtj") taken directly
from the `freebase_id` field stored on every City document.
"""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

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

        # Log outgoing request params (mask api_key)
        log_params = {k: v for k, v in params.items() if k != "api_key"}
        logger.info("[SerpApi] search request params: %s", log_params)

        async with httpx.AsyncClient(timeout=20, verify=verify) as client:
            response = await client.get(_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        logger.info("[SerpApi] raw response keys: %s", list(data.keys()))
        logger.info("[SerpApi] full response:\n%s", json.dumps(data, indent=2))

        best_count = len(data.get("best_flights", []))
        other_count = len(data.get("other_flights", []))
        logger.info("[SerpApi] best_flights=%d, other_flights=%d", best_count, other_count)

        offers = _parse_serpapi_response(data, adults=adults)
        logger.info("[SerpApi] parsed %d FlightOffer(s)", len(offers))
        return offers

    async def search_multi_origin(
        self,
        origins: list[str],
        destination: str,
        outbound_date: str,
        return_date: str | None,
        adults: int,
    ) -> list[FlightOffer]:
        """
        SerpApi accepts up to 5 comma-separated freebase IDs in departure_id.
        Callers must ensure len(origins) <= 5.
        """
        departure_id = ",".join(origins)
        params: dict[str, str | int] = {
            "engine": "google_flights",
            "departure_id": departure_id,
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
            params["type"] = "1"
        else:
            params["type"] = "2"

        try:
            import ssl as _ssl
            import truststore
            ssl_ctx = truststore.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
            verify: bool | object = ssl_ctx
        except ImportError:
            verify = True

        # Log outgoing request params (mask api_key)
        log_params = {k: v for k, v in params.items() if k != "api_key"}
        logger.info("[SerpApi] search_multi_origin request params: %s", log_params)

        async with httpx.AsyncClient(timeout=20, verify=verify) as client:
            response = await client.get(_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        logger.info("[SerpApi] multi-origin raw response keys: %s", list(data.keys()))
        logger.info("[SerpApi] multi-origin full response:\n%s", json.dumps(data, indent=2))

        best_count = len(data.get("best_flights", []))
        other_count = len(data.get("other_flights", []))
        logger.info("[SerpApi] multi-origin best_flights=%d, other_flights=%d", best_count, other_count)

        offers = _parse_serpapi_response(data, adults=adults)
        logger.info("[SerpApi] multi-origin parsed %d FlightOffer(s)", len(offers))
        return offers


def _parse_serpapi_response(data: dict, adults: int = 1) -> list[FlightOffer]:
    """Parse a SerpApi Google Flights JSON response into domain FlightOffer objects."""
    offers: list[FlightOffer] = []

    # SerpApi splits results into best_flights and other_flights
    raw_groups: list[dict] = data.get("best_flights", []) + data.get("other_flights", [])

    for group in raw_groups:
        # Skip offers that have no price — SerpApi sometimes omits it
        # for other_flights entries. Showing €0 to the user is misleading.
        if "price" not in group or group["price"] is None:
            logger.info(
                "[SerpApi] skipping offer without price (flights: %s)",
                [f.get("flight_number", "?") for f in group.get("flights", [])],
            )
            continue

        raw_legs: list[dict] = group.get("flights", [])
        legs = [_parse_leg(leg) for leg in raw_legs]

        offers.append(
            FlightOffer(
                price=float(group["price"]),
                currency=data.get("search_parameters", {}).get("currency", "EUR"),
                total_duration_minutes=group.get("total_duration", 0),
                legs=legs,
                stops=max(0, len(legs) - 1),
                airline_logo=group.get("airline_logo", ""),
                booking_token=group.get("booking_token", ""),
                source="serpapi",
                adults=adults,
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

