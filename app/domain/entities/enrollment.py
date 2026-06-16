import uuid
from datetime import datetime
from enum import Enum


class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class Enrollment:
    def __init__(
        self,
        id: uuid.UUID,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        status: EnrollmentStatus,
        payment_intent_id: str | None,
        enrolled_at: datetime,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.student_id = student_id
        self.course_id = course_id
        self.status = status
        self.payment_intent_id = payment_intent_id
        self.enrolled_at = enrolled_at
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def is_active(self) -> bool:
        return self.status == EnrollmentStatus.ACTIVE


class LessonProgress:
    def __init__(
        self,
        id: uuid.UUID,
        enrollment_id: uuid.UUID,
        lesson_id: uuid.UUID,
        completed_at: datetime | None,
        last_watched_at: datetime | None,
        watch_seconds: int,
    ):
        self.id = id
        self.enrollment_id = enrollment_id
        self.lesson_id = lesson_id
        self.completed_at = completed_at
        self.last_watched_at = last_watched_at
        self.watch_seconds = watch_seconds

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None


class CourseCompletion:
    def __init__(
        self,
        id: uuid.UUID,
        enrollment_id: uuid.UUID,
        completed_at: datetime,
        certificate_id: uuid.UUID | None,
    ):
        self.id = id
        self.enrollment_id = enrollment_id
        self.completed_at = completed_at
        self.certificate_id = certificate_id