import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.attachment import LessonAttachment
from app.infrastructure.db.models.media import LessonAttachmentModel


class SQLAlchemyAttachmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        lesson_id: uuid.UUID,
        filename: str,
        object_key: str,
        size_bytes: int,
    ) -> LessonAttachment:
        model = LessonAttachmentModel(
            id=uuid.uuid4(),
            lesson_id=lesson_id,
            filename=filename,
            object_key=object_key,
            size_bytes=size_bytes,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, attachment_id: uuid.UUID) -> LessonAttachment | None:
        result = await self.session.execute(
            select(LessonAttachmentModel).where(
                LessonAttachmentModel.id == attachment_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_lesson(self, lesson_id: uuid.UUID) -> list[LessonAttachment]:
        result = await self.session.execute(
            select(LessonAttachmentModel).where(
                LessonAttachmentModel.lesson_id == lesson_id
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, attachment_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(LessonAttachmentModel).where(
                LessonAttachmentModel.id == attachment_id
            )
        )
        model = result.scalar_one()
        await self.session.delete(model)
        await self.session.flush()

    @staticmethod
    def _to_entity(model: LessonAttachmentModel) -> LessonAttachment:
        return LessonAttachment(
            id=model.id,
            lesson_id=model.lesson_id,
            filename=model.filename,
            object_key=model.object_key,
            size_bytes=model.size_bytes,
            created_at=model.created_at,
        )