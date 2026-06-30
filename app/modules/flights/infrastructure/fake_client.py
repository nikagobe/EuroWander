"""
Fake flight provider — reads SerpApi-shaped JSON fixtures from disk.
Zero API calls; useful for development when you don't want to burn SerpApi quota.

Toggle via leaving SERPAPI_KEY empty in .env (or not set at all).

Fixtures:
  data/flights/fake_single_results.json  — single origin → single destination
  data/flights/fake_results.json         — multi-origin (up to 5) → single destination
"""

import json
from pathlib import Path

from app.modules.flights.domain.entities import FlightOffer
from app.modules.flights.domain.interfaces import FlightSearchProvider
from app.modules.flights.infrastructure.serpapi_client import _parse_serpapi_response

_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "flights"

_FAKE_SINGLE_PATH = _DATA_DIR / "fake_single_results.json"
_FAKE_MULTI_DEFAULT_PATH = _DATA_DIR / "fake_results.json"

# Maps destination freebase_id → specific multi-origin fixture file.
# Add entries here whenever you record a new real API response for a route.
_FAKE_MULTI_BY_DESTINATION: dict[str, Path] = {
    "/m/0bm4j": _DATA_DIR / "fake_regional_spain_tbilisi.json",  # Tbilisi
}


def _load_fixture(path: Path, adults: int = 1) -> list[FlightOffer]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as f:
        data: dict = json.load(f)
    return _parse_serpapi_response(data, adults=adults)


def _multi_fixture(destination: str) -> Path:
    """Return the best-matching fixture file for the given destination."""
    return _FAKE_MULTI_BY_DESTINATION.get(destination, _FAKE_MULTI_DEFAULT_PATH)


class FakeFlightClient(FlightSearchProvider):
    """
    Returns hardcoded offers parsed from local JSON fixtures that mirror
    the real SerpApi Google Flights response shape.
    Origin / destination / date are ignored — the files act as fixed fixtures.
    """

    async def search(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        return_date: str | None,
        adults: int,
    ) -> list[FlightOffer]:
        return _load_fixture(_FAKE_SINGLE_PATH, adults=adults)

    async def search_multi_origin(
        self,
        origins: list[str],
        destination: str,
        outbound_date: str,
        return_date: str | None,
        adults: int,
    ) -> list[FlightOffer]:
        return _load_fixture(_multi_fixture(destination), adults=adults)
