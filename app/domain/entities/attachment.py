import uuid
from datetime import datetime


class LessonAttachment:
    def __init__(
        self,
        id: uuid.UUID,
        lesson_id: uuid.UUID,
        filename: str,
        object_key: str,
        size_bytes: int,
        created_at: datetime,
    ):
        self.id = id
        self.lesson_id = lesson_id
        self.filename = filename
        self.object_key = object_key
        self.size_bytes = size_bytes
        self.created_at = created_at