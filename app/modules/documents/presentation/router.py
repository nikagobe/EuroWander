"""
FastAPI router for trip document management.

All endpoints are scoped under /trips/{trip_id}/documents.
The backend never handles file bytes — only metadata and presigned URLs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.client import get_db
from app.modules.documents.application.services import DocumentService
from app.modules.documents.infrastructure.clients import S3StorageClient
from app.modules.documents.infrastructure.repositories import MongoDocumentRepository
from app.modules.documents.presentation.schemas import (
    ConfirmUploadRequest,
    DocumentResponse,
    DownloadUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/trips/{trip_id}/documents", tags=["documents"])


# ── Dependency factory ─────────────────────────────────────────────────────────

def get_document_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DocumentService:
    doc_repo = MongoDocumentRepository(db["documents"])
    trip_repo = MongoTripRepository(db["trips"])
    storage = S3StorageClient(
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
        bucket_name=settings.aws_s3_bucket_name,
        region=settings.aws_s3_region,
        url_expiration_seconds=settings.s3_url_expiration_seconds,
    )
    return DocumentService(repo=doc_repo, storage=storage, trip_repo=trip_repo)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/upload-url", response_model=UploadUrlResponse)
async def request_upload_url(
    trip_id: str,
    req: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> UploadUrlResponse:
    """
    Request a presigned PUT URL for direct upload to Amazon S3.

    The Flutter client should:
    1. Call this endpoint with file metadata.
    2. Use the returned `upload_url` to PUT file bytes directly to S3.
    3. Call `POST /trips/{trip_id}/documents` to confirm the upload.
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

    return UploadUrlResponse(
        upload_url=upload_url,
        file_key=file_key,
        expires_at=expires_at,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def confirm_upload(
    trip_id: str,
    req: ConfirmUploadRequest,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """
    Confirm a successful direct upload by saving document metadata.

    Call this after the file has been PUT to the presigned URL.
    """
    try:
        doc = await service.confirm_upload(
            trip_id=trip_id,
            user_id=current_user.id,
            file_key=req.file_key,
            file_name=req.file_name,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
            category=req.category,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DocumentResponse.from_entity(doc)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    """List all documents for a trip (caller must be a member)."""
    try:
        docs = await service.list_documents(trip_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return [DocumentResponse.from_entity(d) for d in docs]


@router.get("/{doc_id}/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    trip_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DownloadUrlResponse:
    """
    Get a presigned GET URL for downloading a specific document.

    The URL expires after the configured duration (default 1 hour).
    """
    try:
        download_url, expires_at = await service.get_download_url(
            trip_id=trip_id,
            user_id=current_user.id,
            doc_id=doc_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DownloadUrlResponse(download_url=download_url, expires_at=expires_at)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    trip_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> None:
    """
    Delete a document (removes file from S3 and metadata from MongoDB).

    Only the uploader or the trip master can delete.
    """
    try:
        await service.delete_document(
            trip_id=trip_id,
            user_id=current_user.id,
            doc_id=doc_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

