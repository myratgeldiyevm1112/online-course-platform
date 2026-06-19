import json
import uuid

from app.domain.entities.notification import Notification, NotificationType
from app.infrastructure.db.repositories.notification_repository import SQLAlchemyNotificationRepository

UNREAD_CACHE_TTL = 60 * 5  # 5 минут
OFFLINE_QUEUE_TTL = 60 * 60 * 24 * 7  # 7 дней


class NotificationService:
    def __init__(
        self,
        repo: SQLAlchemyNotificationRepository,
        redis=None,
        ws_manager=None,
    ):
        self.repo = repo
        self.redis = redis
        self.ws_manager = ws_manager

    async def send(
        self,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: str,
        metadata: dict | None = None,
    ) -> Notification:
        # 1. Persist to DB
        notification = await self.repo.create(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            metadata=metadata,
        )

        # 2. Invalidate unread cache
        if self.redis:
            await self.redis.delete(f"notifications:unread:{user_id}")

        payload = json.dumps({
            "id": str(notification.id),
            "type": notification.type.value,
            "title": notification.title,
            "body": notification.body,
            "created_at": notification.created_at.isoformat(),
        })

        # 3. Push live via WebSocket or offline queue
        if self.ws_manager and self.ws_manager.is_connected(user_id):
            await self.ws_manager.send(user_id, payload)
        elif self.redis:
            queue_key = f"notifications:offline:{user_id}"
            await self.redis.lpush(queue_key, payload)
            await self.redis.expire(queue_key, OFFLINE_QUEUE_TTL)

        return notification

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        if self.redis:
            cache_key = f"notifications:unread:{user_id}"
            cached = await self.redis.get(cache_key)
            if cached:
                return int(cached)

        count = await self.repo.count_unread(user_id)

        if self.redis:
            await self.redis.setex(cache_key, UNREAD_CACHE_TTL, str(count))

        return count

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        notification = await self.repo.get_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            raise ValueError("Notification not found")
        await self.repo.mark_read(notification_id)
        if self.redis:
            await self.redis.delete(f"notifications:unread:{user_id}")

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.repo.mark_all_read(user_id)
        if self.redis:
            await self.redis.delete(f"notifications:unread:{user_id}")