import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.tasks import transcode_video
from app.core.deps import get_current_user, require_role
from app.core.exceptions import raise_400, raise_404
from app.domain.entities.media import UploadStatus
from app.domain.entities.user import User, UserRole
from app.infrastructure.db.repositories.media_repository import SQLAlchemyMediaRepository
from app.infrastructure.db.repositories.section_repository import SQLAlchemySectionRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.redis.client import get_redis
from app.infrastructure.storage.minio_client import (
    BUCKET_VIDEOS,
    ensure_buckets,
    generate_presigned_put_url,
)

router = APIRouter(prefix="/media", tags=["Media"])

UPLOAD_URL_TTL = 3600  # 1 час


class UploadUrlRequest(BaseModel):
    lesson_id: uuid.UUID
    content_type: str


class UploadUrlResponse(BaseModel):
    upload_id: str
    upload_url: str
    object_key: str
    expires_in: int


class ConfirmUploadRequest(BaseModel):
    upload_id: uuid.UUID


class MediaStatusResponse(BaseModel):
    upload_id: str
    status: str


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    body: UploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    allowed = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
    if body.content_type not in allowed:
        raise_400(f"Invalid content type. Allowed: {', '.join(allowed)}")

    ensure_buckets()

    ext = body.content_type.split("/")[1]
    object_key = f"{body.lesson_id}/{uuid.uuid4()}.{ext}"

    upload_url = generate_presigned_put_url(
        bucket=BUCKET_VIDEOS,
        object_key=object_key,
        expires_seconds=UPLOAD_URL_TTL,
    )

    repo = SQLAlchemyMediaRepository(db)
    upload = await repo.create(lesson_id=body.lesson_id, object_key=object_key)

    return UploadUrlResponse(
        upload_id=str(upload.id),
        upload_url=upload_url,
        object_key=object_key,
        expires_in=UPLOAD_URL_TTL,
    )


@router.post("/confirm-upload", status_code=200)
async def confirm_upload(
    body: ConfirmUploadRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    repo = SQLAlchemyMediaRepository(db)
    upload = await repo.get_by_id(body.upload_id)
    if not upload:
        raise_404("Upload not found")

    await repo.update_status(body.upload_id, UploadStatus.PROCESSING)

    await redis.set(f"upload:status:{body.upload_id}", UploadStatus.PROCESSING, ex=3600 * 24)

    transcode_video.delay(str(body.upload_id))

    return {"upload_id": str(body.upload_id), "status": UploadStatus.PROCESSING}


@router.get("/status/{upload_id}", response_model=MediaStatusResponse)
async def get_upload_status(
    upload_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    cached = await redis.get(f"upload:status:{upload_id}")
    if cached:
        return MediaStatusResponse(upload_id=str(upload_id), status=cached)

    repo = SQLAlchemyMediaRepository(db)
    upload = await repo.get_by_id(upload_id)
    if not upload:
        raise_404("Upload not found")

    return MediaStatusResponse(upload_id=str(upload_id), status=upload.status)