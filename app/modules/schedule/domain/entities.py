"""
Schedule domain entities.

A TripSchedule divides the trip date range into days, each split into
four time slots: MORNING, MIDDAY, EVENING, NIGHT.

Items are either auto-generated (flights, transits, hotel check-in/out)
or manually added by the user (attractions, restaurants).
"""

from dataclasses import dataclass, field
from enum import Enum


class TimeSlot(str, Enum):
    """
    Day divided into four parts:
      MORNING : 06:00 – 11:59
      MIDDAY  : 12:00 – 16:59
      EVENING : 17:00 – 20:59
      NIGHT   : 21:00 – 05:59
    """
    MORNING = "morning"
    MIDDAY = "midday"
    EVENING = "evening"
    NIGHT = "night"


class ScheduleItemType(str, Enum):
    """Type of item in the schedule."""
    FLIGHT = "flight"
    TRANSIT = "transit"
    HOTEL_CHECK_IN = "hotel_check_in"
    HOTEL_CHECK_OUT = "hotel_check_out"
    ATTRACTION = "attraction"
    RESTAURANT = "restaurant"
    CUSTOM = "custom"


# Types the user can manually add/edit/remove
MANUAL_ITEM_TYPES: set[ScheduleItemType] = {
    ScheduleItemType.ATTRACTION,
    ScheduleItemType.RESTAURANT,
    ScheduleItemType.CUSTOM,
}


@dataclass
class ScheduleItem:
    """
    A single entry in the schedule.
    Pure domain model — no MongoDB or FastAPI awareness.
    """
    day_date: str                   # YYYY-MM-DD
    time_slot: TimeSlot
    item_type: ScheduleItemType
    title: str                      # e.g. "Eiffel Tower", "Flight TBS→CDG"
    subtitle: str = ""              # e.g. "12:30 – 14:45", "French cuisine"
    reference_id: str = ""          # Location ID for attractions/restaurants, flight_id, etc.
    note: str = ""                  # User/creator note (e.g. tips, warnings)
    is_auto: bool = False           # True = derived from trip data, cannot be edited
    id: str = ""                    # Unique item ID (for manual items)
    order: int = 0                  # Sort order within the same time slot


@dataclass
class ScheduleDay:
    """One day of the schedule with items grouped by time slot."""
    date: str                       # YYYY-MM-DD
    items: list[ScheduleItem] = field(default_factory=list)


@dataclass
class TripSchedule:
    """
    Complete schedule for a trip — list of days, each with time-slot items.
    Computed on-the-fly: auto items from trip data + manual items from DB.
    Items whose dates fall outside the trip range go into `unscheduled`.
    """
    trip_id: str
    days: list[ScheduleDay] = field(default_factory=list)
    unscheduled: list[ScheduleItem] = field(default_factory=list)

