import uuid
from datetime import datetime, timezone

from app.domain.entities.enrollment import EnrollmentStatus
from app.infrastructure.db.repositories.course_repository import SQLAlchemyCourseRepository
from app.infrastructure.db.repositories.enrollment_repository import (
    SQLAlchemyEnrollmentRepository,
    SQLAlchemyProgressRepository,
)
from app.infrastructure.db.repositories.section_repository import (
    SQLAlchemyLessonRepository,
    SQLAlchemySectionRepository,
)


class EnrollmentService:
    def __init__(
        self,
        enrollment_repo: SQLAlchemyEnrollmentRepository,
        course_repo: SQLAlchemyCourseRepository,
        progress_repo: SQLAlchemyProgressRepository,
    ):
        self.enrollment_repo = enrollment_repo
        self.course_repo = course_repo
        self.progress_repo = progress_repo

    async def enroll(
        self,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        payment_intent_id: str | None = None,
    ):
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        if not course.is_published:
            raise ValueError("Course is not published")

        existing = await self.enrollment_repo.get_by_student_and_course(
            student_id, course_id
        )
        if existing and existing.is_active:
            raise ValueError("Already enrolled")

        enrollment = await self.enrollment_repo.create(
            student_id=student_id,
            course_id=course_id,
            payment_intent_id=payment_intent_id,
        )

        # Update course total_enrolled
        course.total_enrolled += 1
        await self.course_repo.update(course)

        return enrollment

    async def get_enrolled_courses(self, student_id: uuid.UUID) -> list[dict]:
        enrollments = await self.enrollment_repo.list_by_student(student_id)
        result = []
        for enrollment in enrollments:
            course = await self.course_repo.get_by_id(enrollment.course_id)
            if not course:
                continue
            progress = await self.get_progress(enrollment.id, enrollment.course_id)
            result.append({
                "enrollment": enrollment,
                "course": course,
                "progress_percent": progress,
            })
        return result

    async def get_progress(
        self, enrollment_id: uuid.UUID, course_id: uuid.UUID
    ) -> float:
        course = await self.course_repo.get_by_id(course_id)
        if not course or course.total_lessons == 0:
            return 0.0

        progresses = await self.progress_repo.list_by_enrollment(enrollment_id)
        completed = sum(1 for p in progresses if p.is_completed)
        return round(completed / course.total_lessons * 100, 1)

    async def mark_lesson_complete(
        self, student_id: uuid.UUID, lesson_id: uuid.UUID,
        section_repo: SQLAlchemySectionRepository,
        lesson_repo: SQLAlchemyLessonRepository,
    ):
        lesson = await lesson_repo.get_by_id(lesson_id)
        if not lesson:
            raise ValueError("Lesson not found")

        section = await section_repo.get_by_id(lesson.section_id)
        enrollment = await self.enrollment_repo.get_by_student_and_course(
            student_id, section.course_id
        )
        if not enrollment or not enrollment.is_active:
            raise PermissionError("Not enrolled in this course")

        return await self.progress_repo.mark_completed(enrollment.id, lesson_id)

    async def is_enrolled(
        self, student_id: uuid.UUID, course_id: uuid.UUID
    ) -> bool:
        enrollment = await self.enrollment_repo.get_by_student_and_course(
            student_id, course_id
        )
        return enrollment is not None and enrollment.is_active