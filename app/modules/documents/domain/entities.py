"""
Document domain entities.

A Document represents a file (boarding pass, hotel confirmation, passport, etc.)
uploaded by a trip member. The backend only stores metadata — actual file bytes
live in Amazon S3 and are accessed via presigned URLs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DocumentCategory(str, Enum):
    BOARDING_PASS = "boarding_pass"
    HOTEL_CONFIRMATION = "hotel_confirmation"
    PASSPORT = "passport"
    VISA = "visa"
    INSURANCE = "insurance"
    TICKET = "ticket"
    OTHER = "other"

    def default_display_name(self) -> str:
        """Human-readable name used when the user doesn't provide a custom name."""
        return self.value.replace("_", " ").title()


class DocumentVisibility(str, Enum):
    PRIVATE = "private"  # only the uploader can see
    GROUP = "group"      # all trip members can see


# Only these MIME types are accepted for upload.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({
    # PDF
    "application/pdf",
    # Images
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
})

# Maximum number of documents allowed per trip.
MAX_DOCUMENTS_PER_TRIP: int = 50


@dataclass
class Document:
    """Pure domain model — no MongoDB or FastAPI awareness."""

    trip_id: str
    uploaded_by: str  # user_id of the uploader
    file_name: str  # original filename chosen by user
    file_key: str  # object key in S3 bucket
    content_type: str  # MIME type (validated against whitelist)
    size_bytes: int
    category: DocumentCategory
    name: str = ""  # user-defined display name; defaults to category label
    visibility: DocumentVisibility = DocumentVisibility.GROUP
    id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

