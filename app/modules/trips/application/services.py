from fastapi import HTTPException, status

from app.modules.buses.domain.entities import BusOffer
from app.modules.trips.domain.entities import (
    SavedAttraction,
    SavedHotel,
    SavedRestaurant,
    Trip,
    TripMember,
    TripRole,
)
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
        creator_first_name: str = "",
        creator_last_name: str = "",
        forked_from_template_id: str = "",
        destination_image_filename: str = "",
        destination_image_url: str = "",
    ) -> Trip:
        """Snapshot flight (and optional bus) offers and persist a new Trip.
        The creator is automatically added as MASTER member."""
        master = TripMember(
            user_id=user_id,
            role=TripRole.MASTER,
            first_name=creator_first_name,
            last_name=creator_last_name,
        )
        trip = Trip(
            user_id=user_id,
            name=name,
            outbound_flight=snapshot_flight(outbound_offer),
            return_flight=snapshot_flight(return_offer),
            bus_journey=snapshot_bus(bus_offer) if bus_offer is not None else None,
            members=[master],
            forked_from_template_id=forked_from_template_id,
            destination_image_filename=destination_image_filename,
            destination_image_url=destination_image_url,
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

    async def add_member(
        self,
        trip_id: str,
        requester_id: str,
        new_user_id: str,
        first_name: str = "",
        last_name: str = "",
    ) -> Trip:
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
        member = TripMember(user_id=new_user_id, role=TripRole.MEMBER, first_name=first_name, last_name=last_name)
        await self._repo.add_member(trip_id, member)
        # Return refreshed entity
        return await self._repo.get_by_id_any_user(trip_id)  # type: ignore[return-value]

    async def mark_flight_paid(
        self,
        trip_id: str,
        requester_id: str,
        flight_type: str,   # "outbound" | "return"
        actual_paid_amount: float,
        paid_currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> Trip:
        """Mark a flight ticket as paid and record the actual price + who shares the cost.
        Only trip members (master or member) may call this."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        updated = await self._repo.update_flight_payment(
            trip_id=trip_id,
            flight_type=flight_type,
            is_paid=True,
            actual_paid_amount=actual_paid_amount,
            paid_currency=paid_currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def unmark_flight_paid(
        self,
        trip_id: str,
        requester_id: str,
        flight_type: str,
    ) -> Trip:
        """Clear payment info from a flight ticket."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        await self._repo.update_flight_payment(
            trip_id=trip_id,
            flight_type=flight_type,
            is_paid=False,
            actual_paid_amount=None,
            paid_currency=None,
            paid_by=None,
            eligible_member_ids=[],
        )
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    # ── Bus payment management ────────────────────────────────────────────────

    async def mark_bus_paid(
        self,
        trip_id: str,
        requester_id: str,
        actual_paid_amount: float,
        paid_currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> Trip:
        """Mark the bus journey ticket as paid. Only trip members may call this."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if trip.bus_journey is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This trip has no bus journey.",
            )
        updated = await self._repo.update_bus_payment(
            trip_id=trip_id,
            is_paid=True,
            actual_paid_amount=actual_paid_amount,
            paid_currency=paid_currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def unmark_bus_paid(
        self,
        trip_id: str,
        requester_id: str,
    ) -> Trip:
        """Clear payment info from the bus journey ticket."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if trip.bus_journey is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This trip has no bus journey.",
            )
        await self._repo.update_bus_payment(
            trip_id=trip_id,
            is_paid=False,
            actual_paid_amount=None,
            paid_currency=None,
            paid_by=None,
            eligible_member_ids=[],
        )
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

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

    # ── Hotel management ─────────────────────────────────────────────────────

    async def add_hotel(
        self,
        trip_id: str,
        requester_id: str,
        hotel: SavedHotel,
    ) -> Trip:
        """Add a hotel to the trip's hotels list. Only members may call this."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        # Prevent duplicate hotel_id
        if trip.find_hotel(hotel.hotel_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Hotel {hotel.hotel_id} is already saved in this trip.",
            )
        updated = await self._repo.add_hotel(trip_id, hotel)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def remove_hotel(
        self,
        trip_id: str,
        requester_id: str,
        hotel_id: int,
    ) -> Trip:
        """Remove a specific hotel from the trip by hotel_id."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_hotel(hotel_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hotel {hotel_id} not found in this trip.",
            )
        await self._repo.remove_hotel(trip_id, hotel_id)
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def mark_hotel_paid(
        self,
        trip_id: str,
        requester_id: str,
        hotel_id: int,
        actual_paid_amount: float,
        paid_currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> Trip:
        """Mark a specific hotel as paid and record cost-sharing info."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_hotel(hotel_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hotel {hotel_id} not found in this trip.",
            )
        updated = await self._repo.update_hotel_payment(
            trip_id=trip_id,
            hotel_id=hotel_id,
            is_paid=True,
            actual_paid_amount=actual_paid_amount,
            paid_currency=paid_currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def unmark_hotel_paid(
        self,
        trip_id: str,
        requester_id: str,
        hotel_id: int,
    ) -> Trip:
        """Clear payment info from a specific hotel."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_hotel(hotel_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hotel {hotel_id} not found in this trip.",
            )
        await self._repo.update_hotel_payment(
            trip_id=trip_id,
            hotel_id=hotel_id,
            is_paid=False,
            actual_paid_amount=None,
            paid_currency=None,
            paid_by=None,
            eligible_member_ids=[],
        )
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    # ── Attraction management ─────────────────────────────────────────────────

    async def add_attraction(
        self,
        trip_id: str,
        requester_id: str,
        attraction: SavedAttraction,
    ) -> Trip:
        """Add an attraction to the trip. Only members may call this."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if trip.find_attraction(attraction.location_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Attraction {attraction.location_id} is already saved in this trip.",
            )
        updated = await self._repo.add_attraction(trip_id, attraction)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def remove_attraction(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
    ) -> Trip:
        """Remove a specific attraction from the trip by location_id."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_attraction(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attraction {location_id} not found in this trip.",
            )
        await self._repo.remove_attraction(trip_id, location_id)
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def mark_attraction_paid(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
        actual_paid_amount: float,
        paid_currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> Trip:
        """Mark a specific attraction as paid and record cost-sharing info."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_attraction(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attraction {location_id} not found in this trip.",
            )
        updated = await self._repo.update_attraction_payment(
            trip_id=trip_id,
            location_id=location_id,
            is_paid=True,
            actual_paid_amount=actual_paid_amount,
            paid_currency=paid_currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def unmark_attraction_paid(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
    ) -> Trip:
        """Clear payment info from a specific attraction."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_attraction(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attraction {location_id} not found in this trip.",
            )
        await self._repo.update_attraction_payment(
            trip_id=trip_id,
            location_id=location_id,
            is_paid=False,
            actual_paid_amount=None,
            paid_currency=None,
            paid_by=None,
            eligible_member_ids=[],
        )
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def reschedule_attraction(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
        day_date: str | None,
        time_slot: str | None,
    ) -> Trip:
        """Move an attraction to a different day/time slot (drag-and-drop reschedule)."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_attraction(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attraction {location_id} not found in this trip.",
            )
        if day_date is None and time_slot is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of day_date or time_slot must be provided.",
            )
        updated = await self._repo.update_attraction_schedule(
            trip_id=trip_id,
            location_id=location_id,
            day_date=day_date,
            time_slot=time_slot,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attraction not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    # ── Restaurant management ─────────────────────────────────────────────────

    async def add_restaurant(
        self,
        trip_id: str,
        requester_id: str,
        restaurant: SavedRestaurant,
    ) -> Trip:
        """Add a restaurant to the trip. Only members may call this."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if trip.find_restaurant(restaurant.location_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Restaurant {restaurant.location_id} is already saved in this trip.",
            )
        updated = await self._repo.add_restaurant(trip_id, restaurant)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def remove_restaurant(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
    ) -> Trip:
        """Remove a specific restaurant from the trip by location_id."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_restaurant(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Restaurant {location_id} not found in this trip.",
            )
        await self._repo.remove_restaurant(trip_id, location_id)
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def mark_restaurant_paid(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
        actual_paid_amount: float,
        paid_currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> Trip:
        """Mark a specific restaurant as paid and record cost-sharing info."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_restaurant(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Restaurant {location_id} not found in this trip.",
            )
        updated = await self._repo.update_restaurant_payment(
            trip_id=trip_id,
            location_id=location_id,
            is_paid=True,
            actual_paid_amount=actual_paid_amount,
            paid_currency=paid_currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def unmark_restaurant_paid(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
    ) -> Trip:
        """Clear payment info from a specific restaurant."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_restaurant(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Restaurant {location_id} not found in this trip.",
            )
        await self._repo.update_restaurant_payment(
            trip_id=trip_id,
            location_id=location_id,
            is_paid=False,
            actual_paid_amount=None,
            paid_currency=None,
            paid_by=None,
            eligible_member_ids=[],
        )
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]

    async def reschedule_restaurant(
        self,
        trip_id: str,
        requester_id: str,
        location_id: str,
        day_date: str | None,
        time_slot: str | None,
    ) -> Trip:
        """Move a restaurant to a different day/time slot (drag-and-drop reschedule)."""
        trip = await self._repo.get_by_id(trip_id, requester_id)
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
        if not trip.find_restaurant(location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Restaurant {location_id} not found in this trip.",
            )
        if day_date is None and time_slot is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of day_date or time_slot must be provided.",
            )
        updated = await self._repo.update_restaurant_schedule(
            trip_id=trip_id,
            location_id=location_id,
            day_date=day_date,
            time_slot=time_slot,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
        return await self._repo.get_by_id(trip_id, requester_id)  # type: ignore[return-value]


