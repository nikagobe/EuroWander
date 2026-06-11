"""
Pydantic schemas for the photos module.

Optimized for Flutter frontend consumption.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.photos.domain.entities import ALLOWED_PHOTO_TYPES, Photo


class PhotoUploadUrlRequest(BaseModel):
    """Request body to obtain a presigned upload URL for a photo."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_name": "sunset_paris.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 3_500_000,
            }
        }
    )

    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(
        ...,
        description=f"Allowed types: {', '.join(sorted(ALLOWED_PHOTO_TYPES))}",
    )
    size_bytes: int = Field(..., gt=0)


class PhotoUploadUrlResponse(BaseModel):
    """Presigned URL + metadata returned after requesting a photo upload slot."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "upload_url": "https://your-bucket.s3.eu-north-1.amazonaws.com/...",
                "file_key": "trips/abc123/photos/f9e2a1b3c4d5/sunset.jpg",
                "expires_at": "2026-06-10T15:00:00",
            }
        }
    )

    upload_url: str
    file_key: str
    expires_at: datetime


class PhotoConfirmRequest(BaseModel):
    """Request body sent after a successful direct upload to S3."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_key": "trips/abc123/photos/f9e2a1b3c4d5/sunset.jpg",
                "file_name": "sunset_paris.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 3_500_000,
                "caption": "Beautiful sunset from Eiffel Tower",
            }
        }
    )

    file_key: str = Field(..., min_length=1)
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(..., gt=0)
    caption: str = Field(default="", max_length=500)


class PhotoResponse(BaseModel):
    """Photo metadata returned to the Flutter frontend."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "665f1a2b3c4d5e6f7a8b9c0d",
                "trip_id": "665e0a1b2c3d4e5f6a7b8c9d",
                "uploaded_by": "665d0a1b2c3d4e5f6a7b8c9d",
                "file_name": "sunset_paris.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 3_500_000,
                "caption": "Beautiful sunset from Eiffel Tower",
                "created_at": "2026-06-10T12:30:00",
            }
        }
    )

    id: str
    trip_id: str
    uploaded_by: str
    file_name: str
    content_type: str
    size_bytes: int
    caption: str
    created_at: datetime

    @classmethod
    def from_entity(cls, photo: Photo) -> "PhotoResponse":
        return cls(
            id=photo.id,
            trip_id=photo.trip_id,
            uploaded_by=photo.uploaded_by,
            file_name=photo.file_name,
            content_type=photo.content_type,
            size_bytes=photo.size_bytes,
            caption=photo.caption,
            created_at=photo.created_at,
        )


class PhotoDownloadUrlResponse(BaseModel):
    """Presigned download URL for a specific photo."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "download_url": "https://your-bucket.s3.eu-north-1.amazonaws.com/...",
                "expires_at": "2026-06-10T15:00:00",
            }
        }
    )

    download_url: str
    expires_at: datetime


class PaginatedPhotosResponse(BaseModel):
    """Paginated list of photos for infinite scroll / grid view."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "665f1a2b3c4d5e6f7a8b9c0d",
                        "trip_id": "665e0a1b2c3d4e5f6a7b8c9d",
                        "uploaded_by": "665d0a1b2c3d4e5f6a7b8c9d",
                        "file_name": "sunset_paris.jpg",
                        "content_type": "image/jpeg",
                        "size_bytes": 3_500_000,
                        "caption": "Beautiful sunset from Eiffel Tower",
                        "created_at": "2026-06-10T12:30:00",
                    }
                ],
                "total": 42,
                "skip": 0,
                "limit": 10,
                "has_more": True,
            }
        }
    )

    items: list[PhotoResponse]
    total: int = Field(..., description="Total number of photos in this trip")
    skip: int = Field(..., description="Number of items skipped (offset)")
    limit: int = Field(..., description="Page size used for this request")
    has_more: bool = Field(..., description="True if more photos exist beyond this page")


