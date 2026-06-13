import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.domain.entities.course import Category, Course


@dataclass
class CourseFilters:
    query: str | None = None
    category_slug: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_rating: float | None = None
    language: str | None = None
    difficulty: str | None = None
    sort: str = "newest"  # newest | rating | enrolled | price_asc | price_desc
    page: int = 1
    page_size: int = 20


@dataclass
class PaginatedCourses:
    items: list[Course]
    total: int
    page: int
    page_size: int


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

    @abstractmethod
    async def list_published(self, filters: CourseFilters) -> PaginatedCourses:
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