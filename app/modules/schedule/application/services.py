"""
Schedule application service.

Orchestrates building the full trip schedule by:
1. Computing auto-items from trip flights, transits, hotels, attractions, and restaurants.
2. Merging persisted manual items (ad-hoc notes).
3. Providing CRUD for manual items with validation.
"""

from datetime import date, datetime, timedelta

from app.modules.schedule.domain.entities import (
    MANUAL_ITEM_TYPES,
    ScheduleDay,
    ScheduleItem,
    ScheduleItemType,
    TimeSlot,
    TripSchedule,
)
from app.modules.schedule.domain.interfaces import ScheduleRepository
from app.modules.trips.domain.entities import (
    SavedAttraction,
    SavedBusJourney,
    SavedFlight,
    SavedHotel,
    SavedRestaurant,
    Trip,
)
from app.modules.trips.domain.interfaces import TripRepository


class ScheduleService:
    """Orchestrates schedule logic — never touches DB directly."""

    def __init__(self, schedule_repo: ScheduleRepository, trip_repo: TripRepository) -> None:
        self._schedule_repo = schedule_repo
        self._trip_repo = trip_repo

    # ── Read ────────────────────────────────────────────────────────────────

    async def get_full_schedule(self, trip_id: str, user_id: str) -> TripSchedule:
        """
        Build the complete schedule for a trip.
        Merges auto-items (flights, transits, hotels) with manual items.
        """
        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found or access denied")

        # Determine trip date range
        start_date, end_date = _get_trip_date_range(trip)

        # Generate auto items from trip data
        auto_items: list[ScheduleItem] = []
        auto_items.extend(_flight_to_items(trip.outbound_flight, "outbound"))
        auto_items.extend(_flight_to_items(trip.return_flight, "return"))
        if trip.bus_journey:
            auto_items.extend(_bus_to_items(trip.bus_journey))
        for hotel in trip.hotels:
            auto_items.extend(_hotel_to_items(hotel))
        for attraction in trip.attractions:
            auto_items.extend(_attraction_to_items(attraction))
        for restaurant in trip.restaurants:
            auto_items.extend(_restaurant_to_items(restaurant))

        # Get manual items from DB
        manual_items = await self._schedule_repo.get_manual_items(trip_id)

        # Merge and organize by day
        all_items = auto_items + manual_items
        return _build_schedule(trip_id, start_date, end_date, all_items)

    # ── Create ──────────────────────────────────────────────────────────────

    async def add_item(
        self,
        trip_id: str,
        user_id: str,
        day_date: str,
        time_slot: TimeSlot,
        item_type: ScheduleItemType,
        title: str,
        subtitle: str = "",
        reference_id: str = "",
    ) -> ScheduleItem:
        """Add a manual item (attraction/restaurant) to the schedule."""
        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found or access denied")

        if item_type not in MANUAL_ITEM_TYPES:
            raise ValueError(f"Cannot manually add items of type '{item_type.value}'. Only attractions and restaurants allowed.")

        # Validate date is within trip range
        start_date, end_date = _get_trip_date_range(trip)
        item_date = date.fromisoformat(day_date)
        if item_date < start_date or item_date > end_date:
            raise ValueError(f"Date {day_date} is outside trip range ({start_date} – {end_date})")

        item = ScheduleItem(
            day_date=day_date,
            time_slot=time_slot,
            item_type=item_type,
            title=title,
            subtitle=subtitle,
            reference_id=reference_id,
            is_auto=False,
        )

        return await self._schedule_repo.add_item(trip_id, item)

    # ── Update ──────────────────────────────────────────────────────────────

    async def update_item(
        self,
        trip_id: str,
        item_id: str,
        user_id: str,
        day_date: str | None = None,
        time_slot: str | None = None,
        title: str | None = None,
        subtitle: str | None = None,
        order: int | None = None,
    ) -> ScheduleItem:
        """Update a manual schedule item (move to different slot, rename, reorder)."""
        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found or access denied")

        # Validate new date if provided
        if day_date:
            start_date, end_date = _get_trip_date_range(trip)
            item_date = date.fromisoformat(day_date)
            if item_date < start_date or item_date > end_date:
                raise ValueError(f"Date {day_date} is outside trip range ({start_date} – {end_date})")

        result = await self._schedule_repo.update_item(
            trip_id=trip_id,
            item_id=item_id,
            day_date=day_date,
            time_slot=time_slot,
            title=title,
            subtitle=subtitle,
            order=order,
        )
        if not result:
            raise ValueError("Schedule item not found or is an auto-item")
        return result

    # ── Delete ──────────────────────────────────────────────────────────────

    async def remove_item(self, trip_id: str, item_id: str, user_id: str) -> None:
        """Remove a manual schedule item."""
        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found or access denied")

        removed = await self._schedule_repo.remove_item(trip_id, item_id)
        if not removed:
            raise ValueError("Schedule item not found or is an auto-item")


