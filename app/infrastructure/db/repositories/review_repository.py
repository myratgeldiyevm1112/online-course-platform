import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.review import Review, ReviewHelpful
from app.infrastructure.db.models.review import Review as ReviewModel, ReviewHelpful as ReviewHelpfulModel


def _to_entity(m: ReviewModel) -> Review:
    return Review(
        id=m.id,
        course_id=m.course_id,
        student_id=m.user_id,
        enrollment_id=m.enrollment_id,
        rating=m.rating,
        body=m.body,
        is_hidden=m.is_hidden,
        helpful_count=m.helpful_count,
        instructor_response=m.instructor_response,
        instructor_responded_at=m.instructor_responded_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        course_id: uuid.UUID,
        student_id: uuid.UUID,
        enrollment_id: uuid.UUID,
        rating: int,
        body: str,
    ) -> Review:
        model = ReviewModel(
            course_id=course_id,
            user_id=student_id,
            enrollment_id=enrollment_id,
            rating=rating,
            body=body,
            is_hidden=False,
            helpful_count=0,
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, review_id: uuid.UUID) -> Review | None:
        result = await self.db.execute(
            select(ReviewModel).where(ReviewModel.id == review_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_student_and_course(
        self, student_id: uuid.UUID, course_id: uuid.UUID
    ) -> Review | None:
        result = await self.db.execute(
            select(ReviewModel).where(
                ReviewModel.user_id == student_id,
                ReviewModel.course_id == course_id,
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_course(
        self,
        course_id: uuid.UUID,
        sort: str = "newest",
        offset: int = 0,
        limit: int = 20,
    ) -> list[Review]:
        q = select(ReviewModel).where(
            ReviewModel.course_id == course_id,
            ReviewModel.is_hidden == False,  # noqa: E712
        )
        if sort == "newest":
            q = q.order_by(ReviewModel.created_at.desc())
        elif sort == "most_helpful":
            q = q.order_by(ReviewModel.helpful_count.desc())
        elif sort == "highest":
            q = q.order_by(ReviewModel.rating.desc())
        elif sort == "lowest":
            q = q.order_by(ReviewModel.rating.asc())

        q = q.offset(offset).limit(limit)
        result = await self.db.execute(q)
        return [_to_entity(m) for m in result.scalars().all()]

    async def update(
        self,
        review_id: uuid.UUID,
        rating: int | None = None,
        body: str | None = None,
    ) -> Review | None:
        model_result = await self.db.execute(
            select(ReviewModel).where(ReviewModel.id == review_id)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            return None
        if rating is not None:
            model.rating = rating
        if body is not None:
            model.body = body
        model.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(model)
        return _to_entity(model)

    async def delete(self, review_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(ReviewModel).where(ReviewModel.id == review_id)
        )
        await self.db.flush()

    async def set_instructor_response(
        self, review_id: uuid.UUID, response: str
    ) -> Review | None:
        model_result = await self.db.execute(
            select(ReviewModel).where(ReviewModel.id == review_id)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            return None
        model.instructor_response = response
        model.instructor_responded_at = datetime.now(timezone.utc)
        model.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(model)
        return _to_entity(model)

    async def recalc_avg_rating(self, course_id: uuid.UUID) -> float:
        result = await self.db.execute(
            select(func.avg(ReviewModel.rating)).where(
                ReviewModel.course_id == course_id,
                ReviewModel.is_hidden == False,  # noqa: E712
            )
        )
        avg = result.scalar_one_or_none()
        return round(float(avg), 2) if avg else 0.0

    # ── ReviewHelpful ──────────────────────────────────────────────────────

    async def get_helpful(
        self, review_id: uuid.UUID, student_id: uuid.UUID
    ) -> ReviewHelpful | None:
        result = await self.db.execute(
            select(ReviewHelpfulModel).where(
                ReviewHelpfulModel.review_id == review_id,
                ReviewHelpfulModel.user_id == student_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return ReviewHelpful(
            id=model.id,
            review_id=model.review_id,
            student_id=model.user_id,
            created_at=model.created_at,
        )

    async def add_helpful(
        self, review_id: uuid.UUID, student_id: uuid.UUID
    ) -> None:
        model = ReviewHelpfulModel(review_id=review_id, user_id=student_id)
        self.db.add(model)
        await self.db.execute(
            update(ReviewModel)
            .where(ReviewModel.id == review_id)
            .values(helpful_count=ReviewModel.helpful_count + 1)
        )
        await self.db.flush()

    async def remove_helpful(
        self, review_id: uuid.UUID, student_id: uuid.UUID
    ) -> None:
        await self.db.execute(
            delete(ReviewHelpfulModel).where(
                ReviewHelpfulModel.review_id == review_id,
                ReviewHelpfulModel.user_id == student_id,
            )
        )
        await self.db.execute(
            update(ReviewModel)
            .where(ReviewModel.id == review_id)
            .values(helpful_count=ReviewModel.helpful_count - 1)
        )
        await self.db.flush()
    
    async def list_by_instructor(self, instructor_id: uuid.UUID) -> list[Review]:
        from app.infrastructure.db.models.course import CourseModel
        result = await self.db.execute(
            select(ReviewModel)
            .join(CourseModel, ReviewModel.course_id == CourseModel.id)
            .where(
                CourseModel.instructor_id == instructor_id,
                ReviewModel.is_hidden == False,  # noqa: E712
            )
            .order_by(ReviewModel.created_at.desc())
        )
        return [_to_entity(m) for m in result.scalars().all()]