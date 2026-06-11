import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.user import UserRole
from app.infrastructure.db.base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    instructor_profile: Mapped["InstructorProfileModel | None"] = relationship(
        "InstructorProfileModel", back_populates="user", uselist=False
    )
    student_profile: Mapped["StudentProfileModel | None"] = relationship(
        "StudentProfileModel", back_populates="user", uselist=False
    )


class InstructorProfileModel(BaseModel):
    __tablename__ = "instructor_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    expertise: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    social_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    total_students: Mapped[int] = mapped_column(default=0, nullable=False)
    total_courses: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="instructor_profile")


class StudentProfileModel(BaseModel):
    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    total_enrolled: Mapped[int] = mapped_column(default=0, nullable=False)
    total_completed: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="student_profile")