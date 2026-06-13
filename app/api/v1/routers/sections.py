import uuid as uuid_lib

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.section import (
    CreateLessonRequest,
    CreateSectionRequest,
    CurriculumResponse,
    LessonResponse,
    SectionResponse,
    UpdateLessonRequest,
    UpdateSectionRequest,
)
from app.application.services.section_service import LessonService, SectionService
from app.core.deps import get_current_user, require_role
from app.core.exceptions import raise_400, raise_403, raise_404
from app.domain.entities.course import LessonType
from app.domain.entities.user import User, UserRole
from app.infrastructure.db.repositories.course_repository import SQLAlchemyCourseRepository
from app.infrastructure.db.repositories.section_repository import (
    SQLAlchemyLessonRepository,
    SQLAlchemySectionRepository,
)
from app.infrastructure.db.session import get_db

router = APIRouter(tags=["Sections & Lessons"])


def _section_service(db: AsyncSession) -> SectionService:
    return SectionService(
        SQLAlchemySectionRepository(db),
        SQLAlchemyCourseRepository(db),
    )


def _lesson_service(db: AsyncSession) -> LessonService:
    return LessonService(
        SQLAlchemyLessonRepository(db),
        SQLAlchemySectionRepository(db),
        SQLAlchemyCourseRepository(db),
    )


def _section_to_response(s) -> SectionResponse:
    return SectionResponse(
        id=str(s.id),
        course_id=str(s.course_id),
        title=s.title,
        position=s.position,
    )


def _lesson_to_response(l) -> LessonResponse:
    return LessonResponse(
        id=str(l.id),
        section_id=str(l.section_id),
        title=l.title,
        position=l.position,
        lesson_type=l.lesson_type.value,
        content_url=l.content_url,
        article_body=l.article_body,
        duration_seconds=l.duration_seconds,
        is_preview=l.is_preview,
    )


# --- Section endpoints ---
@router.post("/courses/{course_id}/sections", response_model=SectionResponse, status_code=201)
async def create_section(
    course_id: str,
    body: CreateSectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    try:
        section = await _section_service(db).create_section(cid, current_user.id, body.title)
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _section_to_response(section)


@router.patch("/courses/{course_id}/sections/{section_id}", response_model=SectionResponse)
async def update_section(
    course_id: str,
    section_id: str,
    body: UpdateSectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        sid = uuid_lib.UUID(section_id)
    except ValueError:
        raise_400("Invalid section ID")

    try:
        section = await _section_service(db).update_section(
            sid, current_user.id,
            title=body.title,
            position=body.position,
        )
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _section_to_response(section)


@router.delete("/courses/{course_id}/sections/{section_id}", status_code=204)
async def delete_section(
    course_id: str,
    section_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        sid = uuid_lib.UUID(section_id)
    except ValueError:
        raise_400("Invalid section ID")

    try:
        await _section_service(db).delete_section(sid, current_user.id)
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))


# --- Lesson endpoints ---
@router.post("/sections/{section_id}/lessons", response_model=LessonResponse, status_code=201)
async def create_lesson(
    section_id: str,
    body: CreateLessonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        sid = uuid_lib.UUID(section_id)
    except ValueError:
        raise_400("Invalid section ID")

    try:
        lesson_type = LessonType(body.lesson_type)
    except ValueError:
        raise_400(f"Invalid lesson type: {body.lesson_type}")

    try:
        lesson = await _lesson_service(db).create_lesson(
            section_id=sid,
            instructor_id=current_user.id,
            title=body.title,
            lesson_type=lesson_type,
            article_body=body.article_body,
            is_preview=body.is_preview,
        )
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _lesson_to_response(lesson)


@router.patch("/sections/{section_id}/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    section_id: str,
    lesson_id: str,
    body: UpdateLessonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        lid = uuid_lib.UUID(lesson_id)
    except ValueError:
        raise_400("Invalid lesson ID")

    try:
        lesson = await _lesson_service(db).update_lesson(
            lid, current_user.id,
            **body.model_dump(exclude_none=True),
        )
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))
    return _lesson_to_response(lesson)


@router.delete("/sections/{section_id}/lessons/{lesson_id}", status_code=204)
async def delete_lesson(
    section_id: str,
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    try:
        lid = uuid_lib.UUID(lesson_id)
    except ValueError:
        raise_400("Invalid lesson ID")

    try:
        await _lesson_service(db).delete_lesson(lid, current_user.id)
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))


# --- Curriculum ---
@router.get("/courses/{course_id}/curriculum", response_model=CurriculumResponse)
async def get_curriculum(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    section_svc = _section_service(db)
    lesson_svc = _lesson_service(db)

    sections = await section_svc.list_sections(cid)
    result = []
    for section in sections:
        lessons = await lesson_svc.list_lessons(section.id)
        result.append({
            "id": str(section.id),
            "title": section.title,
            "position": section.position,
            "lessons": [_lesson_to_response(l).__dict__ for l in lessons],
        })

    return CurriculumResponse(sections=result)