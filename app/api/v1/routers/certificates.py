import uuid as uuid_lib

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import raise_400, raise_404
from app.domain.entities.user import User
from app.infrastructure.db.repositories.certificate_repository import SQLAlchemyCertificateRepository
from app.infrastructure.db.session import get_db

router = APIRouter(tags=["Certificates"])


def _fmt(cert) -> dict:
    return {
        "id": str(cert.id),
        "enrollment_id": str(cert.enrollment_id),
        "student_name": cert.student_name,
        "course_title": cert.course_title,
        "instructor_name": cert.instructor_name,
        "issued_at": cert.issued_at.isoformat(),
        "verification_uuid": str(cert.verification_uuid),
        "pdf_url": cert.pdf_url,
    }


@router.get("/certificates/{verification_uuid}/verify")
async def verify_certificate(
    verification_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        vuuid = uuid_lib.UUID(verification_uuid)
    except ValueError:
        raise_400("Invalid verification UUID")

    repo = SQLAlchemyCertificateRepository(db)
    cert = await repo.get_by_verification_uuid(vuuid)
    if not cert:
        raise_404("Certificate not found")

    return {
        "student_name": cert.student_name,
        "course_title": cert.course_title,
        "instructor_name": cert.instructor_name,
        "issued_at": cert.issued_at.isoformat(),
        "verification_uuid": str(cert.verification_uuid),
    }


@router.get("/certificates/mine")
async def my_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SQLAlchemyCertificateRepository(db)
    certs = await repo.list_by_student(current_user.id)
    return [_fmt(c) for c in certs]