# ── Private helpers ─────────────────────────────────────────────────────────────


def _resolve_time_slot(hour: int) -> TimeSlot:
    """Map hour (0-23) to a TimeSlot."""
    if 6 <= hour < 12:
        return TimeSlot.MORNING
    elif 12 <= hour < 17:
        return TimeSlot.MIDDAY
    elif 17 <= hour < 21:
        return TimeSlot.EVENING
    else:
        return TimeSlot.NIGHT


def _parse_datetime(dt_str: str) -> datetime | None:
    """Parse various datetime string formats from trip data."""
    if not dt_str:
        return None
    # Try common formats
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    # Try ISO format as fallback
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _get_trip_date_range(trip: Trip) -> tuple[date, date]:
    """Extract start/end dates from a Trip's flights."""
    # Start: outbound flight first leg departure
    outbound_legs = trip.outbound_flight.legs
    if outbound_legs:
        start_dt = _parse_datetime(outbound_legs[0].departure_time)
    else:
        start_dt = None

    # End: return flight first leg departure
    return_legs = trip.return_flight.legs
    if return_legs:
        end_dt = _parse_datetime(return_legs[0].departure_time)
    else:
        end_dt = None

    # Fallback to today + 7 days if parsing fails
    today = date.today()
    start = start_dt.date() if start_dt else today
    end = end_dt.date() if end_dt else start + timedelta(days=7)

    return start, end


def _flight_to_items(flight: SavedFlight, direction: str) -> list[ScheduleItem]:
    """Convert a SavedFlight into schedule items (one per leg)."""
    items: list[ScheduleItem] = []
    for leg in flight.legs:
        dep_dt = _parse_datetime(leg.departure_time)
        if not dep_dt:
            continue
        day_str = dep_dt.date().isoformat()
        slot = _resolve_time_slot(dep_dt.hour)

        # Format subtitle: "10:45 TBS → CDG (2h 30m)"
        dep_time_fmt = dep_dt.strftime("%H:%M")
        arr_dt = _parse_datetime(leg.arrival_time)
        arr_time_fmt = arr_dt.strftime("%H:%M") if arr_dt else ""
        duration_h = leg.duration_minutes // 60
        duration_m = leg.duration_minutes % 60
        duration_str = f"{duration_h}h {duration_m}m" if duration_h else f"{duration_m}m"

        subtitle = f"{dep_time_fmt} → {arr_time_fmt} ({duration_str})"
        title = f"✈️ {leg.departure_airport} → {leg.arrival_airport}"

        items.append(ScheduleItem(
            day_date=day_str,
            time_slot=slot,
            item_type=ScheduleItemType.FLIGHT,
            title=title,
            subtitle=subtitle,
            reference_id=flight.flight_id,
            is_auto=True,
        ))
    return items


