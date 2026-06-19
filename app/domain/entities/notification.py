import uuid
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    ENROLLMENT_CONFIRMED = "enrollment_confirmed"
    PAYMENT_RECEIVED = "payment_received"
    REVIEW_RECEIVED = "review_received"
    INSTRUCTOR_RESPONSE = "instructor_response"
    CERTIFICATE_READY = "certificate_ready"
    COURSE_PUBLISHED = "course_published"
    COURSE_UPDATED = "course_updated"
    REFUND_PROCESSED = "refund_processed"


class Notification:
    def __init__(
        self,
        id: uuid.UUID,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: str,
        is_read: bool,
        metadata: dict | None,
        created_at: datetime,
    ):
        self.id = id
        self.user_id = user_id
        self.type = type
        self.title = title
        self.body = body
        self.is_read = is_read
        self.metadata = metadata or {}
        self.created_at = created_at