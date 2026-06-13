import uuid
from datetime import datetime, timezone

from app.core.exceptions import (
    UserNotFoundError,
)
from app.domain.entities.course import Course, CourseStatus, DifficultyLevel
from app.domain.interfaces.course_repository import (
    AbstractCategoryRepository,
    AbstractCourseRepository,
)


class CourseService:
    def __init__(
        self,
        course_repo: AbstractCourseRepository,
        category_repo: AbstractCategoryRepository,
    ):
        self.course_repo = course_repo
        self.category_repo = category_repo

    async def create_course(
        self,
        instructor_id: uuid.UUID,
        title: str,
        description: str,
        price: float = 0.0,
        short_description: str | None = None,
        category_id: uuid.UUID | None = None,
        language: str = "English",
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
    ) -> Course:
        slug = self._generate_slug(title)

        existing = await self.course_repo.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        course = Course(
            id=uuid.uuid4(),
            instructor_id=instructor_id,
            category_id=category_id,
            title=title,
            slug=slug,
            description=description,
            short_description=short_description,
            price=price,
            thumbnail_url=None,
            language=language,
            difficulty=difficulty,
            status=CourseStatus.DRAFT,
            total_lessons=0,
            total_duration_seconds=0,
            avg_rating=0.0,
            total_enrolled=0,
            is_featured=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return await self.course_repo.create(course)

    async def get_course(
        self,
        course_id: uuid.UUID,
        requester_id: uuid.UUID | None = None,
        is_instructor: bool = False,
    ) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")

        # Instructor owner sees all statuses
        if is_instructor and course.instructor_id == requester_id:
            return course

        # Others only see published
        if not course.is_published:
            raise ValueError("Course not found")

        return course

    async def update_course(
        self,
        course_id: uuid.UUID,
        instructor_id: uuid.UUID,
        **kwargs,
    ) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        for key, value in kwargs.items():
            if value is not None and hasattr(course, key):
                setattr(course, key, value)

        return await self.course_repo.update(course)

    async def soft_delete(self, course_id: uuid.UUID, instructor_id: uuid.UUID) -> None:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")
        await self.course_repo.soft_delete(course_id)

    async def publish_course(self, course_id: uuid.UUID, instructor_id: uuid.UUID) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")
        if course.total_lessons == 0:
            raise ValueError("Cannot publish course with no lessons")

        course.status = CourseStatus.PUBLISHED
        return await self.course_repo.update(course)

    async def unpublish_course(self, course_id: uuid.UUID, instructor_id: uuid.UUID) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        course.status = CourseStatus.DRAFT
        return await self.course_repo.update(course)

    async def list_instructor_courses(self, instructor_id: uuid.UUID) -> list[Course]:
        return await self.course_repo.list_by_instructor(instructor_id)

    async def update_thumbnail(
        self, course_id: uuid.UUID, instructor_id: uuid.UUID, thumbnail_url: str
    ) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")
        course.thumbnail_url = thumbnail_url
        return await self.course_repo.update(course)

    @staticmethod
    def _generate_slug(title: str) -> str:
        import re
        slug = title.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "-", slug)
        slug = slug.strip("-")
        return slug