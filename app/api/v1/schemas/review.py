from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    body: str = Field(..., min_length=10, max_length=2000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    body: str | None = Field(None, min_length=10, max_length=2000)


class InstructorResponseCreate(BaseModel):
    body: str = Field(..., min_length=5, max_length=2000)


class ReviewResponse(BaseModel):
    id: str
    course_id: str
    student_id: str
    rating: int
    body: str
    helpful_count: int
    instructor_response: str | None
    instructor_responded_at: str | None
    created_at: str
    updated_at: str