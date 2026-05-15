from dataclasses import dataclass


@dataclass
class Airport:
    """Pure domain model — no MongoDB or FastAPI awareness."""

    wikidata_id: str
    name: str
    iata_code: str
    country_code: str
    lat: float | None = None
    lng: float | None = None

