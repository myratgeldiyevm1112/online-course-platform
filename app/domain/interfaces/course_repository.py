import uuid
from abc import ABC, abstractmethod

from app.domain.entities.course import Category, Course


class AbstractCourseRepository(ABC):

    @abstractmethod
    async def create(self, course: Course) -> Course:
        ...

    @abstractmethod
    async def get_by_id(self, course_id: uuid.UUID) -> Course | None:
        ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Course | None:
        ...

    @abstractmethod
    async def update(self, course: Course) -> Course:
        ...

    @abstractmethod
    async def soft_delete(self, course_id: uuid.UUID) -> None:
        ...

    @abstractmethod
    async def list_by_instructor(self, instructor_id: uuid.UUID) -> list[Course]:
        ...


class AbstractCategoryRepository(ABC):

    @abstractmethod
    async def create(self, category: Category) -> Category:
        ...

    @abstractmethod
    async def get_by_id(self, category_id: uuid.UUID) -> Category | None:
        ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Category | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[Category]:
        ...