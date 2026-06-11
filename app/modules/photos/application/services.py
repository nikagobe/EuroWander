"""
Photo application service.

Orchestrates upload-URL generation, metadata persistence, and deletion.
All photos in a trip are visible to every member (no privacy toggle).
"""

from datetime import datetime
from uuid import uuid4

from app.modules.documents.domain.interfaces import StorageClient
from app.modules.photos.domain.entities import (
    ALLOWED_PHOTO_TYPES,
    MAX_PHOTOS_PER_TRIP,
    Photo,
)
from app.modules.photos.domain.interfaces import PhotoRepository
from app.modules.trips.domain.interfaces import TripRepository


class PhotoService:
    def __init__(
        self,
        repo: PhotoRepository,
        storage: StorageClient,
        trip_repo: TripRepository,
    ) -> None:
        self._repo = repo
        self._storage = storage
        self._trip_repo = trip_repo

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _assert_trip_member(self, trip_id: str, user_id: str) -> None:
        """Raise ValueError if user is not a member/owner of the trip."""
        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if trip is None:
            raise ValueError("Trip not found or access denied.")

    @staticmethod
    def _validate_content_type(content_type: str) -> None:
        """Raise ValueError if the MIME type is not an allowed image type."""
        if content_type not in ALLOWED_PHOTO_TYPES:
            allowed = ", ".join(sorted(ALLOWED_PHOTO_TYPES))
            raise ValueError(
                f"Content type '{content_type}' is not allowed for photos. "
                f"Accepted types: {allowed}"
            )

    @staticmethod
    def _build_file_key(trip_id: str, file_name: str) -> str:
        """Build a unique, namespaced object key for S3."""
        unique = uuid4().hex[:12]
        return f"trips/{trip_id}/photos/{unique}/{file_name}"

    # ── Use Cases ──────────────────────────────────────────────────────────────

    async def request_upload_url(
        self,
        trip_id: str,
        user_id: str,
        file_name: str,
        content_type: str,
        size_bytes: int,
        max_size_bytes: int,
    ) -> tuple[str, str, datetime]:
        """
        Validate constraints and generate a presigned PUT URL.

        Returns (upload_url, file_key, expires_at).
        """
        await self._assert_trip_member(trip_id, user_id)
        self._validate_content_type(content_type)

        if size_bytes <= 0:
            raise ValueError("File size must be greater than zero.")
        if size_bytes > max_size_bytes:
            max_mb = max_size_bytes / (1024 * 1024)
            raise ValueError(f"File exceeds maximum allowed size ({max_mb:.0f} MB).")

        count = await self._repo.count_by_trip(trip_id)
        if count >= MAX_PHOTOS_PER_TRIP:
            raise ValueError(
                f"Trip already has {MAX_PHOTOS_PER_TRIP} photos (limit reached)."
            )

        file_key = self._build_file_key(trip_id, file_name)
        upload_url, expires_at = await self._storage.generate_upload_url(
            file_key, content_type, size_bytes
        )
        return upload_url, file_key, expires_at

    async def confirm_upload(
        self,
        trip_id: str,
        user_id: str,
        file_key: str,
        file_name: str,
        content_type: str,
        size_bytes: int,
        caption: str = "",
    ) -> Photo:
        """Persist photo metadata after a successful direct upload."""
        await self._assert_trip_member(trip_id, user_id)
        self._validate_content_type(content_type)

        photo = Photo(
            trip_id=trip_id,
            uploaded_by=user_id,
            file_name=file_name,
            file_key=file_key,
            content_type=content_type,
            size_bytes=size_bytes,
            caption=caption,
        )
        return await self._repo.create(photo)

    async def list_photos(self, trip_id: str, user_id: str) -> list[Photo]:
        """Return all photos for a trip (all members can see all photos)."""
        await self._assert_trip_member(trip_id, user_id)
        return await self._repo.list_by_trip(trip_id)

    async def list_photos_paginated(
        self, trip_id: str, user_id: str, skip: int = 0, limit: int = 10
    ) -> tuple[list[Photo], int]:
        """
        Return a paginated page of photos for a trip.

        Returns (photos, total_count) so the frontend knows if more pages exist.
        """
        await self._assert_trip_member(trip_id, user_id)
        photos = await self._repo.list_by_trip_paginated(trip_id, skip, limit)
        total = await self._repo.count_by_trip(trip_id)
        return photos, total

    async def get_download_url(
        self, trip_id: str, user_id: str, photo_id: str
    ) -> tuple[str, datetime]:
        """
        Generate a presigned GET URL for a specific photo.

        Returns (download_url, expires_at).
        """
        await self._assert_trip_member(trip_id, user_id)

        photo = await self._repo.get_by_id(photo_id)
        if photo is None or photo.trip_id != trip_id:
            raise ValueError("Photo not found.")

        return await self._storage.generate_download_url(photo.file_key)

    async def delete_photo(
        self, trip_id: str, user_id: str, photo_id: str
    ) -> None:
        """
        Delete a photo from S3 and MongoDB.

        Only the uploader or the trip master may delete.
        """
        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if trip is None:
            raise ValueError("Trip not found or access denied.")

        photo = await self._repo.get_by_id(photo_id)
        if photo is None or photo.trip_id != trip_id:
            raise ValueError("Photo not found.")

        is_master = trip.is_master(user_id)
        is_uploader = photo.uploaded_by == user_id
        if not (is_master or is_uploader):
            raise PermissionError("Only the uploader or trip master can delete this photo.")

        await self._storage.delete_file(photo.file_key)
        await self._repo.delete(photo_id)

