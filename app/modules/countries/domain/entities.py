from dataclasses import dataclass, field


@dataclass
class MajorCity:
    """Lightweight city snapshot embedded in a Country document."""
    name: str
    wikidata_id: str
    freebase_id: str
    description: str = ""


@dataclass
class Country:
    """Pure domain model — no MongoDB or FastAPI awareness."""
    name: str
    neighbors: list[str] = field(default_factory=list)
    major_cities: list[MajorCity] = field(default_factory=list)

