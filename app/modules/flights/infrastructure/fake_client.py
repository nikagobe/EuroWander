"""
Fake flight provider — reads a SerpApi-shaped JSON from data/flights/fake_results.json.
Zero API calls; useful for development when you don't want to burn SerpApi quota.

Toggle via leaving SERPAPI_KEY empty in .env (or not set at all).
"""

import json
from pathlib import Path

from app.modules.flights.domain.entities import FlightOffer
from app.modules.flights.domain.interfaces import FlightSearchProvider
from app.modules.flights.infrastructure.serpapi_client import _parse_serpapi_response

_FAKE_DATA_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "data"
    / "flights"
    / "fake_results.json"
)


class FakeFlightClient(FlightSearchProvider):
    """
    Returns hardcoded offers parsed from a local JSON file that mirrors
    the real SerpApi Google Flights response shape.
    Origin / destination are ignored — the file acts as a fixed fixture.
    """

    async def search(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        return_date: str | None,
        adults: int,
    ) -> list[FlightOffer]:
        if not _FAKE_DATA_PATH.exists():
            return []

        with _FAKE_DATA_PATH.open(encoding="utf-8-sig") as f:
            data: dict = json.load(f)

        # Reuse exactly the same parser as the real client
        return _parse_serpapi_response(data)

