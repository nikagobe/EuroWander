from fastapi import HTTPException, status

from app.modules.trips.domain.entities import Trip
from app.modules.trips.domain.interfaces import TripRepository
from app.modules.trips.application.flight_snapshot import snapshot_flight
from app.modules.flights.domain.entities import FlightOffer


class TripService:
    def __init__(self, repo: TripRepository) -> None:
        self._repo = repo

    async def create_trip(
        self,
        user_id: str,
        outbound_offer: FlightOffer,
        return_offer: FlightOffer,
    ) -> Trip:
        """Snapshot both flight offers and persist a new Trip for the user."""
        trip = Trip(
            user_id=user_id,
            outbound_flight=snapshot_flight(outbound_offer),
            return_flight=snapshot_flight(return_offer),
        )
        return await self._repo.create(trip)

    async def get_trip(self, trip_id: str, user_id: str) -> Trip:
        trip = await self._repo.get_by_id(trip_id, user_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return trip

    async def list_trips(self, user_id: str) -> list[Trip]:
        return await self._repo.list_by_user(user_id)

    async def delete_trip(self, trip_id: str, user_id: str) -> None:
        deleted = await self._repo.delete(trip_id, user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")


