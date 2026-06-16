from pydantic import BaseModel


class EnrollResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    status: str
    enrolled_at: str


class EnrolledCourseResponse(BaseModel):
    enrollment_id: str
    course_id: str
    course_title: str
    course_slug: str
    thumbnail_url: str | None
    progress_percent: float
    status: str


class LessonProgressResponse(BaseModel):
    lesson_id: str
    is_completed: bool
    watch_seconds: int