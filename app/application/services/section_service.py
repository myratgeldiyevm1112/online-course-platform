import uuid
from datetime import datetime, timezone

from app.domain.entities.course import Lesson, LessonType, Section
from app.domain.interfaces.course_repository import AbstractCourseRepository
from app.domain.interfaces.section_repository import (
    AbstractLessonRepository,
    AbstractSectionRepository,
)


class SectionService:
    def __init__(
        self,
        section_repo: AbstractSectionRepository,
        course_repo: AbstractCourseRepository,
    ):
        self.section_repo = section_repo
        self.course_repo = course_repo

    async def create_section(
        self, course_id: uuid.UUID, instructor_id: uuid.UUID, title: str
    ) -> Section:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        existing = await self.section_repo.list_by_course(course_id)
        position = len(existing)

        section = Section(
            id=uuid.uuid4(),
            course_id=course_id,
            title=title,
            position=position,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return await self.section_repo.create(section)

    async def update_section(
        self,
        section_id: uuid.UUID,
        instructor_id: uuid.UUID,
        title: str | None = None,
        position: int | None = None,
    ) -> Section:
        section = await self.section_repo.get_by_id(section_id)
        if not section:
            raise ValueError("Section not found")

        course = await self.course_repo.get_by_id(section.course_id)
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        if title is not None:
            section.title = title
        if position is not None:
            section.position = position

        return await self.section_repo.update(section)

    async def delete_section(
        self, section_id: uuid.UUID, instructor_id: uuid.UUID
    ) -> None:
        section = await self.section_repo.get_by_id(section_id)
        if not section:
            raise ValueError("Section not found")

        course = await self.course_repo.get_by_id(section.course_id)
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        await self.section_repo.delete(section_id)

    async def list_sections(self, course_id: uuid.UUID) -> list[Section]:
        return await self.section_repo.list_by_course(course_id)


class LessonService:
    def __init__(
        self,
        lesson_repo: AbstractLessonRepository,
        section_repo: AbstractSectionRepository,
        course_repo: AbstractCourseRepository,
    ):
        self.lesson_repo = lesson_repo
        self.section_repo = section_repo
        self.course_repo = course_repo

    async def create_lesson(
        self,
        section_id: uuid.UUID,
        instructor_id: uuid.UUID,
        title: str,
        lesson_type: LessonType = LessonType.VIDEO,
        article_body: str | None = None,
        is_preview: bool = False,
    ) -> Lesson:
        section = await self.section_repo.get_by_id(section_id)
        if not section:
            raise ValueError("Section not found")

        course = await self.course_repo.get_by_id(section.course_id)
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        existing = await self.lesson_repo.list_by_section(section_id)
        position = len(existing)

        lesson = Lesson(
            id=uuid.uuid4(),
            section_id=section_id,
            title=title,
            position=position,
            lesson_type=lesson_type,
            content_url=None,
            article_body=article_body,
            duration_seconds=0,
            is_preview=is_preview,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        created = await self.lesson_repo.create(lesson)

        # Update course total_lessons count
        course.total_lessons += 1
        await self.course_repo.update(course)

        return created

    async def update_lesson(
        self,
        lesson_id: uuid.UUID,
        instructor_id: uuid.UUID,
        **kwargs,
    ) -> Lesson:
        lesson = await self.lesson_repo.get_by_id(lesson_id)
        if not lesson:
            raise ValueError("Lesson not found")

        section = await self.section_repo.get_by_id(lesson.section_id)
        course = await self.course_repo.get_by_id(section.course_id)
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        for key, value in kwargs.items():
            if value is not None and hasattr(lesson, key):
                setattr(lesson, key, value)

        return await self.lesson_repo.update(lesson)

    async def delete_lesson(
        self, lesson_id: uuid.UUID, instructor_id: uuid.UUID
    ) -> None:
        lesson = await self.lesson_repo.get_by_id(lesson_id)
        if not lesson:
            raise ValueError("Lesson not found")

        section = await self.section_repo.get_by_id(lesson.section_id)
        course = await self.course_repo.get_by_id(section.course_id)
        if course.instructor_id != instructor_id:
            raise PermissionError("Not the course owner")

        await self.lesson_repo.delete(lesson_id)

        course.total_lessons = max(0, course.total_lessons - 1)
        await self.course_repo.update(course)

    async def list_lessons(self, section_id: uuid.UUID) -> list[Lesson]:
        return await self.lesson_repo.list_by_section(section_id)