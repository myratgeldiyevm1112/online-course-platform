import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.enrollment_service import EnrollmentService
from app.domain.entities.course import Course, CourseStatus, DifficultyLevel
from app.domain.entities.enrollment import Enrollment, EnrollmentStatus, LessonProgress


# ─── Factories ────────────────────────────────────────────────────────────────

def make_course(**kwargs) -> Course:
    defaults = dict(
        id=uuid.uuid4(),
        instructor_id=uuid.uuid4(),
        category_id=None,
        title="Test Course",
        slug="test-course",
        description="Desc",
        short_description=None,
        price=0.0,
        thumbnail_url=None,
        language="English",
        difficulty=DifficultyLevel.BEGINNER,
        status=CourseStatus.PUBLISHED,
        total_lessons=3,
        total_duration_seconds=0,
        avg_rating=0.0,
        total_enrolled=0,
        is_featured=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Course(**defaults)


def make_enrollment(**kwargs) -> Enrollment:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        status=EnrollmentStatus.ACTIVE,
        payment_intent_id=None,
        enrolled_at=now,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return Enrollment(**defaults)


def make_progress(lesson_id=None, is_completed=False, watch_seconds=0) -> LessonProgress:
    """
    LessonProgress.is_completed — это @property: completed_at is not None.
    """
    return LessonProgress(
        id=uuid.uuid4(),
        enrollment_id=uuid.uuid4(),
        lesson_id=lesson_id or uuid.uuid4(),
        completed_at=datetime.now(timezone.utc) if is_completed else None,
        last_watched_at=datetime.now(timezone.utc),
        watch_seconds=watch_seconds,
    )


def make_service(course=None, enrollment=None, progresses=None):
    enrollment_repo = AsyncMock()
    course_repo = AsyncMock()
    progress_repo = AsyncMock()

    enrollment_repo.get_by_student_and_course = AsyncMock(return_value=enrollment)
    enrollment_repo.create = AsyncMock(return_value=enrollment)
    enrollment_repo.list_by_student = AsyncMock(
        return_value=[enrollment] if enrollment else []
    )

    course_repo.get_by_id = AsyncMock(return_value=course)
    course_repo.update = AsyncMock(side_effect=lambda c: c)

    progress_repo.list_by_enrollment = AsyncMock(return_value=progresses or [])
    progress_repo.mark_completed = AsyncMock(
        return_value=make_progress(is_completed=True)
    )

    service = EnrollmentService(enrollment_repo, course_repo, progress_repo)
    return service, enrollment_repo, course_repo, progress_repo


# ─── TestEnroll ───────────────────────────────────────────────────────────────

class TestEnroll:
    async def test_success(self):
        course = make_course()
        enrollment = make_enrollment(course_id=course.id)
        service, enrollment_repo, course_repo, _ = make_service(course=course)
        enrollment_repo.get_by_student_and_course = AsyncMock(return_value=None)
        enrollment_repo.create = AsyncMock(return_value=enrollment)

        result = await service.enroll(enrollment.student_id, course.id)

        assert result.course_id == course.id
        course_repo.update.assert_called_once()

    async def test_already_enrolled_raises(self):
        course = make_course()
        enrollment = make_enrollment(course_id=course.id)
        service, _, _, _ = make_service(course=course, enrollment=enrollment)

        with pytest.raises(ValueError, match="Already enrolled"):
            await service.enroll(enrollment.student_id, course.id)

    async def test_unpublished_course_raises(self):
        course = make_course(status=CourseStatus.DRAFT)
        service, enrollment_repo, _, _ = make_service(course=course)
        enrollment_repo.get_by_student_and_course = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not published"):
            await service.enroll(uuid.uuid4(), course.id)

    async def test_course_not_found_raises(self):
        service, enrollment_repo, _, _ = make_service(course=None)
        enrollment_repo.get_by_student_and_course = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Course not found"):
            await service.enroll(uuid.uuid4(), uuid.uuid4())


# ─── TestGetProgress ──────────────────────────────────────────────────────────

class TestGetProgress:
    async def test_no_lessons_returns_zero(self):
        course = make_course(total_lessons=0)
        enrollment = make_enrollment(course_id=course.id)
        service, _, _, _ = make_service(course=course, enrollment=enrollment)

        result = await service.get_progress(enrollment.id, course.id)
        assert result == 0.0

    async def test_partial_progress(self):
        course = make_course(total_lessons=4)
        enrollment = make_enrollment(course_id=course.id)
        progresses = [
            make_progress(is_completed=True),
            make_progress(is_completed=True),
            make_progress(is_completed=False),
            make_progress(is_completed=False),
        ]
        service, _, _, _ = make_service(
            course=course, enrollment=enrollment, progresses=progresses
        )

        result = await service.get_progress(enrollment.id, course.id)
        assert result == 50.0

    async def test_full_completion(self):
        course = make_course(total_lessons=2)
        enrollment = make_enrollment(course_id=course.id)
        progresses = [
            make_progress(is_completed=True),
            make_progress(is_completed=True),
        ]
        service, _, _, _ = make_service(
            course=course, enrollment=enrollment, progresses=progresses
        )

        result = await service.get_progress(enrollment.id, course.id)
        assert result == 100.0


# ─── TestMarkLessonComplete ───────────────────────────────────────────────────

class TestMarkLessonComplete:
    def _make_repos(self, course_id):
        lesson = MagicMock()
        lesson.id = uuid.uuid4()
        lesson.section_id = uuid.uuid4()

        section = MagicMock()
        section.id = lesson.section_id
        section.course_id = course_id

        lesson_repo = AsyncMock()
        lesson_repo.get_by_id = AsyncMock(return_value=lesson)

        section_repo = AsyncMock()
        section_repo.get_by_id = AsyncMock(return_value=section)

        return lesson, section_repo, lesson_repo

    async def test_success_no_certificate(self):
        """Урок завершён, но не все уроки пройдены — certificate не вызывается."""
        course = make_course(total_lessons=3)
        enrollment = make_enrollment(course_id=course.id)
        lesson, section_repo, lesson_repo = self._make_repos(course.id)

        # После mark_completed — 1 из 3 completed
        progresses = [make_progress(is_completed=True)]
        service, _, _, _ = make_service(
            course=course, enrollment=enrollment, progresses=progresses
        )

        with patch("app.tasks.tasks.generate_certificate.delay") as mock_cert:
            result = await service.mark_lesson_complete(
                student_id=enrollment.student_id,
                lesson_id=lesson.id,
                section_repo=section_repo,
                lesson_repo=lesson_repo,
            )

        assert result.is_completed is True
        mock_cert.assert_not_called()

    async def test_completion_triggers_certificate(self):
        """Все уроки пройдены → generate_certificate.delay вызывается."""
        course = make_course(total_lessons=2)
        enrollment = make_enrollment(course_id=course.id)
        lesson, section_repo, lesson_repo = self._make_repos(course.id)

        # list_by_enrollment возвращает 2 completed из 2
        progresses = [
            make_progress(is_completed=True),
            make_progress(is_completed=True),
        ]
        service, _, _, _ = make_service(
            course=course, enrollment=enrollment, progresses=progresses
        )

        with patch("app.tasks.tasks.generate_certificate.delay") as mock_cert:
            await service.mark_lesson_complete(
                student_id=enrollment.student_id,
                lesson_id=lesson.id,
                section_repo=section_repo,
                lesson_repo=lesson_repo,
            )

        mock_cert.assert_called_once_with(
            enrollment_id=str(enrollment.id),
            student_id=str(enrollment.student_id),
            course_id=str(course.id),
        )

    async def test_not_enrolled_raises(self):
        course = make_course()
        lesson, section_repo, lesson_repo = self._make_repos(course.id)
        service, enrollment_repo, _, _ = make_service(course=course, enrollment=None)
        enrollment_repo.get_by_student_and_course = AsyncMock(return_value=None)

        with pytest.raises(PermissionError):
            await service.mark_lesson_complete(
                student_id=uuid.uuid4(),
                lesson_id=lesson.id,
                section_repo=section_repo,
                lesson_repo=lesson_repo,
            )

    async def test_lesson_not_found_raises(self):
        course = make_course()
        enrollment = make_enrollment(course_id=course.id)
        service, _, _, _ = make_service(course=course, enrollment=enrollment)

        lesson_repo = AsyncMock()
        lesson_repo.get_by_id = AsyncMock(return_value=None)
        section_repo = AsyncMock()

        with pytest.raises(ValueError, match="Lesson not found"):
            await service.mark_lesson_complete(
                student_id=enrollment.student_id,
                lesson_id=uuid.uuid4(),
                section_repo=section_repo,
                lesson_repo=lesson_repo,
            )

    async def test_refunded_enrollment_raises(self):
        """Refunded enrollment — доступ запрещён."""
        course = make_course()
        enrollment = make_enrollment(
            course_id=course.id, status=EnrollmentStatus.REFUNDED
        )
        lesson, section_repo, lesson_repo = self._make_repos(course.id)
        service, _, _, _ = make_service(course=course, enrollment=enrollment)

        with pytest.raises(PermissionError):
            await service.mark_lesson_complete(
                student_id=enrollment.student_id,
                lesson_id=lesson.id,
                section_repo=section_repo,
                lesson_repo=lesson_repo,
            )


# ─── TestIsEnrolled ───────────────────────────────────────────────────────────

class TestIsEnrolled:
    async def test_active_enrollment_returns_true(self):
        enrollment = make_enrollment(status=EnrollmentStatus.ACTIVE)
        service, _, _, _ = make_service(enrollment=enrollment)

        result = await service.is_enrolled(enrollment.student_id, enrollment.course_id)
        assert result is True

    async def test_no_enrollment_returns_false(self):
        service, enrollment_repo, _, _ = make_service(enrollment=None)
        enrollment_repo.get_by_student_and_course = AsyncMock(return_value=None)

        result = await service.is_enrolled(uuid.uuid4(), uuid.uuid4())
        assert result is False

    async def test_refunded_enrollment_returns_false(self):
        enrollment = make_enrollment(status=EnrollmentStatus.REFUNDED)
        service, _, _, _ = make_service(enrollment=enrollment)

        result = await service.is_enrolled(enrollment.student_id, enrollment.course_id)
        assert result is False