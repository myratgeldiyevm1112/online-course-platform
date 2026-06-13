from pydantic import BaseModel, Field


class CreateSectionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class UpdateSectionRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    position: int | None = Field(None, ge=0)


class SectionResponse(BaseModel):
    id: str
    course_id: str
    title: str
    position: int


class CreateLessonRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    lesson_type: str = "video"
    article_body: str | None = None
    is_preview: bool = False


class UpdateLessonRequest(BaseModel):
    title: str | None = None
    lesson_type: str | None = None
    article_body: str | None = None
    is_preview: bool | None = None
    position: int | None = None


class LessonResponse(BaseModel):
    id: str
    section_id: str
    title: str
    position: int
    lesson_type: str
    content_url: str | None
    article_body: str | None
    duration_seconds: int
    is_preview: bool


class CurriculumResponse(BaseModel):
    sections: list[dict]