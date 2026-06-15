import uuid
from datetime import datetime
from enum import Enum


class UploadStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class MediaUpload:
    def __init__(
        self,
        id: uuid.UUID,
        lesson_id: uuid.UUID,
        object_key: str,
        status: UploadStatus,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.lesson_id = lesson_id
        self.object_key = object_key
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
