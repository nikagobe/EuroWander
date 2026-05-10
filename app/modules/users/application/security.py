"""
Security helpers: password hashing (bcrypt) and JWT tokens (python-jose).
These are pure functions with no framework coupling — testable in isolation.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24      # 24 hours
ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plaintext matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """
    Create a signed JWT.
    `subject` is the user's ID (string).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Decode and verify a JWT.
    Returns the subject (user ID) or raises JWTError on invalid/expired tokens.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("Token has no subject")
    return sub

