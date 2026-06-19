import uuid

from app.infrastructure.db.repositories.course_repository import SQLAlchemyCourseRepository
from app.infrastructure.db.repositories.enrollment_repository import SQLAlchemyEnrollmentRepository
from app.infrastructure.db.repositories.review_repository import SQLAlchemyReviewRepository


class ReviewService:
    def __init__(
        self,
        review_repo: SQLAlchemyReviewRepository,
        enrollment_repo: SQLAlchemyEnrollmentRepository,
        course_repo: SQLAlchemyCourseRepository,
    ):
        self.review_repo = review_repo
        self.enrollment_repo = enrollment_repo
        self.course_repo = course_repo

    async def submit_review(
        self,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        rating: int,
        body: str,
    ):
        course = await self.course_repo.get_by_id(course_id)
        if not course or not course.is_published:
            raise ValueError("Course not found")

        enrollment = await self.enrollment_repo.get_by_student_and_course(student_id, course_id)
        if not enrollment or not enrollment.is_active:
            raise PermissionError("Must be enrolled to review")

        existing = await self.review_repo.get_by_student_and_course(student_id, course_id)
        if existing:
            raise ValueError("Already reviewed this course")

        review = await self.review_repo.create(
            course_id=course_id,
            student_id=student_id,
            enrollment_id=enrollment.id,
            rating=rating,
            body=body,
        )

        avg = await self.review_repo.recalc_avg_rating(course_id)
        course.avg_rating = avg
        await self.course_repo.update(course)

        return review

    async def edit_review(
        self,
        student_id: uuid.UUID,
        review_id: uuid.UUID,
        rating: int | None,
        body: str | None,
    ):
        review = await self.review_repo.get_by_id(review_id)
        if not review:
            raise ValueError("Review not found")
        if review.student_id != student_id:
            raise PermissionError("Access denied")

        updated = await self.review_repo.update(review_id, rating=rating, body=body)

        avg = await self.review_repo.recalc_avg_rating(review.course_id)
        course = await self.course_repo.get_by_id(review.course_id)
        if course:
            course.avg_rating = avg
            await self.course_repo.update(course)

        return updated

    async def delete_review(self, student_id: uuid.UUID, review_id: uuid.UUID) -> None:
        review = await self.review_repo.get_by_id(review_id)
        if not review:
            raise ValueError("Review not found")
        if review.student_id != student_id:
            raise PermissionError("Access denied")

        await self.review_repo.delete(review_id)

        avg = await self.review_repo.recalc_avg_rating(review.course_id)
        course = await self.course_repo.get_by_id(review.course_id)
        if course:
            course.avg_rating = avg
            await self.course_repo.update(course)