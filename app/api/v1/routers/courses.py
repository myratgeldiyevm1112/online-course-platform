import uuid as uuid_lib

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.course import (
    CourseListResponse,
    CourseResponse,
    CreateCourseRequest,
    UpdateCourseRequest,
)
from app.application.services.course_service import CourseService
from app.core.deps import get_current_user, require_role
from app.core.exceptions import raise_400, raise_403, raise_404
from app.domain.entities.course import DifficultyLevel
from app.domain.entities.user import User, UserRole
from app.infrastructure.db.repositories.course_repository import (
    SQLAlchemyCategoryRepository,
    SQLAlchemyCourseRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.storage.minio_client import ensure_buckets, upload_thumbnail

router = APIRouter(prefix="/courses", tags=["Courses"])


def _get_service(db: AsyncSession) -> CourseService:
    return CourseService(
        SQLAlchemyCourseRepository(db),
        SQLAlchemyCategoryRepository(db),
    )


def _to_response(course) -> CourseResponse:
    return CourseResponse(
        id=str(course.id),
        instructor_id=str(course.instructor_id),
        category_id=str(course.category_id) if course.category_id else None,
        title=course.title,
        slug=course.slug,
        description=course.description,
        short_description=course.short_description,
        price=course.price,
        thumbnail_url=course.thumbnail_url,
        language=course.language,
        difficulty=course.difficulty.value,
        status=course.status.value,
        total_lessons=course.total_lessons,
        total_duration_seconds=course.total_duration_seconds,
        avg_rating=course.avg_rating,
        total_enrolled=course.total_enrolled,
        is_featured=course.is_featured,
    )


@router.post("", response_model=CourseResponse, status_code=201)
async def create_course(
    body: CreateCourseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        difficulty = DifficultyLevel(body.difficulty)
    except ValueError:
        raise_400(f"Invalid difficulty: {body.difficulty}")

    service = _get_service(db)
    try:
        course = await service.create_course(
            instructor_id=current_user.id,
            title=body.title,
            description=body.description,
            short_description=body.short_description,
            price=body.price,
            category_id=body.category_id,
            language=body.language,
            difficulty=difficulty,
        )
    except ValueError as e:
        raise_400(str(e))
    return _to_response(course)


@router.get("/instructor/me", response_model=CourseListResponse)
async def get_my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    service = _get_service(db)
    courses = await service.list_instructor_courses(current_user.id)
    return CourseListResponse(
        items=[_to_response(c) for c in courses],
        total=len(courses),
    )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
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
        course = await service.get_course(
            course_id=cid,
            requester_id=current_user.id,
            is_instructor=current_user.is_instructor or current_user.is_admin,
        )
    except ValueError:
        raise_404("Course not found")
    return _to_response(course)


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    body: UpdateCourseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    service = _get_service(db)
    try:
        course = await service.update_course(
            course_id=cid,
            instructor_id=current_user.id,
            **body.model_dump(exclude_none=True),
        )
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _to_response(course)


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    service = _get_service(db)
    try:
        await service.soft_delete(cid, current_user.id)
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))


@router.post("/{course_id}/publish", response_model=CourseResponse)
async def publish_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    service = _get_service(db)
    try:
        course = await service.publish_course(cid, current_user.id)
    except ValueError as e:
        raise_400(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _to_response(course)


@router.post("/{course_id}/unpublish", response_model=CourseResponse)
async def unpublish_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    service = _get_service(db)
    try:
        course = await service.unpublish_course(cid, current_user.id)
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _to_response(course)


@router.post("/{course_id}/thumbnail", response_model=CourseResponse)
async def upload_course_thumbnail(
    course_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    ensure_buckets()
    file_data = await file.read()
    try:
        thumbnail_url = await upload_thumbnail(file_data, file.content_type, cid)
    except ValueError as e:
        raise_400(str(e))

    service = _get_service(db)
    try:
        course = await service.update_thumbnail(cid, current_user.id, thumbnail_url)
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _to_response(course)