"""Schedule API endpoints — nested under /trips/{trip_id}/schedule."""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.schedule.application.services import ScheduleService
from app.modules.schedule.domain.entities import ScheduleItemType, TimeSlot
from app.modules.schedule.infrastructure.repositories import MongoScheduleRepository
from app.modules.schedule.presentation.schemas import (
    AddScheduleItemRequest,
    DayMapUrlResponse,
    FullScheduleResponse,
    ScheduleDayResponse,
    ScheduleItemResponse,
    UpdateScheduleItemRequest,
)
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/trips/{trip_id}/schedule", tags=["schedule"])


# ── Dependency factory ──────────────────────────────────────────────────────────


def get_schedule_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> ScheduleService:
    schedule_repo = MongoScheduleRepository(db["schedule_items"])
    trip_repo = MongoTripRepository(db["trips"])
    return ScheduleService(schedule_repo=schedule_repo, trip_repo=trip_repo)


# ── Endpoints ───────────────────────────────────────────────────────────────────


@router.get("", response_model=FullScheduleResponse)
async def get_trip_schedule(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> FullScheduleResponse:
    """
    Get the full trip schedule — all days from departure to return.

    Auto-items (flights, transits, hotel check-in/out) are computed from trip data.
    Manual items (attractions, restaurants) are loaded from the database.

    **Flutter flow:**
    1. Open trip detail → call this endpoint
    2. Render a day-by-day list grouped by time slots (morning/midday/evening/night)
    3. Auto items have `is_auto: true` — show them as read-only
    4. Manual items can be edited/deleted
    """
    try:
        schedule = await service.get_full_schedule(trip_id=trip_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return FullScheduleResponse(
        trip_id=schedule.trip_id,
        days=[
            ScheduleDayResponse(
                date=day.date,
                items=[_item_to_response(item) for item in day.items],
            )
            for day in schedule.days
        ],
        unscheduled=[_item_to_response(item) for item in schedule.unscheduled],
    )


@router.post("/items", response_model=ScheduleItemResponse, status_code=status.HTTP_201_CREATED)
async def add_schedule_item(
    trip_id: str,
    body: AddScheduleItemRequest,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleItemResponse:
    """
    Add an attraction or restaurant to the schedule.

    - `item_type`: Only `attraction` or `restaurant` allowed.
    - `time_slot`: One of `morning`, `midday`, `evening`, `night`.
    - `day_date`: Must be within the trip date range.
    - `reference_id`: TripAdvisor location_id (for linking back to detail pages).

    **Flutter flow:**
    1. User views attraction/restaurant detail
    2. Taps "Add to schedule"
    3. Picks a day + time slot
    4. Item appears in the schedule
    """
    try:
        time_slot = TimeSlot(body.time_slot)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_slot: '{body.time_slot}'. Must be: morning, midday, evening, night.",
        )

    try:
        item_type = ScheduleItemType(body.item_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid item_type: '{body.item_type}'. Must be: attraction, restaurant, custom.",
        )

    try:
        item = await service.add_item(
            trip_id=trip_id,
            user_id=current_user.id,
            day_date=body.day_date,
            time_slot=time_slot,
            item_type=item_type,
            title=body.title,
            subtitle=body.subtitle,
            reference_id=body.reference_id,
            note=body.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return _item_to_response(item)


@router.patch("/items/{item_id}", response_model=ScheduleItemResponse)
async def update_schedule_item(
    trip_id: str,
    item_id: str,
    body: UpdateScheduleItemRequest,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleItemResponse:
    """
    Update a manual schedule item — move to a different day/slot, rename, or reorder.

    Only attractions and restaurants can be updated. Auto-items are read-only.

    **Flutter flow:** User long-presses an item → edit modal → change day or time slot.
    """
    try:
        item = await service.update_item(
            trip_id=trip_id,
            item_id=item_id,
            user_id=current_user.id,
            day_date=body.day_date,
            time_slot=body.time_slot,
            title=body.title,
            subtitle=body.subtitle,
            note=body.note,
            order=body.order,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return _item_to_response(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_schedule_item(
    trip_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> None:
    """
    Remove a manual item from the schedule.

    Only attractions and restaurants can be removed. Auto-items cannot be deleted.

    **Flutter flow:** User swipes to delete or taps remove button.
    """
    try:
        await service.remove_item(trip_id=trip_id, item_id=item_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/day/{day_date}/map-url", response_model=DayMapUrlResponse)
async def get_day_map_url(
    trip_id: str,
    day_date: str,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> DayMapUrlResponse:
    """
    Get a Google Maps directions URL for all attractions/restaurants on a specific day.

    Opens Google Maps with waypoints ordered by time slot (morning → night).
    On mobile, this deep-links into the native Google Maps app.

    **Flutter flow:**
    1. User views a day in the schedule
    2. Taps "Show on Map" button
    3. Flutter calls this endpoint → receives `map_url`
    4. Flutter opens URL with `url_launcher` → Google Maps opens with all stops marked
    """
    try:
        map_url = await service.get_day_map_url(
            trip_id=trip_id, user_id=current_user.id, day_date=day_date
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Count stops: everything after /dir/ split by /
    path_part = map_url.split("/maps/dir/")[1].rstrip("/")
    stop_count = len(path_part.split("/")) if path_part else 0

    return DayMapUrlResponse(
        day_date=day_date,
        map_url=map_url,
        stop_count=stop_count,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _item_to_response(item) -> ScheduleItemResponse:
    return ScheduleItemResponse(
        id=item.id or "",
        day_date=item.day_date,
        time_slot=item.time_slot.value if hasattr(item.time_slot, "value") else item.time_slot,
        item_type=item.item_type.value if hasattr(item.item_type, "value") else item.item_type,
        title=item.title,
        subtitle=item.subtitle,
        reference_id=item.reference_id,
        note=getattr(item, "note", ""),
        is_auto=item.is_auto,
        order=item.order,
    )

