import uuid
from datetime import datetime
from sqlalchemy import (
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import BaseModel


class Review(BaseModel):
    __tablename__ = "reviews"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    comment: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    instructor_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    instructor_responded_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_review_user_course"),

        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
    )

class ReviewHelpful(BaseModel):
    __tablename__ = "review_helpful"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("review_id", "user_id", name="uq_review_helpful"),
    )