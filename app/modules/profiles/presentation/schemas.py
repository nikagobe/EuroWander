from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.profiles.domain.entities import UserProfile


# ── Requests ──────────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bio": "Exploring every corner of Europe",
                "home_city": "Tbilisi",
                "base_airport": "TBS",
                "preferred_languages": ["en", "ka"],
                "travel_style_tags": ["backpacker", "foodie"],
            }
        }
    )

    bio: str | None = None
    home_city: str | None = None
    base_airport: str | None = None
    profile_photo_url: str | None = None
    cover_photo_url: str | None = None
    preferred_languages: list[str] | None = None
    travel_style_tags: list[str] | None = None


# ── Responses ─────────────────────────────────────────────────────────────────

class ProfileResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "664abc123def456",
                "bio": "Exploring every corner of Europe",
                "home_city": "Tbilisi",
                "base_airport": "TBS",
                "profile_photo_url": "https://s3.amazonaws.com/eurowander/photo.jpg",
                "cover_photo_url": "",
                "preferred_languages": ["en", "ka"],
                "travel_style_tags": ["backpacker", "foodie"],
            }
        }
    )

    user_id: str
    bio: str
    home_city: str
    base_airport: str
    profile_photo_url: str
    cover_photo_url: str
    preferred_languages: list[str]
    travel_style_tags: list[str]
    updated_at: datetime

    @classmethod
    def from_entity(cls, p: UserProfile) -> "ProfileResponse":
        return cls(
            user_id=p.user_id,
            bio=p.bio,
            home_city=p.home_city,
            base_airport=p.base_airport,
            profile_photo_url=p.profile_photo_url,
            cover_photo_url=p.cover_photo_url,
            preferred_languages=p.preferred_languages,
            travel_style_tags=p.travel_style_tags,
            updated_at=p.updated_at,
        )


class TravelStatsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trips_completed": 7,
                "cities_visited": ["Paris CDG", "Berlin BER", "Rome FCO"],
                "total_distance_km": 4320.5,
                "favorite_destination": "Paris CDG",
            }
        }
    )

    trips_completed: int
    cities_visited: list[str]
    total_distance_km: float
    favorite_destination: str


class BadgeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"badge": "first_trip", "label": "First Trip"}
        }
    )

    badge: str
    label: str


class CollaboratorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "664abc123def456",
                "first_name": "Jane",
                "last_name": "Doe",
                "profile_photo_url": "",
                "shared_trip_count": 3,
            }
        }
    )

    user_id: str
    first_name: str
    last_name: str
    profile_photo_url: str
    shared_trip_count: int


class ActivityTripSummary(BaseModel):
    """Lightweight trip representation for the activity feed."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": "664abc123def456",
                "name": "Berlin Weekend",
                "status": "completed",
                "destination": "Berlin BER",
                "created_at": "2026-06-15T12:00:00",
            }
        }
    )

    trip_id: str
    name: str
    status: str
    destination: str
    created_at: datetime


class ActivityFeedResponse(BaseModel):
    recent_completed: list[ActivityTripSummary]
    upcoming: list[ActivityTripSummary]


class FullProfileResponse(BaseModel):
    """Aggregate response for GET /profiles/me — everything in one call."""
    profile: ProfileResponse
    stats: TravelStatsResponse
    badges: list[BadgeResponse]
    collaborators: list[CollaboratorResponse]


# ── Photo Upload Schemas ──────────────────────────────────────────────────────

class PhotoUploadUrlRequest(BaseModel):
    """Request a presigned upload URL for profile or cover photo."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_name": "avatar.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 245000,
            }
        }
    )

    file_name: str
    content_type: str
    size_bytes: int


class PhotoUploadUrlResponse(BaseModel):
    """Presigned S3 PUT URL for the Flutter client to upload directly."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "upload_url": "https://s3.eu-central-1.amazonaws.com/eurowander/profiles/...",
                "file_key": "profiles/664abc/profile_a1b2c3d4e5f6.jpg",
                "expires_at": "2026-07-28T14:00:00",
            }
        }
    )

    upload_url: str
    file_key: str
    expires_at: datetime


class PhotoConfirmRequest(BaseModel):
    """Confirm that the photo was uploaded to S3 successfully."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_key": "profiles/664abc/profile_a1b2c3d4e5f6.jpg",
            }
        }
    )

    file_key: str


class PhotoDownloadUrlResponse(BaseModel):
    """Presigned GET URL to view the photo."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "download_url": "https://s3.eu-central-1.amazonaws.com/eurowander/profiles/...",
                "expires_at": "2026-07-28T14:00:00",
            }
        }
    )

    download_url: str
    expires_at: datetime
