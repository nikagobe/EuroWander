"""
TripBookingService — resolves a flight's booking_token into a purchasable URL.

Orchestration:
  1. Load the trip (ownership check).
  2. Extract booking_token + route from the chosen flight.
  3. Ask the BookingLinkProvider for booking options (SerpApi re-call).
  4. Pick the cheapest option and resolve the final vendor URL.
"""

from fastapi import HTTPException, status

from app.modules.flights.domain.interfaces import BookingLinkProvider
from app.modules.trips.domain.entities import SavedFlight
from app.modules.trips.domain.interfaces import TripRepository


class TripBookingService:
    def __init__(
        self,
        repo: TripRepository,
        booking_provider: BookingLinkProvider,
    ) -> None:
        self._repo = repo
        self._provider = booking_provider

    async def generate_booking_link(
        self,
        trip_id: str,
        user_id: str,
        flight: str = "outbound",   # "outbound" | "return"
    ) -> str:
        """
        Return a direct vendor booking URL for the specified flight leg.
        Raises 404 if the trip doesn't exist / doesn't belong to the user.
        Raises 400 if the flight has no booking_token.
        """
        trip = await self._repo.get_by_id(trip_id, user_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")

        saved: SavedFlight = (
            trip.outbound_flight if flight == "outbound" else trip.return_flight
        )

        if not saved.booking_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This flight has no booking_token; cannot generate a booking link.",
            )

        # Derive route & date from the saved leg snapshots
        departure_id: str = saved.legs[0].departure_airport if saved.legs else ""
        arrival_id: str = saved.legs[-1].arrival_airport if saved.legs else ""
        # departure_time is stored as "YYYY-MM-DD HH:MM" — extract just the date
        raw_time: str = saved.legs[0].departure_time if saved.legs else ""
        outbound_date: str = raw_time.split(" ")[0] if " " in raw_time else raw_time[:10]

        booking_options = await self._provider.fetch_booking_options(
            booking_token=saved.booking_token,
            departure_id=departure_id,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
        )

        if not booking_options:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No booking options returned by the flight provider.",
            )

        # Pick the cheapest "together" option
        best: dict | None = _pick_cheapest(booking_options)
        if best is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not determine a valid booking option.",
            )

        booking_url = await self._provider.resolve_url(
            url=best["url"],
            post_data=best["post_data"],
        )
        return booking_url


def _pick_cheapest(booking_options: list[dict]) -> dict | None:
    """Return the booking_request dict for the cheapest 'together' option."""
    best_request: dict | None = None
    best_price: float = float("inf")

    for option in booking_options:
        together = option.get("together", {})
        price = float(together.get("price", float("inf")))
        if price < best_price:
            req = together.get("booking_request")
            if req:
                best_price = price
                best_request = req

    return best_request

