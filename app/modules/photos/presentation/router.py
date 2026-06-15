"""
FastAPI router for trip photo gallery.

All endpoints are scoped under /trips/{trip_id}/photos.
Photos are always visible to all trip members.
The backend never handles file bytes — only metadata and presigned URLs.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.client import get_db
from app.modules.documents.infrastructure.clients import S3StorageClient
from app.modules.photos.application.services import PhotoService
from app.modules.photos.infrastructure.repositories import MongoPhotoRepository
from app.modules.photos.presentation.schemas import (
    PaginatedPhotosResponse,
    PhotoConfirmRequest,
    PhotoDownloadUrlResponse,
    PhotoResponse,
    PhotoUploadUrlRequest,
    PhotoUploadUrlResponse,
)
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trips/{trip_id}/photos", tags=["photos"])


# ── Dependency factory ─────────────────────────────────────────────────────────

def get_photo_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PhotoService:
    photo_repo = MongoPhotoRepository(db["photos"])
    trip_repo = MongoTripRepository(db["trips"])
    storage = S3StorageClient(
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
        bucket_name=settings.aws_s3_bucket_name,
        region=settings.aws_s3_region,
        url_expiration_seconds=settings.s3_url_expiration_seconds,
    )
    return PhotoService(repo=photo_repo, storage=storage, trip_repo=trip_repo)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/upload-url", response_model=PhotoUploadUrlResponse)
async def request_upload_url(
    trip_id: str,
    req: PhotoUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    service: PhotoService = Depends(get_photo_service),
) -> PhotoUploadUrlResponse:
    """
    Request a presigned PUT URL for direct photo upload to Amazon S3.

    The Flutter client should:
    1. Call this endpoint with file metadata.
    2. Use the returned `upload_url` to PUT image bytes directly to S3.
    3. Call `POST /trips/{trip_id}/photos` to confirm the upload.
    """
    try:
        upload_url, file_key, expires_at = await service.request_upload_url(
            trip_id=trip_id,
            user_id=current_user.id,
            file_name=req.file_name,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
            max_size_bytes=settings.document_max_size_bytes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("[Photos] upload-url failed for trip=%s user=%s", trip_id, current_user.id)
        raise HTTPException(status_code=500, detail="Internal error generating upload URL.")

    return PhotoUploadUrlResponse(
        upload_url=upload_url,
        file_key=file_key,
        expires_at=expires_at,
    )


@router.post("", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def confirm_upload(
    trip_id: str,
    req: PhotoConfirmRequest,
    current_user: User = Depends(get_current_user),
    service: PhotoService = Depends(get_photo_service),
) -> PhotoResponse:
    """
    Confirm a successful direct upload by saving photo metadata.

    Call this after the image has been PUT to the presigned URL.
    """
    try:
        photo = await service.confirm_upload(
            trip_id=trip_id,
            user_id=current_user.id,
            file_key=req.file_key,
            file_name=req.file_name,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
            caption=req.caption,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("[Photos] confirm_upload failed for trip=%s user=%s", trip_id, current_user.id)
        raise HTTPException(status_code=500, detail="Internal error confirming upload.")

    return PhotoResponse.from_entity(photo)


@router.get("", response_model=PaginatedPhotosResponse)
async def list_photos(
    trip_id: str,
    skip: int = Query(default=0, ge=0, description="Number of photos to skip (offset for pagination)"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of photos per page (max 50)"),
    current_user: User = Depends(get_current_user),
    service: PhotoService = Depends(get_photo_service),
) -> PaginatedPhotosResponse:
    """
    List trip photos with pagination (for grid / infinite scroll).

    **Flutter usage:** Start with `skip=0&limit=10`. When the user scrolls to the bottom,
    increment `skip` by `limit` and fetch the next page. Stop when `has_more` is `false`.

    Photos are sorted by `created_at` (newest first). All trip members can see all photos.
    """
    try:
        photos, total = await service.list_photos_paginated(
            trip_id, current_user.id, skip=skip, limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    items = [PhotoResponse.from_entity(p) for p in photos]
    return PaginatedPhotosResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


@router.get("/{photo_id}/download-url", response_model=PhotoDownloadUrlResponse)
async def get_download_url(
    trip_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    service: PhotoService = Depends(get_photo_service),
) -> PhotoDownloadUrlResponse:
    """
    Get a presigned GET URL for downloading a specific photo.

    The URL expires after the configured duration (default 1 hour).
    """
    try:
        download_url, expires_at = await service.get_download_url(
            trip_id=trip_id,
            user_id=current_user.id,
            photo_id=photo_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return PhotoDownloadUrlResponse(download_url=download_url, expires_at=expires_at)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    trip_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    service: PhotoService = Depends(get_photo_service),
) -> None:
    """
    Delete a photo (removes file from S3 and metadata from MongoDB).

    Only the uploader or the trip master can delete.
    """
    try:
        await service.delete_photo(
            trip_id=trip_id,
            user_id=current_user.id,
            photo_id=photo_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

