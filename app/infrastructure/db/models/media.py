import uuid
from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.entities.media import UploadStatus
from app.infrastructure.db.base import BaseModel


class MediaUploadModel(BaseModel):
    __tablename__ = "media_uploads"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[UploadStatus] = mapped_column(
        SAEnum(UploadStatus, name="uploadstatus"), nullable=False,
        default=UploadStatus.PENDING,
    )