"""
MultiOriginFlightService — searches flights from the user's region.

Business logic:
  1. Look up the user's country and collect its major-city freebase_ids.
  2. Look up all neighbouring countries and collect their major-city freebase_ids.
  3. Deduplicate and strip cities without a freebase_id.
  4. Batch the list into groups of ≤ MAX_ORIGINS_PER_CALL (SerpApi limit = 5).
  5. Fire one SerpApi call per batch concurrently.
  6. Merge all results, deduplicate by booking_token, sort by price.
"""

import asyncio
from dataclasses import dataclass

from app.modules.countries.domain.interfaces import CountryRepository
from app.modules.flights.domain.entities import FlightOffer
from app.modules.flights.domain.interfaces import FlightSearchProvider

MAX_ORIGINS_PER_CALL = 5
MAX_RESULTS = 30


@dataclass
class RegionalSearchParams:
    """Value object carrying all inputs for a regional flight search."""
    origin_country: str       # Country name, e.g. "Germany"
    destination_id: str       # freebase_id of the destination city
    outbound_date: str        # YYYY-MM-DD
    return_date: str | None = None
    adults: int = 1
    limit: int = 20


class MultiOriginFlightService:
    """
    Orchestrates regional flight search.
    Depends only on abstract interfaces — no infrastructure concerns here.
    """

    def __init__(
        self,
        provider: FlightSearchProvider,
        country_repo: CountryRepository,
    ) -> None:
        self._provider = provider
        self._country_repo = country_repo

    async def search_from_region(
        self,
        params: RegionalSearchParams,
    ) -> list[FlightOffer]:
        """
        Gather all departure freebase_ids from the origin country +
        its neighbours, batch them, fire concurrent searches, and return
        merged results ranked by price.
        """
        freebase_ids = await self._collect_departure_ids(params.origin_country)

        if not freebase_ids:
            return []

        batches = _chunk(freebase_ids, MAX_ORIGINS_PER_CALL)

        tasks = [
            self._provider.search_multi_origin(
                origins=batch,
                destination=params.destination_id,
                outbound_date=params.outbound_date,
                return_date=params.return_date,
                adults=params.adults,
            )
            for batch in batches
        ]

        results_per_batch: tuple[list[FlightOffer], ...] = await asyncio.gather(*tasks)

        merged = _merge_and_deduplicate(results_per_batch)
        return sorted(merged, key=lambda o: o.price)[: min(params.limit, MAX_RESULTS)]

    async def _collect_departure_ids(self, country_name: str) -> list[str]:
        """
        Return deduplicated freebase_ids for major cities in the given
        country and all its neighbours.  Cities without a freebase_id
        are silently excluded.
        """
        origin_country = await self._country_repo.get_by_name(country_name)
        neighbor_countries = await self._country_repo.get_neighbors_with_cities(country_name)

        all_countries = neighbor_countries[:]
        if origin_country is not None:
            all_countries.insert(0, origin_country)

        seen: set[str] = set()
        ids: list[str] = []
        for country in all_countries:
            for city in country.major_cities:
                fid = city.freebase_id.strip()
                if fid and fid not in seen:
                    seen.add(fid)
                    ids.append(fid)

        return ids


# ── helpers ──────────────────────────────────────────────────────────────────

def _chunk(lst: list[str], size: int) -> list[list[str]]:
    """Split a list into sub-lists of at most `size` elements."""
    return [lst[i: i + size] for i in range(0, len(lst), size)]


def _merge_and_deduplicate(
    batches: tuple[list[FlightOffer], ...] | list[list[FlightOffer]],
) -> list[FlightOffer]:
    """
    Flatten and deduplicate by booking_token.
    Offers without a token are all kept (they come from the fake client).
    """
    seen_tokens: set[str] = set()
    merged: list[FlightOffer] = []
    for batch in batches:
        for offer in batch:
            token = offer.booking_token
            if token and token in seen_tokens:
                continue
            if token:
                seen_tokens.add(token)
            merged.append(offer)
    return merged



