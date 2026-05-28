from app.modules.buses.domain.entities import BusOffer
from app.modules.buses.domain.interfaces import BusSearchProvider

MAX_RESULTS = 30


def _parse_duration_minutes(duration: str) -> int:
    """Convert "07:40" → 460 minutes."""
    try:
        h, m = duration.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 0


class BusService:
    """
    Orchestrates bus search business logic.
    Depends on the abstract BusSearchProvider — never on a concrete client.
    """

    def __init__(self, provider: BusSearchProvider) -> None:
        self._provider = provider

    async def search_buses(
        self,
        from_id: str,
        to_id: str,
        date: str,          # DD.MM.YYYY
        adults: int = 1,
        currency: str = "EUR",
        limit: int = 20,
    ) -> list[BusOffer]:
        """Search for bus journeys, sorted by price (cheapest first)."""
        offers = await self._provider.search(
            from_id=from_id,
            to_id=to_id,
            date=date,
            adults=adults,
            currency=currency,
        )
        # Business rule: parse duration minutes if not already set, then sort
        for offer in offers:
            if offer.duration_minutes == 0 and offer.duration:
                offer.duration_minutes = _parse_duration_minutes(offer.duration)

        sorted_offers = sorted(offers, key=lambda o: o.price)
        return sorted_offers[: min(limit, MAX_RESULTS)]

