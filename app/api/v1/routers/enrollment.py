import uuid as uuid_lib

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.enrollment import (
    EnrollResponse,
    EnrolledCourseResponse,
    LessonProgressResponse,
)
from app.application.services.enrollment_service import EnrollmentService
from app.core.deps import get_current_user
from app.core.exceptions import raise_400, raise_403, raise_404
from app.domain.entities.user import User
from app.infrastructure.db.repositories.course_repository import SQLAlchemyCourseRepository
from app.infrastructure.db.repositories.enrollment_repository import (
    SQLAlchemyEnrollmentRepository,
    SQLAlchemyProgressRepository,
)
from app.infrastructure.db.repositories.section_repository import (
    SQLAlchemyLessonRepository,
    SQLAlchemySectionRepository,
)
from app.infrastructure.db.session import get_db

router = APIRouter(tags=["Enrollment"])


def _get_service(db: AsyncSession) -> EnrollmentService:
    return EnrollmentService(
        SQLAlchemyEnrollmentRepository(db),
        SQLAlchemyCourseRepository(db),
        SQLAlchemyProgressRepository(db),
    )


@router.get("/enrollments/my", response_model=list[EnrolledCourseResponse])
async def get_enrolled_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db)
    items = await service.get_enrolled_courses(current_user.id)
    return [
        EnrolledCourseResponse(
            enrollment_id=str(item["enrollment"].id),
            course_id=str(item["course"].id),
            course_title=item["course"].title,
            course_slug=item["course"].slug,
            thumbnail_url=item["course"].thumbnail_url,
            progress_percent=item["progress_percent"],
            status=item["enrollment"].status.value,
        )
        for item in items
    ]


@router.post("/courses/{course_id}/enroll", response_model=EnrollResponse, status_code=201)
async def enroll_free_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    service = _get_service(db)
    try:
        enrollment = await service.enroll(current_user.id, cid)
    except ValueError as e:
        raise_400(str(e))

    return EnrollResponse(
        id=str(enrollment.id),
        student_id=str(enrollment.student_id),
        course_id=str(enrollment.course_id),
        status=enrollment.status.value,
        enrolled_at=enrollment.enrolled_at.isoformat(),
    )


@router.post("/lessons/{lesson_id}/complete", response_model=LessonProgressResponse)
async def mark_lesson_complete(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        lid = uuid_lib.UUID(lesson_id)
    except ValueError:
        raise_400("Invalid lesson ID")

    service = _get_service(db)
    try:
        progress = await service.mark_lesson_complete(
            student_id=current_user.id,
            lesson_id=lid,
            section_repo=SQLAlchemySectionRepository(db),
            lesson_repo=SQLAlchemyLessonRepository(db),
        )
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))

    return LessonProgressResponse(
        lesson_id=str(progress.lesson_id),
        is_completed=progress.is_completed,
        watch_seconds=progress.watch_seconds,
    )


@router.get("/courses/{course_id}/progress")
async def get_course_progress(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    enrollment_repo = SQLAlchemyEnrollmentRepository(db)
    enrollment = await enrollment_repo.get_by_student_and_course(current_user.id, cid)
    if not enrollment:
        raise_404("Not enrolled in this course")

    service = _get_service(db)
    percent = await service.get_progress(enrollment.id, cid)
    progresses = await SQLAlchemyProgressRepository(db).list_by_enrollment(enrollment.id)

    return {
        "course_id": course_id,
        "progress_percent": percent,
        "lessons": [
            {
                "lesson_id": str(p.lesson_id),
                "is_completed": p.is_completed,
                "watch_seconds": p.watch_seconds,
            }
            for p in progresses
        ],
    }