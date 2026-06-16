import uuid as uuid_lib

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.exceptions import raise_400, raise_403, raise_404
from app.domain.entities.user import User, UserRole
from app.infrastructure.db.repositories.attachment_repository import SQLAlchemyAttachmentRepository
from app.infrastructure.db.repositories.section_repository import (
    SQLAlchemyLessonRepository,
    SQLAlchemySectionRepository,
)
from app.infrastructure.db.repositories.course_repository import SQLAlchemyCourseRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.storage.minio_client import minio_client, ensure_buckets
import io

router = APIRouter(tags=["Attachments"])

BUCKET_ATTACHMENTS = "course-attachments"
MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "text/plain",
}


class AttachmentResponse(BaseModel):
    id: str
    lesson_id: str
    filename: str
    size_bytes: int


class StreamUrlResponse(BaseModel):
    stream_url: str
    expires_in: int


@router.get("/lessons/{lesson_id}/stream", response_model=StreamUrlResponse)
async def get_stream_url(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        lid = uuid_lib.UUID(lesson_id)
    except ValueError:
        raise_400("Invalid lesson ID")

    lesson_repo = SQLAlchemyLessonRepository(db)
    lesson = await lesson_repo.get_by_id(lid)
    if not lesson:
        raise_404("Lesson not found")

    if not lesson.content_url:
        raise_404("No video available for this lesson")

    # Check access: instructor owner or preview lesson
    if not lesson.is_preview:
        section_repo = SQLAlchemySectionRepository(db)
        section = await section_repo.get_by_id(lesson.section_id)
        course_repo = SQLAlchemyCourseRepository(db)
        course = await course_repo.get_by_id(section.course_id)

        is_owner = course.instructor_id == current_user.id
        if not is_owner:
            raise_403("Access denied. Enroll in the course to watch this lesson.")

    from datetime import timedelta
    stream_url = minio_client.presigned_get_object(
        bucket_name="courses-videos",
        object_name=lesson.content_url,
        expires=timedelta(hours=4),
    )

    return StreamUrlResponse(stream_url=stream_url, expires_in=4 * 3600)


@router.post("/lessons/{lesson_id}/attachments", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(
    lesson_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        lid = uuid_lib.UUID(lesson_id)
    except ValueError:
        raise_400("Invalid lesson ID")

    if file.content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise_400(f"Invalid file type. Allowed: pdf, zip, txt")

    file_data = await file.read()
    if len(file_data) > MAX_ATTACHMENT_SIZE:
        raise_400("File too large. Max size is 50MB")

    ensure_buckets()
    object_key = f"{lesson_id}/{uuid_lib.uuid4()}/{file.filename}"
    minio_client.put_object(
        bucket_name=BUCKET_ATTACHMENTS,
        object_name=object_key,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=file.content_type,
    )

    repo = SQLAlchemyAttachmentRepository(db)
    attachment = await repo.create(
        lesson_id=lid,
        filename=file.filename,
        object_key=object_key,
        size_bytes=len(file_data),
    )

    return AttachmentResponse(
        id=str(attachment.id),
        lesson_id=str(attachment.lesson_id),
        filename=attachment.filename,
        size_bytes=attachment.size_bytes,
    )


@router.get("/lessons/{lesson_id}/attachments", response_model=list[AttachmentResponse])
async def list_attachments(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        lid = uuid_lib.UUID(lesson_id)
    except ValueError:
        raise_400("Invalid lesson ID")

    repo = SQLAlchemyAttachmentRepository(db)
    attachments = await repo.list_by_lesson(lid)
    return [
        AttachmentResponse(
            id=str(a.id),
            lesson_id=str(a.lesson_id),
            filename=a.filename,
            size_bytes=a.size_bytes,
        )
        for a in attachments
    ]


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        aid = uuid_lib.UUID(attachment_id)
    except ValueError:
        raise_400("Invalid attachment ID")

    repo = SQLAlchemyAttachmentRepository(db)
    attachment = await repo.get_by_id(aid)
    if not attachment:
        raise_404("Attachment not found")

    from datetime import timedelta
    url = minio_client.presigned_get_object(
        bucket_name=BUCKET_ATTACHMENTS,
        object_name=attachment.object_key,
        expires=timedelta(hours=1),
    )
    return {"download_url": url, "filename": attachment.filename}


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        aid = uuid_lib.UUID(attachment_id)
    except ValueError:
        raise_400("Invalid attachment ID")

    repo = SQLAlchemyAttachmentRepository(db)
    attachment = await repo.get_by_id(aid)
    if not attachment:
        raise_404("Attachment not found")

    try:
        minio_client.remove_object(BUCKET_ATTACHMENTS, attachment.object_key)
    except Exception:
        pass

    await repo.delete(aid)