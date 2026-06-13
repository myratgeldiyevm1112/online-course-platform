import io
import uuid

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
BUCKET_PORTFOLIOS = "course-thumbnails"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB

BUCKET_THUMBNAILS = "course-thumbnails"
MAX_THUMBNAIL_SIZE = 2 * 1024 * 1024  # 2MB

def ensure_buckets() -> None:
    for bucket in [BUCKET_AVATARS, BUCKET_PORTFOLIOS]:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)


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
        raise ValueError(f"Invalid file type. Allowed: jpeg, png, webp")
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