from app.modules.flights.domain.entities import FlightOffer
from app.modules.flights.domain.interfaces import FlightSearchProvider

MAX_RESULTS = 20


class FlightService:
    """
    Orchestrates flight search business logic.
    Depends on the abstract FlightSearchProvider — never on a concrete client.
    """

    def __init__(self, provider: FlightSearchProvider) -> None:
        self._provider = provider

    async def search_flights(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        return_date: str | None = None,
        adults: int = 1,
        limit: int = 10,
    ) -> list[FlightOffer]:
        """Search for flights and return results ranked by price (cheapest first)."""
        offers = await self._provider.search(
            origin=origin,
            destination=destination,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
        )
        # Business rule: rank by price, cap at limit
        sorted_offers = sorted(offers, key=lambda o: o.price)
        return sorted_offers[: min(limit, MAX_RESULTS)]

