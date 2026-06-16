import uuid as uuid_lib
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.enrollment_service import EnrollmentService
from app.core.config import settings
from app.core.deps import get_current_user, require_role
from app.core.exceptions import raise_400, raise_404
from app.domain.entities.user import User, UserRole
from app.infrastructure.db.repositories.course_repository import SQLAlchemyCourseRepository
from app.infrastructure.db.repositories.enrollment_repository import (
    SQLAlchemyEnrollmentRepository,
    SQLAlchemyProgressRepository,
)
from app.infrastructure.db.session import get_db

stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/payments", tags=["Payments"])


class CheckoutRequest(BaseModel):
    course_id: uuid_lib.UUID


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_repo = SQLAlchemyCourseRepository(db)
    course = await course_repo.get_by_id(body.course_id)
    if not course:
        raise_404("Course not found")
    if not course.is_published:
        raise_400("Course is not available")

    # Free course — enroll directly
    if course.is_free:
        service = EnrollmentService(
            SQLAlchemyEnrollmentRepository(db),
            course_repo,
            SQLAlchemyProgressRepository(db),
        )
        try:
            await service.enroll(current_user.id, course.id)
        except ValueError as e:
            raise_400(str(e))
        return CheckoutResponse(
            checkout_url=f"http://localhost:3000/courses/{course.slug}",
            session_id="free",
        )

    # Paid course — Stripe Checkout
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(course.price * 100),
                    "product_data": {
                        "name": course.title,
                        "description": course.short_description or course.title,
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"http://localhost:3000/courses/{course.slug}?payment=success",
            cancel_url=f"http://localhost:3000/courses/{course.slug}?payment=cancel",
            metadata={
                "student_id": str(current_user.id),
                "course_id": str(course.id),
            },
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CheckoutResponse(
        checkout_url=session.url,
        session_id=session.id,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        student_id = metadata.get("student_id")
        course_id = metadata.get("course_id")
        payment_intent_id = session.get("payment_intent")

        if student_id and course_id:
            course_repo = SQLAlchemyCourseRepository(db)
            enrollment_repo = SQLAlchemyEnrollmentRepository(db)

            # Idempotency check
            existing = await enrollment_repo.get_by_payment_intent(payment_intent_id)
            if not existing:
                service = EnrollmentService(
                    enrollment_repo,
                    course_repo,
                    SQLAlchemyProgressRepository(db),
                )
                try:
                    await service.enroll(
                        student_id=uuid_lib.UUID(student_id),
                        course_id=uuid_lib.UUID(course_id),
                        payment_intent_id=payment_intent_id,
                    )
                except Exception:
                    pass

    elif event["type"] == "charge.refunded":
        charge = event["data"]["object"]
        payment_intent_id = charge.get("payment_intent")
        if payment_intent_id:
            enrollment_repo = SQLAlchemyEnrollmentRepository(db)
            enrollment = await enrollment_repo.get_by_payment_intent(payment_intent_id)
            if enrollment:
                from app.domain.entities.enrollment import EnrollmentStatus
                await enrollment_repo.update_status(
                    enrollment.id, EnrollmentStatus.REFUNDED
                )

    return {"status": "ok"}


@router.get("/history")
async def payment_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment_repo = SQLAlchemyEnrollmentRepository(db)
    enrollments = await enrollment_repo.list_by_student(current_user.id)
    course_repo = SQLAlchemyCourseRepository(db)

    result = []
    for e in enrollments:
        if not e.payment_intent_id:
            continue
        course = await course_repo.get_by_id(e.course_id)
        if course:
            result.append({
                "enrollment_id": str(e.id),
                "course_title": course.title,
                "payment_intent_id": e.payment_intent_id,
                "status": e.status.value,
                "enrolled_at": e.enrolled_at.isoformat(),
            })
    return result


@router.get("/instructor/earnings")
async def instructor_earnings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    course_repo = SQLAlchemyCourseRepository(db)
    courses = await course_repo.list_by_instructor(current_user.id)

    total = 0.0
    breakdown = []
    for course in courses:
        revenue = course.total_enrolled * float(course.price) * 0.7
        total += revenue
        breakdown.append({
            "course_id": str(course.id),
            "course_title": course.title,
            "total_enrolled": course.total_enrolled,
            "price": float(course.price),
            "instructor_share": round(revenue, 2),
        })

    return {
        "total_earnings": round(total, 2),
        "platform_fee_percent": 30,
        "instructor_share_percent": 70,
        "courses": breakdown,
    }