import io
import logging
import os
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://course_user:course_pass@localhost:5432/course_db"
)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
BUCKET_CERTS = "certificates"


def _get_minio():
    from minio import Minio
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def _get_db_conn():
    import psycopg2
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(db_url)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_certificate(self, enrollment_id: str, student_id: str, course_id: str):
    logger.info(f"[generate_certificate] enrollment_id={enrollment_id}")

    try:
        conn = _get_db_conn()
        cur = conn.cursor()

        # 1. Fetch enrollment + course + student data
        cur.execute("""
            SELECT
                u.email, u.email as name,
                c.title, c.instructor_id,
                u2.email as instructor_email
            FROM enrollments e
            JOIN users u ON e.student_id = u.id
            JOIN courses c ON e.course_id = c.id
            JOIN users u2 ON c.instructor_id = u2.id
            WHERE e.id = %s
        """, (enrollment_id,))
        row = cur.fetchone()
        if not row:
            logger.error(f"[generate_certificate] Enrollment not found: {enrollment_id}")
            return {"status": "failed"}

        student_email, student_name, course_title, instructor_id, instructor_email = row

        # 2. Check if certificate already exists
        cur.execute(
            "SELECT id FROM certificates WHERE enrollment_id = %s", (enrollment_id,)
        )
        if cur.fetchone():
            logger.info(f"[generate_certificate] Already exists for {enrollment_id}")
            cur.close()
            conn.close()
            return {"status": "already_exists"}

        # 3. Generate PDF
        from app.infrastructure.pdf.certificate_generator import generate_certificate_pdf
        from datetime import datetime, timezone
        issued_at = datetime.now(timezone.utc)
        verification_uuid = uuid.uuid4()

        pdf_bytes = generate_certificate_pdf(
            student_name=student_name,
            course_title=course_title,
            instructor_name=instructor_email,
            issued_at=issued_at,
            verification_uuid=verification_uuid,
        )

        # 4. Upload PDF to MinIO
        minio = _get_minio()
        pdf_key = f"{enrollment_id}/certificate.pdf"

        # Ensure bucket exists
        if not minio.bucket_exists(BUCKET_CERTS):
            minio.make_bucket(BUCKET_CERTS)

        minio.put_object(
            BUCKET_CERTS,
            pdf_key,
            io.BytesIO(pdf_bytes),
            len(pdf_bytes),
            content_type="application/pdf",
        )
        pdf_url = f"{pdf_key}"

        # 5. Create Certificate record in DB
        cert_id = uuid.uuid4()
        cur.execute("""
            INSERT INTO certificates
                (id, enrollment_id, student_name, course_title, instructor_name,
                 issued_at, verification_uuid, pdf_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (
            str(cert_id), enrollment_id, student_name, course_title,
            instructor_email, issued_at, str(verification_uuid), pdf_url,
        ))
        conn.commit()

        # 6. Send certificate_ready notification via email
        from app.tasks.email_tasks import send_certificate_email
        download_url = f"http://localhost:8000/api/v1/certificates/{verification_uuid}/verify"
        send_certificate_email.delay(
            to=student_email,
            name=student_name,
            course_title=course_title,
            download_url=download_url,
        )

        cur.close()
        conn.close()

        logger.info(f"[generate_certificate] Done! cert_id={cert_id}")
        return {"status": "ready", "certificate_id": str(cert_id), "verification_uuid": str(verification_uuid)}

    except Exception as exc:
        logger.error(f"[generate_certificate] Error: {exc}", exc_info=True)
        raise self.retry(exc=exc)