import uuid
from datetime import datetime
from enum import Enum


class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LessonType(str, Enum):
    VIDEO = "video"
    ARTICLE = "article"
    QUIZ = "quiz"


class Category:
    def __init__(
        self,
        id: uuid.UUID,
        name: str,
        slug: str,
        description: str | None = None,
        parent_id: uuid.UUID | None = None,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.slug = slug
        self.description = description
        self.parent_id = parent_id
        self.created_at = created_at
        self.updated_at = updated_at


class Course:
    def __init__(
        self,
        id: uuid.UUID,
        instructor_id: uuid.UUID,
        category_id: uuid.UUID | None,
        title: str,
        slug: str,
        description: str,
        short_description: str | None,
        price: float,
        thumbnail_url: str | None,
        language: str,
        difficulty: DifficultyLevel,
        status: CourseStatus,
        total_lessons: int,
        total_duration_seconds: int,
        avg_rating: float,
        total_enrolled: int,
        is_featured: bool,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
    ):
        self.id = id
        self.instructor_id = instructor_id
        self.category_id = category_id
        self.title = title
        self.slug = slug
        self.description = description
        self.short_description = short_description
        self.price = price
        self.thumbnail_url = thumbnail_url
        self.language = language
        self.difficulty = difficulty
        self.status = status
        self.total_lessons = total_lessons
        self.total_duration_seconds = total_duration_seconds
        self.avg_rating = avg_rating
        self.total_enrolled = total_enrolled
        self.is_featured = is_featured
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at

    @property
    def is_published(self) -> bool:
        return self.status == CourseStatus.PUBLISHED

    @property
    def is_free(self) -> bool:
        return self.price == 0.0

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class Section:
    def __init__(
        self,
        id: uuid.UUID,
        course_id: uuid.UUID,
        title: str,
        position: int,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.course_id = course_id
        self.title = title
        self.position = position
        self.created_at = created_at
        self.updated_at = updated_at


class Lesson:
    def __init__(
        self,
        id: uuid.UUID,
        section_id: uuid.UUID,
        title: str,
        position: int,
        lesson_type: LessonType,
        content_url: str | None,
        article_body: str | None,
        duration_seconds: int,
        is_preview: bool,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.section_id = section_id
        self.title = title
        self.position = position
        self.lesson_type = lesson_type
        self.content_url = content_url
        self.article_body = article_body
        self.duration_seconds = duration_seconds
        self.is_preview = is_preview
        self.created_at = created_at
        self.updated_at = updated_at