def _bus_to_items(bus: SavedBusJourney) -> list[ScheduleItem]:
    """Convert a SavedBusJourney into a schedule item."""
    dep_dt = _parse_datetime(bus.dep_time)
    if not dep_dt:
        return []

    day_str = dep_dt.date().isoformat()
    slot = _resolve_time_slot(dep_dt.hour)

    dep_time_fmt = dep_dt.strftime("%H:%M")
    arr_dt = _parse_datetime(bus.arr_time)
    arr_time_fmt = arr_dt.strftime("%H:%M") if arr_dt else ""
    subtitle = f"{dep_time_fmt} → {arr_time_fmt} ({bus.duration})"
    title = f"🚌 {bus.dep_name} → {bus.arr_name}"

    return [ScheduleItem(
        day_date=day_str,
        time_slot=slot,
        item_type=ScheduleItemType.TRANSIT,
        title=title,
        subtitle=subtitle,
        reference_id=bus.journey_id,
        is_auto=True,
    )]


def _hotel_to_items(hotel: SavedHotel) -> list[ScheduleItem]:
    """Convert a SavedHotel into check-in and check-out schedule items."""
    items: list[ScheduleItem] = []

    # Check-in: default to MIDDAY (14:00 convention)
    if hotel.checkin_date:
        items.append(ScheduleItem(
            day_date=hotel.checkin_date,
            time_slot=TimeSlot.MIDDAY,
            item_type=ScheduleItemType.HOTEL_CHECK_IN,
            title=f"🏨 Check-in: {hotel.name}",
            subtitle=hotel.address,
            reference_id=str(hotel.hotel_id),
            is_auto=True,
        ))

    # Check-out: default to MORNING (10:00 convention)
    if hotel.checkout_date:
        items.append(ScheduleItem(
            day_date=hotel.checkout_date,
            time_slot=TimeSlot.MORNING,
            item_type=ScheduleItemType.HOTEL_CHECK_OUT,
            title=f"🏨 Check-out: {hotel.name}",
            subtitle=hotel.address,
            reference_id=str(hotel.hotel_id),
            is_auto=True,
        ))

    return items


def _attraction_to_items(attraction: SavedAttraction) -> list[ScheduleItem]:
    """Convert a SavedAttraction into a schedule item."""
    if not attraction.day_date:
        return []

    # Map the stored time_slot string to the TimeSlot enum
    try:
        slot = TimeSlot(attraction.time_slot)
    except ValueError:
        slot = TimeSlot.MORNING

    return [ScheduleItem(
        day_date=attraction.day_date,
        time_slot=slot,
        item_type=ScheduleItemType.ATTRACTION,
        title=f"🎯 {attraction.name}",
        subtitle=attraction.address or attraction.category,
        reference_id=attraction.location_id,
        is_auto=True,
    )]


def _restaurant_to_items(restaurant: SavedRestaurant) -> list[ScheduleItem]:
    """Convert a SavedRestaurant into a schedule item."""
    if not restaurant.day_date:
        return []

    try:
        slot = TimeSlot(restaurant.time_slot)
    except ValueError:
        slot = TimeSlot.EVENING

    return [ScheduleItem(
        day_date=restaurant.day_date,
        time_slot=slot,
        item_type=ScheduleItemType.RESTAURANT,
        title=f"🍽️ {restaurant.name}",
        subtitle=restaurant.address or restaurant.cuisine,
        reference_id=restaurant.location_id,
        is_auto=True,
    )]


def _build_schedule(
    trip_id: str,
    start_date: date,
    end_date: date,
    items: list[ScheduleItem],
) -> TripSchedule:
    """Organize items into days, sorted by time slot and order."""
    # Build day map
    day_map: dict[str, list[ScheduleItem]] = {}
    current = start_date
    while current <= end_date:
        day_map[current.isoformat()] = []
        current += timedelta(days=1)

    # Assign items to days
    for item in items:
        if item.day_date in day_map:
            day_map[item.day_date].append(item)

    # Sort within each day by time slot order then by item order
    slot_order = {TimeSlot.MORNING: 0, TimeSlot.MIDDAY: 1, TimeSlot.EVENING: 2, TimeSlot.NIGHT: 3}

    days: list[ScheduleDay] = []
    for day_str in sorted(day_map.keys()):
        day_items = sorted(
            day_map[day_str],
            key=lambda x: (slot_order.get(x.time_slot, 9), x.is_auto, x.order),
        )
        days.append(ScheduleDay(date=day_str, items=day_items))

    return TripSchedule(trip_id=trip_id, days=days)





