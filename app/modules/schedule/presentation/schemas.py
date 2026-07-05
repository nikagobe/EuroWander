"""Pydantic schemas for the Schedule module — optimized for Flutter."""

from pydantic import BaseModel, ConfigDict


class ScheduleItemResponse(BaseModel):
    """A single item in the schedule."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4",
                "day_date": "2026-07-27",
                "time_slot": "midday",
                "item_type": "attraction",
                "title": "Eiffel Tower",
                "subtitle": "Champ de Mars, Paris",
                "reference_id": "188757",
                "is_auto": False,
                "order": 0,
            }
        }
    )

    id: str
    day_date: str
    time_slot: str
    item_type: str
    title: str
    subtitle: str
    reference_id: str
    is_auto: bool
    order: int


class ScheduleDayResponse(BaseModel):
    """One day in the schedule with all its items."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-07-27",
                "items": [
                    {"id": "", "day_date": "2026-07-27", "time_slot": "morning", "item_type": "flight", "title": "✈️ TBS → CDG", "subtitle": "10:45 → 14:30 (4h 45m)", "reference_id": "fl_123", "is_auto": True, "order": 0},
                    {"id": "abc", "day_date": "2026-07-27", "time_slot": "evening", "item_type": "attraction", "title": "Eiffel Tower", "subtitle": "Champ de Mars", "reference_id": "188757", "is_auto": False, "order": 0},
                ],
            }
        }
    )

    date: str
    items: list[ScheduleItemResponse]


class FullScheduleResponse(BaseModel):
    """Complete trip schedule — all days with their items."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": "trip_abc123",
                "days": [],
            }
        }
    )

    trip_id: str
    days: list[ScheduleDayResponse]


class AddScheduleItemRequest(BaseModel):
    """Request body to add a manual item to the schedule."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "day_date": "2026-07-28",
                "time_slot": "evening",
                "item_type": "restaurant",
                "title": "Le Jules Verne",
                "subtitle": "French fine dining",
                "reference_id": "1234567",
            }
        }
    )

    day_date: str
    time_slot: str       # morning | midday | evening | night
    item_type: str       # attraction | restaurant
    title: str
    subtitle: str = ""
    reference_id: str = ""


class UpdateScheduleItemRequest(BaseModel):
    """Request body to update a manual schedule item."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "day_date": "2026-07-29",
                "time_slot": "midday",
                "title": "Montmartre Walking Tour",
            }
        }
    )

    day_date: str | None = None
    time_slot: str | None = None
    title: str | None = None
    subtitle: str | None = None
    order: int | None = None

