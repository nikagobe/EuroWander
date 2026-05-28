from dataclasses import dataclass, field


@dataclass
class BusSegment:
    """One leg of a bus journey (may involve a changeover)."""

    dep_name: str           # Station name e.g. "Berlin central bus station"
    arr_name: str           # Station name e.g. "Munich central bus station"
    dep_time: str           # ISO offset string "2026-06-12T08:00:00.000"
    arr_time: str
    product_type: str       # "bus" | "train"
    product: str            # "flixbus"


@dataclass
class BusOffer:
    """
    A complete Flixbus journey offer.
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    dep_name: str           # First departure station
    arr_name: str           # Final arrival station
    dep_time: str           # ISO offset string
    arr_time: str
    duration: str           # Human-readable "07:40"
    duration_minutes: int   # Parsed total minutes
    changeovers: int
    price: float
    currency: str
    deeplink: str
    segments: list[BusSegment] = field(default_factory=list)
    additional_info: str = ""   # e.g. "1 seat left at this price"
    source: str = ""            # "flixbus" | "fake"

