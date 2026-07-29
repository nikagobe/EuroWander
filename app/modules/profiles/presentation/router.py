import logging

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.client import get_db
from app.modules.airports.infrastructure.repositories import MongoAirportRepository
from app.modules.documents.infrastructure.clients import S3StorageClient
from app.modules.profiles.application.services import ProfileService
from app.modules.profiles.infrastructure.repositories import MongoProfileRepository
from app.modules.profiles.presentation.schemas import (
    ActivityFeedResponse,
    ActivityTripSummary,
    BadgeResponse,
    CollaboratorResponse,
    FullProfileResponse,
    PhotoConfirmRequest,
    PhotoDownloadUrlResponse,
    PhotoUploadUrlRequest,
    PhotoUploadUrlResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    TravelStatsResponse,
)
from app.modules.trips.domain.entities import Trip
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

logger = logging.getLogger(__name__)

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
    # Build optional S3 storage provider (reuse the documents S3 client)
    storage: S3StorageClient | None = None
    if settings.aws_s3_bucket_name and settings.aws_access_key_id:
        storage = S3StorageClient(
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
            bucket_name=settings.aws_s3_bucket_name,
            region=settings.aws_s3_region,
            url_expiration_seconds=settings.s3_url_expiration_seconds,
        )
    return ProfileService(
        profile_repo=MongoProfileRepository(db["user_profiles"]),
        trip_repo=MongoTripRepository(db["trips"]),
        airport_repo=MongoAirportRepository(db["airports"]),
        storage=storage,
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
    profile, stats, badges, collaborators = await service.get_full_profile(current_user.id)

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
    profile, stats, badges, collaborators = await service.get_full_profile(user_id)

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


# ── Photo Upload Endpoints ────────────────────────────────────────────────────

@router.post("/me/{photo_type}/upload-url", response_model=PhotoUploadUrlResponse)
async def request_photo_upload_url(
    photo_type: str,
    req: PhotoUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PhotoUploadUrlResponse:
    """
    Request a presigned PUT URL for uploading a profile or cover photo.

    **photo_type** must be `profile` or `cover`.

    Flutter flow:
    1. Call this endpoint with file metadata.
    2. PUT image bytes to the returned `upload_url`.
    3. Call `POST /profiles/me/{photo_type}/confirm` with the `file_key`.
    """
    try:
        upload_url, file_key, expires_at = await service.request_photo_upload_url(
            user_id=current_user.id,
            photo_type=photo_type,
            file_name=req.file_name,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("[Profiles] upload-url failed for user=%s type=%s", current_user.id, photo_type)
        raise HTTPException(status_code=500, detail="Internal error generating upload URL.")

    return PhotoUploadUrlResponse(upload_url=upload_url, file_key=file_key, expires_at=expires_at)


@router.post("/me/{photo_type}/confirm", response_model=ProfileResponse)
async def confirm_photo_upload(
    photo_type: str,
    req: PhotoConfirmRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """
    Confirm that the photo was uploaded to S3 and save the key to the profile.

    **photo_type** must be `profile` or `cover`.
    """
    try:
        profile = await service.confirm_photo_upload(
            user_id=current_user.id,
            photo_type=photo_type,
            file_key=req.file_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("[Profiles] confirm failed for user=%s type=%s", current_user.id, photo_type)
        raise HTTPException(status_code=500, detail="Internal error confirming upload.")

    return ProfileResponse.from_entity(profile)


@router.get("/me/{photo_type}/download-url", response_model=PhotoDownloadUrlResponse)
async def get_photo_download_url(
    photo_type: str,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PhotoDownloadUrlResponse:
    """
    Get a presigned GET URL for the current user's profile or cover photo.

    **photo_type** must be `profile` or `cover`.
    """
    try:
        download_url, expires_at = await service.get_photo_download_url(
            user_id=current_user.id,
            photo_type=photo_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return PhotoDownloadUrlResponse(download_url=download_url, expires_at=expires_at)


@router.delete("/me/{photo_type}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_type: str,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    """
    Delete the current user's profile or cover photo from S3 and clear the URL.

    **photo_type** must be `profile` or `cover`.
    """
    try:
        await service.delete_photo(user_id=current_user.id, photo_type=photo_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
