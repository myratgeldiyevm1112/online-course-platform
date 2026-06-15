import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities.media import MediaUpload, UploadStatus
from app.infrastructure.db.models.media import MediaUploadModel


class SQLAlchemyMediaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, lesson_id: uuid.UUID, object_key: str) -> MediaUpload:
        model = MediaUploadModel(
            id=uuid.uuid4(),
            lesson_id=lesson_id,
            object_key=object_key,
            status=UploadStatus.PENDING,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, upload_id: uuid.UUID) -> MediaUpload | None:
        result = await self.session.execute(
            select(MediaUploadModel).where(MediaUploadModel.id == upload_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update_status(self, upload_id: uuid.UUID, status: UploadStatus) -> None:
        result = await self.session.execute(
            select(MediaUploadModel).where(MediaUploadModel.id == upload_id)
        )
        model = result.scalar_one()
        model.status = status
        await self.session.flush()

    @staticmethod
    def _to_entity(model: MediaUploadModel) -> MediaUpload:
        return MediaUpload(
            id=model.id,
            lesson_id=model.lesson_id,
            object_key=model.object_key,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )