import uuid
from datetime import datetime


class Certificate:
    def __init__(
        self,
        id: uuid.UUID,
        enrollment_id: uuid.UUID,
        student_name: str,
        course_title: str,
        instructor_name: str,
        issued_at: datetime,
        verification_uuid: uuid.UUID,
        pdf_url: str,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.enrollment_id = enrollment_id
        self.student_name = student_name
        self.course_title = course_title
        self.instructor_name = instructor_name
        self.issued_at = issued_at
        self.verification_uuid = verification_uuid
        self.pdf_url = pdf_url
        self.created_at = created_at
        self.updated_at = updated_at