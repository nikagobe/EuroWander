"""
Pydantic schemas for the documents module.

Optimized for Flutter frontend consumption.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.documents.domain.entities import (
    ALLOWED_CONTENT_TYPES,
    Document,
    DocumentCategory,
    DocumentVisibility,
)


class UploadUrlRequest(BaseModel):
    """Request body to obtain a presigned upload URL."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_name": "boarding_pass_paris.pdf",
                "content_type": "application/pdf",
                "size_bytes": 245_120,
                "category": "boarding_pass",
            }
        }
    )

    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(
        ...,
        description=f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
    )
    size_bytes: int = Field(..., gt=0)
    category: DocumentCategory


class UploadUrlResponse(BaseModel):
    """Presigned URL + metadata returned after requesting an upload slot."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "upload_url": "https://your-bucket.s3.eu-central-1.amazonaws.com/...",
                "file_key": "trips/abc123/f9e2a1b3c4d5/boarding_pass.pdf",
                "expires_at": "2026-06-10T15:00:00",
            }
        }
    )

    upload_url: str
    file_key: str
    expires_at: datetime


class ConfirmUploadRequest(BaseModel):
    """Request body sent after a successful direct upload to S3."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_key": "trips/abc123/f9e2a1b3c4d5/boarding_pass.pdf",
                "file_name": "boarding_pass_paris.pdf",
                "content_type": "application/pdf",
                "size_bytes": 245_120,
                "category": "boarding_pass",
                "visibility": "group",
                "name": "Paris Boarding Pass",
            }
        }
    )

    file_key: str = Field(..., min_length=1)
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(..., gt=0)
    category: DocumentCategory
    visibility: DocumentVisibility = DocumentVisibility.GROUP
    name: str = Field(
        default="",
        max_length=255,
        description="Optional display name. If empty, defaults to the category label (e.g. 'Boarding Pass').",
    )


class DocumentResponse(BaseModel):
    """Document metadata returned to the Flutter frontend."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "665f1a2b3c4d5e6f7a8b9c0d",
                "trip_id": "665e0a1b2c3d4e5f6a7b8c9d",
                "uploaded_by": "665d0a1b2c3d4e5f6a7b8c9d",
                "file_name": "boarding_pass_paris.pdf",
                "content_type": "application/pdf",
                "size_bytes": 245_120,
                "category": "boarding_pass",
                "visibility": "group",
                "name": "Paris Boarding Pass",
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
    category: DocumentCategory
    visibility: DocumentVisibility
    name: str
    created_at: datetime

    @classmethod
    def from_entity(cls, doc: Document) -> "DocumentResponse":
        return cls(
            id=doc.id,
            trip_id=doc.trip_id,
            uploaded_by=doc.uploaded_by,
            file_name=doc.file_name,
            content_type=doc.content_type,
            size_bytes=doc.size_bytes,
            category=doc.category,
            visibility=doc.visibility,
            name=doc.name,
            created_at=doc.created_at,
        )


class DownloadUrlResponse(BaseModel):
    """Presigned download URL for a specific document."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "download_url": "https://your-bucket.s3.eu-central-1.amazonaws.com/...",
                "expires_at": "2026-06-10T15:00:00",
            }
        }
    )

    download_url: str
    expires_at: datetime

