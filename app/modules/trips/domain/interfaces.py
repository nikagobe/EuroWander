from abc import ABC, abstractmethod

from app.modules.trips.domain.entities import SavedHotel, Trip, TripMember


class TripRepository(ABC):
    @abstractmethod
    async def create(self, trip: Trip) -> Trip: ...

    @abstractmethod
    async def get_by_id(self, trip_id: str, user_id: str) -> Trip | None:
        """Fetch a trip visible to *user_id* (owner or member)."""
        ...

    @abstractmethod
    async def get_by_id_any_user(self, trip_id: str) -> Trip | None:
        """Fetch a trip by ID without any ownership filter. Used for ownership checks."""
        ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Trip]:
        """Return all trips where *user_id* is the owner or a member."""
        ...

    @abstractmethod
    async def delete(self, trip_id: str, user_id: str) -> bool:
        """Delete a trip; only the master (owner) may delete."""
        ...

    @abstractmethod
    async def add_member(self, trip_id: str, member: TripMember) -> bool:
        """Append *member* to the trip's members list. Returns False if trip not found."""
        ...

    @abstractmethod
    async def remove_member(self, trip_id: str, member_user_id: str) -> bool:
        """Remove the member with *member_user_id* from the trip. Returns False if not found."""
        ...

    @abstractmethod
    async def update_flight_payment(
        self,
        trip_id: str,
        flight_type: str,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        """Persist payment info on outbound_flight or return_flight. Returns False if not found."""
        ...

    @abstractmethod
    async def update_bus_payment(
        self,
        trip_id: str,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        """Persist payment info on bus_journey. Returns False if trip not found or has no bus."""
        ...

    @abstractmethod
    async def add_hotel(self, trip_id: str, hotel: SavedHotel) -> bool:
        """Append a hotel to the trip's hotels list. Returns False if trip not found."""
        ...

    @abstractmethod
    async def remove_hotel(self, trip_id: str, hotel_id: int) -> bool:
        """Remove a specific hotel by hotel_id. Returns False if not found."""
        ...

    @abstractmethod
    async def update_hotel_payment(
        self,
        trip_id: str,
        hotel_id: int,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        """Persist payment info on a specific hotel. Returns False if trip/hotel not found."""
        ...

