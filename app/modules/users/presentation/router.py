from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.users.application.security import decode_access_token
from app.modules.users.application.services import UserService
from app.modules.users.domain.entities import User
from app.modules.users.infrastructure.repositories import MongoUserRepository
from app.modules.users.presentation.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])
_bearer = HTTPBearer()


# ── Dependency factories ──────────────────────────────────────────────────────

def get_user_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> UserService:
    repo = MongoUserRepository(db["users"])
    return UserService(repo)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    service: UserService = Depends(get_user_service),
) -> User:
    """
    Reusable dependency: validates the Bearer JWT and returns the authenticated User.
    Use with `Depends(get_current_user)` on any protected endpoint.
    """
    try:
        user_id = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await service.get_current_user(user_id)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Create a new account. Email must be unique."""
    user = await service.register(
        email=req.email,
        first_name=req.first_name,
        last_name=req.last_name,
        password=req.password,
    )
    return UserResponse.from_entity(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    service: UserService = Depends(get_user_service),
) -> TokenResponse:
    """Authenticate with email + password and receive a JWT Bearer token."""
    token = await service.login(email=req.email, password=req.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.from_entity(current_user)

