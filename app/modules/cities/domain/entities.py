from dataclasses import dataclass


@dataclass
class City:
    """Pure domain model — no MongoDB or FastAPI awareness."""

    wikidata_id: str
    name: str
    country: str
    description: str = ""
    freebase_id: str = ""   # used as departure_id / arrival_id in SerpApi flight search
    lat: float | None = None
    lng: float | None = None
    image_filename: str | None = None   # Wikimedia Commons filename (P18)
    image_url: str | None = None        # Pre-resolved Wikimedia thumbnail URL
    banner_filename: str | None = None  # Wikimedia Commons banner (P948)
