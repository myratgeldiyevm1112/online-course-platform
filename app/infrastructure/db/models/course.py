import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.course import CourseStatus, DifficultyLevel, LessonType
from app.infrastructure.db.base import BaseModel


class CategoryModel(BaseModel):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    children: Mapped[list["CategoryModel"]] = relationship("CategoryModel")
    courses: Mapped[list["CourseModel"]] = relationship("CourseModel", back_populates="category")


class CourseModel(BaseModel):
    __tablename__ = "courses"

    instructor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="English")
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel), nullable=False, default=DifficultyLevel.BEGINNER
    )
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus), nullable=False, default=CourseStatus.DRAFT, index=True
    )
    total_lessons: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.0)
    total_enrolled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    category: Mapped["CategoryModel | None"] = relationship(
        "CategoryModel", back_populates="courses"
    )
    sections: Mapped[list["SectionModel"]] = relationship(
        "SectionModel", back_populates="course", order_by="SectionModel.position"
    )


class SectionModel(BaseModel):
    __tablename__ = "sections"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    course: Mapped["CourseModel"] = relationship("CourseModel", back_populates="sections")
    lessons: Mapped[list["LessonModel"]] = relationship(
        "LessonModel", back_populates="section", order_by="LessonModel.position"
    )


class LessonModel(BaseModel):
    __tablename__ = "lessons"

    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lesson_type: Mapped[LessonType] = mapped_column(
        Enum(LessonType), nullable=False, default=LessonType.VIDEO
    )
    content_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    article_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    section: Mapped["SectionModel"] = relationship("SectionModel", back_populates="lessons")