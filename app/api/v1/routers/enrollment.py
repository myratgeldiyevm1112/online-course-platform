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
        # Wire email + notification tasks
        from app.tasks.email_tasks import send_enrollment_email
        course = await SQLAlchemyCourseRepository(db).get_by_id(cid)
        send_enrollment_email.delay(
            to=current_user.email,
            name=current_user.email,
            course_title=course.title if course else "",
            course_id=str(cid),
        )
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

@router.get("/enrollments/{enrollment_id}")
async def get_enrollment(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        eid = uuid_lib.UUID(enrollment_id)
    except ValueError:
        raise_400("Invalid enrollment ID")

    repo = SQLAlchemyEnrollmentRepository(db)
    enrollment = await repo.get_by_id(eid)
    if not enrollment:
        raise_404("Enrollment not found")
    if enrollment.student_id != current_user.id:
        raise_403("Access denied")

    return {
        "id": str(enrollment.id),
        "student_id": str(enrollment.student_id),
        "course_id": str(enrollment.course_id),
        "status": enrollment.status.value,
        "payment_intent_id": enrollment.payment_intent_id,
        "enrolled_at": enrollment.enrolled_at.isoformat(),
    }


@router.post("/enrollments/{enrollment_id}/refund")
async def request_refund(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import timedelta
    import stripe
    from app.core.config import settings
    from app.domain.entities.enrollment import EnrollmentStatus

    stripe.api_key = settings.stripe_secret_key

    try:
        eid = uuid_lib.UUID(enrollment_id)
    except ValueError:
        raise_400("Invalid enrollment ID")

    repo = SQLAlchemyEnrollmentRepository(db)
    enrollment = await repo.get_by_id(eid)
    if not enrollment:
        raise_404("Enrollment not found")
    if enrollment.student_id != current_user.id:
        raise_403("Access denied")
    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise_400("Enrollment is not active")
    if not enrollment.payment_intent_id:
        raise_400("No payment found for this enrollment")

    # 30-day refund window
    from datetime import datetime, timezone
    days_since = (datetime.now(timezone.utc) - enrollment.enrolled_at).days
    if days_since > 30:
        raise_400("Refund window has expired (30 days)")

    try:
        stripe.Refund.create(payment_intent=enrollment.payment_intent_id)
    except stripe.error.StripeError as e:
        raise_400(str(e))

    await repo.update_status(eid, EnrollmentStatus.REFUNDED)
    return {"status": "refunded", "enrollment_id": enrollment_id}


@router.post("/lessons/{lesson_id}/progress")
async def update_watch_progress(
    lesson_id: str,
    watch_seconds: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        lid = uuid_lib.UUID(lesson_id)
    except ValueError:
        raise_400("Invalid lesson ID")

    lesson_repo = SQLAlchemyLessonRepository(db)
    section_repo = SQLAlchemySectionRepository(db)

    lesson = await lesson_repo.get_by_id(lid)
    if not lesson:
        raise_404("Lesson not found")

    section = await section_repo.get_by_id(lesson.section_id)
    enrollment_repo = SQLAlchemyEnrollmentRepository(db)
    enrollment = await enrollment_repo.get_by_student_and_course(
        current_user.id, section.course_id
    )
    if not enrollment or not enrollment.is_active:
        raise_403("Not enrolled in this course")

    progress_repo = SQLAlchemyProgressRepository(db)
    await progress_repo.update_watch_seconds(enrollment.id, lid, watch_seconds)
    return {"lesson_id": lesson_id, "watch_seconds": watch_seconds}


@router.get("/courses/{course_id}/resume")
async def get_resume_lesson(
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

    progress_repo = SQLAlchemyProgressRepository(db)
    progresses = await progress_repo.list_by_enrollment(enrollment.id)

    # Find last watched lesson
    last = sorted(
        [p for p in progresses if p.last_watched_at],
        key=lambda p: p.last_watched_at,
        reverse=True,
    )
    if last:
        return {"lesson_id": str(last[0].lesson_id), "watch_seconds": last[0].watch_seconds}

    return {"lesson_id": None, "watch_seconds": 0}