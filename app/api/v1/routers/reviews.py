import uuid as uuid_lib

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.review import (
    InstructorResponseCreate, ReviewCreate, ReviewResponse, ReviewUpdate,
)
from app.application.services.review_service import ReviewService
from app.core.deps import get_current_user
from app.core.exceptions import raise_400, raise_403, raise_404
from app.domain.entities.user import User, UserRole
from app.infrastructure.db.repositories.course_repository import SQLAlchemyCourseRepository
from app.infrastructure.db.repositories.enrollment_repository import SQLAlchemyEnrollmentRepository
from app.infrastructure.db.repositories.review_repository import SQLAlchemyReviewRepository
from app.infrastructure.db.session import get_db

router = APIRouter(tags=["Reviews"])


def _get_service(db: AsyncSession) -> ReviewService:
    return ReviewService(
        SQLAlchemyReviewRepository(db),
        SQLAlchemyEnrollmentRepository(db),
        SQLAlchemyCourseRepository(db),
    )


def _fmt(review) -> ReviewResponse:
    return ReviewResponse(
        id=str(review.id),
        course_id=str(review.course_id),
        student_id=str(review.student_id),
        rating=review.rating,
        body=review.body,
        helpful_count=review.helpful_count,
        instructor_response=review.instructor_response,
        instructor_responded_at=(
            review.instructor_responded_at.isoformat()
            if review.instructor_responded_at else None
        ),
        created_at=review.created_at.isoformat(),
        updated_at=review.updated_at.isoformat(),
    )


@router.post("/courses/{course_id}/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    course_id: str,
    body: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    service = _get_service(db)
    try:
        review = await service.submit_review(
            student_id=current_user.id,
            course_id=cid,
            rating=body.rating,
            body=body.body,
        )
    except ValueError as e:
        raise_400(str(e))
    except PermissionError as e:
        raise_403(str(e))

    return _fmt(review)


@router.get("/courses/{course_id}/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    course_id: str,
    sort: str = Query("newest", pattern="^(newest|most_helpful|highest|lowest)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid_lib.UUID(course_id)
    except ValueError:
        raise_400("Invalid course ID")

    review_repo = SQLAlchemyReviewRepository(db)
    reviews = await review_repo.list_by_course(cid, sort=sort, offset=offset, limit=limit)
    return [_fmt(r) for r in reviews]


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    body: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rid = uuid_lib.UUID(review_id)
    except ValueError:
        raise_400("Invalid review ID")

    service = _get_service(db)
    try:
        updated = await service.edit_review(
            student_id=current_user.id,
            review_id=rid,
            rating=body.rating,
            body=body.body,
        )
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))

    return _fmt(updated)


@router.delete("/reviews/{review_id}", status_code=204)
async def delete_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rid = uuid_lib.UUID(review_id)
    except ValueError:
        raise_400("Invalid review ID")

    service = _get_service(db)
    try:
        await service.delete_review(student_id=current_user.id, review_id=rid)
    except ValueError as e:
        raise_404(str(e))
    except PermissionError as e:
        raise_403(str(e))


@router.post("/reviews/{review_id}/respond", response_model=ReviewResponse)
async def instructor_respond(
    review_id: str,
    body: InstructorResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rid = uuid_lib.UUID(review_id)
    except ValueError:
        raise_400("Invalid review ID")

    review_repo = SQLAlchemyReviewRepository(db)
    review = await review_repo.get_by_id(rid)
    if not review:
        raise_404("Review not found")

    course_repo = SQLAlchemyCourseRepository(db)
    course = await course_repo.get_by_id(review.course_id)
    if not course or course.instructor_id != current_user.id:
        raise_403("Only the course instructor can respond")

    updated = await review_repo.set_instructor_response(rid, body.body)
    return _fmt(updated)


@router.post("/reviews/{review_id}/helpful", status_code=200)
async def toggle_helpful(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rid = uuid_lib.UUID(review_id)
    except ValueError:
        raise_400("Invalid review ID")

    review_repo = SQLAlchemyReviewRepository(db)
    review = await review_repo.get_by_id(rid)
    if not review:
        raise_404("Review not found")
    if review.student_id == current_user.id:
        raise_400("Cannot mark your own review as helpful")

    existing = await review_repo.get_helpful(rid, current_user.id)
    if existing:
        await review_repo.remove_helpful(rid, current_user.id)
        return {"helpful": False}
    else:
        await review_repo.add_helpful(rid, current_user.id)
        return {"helpful": True}


@router.get("/instructors/me/reviews", response_model=list[ReviewResponse])
async def get_instructor_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.INSTRUCTOR, UserRole.ADMIN):
        raise_403("Instructor access required")

    review_repo = SQLAlchemyReviewRepository(db)
    reviews = await review_repo.list_by_instructor(current_user.id)
    return [_fmt(r) for r in reviews]