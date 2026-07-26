"""FastAPI router for Trip Templates."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.templates.application.fork_service import ForkService
from app.modules.templates.application.services import TemplateService
from app.modules.templates.domain.entities import (
    HotelPick,
    HotelRecommendations,
    TemplateLeg,
)
from app.modules.templates.infrastructure.repositories import MongoTemplateRepository
from app.modules.templates.presentation.schemas import (
    CreateTemplateRequest,
    ForkCreateTripRequest,
    TemplateListItem,
    TemplateResponse,
    UpdateTemplateRequest,
)
from app.modules.playlists.infrastructure.repositories import MongoPlaylistRepository
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.trips.domain.entities import (
    SavedBusJourney,
    SavedBusSegment,
    SavedFlight,
    SavedFlightLeg,
    SavedHotel,
)
from app.modules.trips.presentation.schemas import TripResponse
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/templates", tags=["templates"])


def get_template_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TemplateService:
    repo = MongoTemplateRepository(db["trip_templates"])
    return TemplateService(repo)


def get_fork_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> ForkService:
    template_repo = MongoTemplateRepository(db["trip_templates"])
    trip_repo = MongoTripRepository(db["trips"])
    playlist_repo = MongoPlaylistRepository(db["playlists"])
    return ForkService(template_repo, trip_repo, playlist_repo)


# ─── Helpers ──────────────────────────────────────────────────────────

def _schema_leg_to_domain(leg_input) -> TemplateLeg:
    """Convert a TemplateLegInput schema to domain entity."""
    hr = None
    if leg_input.hotel_recommendations:
        hr_in = leg_input.hotel_recommendations
        picks = [HotelPick(**p.model_dump()) for p in hr_in.primary_picks]
        hr = HotelRecommendations(
            city=hr_in.city,
            country=hr_in.country,
            primary_picks=picks,
            fallback_neighborhood=hr_in.fallback_neighborhood,
            fallback_star_min=hr_in.fallback_star_min,
            fallback_star_max=hr_in.fallback_star_max,
            fallback_budget_per_night_min=hr_in.fallback_budget_per_night_min,
            fallback_budget_per_night_max=hr_in.fallback_budget_per_night_max,
        )

    return TemplateLeg(
        order=leg_input.order,
        city=leg_input.city,
        country=leg_input.country,
        days=leg_input.days,
        hotel_recommendations=hr,
        playlist_id=leg_input.playlist_id,
        restaurant_ids=leg_input.restaurant_ids,
        author_notes=leg_input.author_notes,
    )


def _template_to_response(t) -> TemplateResponse:
    """Map domain TripTemplate to TemplateResponse."""
    legs = []
    for leg in t.legs:
        hr_resp = None
        if leg.hotel_recommendations:
            hr = leg.hotel_recommendations
            hr_resp = {
                "city": hr.city,
                "country": hr.country,
                "primary_picks": [asdict(p) for p in hr.primary_picks],
                "fallback_neighborhood": hr.fallback_neighborhood,
                "fallback_star_min": hr.fallback_star_min,
                "fallback_star_max": hr.fallback_star_max,
                "fallback_budget_per_night_min": hr.fallback_budget_per_night_min,
                "fallback_budget_per_night_max": hr.fallback_budget_per_night_max,
            }
        legs.append({
            "order": leg.order,
            "city": leg.city,
            "country": leg.country,
            "days": leg.days,
            "hotel_recommendations": hr_resp,
            "playlist_id": leg.playlist_id,
            "restaurant_ids": leg.restaurant_ids,
            "author_notes": leg.author_notes,
        })

    return TemplateResponse(
        id=t.id,
        author_id=t.author_id,
        title=t.title,
        description=t.description,
        legs=legs,
        tags=t.tags,
        cover_photo_url=t.cover_photo_url,
        estimated_budget_min=t.estimated_budget_min,
        estimated_budget_max=t.estimated_budget_max,
        currency=t.currency,
        total_days=t.total_days,
        status=t.status.value,
        fork_count=t.fork_count,
        like_count=t.like_count,
        created_at=t.created_at.isoformat() if t.created_at else "",
        updated_at=t.updated_at.isoformat() if t.updated_at else "",
    )


def _template_to_list_item(t) -> TemplateListItem:
    return TemplateListItem(
        id=t.id,
        author_id=t.author_id,
        title=t.title,
        description=t.description,
        tags=t.tags,
        cover_photo_url=t.cover_photo_url,
        total_days=t.total_days,
        estimated_budget_min=t.estimated_budget_min,
        estimated_budget_max=t.estimated_budget_max,
        currency=t.currency,
        fork_count=t.fork_count,
        like_count=t.like_count,
        status=t.status.value,
        leg_cities=[leg.city for leg in t.legs],
    )


# ─── Endpoints ────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(
    req: CreateTemplateRequest,
    service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    legs = [_schema_leg_to_domain(leg) for leg in req.legs]
    template = await service.create_template(
        author_id=req.author_id,
        title=req.title,
        description=req.description,
        legs=legs,
        tags=req.tags,
        cover_photo_url=req.cover_photo_url,
        estimated_budget_min=req.estimated_budget_min,
        estimated_budget_max=req.estimated_budget_max,
        currency=req.currency,
    )
    return _template_to_response(template)


@router.get("")
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tags: str | None = Query(None, description="Comma-separated tags"),
    destination: str | None = Query(None),
    sort_by: str = Query("newest", regex="^(newest|most_forked|most_liked)$"),
    service: TemplateService = Depends(get_template_service),
) -> list[TemplateListItem]:
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    templates = await service.list_published(skip, limit, tag_list, destination, sort_by)
    return [_template_to_list_item(t) for t in templates]


@router.get("/mine")
async def list_my_templates(
    author_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: TemplateService = Depends(get_template_service),
) -> list[TemplateListItem]:
    templates = await service.list_my_templates(author_id, skip, limit)
    return [_template_to_list_item(t) for t in templates]


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    template = await service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_response(template)


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    req: UpdateTemplateRequest,
    user_id: str = Query(...),
    service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    fields: dict = {}
    if req.title is not None:
        fields["title"] = req.title
    if req.description is not None:
        fields["description"] = req.description
    if req.tags is not None:
        fields["tags"] = req.tags
    if req.cover_photo_url is not None:
        fields["cover_photo_url"] = req.cover_photo_url
    if req.estimated_budget_min is not None:
        fields["estimated_budget_min"] = req.estimated_budget_min
    if req.estimated_budget_max is not None:
        fields["estimated_budget_max"] = req.estimated_budget_max
    if req.currency is not None:
        fields["currency"] = req.currency
    if req.legs is not None:
        fields["legs"] = [_schema_leg_to_domain(leg) for leg in req.legs]

    template = await service.update_template(template_id, user_id, **fields)
    if template is None:
        raise HTTPException(status_code=400, detail="Cannot update template (not found or not author)")
    return _template_to_response(template)


@router.patch("/{template_id}/publish")
async def publish_template(
    template_id: str,
    user_id: str = Query(...),
    service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    template = await service.publish(template_id, user_id)
    if template is None:
        raise HTTPException(status_code=400, detail="Cannot publish (not found, not author, or incomplete)")
    return _template_to_response(template)


@router.patch("/{template_id}/unpublish")
async def unpublish_template(
    template_id: str,
    user_id: str = Query(...),
    service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    template = await service.unpublish(template_id, user_id)
    if template is None:
        raise HTTPException(status_code=400, detail="Cannot unpublish (not found or not author)")
    return _template_to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    user_id: str = Query(...),
    service: TemplateService = Depends(get_template_service),
) -> None:
    deleted = await service.delete_template(template_id, user_id)
    if not deleted:
        raise HTTPException(status_code=400, detail="Cannot delete (not found or not author)")


@router.post("/{template_id}/like")
async def toggle_like(
    template_id: str,
    user_id: str = Query(...),
    service: TemplateService = Depends(get_template_service),
) -> dict:
    template = await service.toggle_like(template_id, user_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found or not published")
    return {"like_count": template.like_count, "liked": user_id in template.liked_by}


@router.get("/{template_id}/fork-guide")
async def get_fork_guide(
    template_id: str,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    service: TemplateService = Depends(get_template_service),
) -> dict:
    guide = await service.generate_fork_guide(template_id, start_date)
    if guide is None:
        raise HTTPException(status_code=404, detail="Template not found or not published")
    return guide


@router.post("/{template_id}/fork")
async def fork_template(
    template_id: str,
    user_id: str = Query(...),
    service: TemplateService = Depends(get_template_service),
) -> dict:
    """Registers a fork (increments count). Client then creates a Trip using fork-guide data."""
    result = await service.fork_template(template_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found or not published")
    return {"template_id": result, "message": "Fork registered. Use fork-guide to build your trip."}


@router.post(
    "/{template_id}/fork/create-trip",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trip_from_template(
    template_id: str,
    req: ForkCreateTripRequest,
    current_user: User = Depends(get_current_user),
    fork_service: ForkService = Depends(get_fork_service),
) -> TripResponse:
    """
    Create a full Trip from a published template.

    Copies attractions & restaurants from template playlists,
    assigns concrete dates based on start_date, saves the selected
    flights/hotels/buses, and increments the template's fork count.
    """
    # Validate start_date format
    try:
        from datetime import datetime
        datetime.strptime(req.start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be in YYYY-MM-DD format.",
        )

    # Convert outbound flight input to SavedFlight
    outbound_flight = _fork_flight_to_saved(req.outbound_flight)

    # Convert return flight
    return_flight: SavedFlight | None = None
    if req.return_flight:
        return_flight = _fork_flight_to_saved(req.return_flight)

    # Convert hotels
    hotels = [
        SavedHotel(
            hotel_id=h.hotel_id,
            name=h.name,
            city=h.city,
            address=h.address,
            latitude=h.latitude,
            longitude=h.longitude,
            photo_url=h.photo_url,
            stars=h.stars,
            review_score=h.review_score,
            review_score_word=h.review_score_word,
            checkin_date=h.checkin_date,
            checkout_date=h.checkout_date,
            price_per_night=h.price_per_night,
            price_total=h.price_total,
            currency=h.currency,
            booking_url=h.booking_url,
        )
        for h in req.hotels
    ]

    # Convert buses
    buses = [_fork_bus_to_saved(b) for b in req.buses]

    trip = await fork_service.create_trip_from_template(
        template_id=template_id,
        user_id=current_user.id,
        user_first_name=current_user.first_name,
        user_last_name=current_user.last_name,
        name=req.name,
        start_date=req.start_date,
        outbound_flight=outbound_flight,
        return_flight=return_flight,
        hotels=hotels,
        buses=buses,
    )

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found, not published, or has no content to fork.",
        )

    return TripResponse.from_entity(trip)


def _fork_flight_to_saved(inp) -> SavedFlight:
    """Convert a ForkFlightInput into a SavedFlight domain entity."""
    import re

    legs = [
        SavedFlightLeg(
            flight_number=leg.flight_number,
            airline=leg.airline,
            airline_logo=leg.airline_logo,
            airplane="",
            departure_airport=leg.departure_airport,
            departure_airport_name=leg.departure_airport_name,
            arrival_airport=leg.arrival_airport,
            arrival_airport_name=leg.arrival_airport_name,
            departure_time=leg.departure_time,
            arrival_time=leg.arrival_time,
            duration_minutes=leg.duration_minutes,
            travel_class="Economy",
            legroom="",
            is_overnight=False,
        )
        for leg in inp.legs
    ]

    # Build flight_id
    flight_id = ""
    if inp.legs:
        first = inp.legs[0]
        last = inp.legs[-1]
        date_slug = re.sub(r"\D", "", first.departure_time.split("T")[0])[:8]
        fn_slug = re.sub(r"\s+", "", first.flight_number).upper()
        flight_id = f"{first.departure_airport}-{last.arrival_airport}-{date_slug}-{fn_slug}"

    return SavedFlight(
        flight_id=flight_id,
        price=inp.price,
        currency=inp.currency,
        total_duration_minutes=inp.total_duration_minutes,
        stops=inp.stops,
        airline_logo=inp.airline_logo,
        booking_token=inp.booking_token,
        legs=legs,
    )


def _fork_bus_to_saved(inp) -> SavedBusJourney:
    """Convert a ForkBusInput into a SavedBusJourney domain entity."""
    import re

    segments = [
        SavedBusSegment(
            dep_name=s.dep_name,
            arr_name=s.arr_name,
            dep_time=s.dep_time,
            arr_time=s.arr_time,
            product_type=s.product_type,
            product=s.product,
        )
        for s in inp.segments
    ]

    dep_slug = re.sub(r"\s+", "_", inp.dep_name.lower())[:20]
    arr_slug = re.sub(r"\s+", "_", inp.arr_name.lower())[:20]
    date_slug = re.sub(r"\D", "", inp.dep_time.split("T")[0])[:8]
    journey_id = f"{dep_slug}-{arr_slug}-{date_slug}"

    # Calculate duration string from minutes
    hours = inp.duration_minutes // 60
    minutes = inp.duration_minutes % 60
    duration_str = f"{hours:02d}:{minutes:02d}"

    return SavedBusJourney(
        journey_id=journey_id,
        dep_name=inp.dep_name,
        arr_name=inp.arr_name,
        dep_time=inp.dep_time,
        arr_time=inp.arr_time,
        duration=duration_str,
        duration_minutes=inp.duration_minutes,
        changeovers=inp.changeovers,
        price=inp.price,
        currency=inp.currency,
        deeplink=inp.deeplink,
        additional_info="",
        segments=segments,
    )
