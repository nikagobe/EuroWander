"""
Photo domain entities.

A Photo represents an image uploaded to a trip's shared gallery.
All photos are visible to every trip member — there is no private mode.
Actual file bytes live in Amazon S3; the backend stores only metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime


# Only image MIME types allowed for photos.
ALLOWED_PHOTO_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
})

# Maximum number of photos per trip.
MAX_PHOTOS_PER_TRIP: int = 200


@dataclass
class Photo:
    """Pure domain model — no MongoDB or FastAPI awareness."""

    trip_id: str
    uploaded_by: str  # user_id of the uploader
    file_name: str  # original filename
    file_key: str  # object key in S3 bucket
    content_type: str  # MIME type (validated against whitelist)
    size_bytes: int
    caption: str = ""  # optional user-provided caption
    id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

