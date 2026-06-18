import uuid
from datetime import datetime


class Review:
    def __init__(
        self,
        id: uuid.UUID,
        course_id: uuid.UUID,
        student_id: uuid.UUID,
        enrollment_id: uuid.UUID,
        rating: int,
        body: str,
        is_hidden: bool,
        helpful_count: int,
        instructor_response: str | None,
        instructor_responded_at: datetime | None,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.course_id = course_id
        self.student_id = student_id
        self.enrollment_id = enrollment_id
        self.rating = rating
        self.body = body
        self.is_hidden = is_hidden
        self.helpful_count = helpful_count
        self.instructor_response = instructor_response
        self.instructor_responded_at = instructor_responded_at
        self.created_at = created_at
        self.updated_at = updated_at


class ReviewHelpful:
    def __init__(
        self,
        id: uuid.UUID,
        review_id: uuid.UUID,
        student_id: uuid.UUID,
        created_at: datetime,
    ):
        self.id = id
        self.review_id = review_id
        self.student_id = student_id
        self.created_at = created_at