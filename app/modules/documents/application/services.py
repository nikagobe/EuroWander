"""
Document application service.

Orchestrates upload-URL generation, metadata persistence, and deletion.
Business rules (access control, MIME validation, size limits) live here.
"""

from datetime import datetime
from uuid import uuid4

from app.modules.documents.domain.entities import (
    ALLOWED_CONTENT_TYPES,
    MAX_DOCUMENTS_PER_TRIP,
    Document,
    DocumentCategory,
)
from app.modules.documents.domain.interfaces import DocumentRepository, StorageClient
from app.modules.trips.domain.interfaces import TripRepository


class DocumentService:
    def __init__(
        self,
        repo: DocumentRepository,
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
        """Raise ValueError if the MIME type is not in the whitelist."""
        if content_type not in ALLOWED_CONTENT_TYPES:
            allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
            raise ValueError(
                f"Content type '{content_type}' is not allowed. "
                f"Accepted types: {allowed}"
            )

    @staticmethod
    def _build_file_key(trip_id: str, file_name: str) -> str:
        """Build a unique, namespaced object key for S3."""
        unique = uuid4().hex[:12]
        return f"trips/{trip_id}/{unique}/{file_name}"

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
        if count >= MAX_DOCUMENTS_PER_TRIP:
            raise ValueError(
                f"Trip already has {MAX_DOCUMENTS_PER_TRIP} documents (limit reached)."
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
        category: DocumentCategory,
    ) -> Document:
        """Persist document metadata after a successful direct upload."""
        await self._assert_trip_member(trip_id, user_id)
        self._validate_content_type(content_type)

        doc = Document(
            trip_id=trip_id,
            uploaded_by=user_id,
            file_name=file_name,
            file_key=file_key,
            content_type=content_type,
            size_bytes=size_bytes,
            category=category,
        )
        return await self._repo.create(doc)

    async def list_documents(self, trip_id: str, user_id: str) -> list[Document]:
        """Return all documents for a trip (caller must be a member)."""
        await self._assert_trip_member(trip_id, user_id)
        return await self._repo.list_by_trip(trip_id)

    async def get_download_url(
        self, trip_id: str, user_id: str, doc_id: str
    ) -> tuple[str, datetime]:
        """
        Generate a presigned GET URL for a specific document.

        Returns (download_url, expires_at).
        """
        await self._assert_trip_member(trip_id, user_id)

        doc = await self._repo.get_by_id(doc_id)
        if doc is None or doc.trip_id != trip_id:
            raise ValueError("Document not found.")

        return await self._storage.generate_download_url(doc.file_key)

    async def delete_document(
        self, trip_id: str, user_id: str, doc_id: str
    ) -> None:
        """
        Delete a document from S3 and MongoDB.

        Only the uploader or the trip master may delete.
        """
        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if trip is None:
            raise ValueError("Trip not found or access denied.")

        doc = await self._repo.get_by_id(doc_id)
        if doc is None or doc.trip_id != trip_id:
            raise ValueError("Document not found.")

        # Authorization: only the uploader or the trip master can delete
        is_master = trip.is_master(user_id)
        is_uploader = doc.uploaded_by == user_id
        if not (is_master or is_uploader):
            raise PermissionError("Only the uploader or trip master can delete this document.")

        await self._storage.delete_file(doc.file_key)
        await self._repo.delete(doc_id)

