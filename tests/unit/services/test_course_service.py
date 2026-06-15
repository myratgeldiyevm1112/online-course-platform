import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.services.course_service import CourseService
from app.domain.entities.course import Course, CourseStatus, DifficultyLevel


def make_course(**kwargs) -> Course:
    instructor_id = kwargs.pop("instructor_id", uuid.uuid4())
    defaults = dict(
        id=uuid.uuid4(),
        instructor_id=instructor_id,
        category_id=None,
        title="Test Course",
        slug="test-course",
        description="A great course about testing",
        short_description=None,
        price=0.0,
        thumbnail_url=None,
        language="English",
        difficulty=DifficultyLevel.BEGINNER,
        status=CourseStatus.DRAFT,
        total_lessons=0,
        total_duration_seconds=0,
        avg_rating=0.0,
        total_enrolled=0,
        is_featured=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    defaults["instructor_id"] = instructor_id
    return Course(**defaults)


def make_service(existing_course=None):
    course_repo = AsyncMock()
    category_repo = AsyncMock()

    course_repo.get_by_id = AsyncMock(return_value=existing_course)
    course_repo.get_by_slug = AsyncMock(return_value=None)
    course_repo.create = AsyncMock(side_effect=lambda c: c)
    course_repo.update = AsyncMock(side_effect=lambda c: c)
    course_repo.soft_delete = AsyncMock(return_value=None)
    course_repo.list_by_instructor = AsyncMock(return_value=[])

    return CourseService(course_repo, category_repo), course_repo, category_repo


class TestCreateCourse:
    async def test_success(self):
        service, course_repo, _ = make_service()
        instructor_id = uuid.uuid4()

        result = await service.create_course(
            instructor_id=instructor_id,
            title="FastAPI Course",
            description="Learn FastAPI from scratch",
        )

        assert result.title == "FastAPI Course"
        assert result.status == CourseStatus.DRAFT
        assert result.instructor_id == instructor_id
        course_repo.create.assert_called_once()

    async def test_slug_generated_from_title(self):
        service, _, _ = make_service()

        result = await service.create_course(
            instructor_id=uuid.uuid4(),
            title="My Awesome Course",
            description="Great description here",
        )

        assert "my-awesome-course" in result.slug

    async def test_duplicate_slug_gets_suffix(self):
        service, course_repo, _ = make_service()
        course_repo.get_by_slug = AsyncMock(return_value=make_course())

        result = await service.create_course(
            instructor_id=uuid.uuid4(),
            title="Test Course",
            description="Description here",
        )

        assert len(result.slug) > len("test-course")


class TestPublishCourse:
    async def test_success(self):
        instructor_id = uuid.uuid4()
        course = make_course(instructor_id=instructor_id, total_lessons=3)
        service, course_repo, _ = make_service(existing_course=course)

        result = await service.publish_course(course.id, instructor_id)

        assert result.status == CourseStatus.PUBLISHED

    async def test_not_owner_raises(self):
        course = make_course(total_lessons=3)
        service, _, _ = make_service(existing_course=course)

        with pytest.raises(PermissionError):
            await service.publish_course(course.id, uuid.uuid4())

    async def test_course_not_found_raises(self):
        service, course_repo, _ = make_service(existing_course=None)

        with pytest.raises(ValueError):
            await service.publish_course(uuid.uuid4(), uuid.uuid4())


class TestUnpublishCourse:
    async def test_success(self):
        instructor_id = uuid.uuid4()
        course = make_course(instructor_id=instructor_id, status=CourseStatus.PUBLISHED)
        service, _, _ = make_service(existing_course=course)

        result = await service.unpublish_course(course.id, instructor_id)

        assert result.status == CourseStatus.DRAFT

    async def test_not_owner_raises(self):
        course = make_course(status=CourseStatus.PUBLISHED)
        service, _, _ = make_service(existing_course=course)

        with pytest.raises(PermissionError):
            await service.unpublish_course(course.id, uuid.uuid4())


class TestSoftDelete:
    async def test_success(self):
        instructor_id = uuid.uuid4()
        course = make_course(instructor_id=instructor_id)
        service, course_repo, _ = make_service(existing_course=course)

        await service.soft_delete(course.id, instructor_id)

        course_repo.soft_delete.assert_called_once_with(course.id)

    async def test_not_owner_raises(self):
        course = make_course()
        service, _, _ = make_service(existing_course=course)

        with pytest.raises(PermissionError):
            await service.soft_delete(course.id, uuid.uuid4())


class TestUpdateCourse:
    async def test_success(self):
        instructor_id = uuid.uuid4()
        course = make_course(instructor_id=instructor_id)
        service, _, _ = make_service(existing_course=course)

        result = await service.update_course(
            course_id=course.id,
            instructor_id=instructor_id,
            title="Updated Title",
        )

        assert result.title == "Updated Title"

    async def test_not_owner_raises(self):
        course = make_course()
        service, _, _ = make_service(existing_course=course)

        with pytest.raises(PermissionError):
            await service.update_course(
                course_id=course.id,
                instructor_id=uuid.uuid4(),
                title="Hacked",
            )