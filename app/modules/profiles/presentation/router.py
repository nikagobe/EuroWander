
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.airports.infrastructure.repositories import MongoAirportRepository
from app.modules.profiles.application.services import ProfileService
from app.modules.profiles.infrastructure.repositories import MongoProfileRepository
from app.modules.profiles.presentation.schemas import (
    ActivityFeedResponse,
    ActivityTripSummary,
    BadgeResponse,
    CollaboratorResponse,
    FullProfileResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    TravelStatsResponse,
)
from app.modules.trips.domain.entities import Trip
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/profiles", tags=["profiles"])


# ── Badge label map ───────────────────────────────────────────────────────────

_BADGE_LABELS: dict[str, str] = {
    "first_trip": "First Trip",
    "countries_5": "5 Countries",
    "countries_10": "10 Countries",
    "countries_20": "20 Countries",
    "frequent_flyer": "Frequent Flyer",
    "bus_explorer": "Bus Explorer",
    "planner_pro": "Planner Pro",
    "collaborator": "Collaborator",
}


# ── Dependency ────────────────────────────────────────────────────────────────

def get_profile_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ProfileService:
    return ProfileService(
        profile_repo=MongoProfileRepository(db["user_profiles"]),
        trip_repo=MongoTripRepository(db["trips"]),
        airport_repo=MongoAirportRepository(db["airports"]),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trip_summary(trip: Trip) -> ActivityTripSummary:
    """Map a Trip entity to a lightweight feed summary."""
    # Use first outbound arrival airport name as destination
    destination = ""
    if trip.outbound_flight and trip.outbound_flight.legs:
        destination = trip.outbound_flight.legs[-1].arrival_airport_name
    return ActivityTripSummary(
        trip_id=trip.id,
        name=trip.name or destination or "Unnamed Trip",
        status=trip.status.value,
        destination=destination,
        created_at=trip.created_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/me", response_model=FullProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> FullProfileResponse:
    """Full profile overview: personalization + stats + badges + collaborators."""
    profile = await service.get_profile(current_user.id)
    stats = await service.get_stats(current_user.id)
    badges = await service.get_badges(current_user.id)
    collaborators = await service.get_collaborators(current_user.id)

    return FullProfileResponse(
        profile=ProfileResponse.from_entity(profile),
        stats=TravelStatsResponse(
            trips_completed=stats.trips_completed,
            cities_visited=stats.cities_visited,
            total_distance_km=stats.total_distance_km,
            favorite_destination=stats.favorite_destination,
        ),
        badges=[
            BadgeResponse(badge=b.value, label=_BADGE_LABELS.get(b.value, b.value))
            for b in badges
        ],
        collaborators=[
            CollaboratorResponse(
                user_id=c.user_id,
                first_name=c.first_name,
                last_name=c.last_name,
                profile_photo_url=c.profile_photo_url,
                shared_trip_count=c.shared_trip_count,
            )
            for c in collaborators
        ],
    )


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """Update personalization fields (bio, photos, tags, etc.)."""
    profile = await service.update_profile(
        current_user.id,
        bio=req.bio,
        home_city=req.home_city,
        base_airport=req.base_airport,
        profile_photo_url=req.profile_photo_url,
        cover_photo_url=req.cover_photo_url,
        preferred_languages=req.preferred_languages,
        travel_style_tags=req.travel_style_tags,
    )
    return ProfileResponse.from_entity(profile)


@router.get("/me/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ActivityFeedResponse:
    """Recent completed trips and upcoming trips."""
    feed = await service.get_activity_feed(current_user.id)
    return ActivityFeedResponse(
        recent_completed=[_trip_summary(t) for t in feed["recent_completed"]],
        upcoming=[_trip_summary(t) for t in feed["upcoming"]],
    )


@router.get("/{user_id}", response_model=FullProfileResponse)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> FullProfileResponse:
    """View another user's public profile."""
    profile = await service.get_profile(user_id)
    stats = await service.get_stats(user_id)
    badges = await service.get_badges(user_id)
    collaborators = await service.get_collaborators(user_id)

    return FullProfileResponse(
        profile=ProfileResponse.from_entity(profile),
        stats=TravelStatsResponse(
            trips_completed=stats.trips_completed,
            cities_visited=stats.cities_visited,
            total_distance_km=stats.total_distance_km,
            favorite_destination=stats.favorite_destination,
        ),
        badges=[
            BadgeResponse(badge=b.value, label=_BADGE_LABELS.get(b.value, b.value))
            for b in badges
        ],
        collaborators=[
            CollaboratorResponse(
                user_id=c.user_id,
                first_name=c.first_name,
                last_name=c.last_name,
                profile_photo_url=c.profile_photo_url,
                shared_trip_count=c.shared_trip_count,
            )
            for c in collaborators
        ],
    )

