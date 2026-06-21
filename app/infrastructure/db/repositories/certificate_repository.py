import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.certificate import Certificate
from app.infrastructure.db.models.certificate import CertificateModel


def _to_entity(m: CertificateModel) -> Certificate:
    return Certificate(
        id=m.id,
        enrollment_id=m.enrollment_id,
        student_name=m.student_name,
        course_title=m.course_title,
        instructor_name=m.instructor_name,
        issued_at=m.issued_at,
        verification_uuid=m.verification_uuid,
        pdf_url=m.pdf_url,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyCertificateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        enrollment_id: uuid.UUID,
        student_name: str,
        course_title: str,
        instructor_name: str,
        pdf_url: str,
    ) -> Certificate:
        model = CertificateModel(
            enrollment_id=enrollment_id,
            student_name=student_name,
            course_title=course_title,
            instructor_name=instructor_name,
            issued_at=datetime.now(timezone.utc),
            verification_uuid=uuid.uuid4(),
            pdf_url=pdf_url,
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return _to_entity(model)

    async def get_by_verification_uuid(self, verification_uuid: uuid.UUID) -> Certificate | None:
        result = await self.db.execute(
            select(CertificateModel).where(
                CertificateModel.verification_uuid == verification_uuid
            )
        )
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def get_by_enrollment(self, enrollment_id: uuid.UUID) -> Certificate | None:
        result = await self.db.execute(
            select(CertificateModel).where(
                CertificateModel.enrollment_id == enrollment_id
            )
        )
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def list_by_student(self, student_id: uuid.UUID) -> list[Certificate]:
        from app.infrastructure.db.models.enrollment import EnrollmentModel
        result = await self.db.execute(
            select(CertificateModel)
            .join(EnrollmentModel, CertificateModel.enrollment_id == EnrollmentModel.id)
            .where(EnrollmentModel.student_id == student_id)
            .order_by(CertificateModel.issued_at.desc())
        )
        return [_to_entity(m) for m in result.scalars().all()]