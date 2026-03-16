"""Authentication service – register / login."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, email: str, password: str) -> dict:
        existing = await self.repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")
        user = await self.repo.create(email, hash_password(password))
        token = create_access_token(user.id)
        return {"user_id": str(user.id), "access_token": token, "token_type": "bearer"}

    async def login(self, email: str, password: str) -> dict:
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        token = create_access_token(user.id)
        return {"user_id": str(user.id), "access_token": token, "token_type": "bearer"}
