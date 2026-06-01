from fastapi import HTTPException, status

from app.modules.buses.domain.entities import BusOffer
from app.modules.trips.domain.entities import Trip, TripMember, TripRole
from app.modules.trips.domain.interfaces import TripRepository
from app.modules.trips.application.flight_snapshot import snapshot_bus, snapshot_flight
from app.modules.flights.domain.entities import FlightOffer


class TripService:
    def __init__(self, repo: TripRepository) -> None:
        self._repo = repo

    async def create_trip(
        self,
        user_id: str,
        outbound_offer: FlightOffer,
        return_offer: FlightOffer,
        name: str = "",
        bus_offer: BusOffer | None = None,
    ) -> Trip:
        """Snapshot flight (and optional bus) offers and persist a new Trip.
        The creator is automatically added as MASTER member."""
        master = TripMember(user_id=user_id, role=TripRole.MASTER)
        trip = Trip(
            user_id=user_id,
            name=name,
            outbound_flight=snapshot_flight(outbound_offer),
            return_flight=snapshot_flight(return_offer),
            bus_journey=snapshot_bus(bus_offer) if bus_offer is not None else None,
            members=[master],
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

    # ── Member management ─────────────────────────────────────────────────────

    async def add_member(self, trip_id: str, requester_id: str, new_user_id: str) -> Trip:
        """Add *new_user_id* as a MEMBER of the trip.  Only the master may do this."""
        trip = await self._repo.get_by_id_any_user(trip_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.is_master(requester_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the trip master can add members.",
            )
        if trip.has_member(new_user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this trip.",
            )
        member = TripMember(user_id=new_user_id, role=TripRole.MEMBER)
        await self._repo.add_member(trip_id, member)
        # Return refreshed entity
        return await self._repo.get_by_id_any_user(trip_id)  # type: ignore[return-value]

    async def remove_member(self, trip_id: str, requester_id: str, target_user_id: str) -> Trip:
        """Remove *target_user_id* from the trip.
        The master can remove any member; a member can remove themselves."""
        trip = await self._repo.get_by_id_any_user(trip_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        is_master = trip.is_master(requester_id)
        is_self_removal = requester_id == target_user_id
        if not (is_master or is_self_removal):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the trip master can remove other members.",
            )
        if target_user_id == trip.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The trip master cannot be removed.",
            )
        removed = await self._repo.remove_member(trip_id, target_user_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this trip.",
            )
        return await self._repo.get_by_id_any_user(trip_id)  # type: ignore[return-value]


