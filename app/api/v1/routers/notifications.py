import uuid as uuid_lib

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.notification_service import NotificationService
from app.core.deps import get_current_user
from app.core.exceptions import raise_400, raise_404
from app.domain.entities.user import User
from app.infrastructure.db.repositories.notification_repository import SQLAlchemyNotificationRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.redis.client import get_redis

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _get_service(db: AsyncSession, redis) -> NotificationService:
    return NotificationService(
        repo=SQLAlchemyNotificationRepository(db),
        redis=redis,
    )


def _fmt(n) -> dict:
    return {
        "id": str(n.id),
        "type": n.type.value,
        "title": n.title,
        "body": n.body,
        "is_read": n.is_read,
        "metadata": n.metadata,
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
async def list_notifications(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    repo = SQLAlchemyNotificationRepository(db)
    notifications = await repo.list_by_user(current_user.id, offset=offset, limit=limit)
    return [_fmt(n) for n in notifications]


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, redis)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read", status_code=200)
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    try:
        nid = uuid_lib.UUID(notification_id)
    except ValueError:
        raise_400("Invalid notification ID")

    service = _get_service(db, redis)
    try:
        await service.mark_read(current_user.id, nid)
    except ValueError:
        raise_404("Notification not found")

    return {"status": "ok"}


@router.post("/read-all", status_code=200)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, redis)
    await service.mark_all_read(current_user.id)
    return {"status": "ok"}