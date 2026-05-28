"""
Real Flixbus client via RapidAPI (flixbus2.p.rapidapi.com).
Active when RAPIDAPI_KEY is set and USE_FAKE_BUS is not "true".
"""

import ssl

import certifi
import httpx

from app.modules.buses.domain.entities import BusOffer, BusSegment
from app.modules.buses.domain.interfaces import BusSearchProvider
from app.modules.buses.infrastructure.fake_client import _parse_journeys

_BASE_URL = "https://flixbus2.p.rapidapi.com/trips"


class FlixbusClient(BusSearchProvider):
    """Calls the RapidAPI Flixbus wrapper to fetch real journey data."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(
        self,
        from_id: str,
        to_id: str,
        date: str,          # DD.MM.YYYY
        adults: int = 1,
        currency: str = "EUR",
    ) -> list[BusOffer]:
        params = {
            "from_id": from_id,
            "to_id": to_id,
            "date": date,
            "adult": str(adults),
            "search_by": "cities",
            "children": "0",
            "bikes": "0",
            "currency": currency,
            "locale": "en",
        }
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": "flixbus2.p.rapidapi.com",
            "x-rapidapi-key": self._api_key,
        }

        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(_BASE_URL, params=params, headers=headers, timeout=15.0)
            response.raise_for_status()
            data: dict = response.json()

        return _parse_journeys(data, source="flixbus")

