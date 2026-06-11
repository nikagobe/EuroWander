"""
Document domain interfaces (ABCs).

These contracts decouple application logic from infrastructure concerns.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from app.modules.documents.domain.entities import Document


class DocumentRepository(ABC):
    """Persistence contract for document metadata."""

    @abstractmethod
    async def create(self, doc: Document) -> Document: ...

    @abstractmethod
    async def list_by_trip(self, trip_id: str) -> list[Document]: ...

    @abstractmethod
    async def get_by_id(self, doc_id: str) -> Document | None: ...

    @abstractmethod
    async def delete(self, doc_id: str) -> bool: ...

    @abstractmethod
    async def count_by_trip(self, trip_id: str) -> int: ...


class StorageClient(ABC):
    """Contract for object-storage operations (presigned URLs, deletion)."""

    @abstractmethod
    async def generate_upload_url(
        self, file_key: str, content_type: str, size_bytes: int
    ) -> tuple[str, datetime]:
        """Return (presigned_put_url, expires_at)."""
        ...

    @abstractmethod
    async def generate_download_url(self, file_key: str) -> tuple[str, datetime]:
        """Return (presigned_get_url, expires_at)."""
        ...

    @abstractmethod
    async def delete_file(self, file_key: str) -> None: ...

