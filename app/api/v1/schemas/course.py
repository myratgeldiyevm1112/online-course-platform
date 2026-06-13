import uuid
from typing import Any
from pydantic import BaseModel, Field


class CreateCourseRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    short_description: str | None = Field(None, max_length=500)
    price: float = Field(0.0, ge=0)
    category_id: uuid.UUID | None = None
    language: str = "English"
    difficulty: str = "beginner"


class UpdateCourseRequest(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    short_description: str | None = None
    price: float | None = Field(None, ge=0)
    category_id: uuid.UUID | None = None
    language: str | None = None
    difficulty: str | None = None


class CourseResponse(BaseModel):
    id: str
    instructor_id: str
    category_id: str | None
    title: str
    slug: str
    description: str
    short_description: str | None
    price: float
    thumbnail_url: str | None
    language: str
    difficulty: str
    status: str
    total_lessons: int
    total_duration_seconds: int
    avg_rating: float
    total_enrolled: int
    is_featured: bool


class CourseListResponse(BaseModel):
    items: list[CourseResponse]
    total: int