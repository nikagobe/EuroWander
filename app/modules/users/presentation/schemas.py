from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.modules.users.domain.entities import User


# ── Requests ─────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "password": "Str0ng!Pass",
            }
        }
    )

    email: EmailStr
    first_name: str
    last_name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "jane@example.com", "password": "Str0ng!Pass"}
        }
    )

    email: EmailStr
    password: str


# ── Responses ────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned on successful login."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user profile — never exposes password_hash."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "664abc123def456",
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "is_active": True,
                "created_at": "2026-05-10T09:00:00",
            }
        }
    )

    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )

