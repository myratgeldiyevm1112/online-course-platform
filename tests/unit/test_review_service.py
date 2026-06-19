import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.services.review_service import ReviewService
from app.domain.entities.course import Course, CourseStatus, DifficultyLevel
from app.domain.entities.enrollment import Enrollment, EnrollmentStatus
from app.domain.entities.review import Review


# ─── Factories ────────────────────────────────────────────────────────────────

def make_course(**kwargs) -> Course:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        instructor_id=uuid.uuid4(),
        category_id=None,
        title="Test Course",
        slug="test-course",
        description="Description",
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
        created_at=now,
        updated_at=now,
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


def make_review(**kwargs) -> Review:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        enrollment_id=uuid.uuid4(),
        rating=5,
        body="Great course!",
        is_hidden=False,
        helpful_count=0,
        instructor_response=None,
        instructor_responded_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return Review(**defaults)


def make_service(course=None, enrollment=None, existing_review=None, new_review=None, avg=4.5):
    review_repo = AsyncMock()
    enrollment_repo = AsyncMock()
    course_repo = AsyncMock()

    course_repo.get_by_id = AsyncMock(return_value=course)
    course_repo.update = AsyncMock(side_effect=lambda c: c)

    enrollment_repo.get_by_student_and_course = AsyncMock(return_value=enrollment)

    review_repo.get_by_student_and_course = AsyncMock(return_value=existing_review)
    review_repo.get_by_id = AsyncMock(return_value=existing_review)
    review_repo.create = AsyncMock(return_value=new_review or make_review())
    review_repo.update = AsyncMock(return_value=new_review or make_review())
    review_repo.delete = AsyncMock(return_value=None)
    review_repo.recalc_avg_rating = AsyncMock(return_value=avg)

    service = ReviewService(review_repo, enrollment_repo, course_repo)
    return service, review_repo, enrollment_repo, course_repo


# ─── TestSubmitReview ─────────────────────────────────────────────────────────

class TestSubmitReview:
    async def test_success(self):
        course = make_course()
        enrollment = make_enrollment(course_id=course.id)
        new_review = make_review(course_id=course.id, student_id=enrollment.student_id)
        service, review_repo, _, course_repo = make_service(
            course=course,
            enrollment=enrollment,
            existing_review=None,
            new_review=new_review,
        )

        result = await service.submit_review(
            student_id=enrollment.student_id,
            course_id=course.id,
            rating=5,
            body="Amazing course!",
        )

        assert result.rating == 5
        review_repo.create.assert_called_once()
        review_repo.recalc_avg_rating.assert_called_once_with(course.id)
        course_repo.update.assert_called_once()

    async def test_course_not_found_raises(self):
        service, _, _, _ = make_service(course=None)

        with pytest.raises(ValueError, match="Course not found"):
            await service.submit_review(uuid.uuid4(), uuid.uuid4(), 5, "Great!")

    async def test_unpublished_course_raises(self):
        course = make_course(status=CourseStatus.DRAFT)
        service, _, _, _ = make_service(course=course)

        with pytest.raises(ValueError, match="Course not found"):
            await service.submit_review(uuid.uuid4(), course.id, 5, "Great!")

    async def test_not_enrolled_raises(self):
        course = make_course()
        service, _, enrollment_repo, _ = make_service(course=course, enrollment=None)
        enrollment_repo.get_by_student_and_course = AsyncMock(return_value=None)

        with pytest.raises(PermissionError, match="Must be enrolled"):
            await service.submit_review(uuid.uuid4(), course.id, 5, "Great!")

    async def test_refunded_enrollment_raises(self):
        course = make_course()
        enrollment = make_enrollment(
            course_id=course.id, status=EnrollmentStatus.REFUNDED
        )
        service, _, _, _ = make_service(course=course, enrollment=enrollment)

        with pytest.raises(PermissionError, match="Must be enrolled"):
            await service.submit_review(enrollment.student_id, course.id, 5, "Great!")

    async def test_duplicate_review_raises(self):
        """One review per course guard."""
        course = make_course()
        enrollment = make_enrollment(course_id=course.id)
        existing = make_review(course_id=course.id, student_id=enrollment.student_id)
        service, _, _, _ = make_service(
            course=course, enrollment=enrollment, existing_review=existing
        )

        with pytest.raises(ValueError, match="Already reviewed"):
            await service.submit_review(enrollment.student_id, course.id, 4, "Good!")

    async def test_avg_rating_recalculated(self):
        course = make_course(avg_rating=0.0)
        enrollment = make_enrollment(course_id=course.id)
        service, review_repo, _, course_repo = make_service(
            course=course, enrollment=enrollment, existing_review=None, avg=4.5
        )

        await service.submit_review(enrollment.student_id, course.id, 5, "Excellent!")

        review_repo.recalc_avg_rating.assert_called_once()
        updated_course = course_repo.update.call_args[0][0]
        assert updated_course.avg_rating == 4.5


# ─── TestEditReview ───────────────────────────────────────────────────────────

class TestEditReview:
    async def test_success(self):
        student_id = uuid.uuid4()
        review = make_review(student_id=student_id, rating=3)
        updated = make_review(student_id=student_id, rating=5)
        course = make_course(id=review.course_id)
        service, review_repo, _, _ = make_service(
            course=course, existing_review=review, new_review=updated
        )
        review_repo.get_by_id = AsyncMock(return_value=review)

        result = await service.edit_review(student_id, review.id, rating=5, body=None)

        assert result.rating == 5
        review_repo.update.assert_called_once_with(review.id, rating=5, body=None)

    async def test_review_not_found_raises(self):
        service, review_repo, _, _ = make_service()
        review_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Review not found"):
            await service.edit_review(uuid.uuid4(), uuid.uuid4(), rating=5, body=None)

    async def test_not_owner_raises(self):
        review = make_review(student_id=uuid.uuid4())
        service, review_repo, _, _ = make_service(existing_review=review)
        review_repo.get_by_id = AsyncMock(return_value=review)

        with pytest.raises(PermissionError, match="Access denied"):
            await service.edit_review(uuid.uuid4(), review.id, rating=5, body=None)

    async def test_avg_rating_recalculated_after_edit(self):
        student_id = uuid.uuid4()
        review = make_review(student_id=student_id)
        course = make_course(id=review.course_id)
        service, review_repo, _, course_repo = make_service(
            course=course, existing_review=review, avg=3.8
        )
        review_repo.get_by_id = AsyncMock(return_value=review)

        await service.edit_review(student_id, review.id, rating=3, body=None)

        review_repo.recalc_avg_rating.assert_called_once()
        updated_course = course_repo.update.call_args[0][0]
        assert updated_course.avg_rating == 3.8


# ─── TestDeleteReview ─────────────────────────────────────────────────────────

class TestDeleteReview:
    async def test_success(self):
        student_id = uuid.uuid4()
        review = make_review(student_id=student_id)
        course = make_course(id=review.course_id)
        service, review_repo, _, _ = make_service(course=course, existing_review=review)
        review_repo.get_by_id = AsyncMock(return_value=review)

        await service.delete_review(student_id, review.id)

        review_repo.delete.assert_called_once_with(review.id)
        review_repo.recalc_avg_rating.assert_called_once()

    async def test_review_not_found_raises(self):
        service, review_repo, _, _ = make_service()
        review_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Review not found"):
            await service.delete_review(uuid.uuid4(), uuid.uuid4())

    async def test_not_owner_raises(self):
        review = make_review(student_id=uuid.uuid4())
        service, review_repo, _, _ = make_service(existing_review=review)
        review_repo.get_by_id = AsyncMock(return_value=review)

        with pytest.raises(PermissionError, match="Access denied"):
            await service.delete_review(uuid.uuid4(), review.id)

    async def test_avg_rating_recalculated_after_delete(self):
        student_id = uuid.uuid4()
        review = make_review(student_id=student_id)
        course = make_course(id=review.course_id)
        service, review_repo, _, course_repo = make_service(
            course=course, existing_review=review, avg=0.0
        )
        review_repo.get_by_id = AsyncMock(return_value=review)

        await service.delete_review(student_id, review.id)

        updated_course = course_repo.update.call_args[0][0]
        assert updated_course.avg_rating == 0.0
