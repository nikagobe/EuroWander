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

router = APIRouter(
    prefix="/trips/{trip_id}/documents",
    tags=["documents"],
    responses={401: {"description": "Missing or invalid Bearer token"}},
)


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

@router.post(
    "/upload-url",
    response_model=UploadUrlResponse,
    summary="Step 1: Get a presigned upload URL",
    description="""
**Integration flow (3 steps):**

1. **Call this endpoint** with file metadata (name, MIME type, size, category).
2. **PUT file bytes** directly to the returned `upload_url` with header `Content-Type: <content_type>`.
3. **Confirm the upload** by calling `POST /trips/{trip_id}/documents` with the `file_key`.

**Allowed MIME types:** `application/pdf`, `image/jpeg`, `image/png`, `image/webp`, `image/heic`, `image/heif`

**Limits:** Max 10 MB per file, max 50 documents per trip.

**Visibility:** Not set here — choose `private` or `group` when confirming in step 3.

The presigned URL expires in 1 hour. If expired, request a new one.
""",
    responses={
        400: {"description": "Invalid MIME type, file too large, or trip limit reached"},
    },
)
async def request_upload_url(
    trip_id: str,
    req: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> UploadUrlResponse:
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


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 3: Confirm upload & save metadata",
    description="""
Call this **after** the file has been successfully PUT to the presigned URL from step 1.

This saves the document metadata in the database and makes it visible in the trip.

**Visibility options:**
- `group` (default) — all trip members can see and download this document.
- `private` — only you (the uploader) can see and download it.

The `file_key` and `content_type` must match what was used in step 1.
""",
    responses={
        400: {"description": "Invalid file_key, MIME type, or access denied"},
    },
)
async def confirm_upload(
    trip_id: str,
    req: ConfirmUploadRequest,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        doc = await service.confirm_upload(
            trip_id=trip_id,
            user_id=current_user.id,
            file_key=req.file_key,
            file_name=req.file_name,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
            category=req.category,
            visibility=req.visibility,
            name=req.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DocumentResponse.from_entity(doc)


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List trip documents",
    description="""
Returns all documents for a trip that are visible to the current user.

- **group** documents: visible to all trip members.
- **private** documents: only the uploader sees their own private docs.

Results are sorted by `created_at` (newest first).
""",
    responses={
        400: {"description": "Trip not found or user is not a member"},
    },
)
async def list_documents(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    try:
        docs = await service.list_documents(trip_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return [DocumentResponse.from_entity(d) for d in docs]


@router.get(
    "/{doc_id}/download-url",
    response_model=DownloadUrlResponse,
    summary="Get a presigned download URL",
    description="""
Returns a temporary presigned GET URL to download the document directly from S3.

**Flutter usage:** Open this URL in a browser/webview or use it with an HTTP client to fetch the file bytes.

The URL expires in 1 hour. Private documents can only be downloaded by the uploader.
""",
    responses={
        400: {"description": "Document not found or access denied (private doc)"},
    },
)
async def get_download_url(
    trip_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DownloadUrlResponse:
    try:
        download_url, expires_at = await service.get_download_url(
            trip_id=trip_id,
            user_id=current_user.id,
            doc_id=doc_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DownloadUrlResponse(download_url=download_url, expires_at=expires_at)


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="""
Permanently deletes the document file from S3 and removes metadata from the database.

**Authorization:** Only the original uploader or the trip master can delete a document.

Returns `204 No Content` on success.
""",
    responses={
        400: {"description": "Document not found or trip access denied"},
        403: {"description": "User is not the uploader or trip master"},
    },
)
async def delete_document(
    trip_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> None:
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

