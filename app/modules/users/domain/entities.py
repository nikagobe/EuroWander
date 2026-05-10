from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    """
    Pure domain model — no MongoDB or FastAPI awareness.
    password_hash stores the bcrypt hash, never the plaintext password.
    """

    email: str
    first_name: str
    last_name: str
    password_hash: str
    id: str = ""                          # MongoDB _id as string
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

