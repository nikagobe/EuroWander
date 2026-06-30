"""
Fake Flixbus client — returns data from a local JSON file.
Used when RAPIDAPI_KEY is not set or USE_FAKE_BUS=true.
"""

import json
from pathlib import Path

from app.modules.buses.domain.entities import BusOffer, BusSegment
from app.modules.buses.domain.interfaces import BusSearchProvider

_FAKE_FILE = Path(__file__).parent.parent.parent.parent.parent / "data" / "buses" / "fake_berlin_munich.json"


def _parse_journeys(data: dict, source: str = "fake", adults: int = 1) -> list[BusOffer]:
    offers: list[BusOffer] = []
    for j in data.get("journeys", []):
        fares = j.get("fares", [{}])
        fare = fares[0] if fares else {}
        price: float = fare.get("price", 0.0)
        currency: str = fare.get("currency", "EUR")
        additional_info: str = fare.get("additional_info", "")

        segments: list[BusSegment] = [
            BusSegment(
                dep_name=s.get("dep_name", ""),
                arr_name=s.get("arr_name", ""),
                dep_time=s.get("dep_offset", ""),
                arr_time=s.get("arr_offset", ""),
                product_type=s.get("product_type", "bus"),
                product=s.get("product", "flixbus"),
            )
            for s in j.get("segments", [])
        ]

        duration_str: str = j.get("duration", "00:00")
        try:
            h, m = duration_str.split(":")
            duration_minutes = int(h) * 60 + int(m)
        except Exception:
            duration_minutes = 0

        offers.append(
            BusOffer(
                dep_name=j.get("dep_name", ""),
                arr_name=j.get("arr_name", ""),
                dep_time=j.get("dep_offset", ""),
                arr_time=j.get("arr_offset", ""),
                duration=duration_str,
                duration_minutes=duration_minutes,
                changeovers=j.get("changeovers", 0),
                price=price,
                currency=currency,
                deeplink=j.get("deeplink", ""),
                segments=segments,
                additional_info=additional_info,
                source=source,
                adults=adults,
            )
        )
    return offers


class FakeBusClient(BusSearchProvider):
    """Returns static fake data regardless of from_id / to_id / date."""

    async def search(
        self,
        from_id: str,
        to_id: str,
        date: str,
        adults: int,
        currency: str,
    ) -> list[BusOffer]:
        with open(_FAKE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return _parse_journeys(data, source="fake", adults=adults)

