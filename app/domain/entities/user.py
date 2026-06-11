import uuid
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class User:
    """Pure domain entity — no SQLAlchemy, no FastAPI dependencies."""

    def __init__(
        self,
        id: uuid.UUID,
        email: str,
        hashed_password: str,
        role: UserRole,
        is_active: bool,
        is_verified: bool,
        avatar_url: str | None,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
    ):
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.role = role
        self.is_active = is_active
        self.is_verified = is_verified
        self.avatar_url = avatar_url
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_instructor(self) -> bool:
        return self.role == UserRole.INSTRUCTOR

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN