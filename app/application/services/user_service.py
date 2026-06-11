import uuid
from dataclasses import dataclass

from app.core.exceptions import UserNotFoundError
from app.core.security import hash_password, verify_password
from app.domain.entities.user import User
from app.domain.interfaces.user_repository import AbstractUserRepository


@dataclass
class UpdateProfileDTO:
    bio: str | None = None
    expertise: str | None = None
    website: str | None = None
    social_links: dict | None = None


class UserService:
    def __init__(self, user_repo: AbstractUserRepository):
        self.user_repo = user_repo

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        return user

    async def change_password(
        self, user_id: uuid.UUID, old_password: str, new_password: str
    ) -> None:
        user = await self.get_by_id(user_id)
        if not verify_password(old_password, user.hashed_password):
            from app.core.exceptions import InvalidCredentialsError
            raise InvalidCredentialsError("Old password is incorrect")
        user.hashed_password = hash_password(new_password)
        await self.user_repo.update(user)

    async def update_avatar(self, user_id: uuid.UUID, avatar_url: str) -> User:
        user = await self.get_by_id(user_id)
        user.avatar_url = avatar_url
        return await self.user_repo.update(user)