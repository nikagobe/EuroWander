from fastapi import HTTPException, status

from app.modules.users.application.security import hash_password, verify_password, create_access_token
from app.modules.users.domain.entities import User
from app.modules.users.domain.interfaces import UserRepository


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register(self, email: str, first_name: str, last_name: str, password: str) -> User:
        """
        Register a new user.
        - Email must be unique.
        - Password is hashed immediately; plaintext never stored.
        """
        existing = await self._repo.get_by_email(email.lower())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            email=email.lower(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            password_hash=hash_password(password),
        )
        return await self._repo.create(user)

    async def login(self, email: str, password: str) -> str:
        """
        Verify credentials and return a signed JWT access token.
        Raises 401 for any invalid combination (no leaking which field was wrong).
        """
        invalid_exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        user = await self._repo.get_by_email(email.lower())
        if user is None:
            raise invalid_exc
        if not user.is_active:
            raise invalid_exc
        if not verify_password(password, user.password_hash):
            raise invalid_exc

        return create_access_token(subject=user.id)

    async def get_current_user(self, user_id: str) -> User:
        """Fetch a user by ID; raises 401 if not found (token refers to deleted account)."""
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

