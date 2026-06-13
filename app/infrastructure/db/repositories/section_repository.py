import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.course import Lesson, LessonType, Section
from app.domain.interfaces.section_repository import (
    AbstractLessonRepository,
    AbstractSectionRepository,
)
from app.infrastructure.db.models.course import LessonModel, SectionModel


class SQLAlchemySectionRepository(AbstractSectionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, section: Section) -> Section:
        model = SectionModel(
            id=section.id,
            course_id=section.course_id,
            title=section.title,
            position=section.position,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, section_id: uuid.UUID) -> Section | None:
        result = await self.session.execute(
            select(SectionModel).where(SectionModel.id == section_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_course(self, course_id: uuid.UUID) -> list[Section]:
        result = await self.session.execute(
            select(SectionModel)
            .where(SectionModel.course_id == course_id)
            .order_by(SectionModel.position)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, section: Section) -> Section:
        result = await self.session.execute(
            select(SectionModel).where(SectionModel.id == section.id)
        )
        model = result.scalar_one()
        model.title = section.title
        model.position = section.position
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, section_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(SectionModel).where(SectionModel.id == section_id)
        )
        model = result.scalar_one()
        await self.session.delete(model)
        await self.session.flush()

    @staticmethod
    def _to_entity(model: SectionModel) -> Section:
        return Section(
            id=model.id,
            course_id=model.course_id,
            title=model.title,
            position=model.position,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyLessonRepository(AbstractLessonRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, lesson: Lesson) -> Lesson:
        model = LessonModel(
            id=lesson.id,
            section_id=lesson.section_id,
            title=lesson.title,
            position=lesson.position,
            lesson_type=lesson.lesson_type,
            content_url=lesson.content_url,
            article_body=lesson.article_body,
            duration_seconds=lesson.duration_seconds,
            is_preview=lesson.is_preview,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, lesson_id: uuid.UUID) -> Lesson | None:
        result = await self.session.execute(
            select(LessonModel).where(LessonModel.id == lesson_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_section(self, section_id: uuid.UUID) -> list[Lesson]:
        result = await self.session.execute(
            select(LessonModel)
            .where(LessonModel.section_id == section_id)
            .order_by(LessonModel.position)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, lesson: Lesson) -> Lesson:
        result = await self.session.execute(
            select(LessonModel).where(LessonModel.id == lesson.id)
        )
        model = result.scalar_one()
        model.title = lesson.title
        model.position = lesson.position
        model.lesson_type = lesson.lesson_type
        model.content_url = lesson.content_url
        model.article_body = lesson.article_body
        model.duration_seconds = lesson.duration_seconds
        model.is_preview = lesson.is_preview
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, lesson_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(LessonModel).where(LessonModel.id == lesson_id)
        )
        model = result.scalar_one()
        await self.session.delete(model)
        await self.session.flush()

    @staticmethod
    def _to_entity(model: LessonModel) -> Lesson:
        return Lesson(
            id=model.id,
            section_id=model.section_id,
            title=model.title,
            position=model.position,
            lesson_type=model.lesson_type,
            content_url=model.content_url,
            article_body=model.article_body,
            duration_seconds=model.duration_seconds,
            is_preview=model.is_preview,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )