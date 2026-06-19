import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.notification import Notification, NotificationType
from app.infrastructure.db.models.notification import NotificationModel


def _to_entity(m: NotificationModel) -> Notification:
    return Notification(
        id=m.id,
        user_id=m.user_id,
        type=m.type,
        title=m.title,
        body=m.body,
        is_read=m.is_read,
        metadata=m.metadata_,
        created_at=m.created_at,
    )


class SQLAlchemyNotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: str,
        metadata: dict | None = None,
    ) -> Notification:
        model = NotificationModel(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            is_read=False,
            metadata_=metadata,
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return _to_entity(model)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Notification]:
        result = await self.db.execute(
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.is_read.asc(), NotificationModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        result = await self.db.execute(
            select(NotificationModel).where(NotificationModel.id == notification_id)
        )
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def mark_read(self, notification_id: uuid.UUID) -> None:
        await self.db.execute(
            update(NotificationModel)
            .where(NotificationModel.id == notification_id)
            .values(is_read=True)
        )
        await self.db.flush()

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(NotificationModel)
            .where(NotificationModel.user_id == user_id, NotificationModel.is_read == False)  # noqa: E712
            .values(is_read=True)
        )
        await self.db.flush()

    async def count_unread(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read == False,  # noqa: E712
            )
        )
        return result.scalar_one()