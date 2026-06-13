import uuid
from abc import ABC, abstractmethod

from app.domain.entities.course import Lesson, Section


class AbstractSectionRepository(ABC):

    @abstractmethod
    async def create(self, section: Section) -> Section:
        ...

    @abstractmethod
    async def get_by_id(self, section_id: uuid.UUID) -> Section | None:
        ...

    @abstractmethod
    async def list_by_course(self, course_id: uuid.UUID) -> list[Section]:
        ...

    @abstractmethod
    async def update(self, section: Section) -> Section:
        ...

    @abstractmethod
    async def delete(self, section_id: uuid.UUID) -> None:
        ...


class AbstractLessonRepository(ABC):

    @abstractmethod
    async def create(self, lesson: Lesson) -> Lesson:
        ...

    @abstractmethod
    async def get_by_id(self, lesson_id: uuid.UUID) -> Lesson | None:
        ...

    @abstractmethod
    async def list_by_section(self, section_id: uuid.UUID) -> list[Lesson]:
        ...

    @abstractmethod
    async def update(self, lesson: Lesson) -> Lesson:
        ...

    @abstractmethod
    async def delete(self, lesson_id: uuid.UUID) -> None:
        ...