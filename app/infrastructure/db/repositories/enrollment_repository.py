import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.enrollment import (
    CourseCompletion,
    Enrollment,
    EnrollmentStatus,
    LessonProgress,
)
from app.infrastructure.db.models.enrollment import (
    CourseCompletionModel,
    EnrollmentModel,
    LessonProgressModel,
)


class SQLAlchemyEnrollmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        payment_intent_id: str | None = None,
    ) -> Enrollment:
        model = EnrollmentModel(
            id=uuid.uuid4(),
            student_id=student_id,
            course_id=course_id,
            status=EnrollmentStatus.ACTIVE,
            payment_intent_id=payment_intent_id,
            enrolled_at=datetime.now(timezone.utc),
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, enrollment_id: uuid.UUID) -> Enrollment | None:
        result = await self.session.execute(
            select(EnrollmentModel).where(EnrollmentModel.id == enrollment_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_student_and_course(
        self, student_id: uuid.UUID, course_id: uuid.UUID
    ) -> Enrollment | None:
        result = await self.session.execute(
            select(EnrollmentModel).where(
                EnrollmentModel.student_id == student_id,
                EnrollmentModel.course_id == course_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_student(self, student_id: uuid.UUID) -> list[Enrollment]:
        result = await self.session.execute(
            select(EnrollmentModel).where(
                EnrollmentModel.student_id == student_id,
                EnrollmentModel.status == EnrollmentStatus.ACTIVE,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update_status(
        self, enrollment_id: uuid.UUID, status: EnrollmentStatus
    ) -> Enrollment:
        result = await self.session.execute(
            select(EnrollmentModel).where(EnrollmentModel.id == enrollment_id)
        )
        model = result.scalar_one()
        model.status = status
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_payment_intent(self, payment_intent_id: str) -> Enrollment | None:
        result = await self.session.execute(
            select(EnrollmentModel).where(
                EnrollmentModel.payment_intent_id == payment_intent_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    @staticmethod
    def _to_entity(model: EnrollmentModel) -> Enrollment:
        return Enrollment(
            id=model.id,
            student_id=model.student_id,
            course_id=model.course_id,
            status=model.status,
            payment_intent_id=model.payment_intent_id,
            enrolled_at=model.enrolled_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyProgressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self, enrollment_id: uuid.UUID, lesson_id: uuid.UUID
    ) -> LessonProgress:
        result = await self.session.execute(
            select(LessonProgressModel).where(
                LessonProgressModel.enrollment_id == enrollment_id,
                LessonProgressModel.lesson_id == lesson_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            model = LessonProgressModel(
                id=uuid.uuid4(),
                enrollment_id=enrollment_id,
                lesson_id=lesson_id,
                watch_seconds=0,
            )
            self.session.add(model)
            await self.session.flush()
            await self.session.refresh(model)
        return self._to_entity(model)

    async def mark_completed(
        self, enrollment_id: uuid.UUID, lesson_id: uuid.UUID
    ) -> LessonProgress:
        progress = await self.get_or_create(enrollment_id, lesson_id)
        result = await self.session.execute(
            select(LessonProgressModel).where(
                LessonProgressModel.enrollment_id == enrollment_id,
                LessonProgressModel.lesson_id == lesson_id,
            )
        )
        model = result.scalar_one()
        model.completed_at = datetime.now(timezone.utc)
        model.last_watched_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def list_by_enrollment(
        self, enrollment_id: uuid.UUID
    ) -> list[LessonProgress]:
        result = await self.session.execute(
            select(LessonProgressModel).where(
                LessonProgressModel.enrollment_id == enrollment_id
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update_watch_seconds(
        self, enrollment_id: uuid.UUID, lesson_id: uuid.UUID, seconds: int
    ) -> LessonProgress:
        progress = await self.get_or_create(enrollment_id, lesson_id)
        result = await self.session.execute(
            select(LessonProgressModel).where(
                LessonProgressModel.enrollment_id == enrollment_id,
                LessonProgressModel.lesson_id == lesson_id,
            )
        )
        model = result.scalar_one()
        model.watch_seconds = seconds
        model.last_watched_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: LessonProgressModel) -> LessonProgress:
        return LessonProgress(
            id=model.id,
            enrollment_id=model.enrollment_id,
            lesson_id=model.lesson_id,
            completed_at=model.completed_at,
            last_watched_at=model.last_watched_at,
            watch_seconds=model.watch_seconds,
        )