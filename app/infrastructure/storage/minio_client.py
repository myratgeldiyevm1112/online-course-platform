import io
import uuid
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

BUCKET_AVATARS = "user-avatars"
BUCKET_THUMBNAILS = "course-thumbnails"
BUCKET_VIDEOS = "courses-videos"
BUCKET_ATTACHMENTS = "course-attachments"
BUCKET_CERTIFICATES = "certificates"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}

MAX_AVATAR_SIZE = 5 * 1024 * 1024       # 5MB
MAX_THUMBNAIL_SIZE = 2 * 1024 * 1024    # 2MB


def ensure_buckets() -> None:
    private_buckets = [BUCKET_VIDEOS, BUCKET_ATTACHMENTS, BUCKET_CERTIFICATES]
    public_buckets = [BUCKET_AVATARS, BUCKET_THUMBNAILS]

    for bucket in private_buckets + public_buckets:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)


def generate_presigned_put_url(
    bucket: str,
    object_key: str,
    expires_seconds: int = 3600,
) -> str:
    return minio_client.presigned_put_object(
        bucket_name=bucket,
        object_name=object_key,
        expires=timedelta(seconds=expires_seconds),
    )


def generate_presigned_get_url(
    bucket: str,
    object_key: str,
    expires_seconds: int = 3600 * 4,  # 4 часа
) -> str:
    return minio_client.presigned_get_object(
        bucket_name=bucket,
        object_name=object_key,
        expires=timedelta(seconds=expires_seconds),
    )


async def upload_avatar(file_data: bytes, content_type: str, user_id: uuid.UUID) -> str:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Invalid file type: {content_type}. Allowed: jpeg, png, webp")
    if len(file_data) > MAX_AVATAR_SIZE:
        raise ValueError("File too large. Max size is 5MB")
    ext = content_type.split("/")[1]
    object_name = f"{user_id}/avatar.{ext}"
    minio_client.put_object(
        bucket_name=BUCKET_AVATARS,
        object_name=object_name,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return f"{settings.minio_endpoint}/{BUCKET_AVATARS}/{object_name}"


async def upload_thumbnail(
    file_data: bytes, content_type: str, course_id: uuid.UUID
) -> str:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Invalid file type. Allowed: jpeg, png, webp")
    if len(file_data) > MAX_THUMBNAIL_SIZE:
        raise ValueError("File too large. Max size is 2MB")
    ext = content_type.split("/")[1]
    object_name = f"{course_id}/thumbnail.{ext}"
    minio_client.put_object(
        bucket_name=BUCKET_THUMBNAILS,
        object_name=object_name,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return f"{settings.minio_endpoint}/{BUCKET_THUMBNAILS}/{object_name}"