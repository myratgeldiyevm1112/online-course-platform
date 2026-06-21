import logging

from app.core.celery_app import celery_app
from app.infrastructure.email.renderer import render_template
from app.infrastructure.email.smtp_client import send_email

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


def _retry_countdown(retries: int) -> int:
    """Exponential backoff: 60, 120, 240 seconds."""
    return 60 * (2 ** retries)


@celery_app.task(bind=True, max_retries=3)
def send_welcome_email(self, to: str, name: str):
    try:
        html = render_template("welcome.html", name=name, base_url=BASE_URL)
        import asyncio
        asyncio.run(send_email(to=to, subject="Welcome to Course Platform!", html_body=html))
        logger.info(f"[send_welcome_email] Sent to {to}")
    except Exception as exc:
        logger.error(f"[send_welcome_email] Failed: {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def send_enrollment_email(self, to: str, name: str, course_title: str, course_id: str):
    try:
        start_url = f"{BASE_URL}/courses/{course_id}"
        html = render_template(
            "enrollment_confirmation.html",
            name=name,
            course_title=course_title,
            start_url=start_url,
        )
        import asyncio
        asyncio.run(send_email(to=to, subject=f"Enrolled: {course_title}", html_body=html))
        logger.info(f"[send_enrollment_email] Sent to {to}")
    except Exception as exc:
        logger.error(f"[send_enrollment_email] Failed: {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def send_payment_receipt(self, to: str, name: str, course_title: str, amount: str, transaction_id: str):
    try:
        html = render_template(
            "payment_receipt.html",
            name=name,
            course_title=course_title,
            amount=amount,
            transaction_id=transaction_id,
        )
        import asyncio
        asyncio.run(send_email(to=to, subject="Payment Receipt", html_body=html))
        logger.info(f"[send_payment_receipt] Sent to {to}")
    except Exception as exc:
        logger.error(f"[send_payment_receipt] Failed: {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def send_certificate_email(self, to: str, name: str, course_title: str, download_url: str):
    try:
        html = render_template(
            "certificate_ready.html",
            name=name,
            course_title=course_title,
            download_url=download_url,
        )
        import asyncio
        asyncio.run(send_email(to=to, subject=f"Certificate Ready: {course_title}", html_body=html))
        logger.info(f"[send_certificate_email] Sent to {to}")
    except Exception as exc:
        logger.error(f"[send_certificate_email] Failed: {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def send_password_reset(self, to: str, name: str, reset_token: str):
    try:
        reset_url = f"{BASE_URL}/reset-password?token={reset_token}"
        html = render_template(
            "password_reset.html",
            name=name,
            reset_url=reset_url,
        )
        import asyncio
        asyncio.run(send_email(to=to, subject="Password Reset Request", html_body=html))
        logger.info(f"[send_password_reset] Sent to {to}")
    except Exception as exc:
        logger.error(f"[send_password_reset] Failed: {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))

@celery_app.task(bind=True, max_retries=3)
def send_instructor_payout(self, to: str, name: str, amount: str, period: str):
    try:
        html = render_template(
            "instructor_payout.html",
            name=name,
            amount=amount,
            period=period,
        )
        import asyncio
        asyncio.run(send_email(to=to, subject="Payout Processed", html_body=html))
        logger.info(f"[send_instructor_payout] Sent to {to}")
    except Exception as exc:
        logger.error(f"[send_instructor_payout] Failed: {exc}")
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))