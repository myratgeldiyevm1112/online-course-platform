import uuid
from abc import ABC, abstractmethod

from app.domain.entities.user import User


class AbstractUserRepository(ABC):
    """Abstract repository interface — domain layer has no knowledge of SQLAlchemy."""

    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def soft_delete(self, user_id: uuid.UUID) -> None:
        ...