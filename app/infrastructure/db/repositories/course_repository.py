import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.course import Category, Course
from app.domain.interfaces.course_repository import (
    AbstractCategoryRepository,
    AbstractCourseRepository,
    CourseFilters,
    PaginatedCourses,
)
from app.infrastructure.db.models.course import CategoryModel, CourseModel


class SQLAlchemyCourseRepository(AbstractCourseRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, course: Course) -> Course:
        model = CourseModel(
            id=course.id,
            instructor_id=course.instructor_id,
            category_id=course.category_id,
            title=course.title,
            slug=course.slug,
            description=course.description,
            short_description=course.short_description,
            price=course.price,
            thumbnail_url=course.thumbnail_url,
            language=course.language,
            difficulty=course.difficulty,
            status=course.status,
            total_lessons=course.total_lessons,
            total_duration_seconds=course.total_duration_seconds,
            avg_rating=course.avg_rating,
            total_enrolled=course.total_enrolled,
            is_featured=course.is_featured,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, course_id: uuid.UUID) -> Course | None:
        result = await self.session.execute(
            select(CourseModel).where(
                CourseModel.id == course_id,
                CourseModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Course | None:
        result = await self.session.execute(
            select(CourseModel).where(
                CourseModel.slug == slug,
                CourseModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, course: Course) -> Course:
        result = await self.session.execute(
            select(CourseModel).where(CourseModel.id == course.id)
        )
        model = result.scalar_one()
        model.title = course.title
        model.slug = course.slug
        model.description = course.description
        model.short_description = course.short_description
        model.price = course.price
        model.thumbnail_url = course.thumbnail_url
        model.language = course.language
        model.difficulty = course.difficulty
        model.status = course.status
        model.category_id = course.category_id
        model.is_featured = course.is_featured
        model.deleted_at = course.deleted_at
        model.total_lessons = course.total_lessons
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def soft_delete(self, course_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(CourseModel).where(CourseModel.id == course_id)
        )
        model = result.scalar_one()
        model.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def list_by_instructor(self, instructor_id: uuid.UUID) -> list[Course]:
        result = await self.session.execute(
            select(CourseModel).where(
                CourseModel.instructor_id == instructor_id,
                CourseModel.deleted_at.is_(None),
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_published(self, filters: CourseFilters) -> PaginatedCourses:
        stmt = select(CourseModel).where(
            CourseModel.status == "published",
            CourseModel.deleted_at.is_(None),
        )

        if filters.query:
            stmt = stmt.where(
                text("search_vector @@ plainto_tsquery('english', :q)").bindparams(q=filters.query)
            )
        if filters.category_slug:
            stmt = stmt.join(CategoryModel).where(
                CategoryModel.slug == filters.category_slug
            )
        if filters.min_price is not None:
            stmt = stmt.where(CourseModel.price >= filters.min_price)
        if filters.max_price is not None:
            stmt = stmt.where(CourseModel.price <= filters.max_price)
        if filters.min_rating is not None:
            stmt = stmt.where(CourseModel.avg_rating >= filters.min_rating)
        if filters.language:
            stmt = stmt.where(CourseModel.language == filters.language)
        if filters.difficulty:
            stmt = stmt.where(CourseModel.difficulty == filters.difficulty)

        sort_map = {
            "newest": CourseModel.created_at.desc(),
            "rating": CourseModel.avg_rating.desc(),
            "enrolled": CourseModel.total_enrolled.desc(),
            "price_asc": CourseModel.price.asc(),
            "price_desc": CourseModel.price.desc(),
        }
        stmt = stmt.order_by(sort_map.get(filters.sort, CourseModel.created_at.desc()))

        total_result = await self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = total_result.scalar()

        offset = (filters.page - 1) * filters.page_size
        stmt = stmt.offset(offset).limit(filters.page_size)

        result = await self.session.execute(stmt)
        items = [self._to_entity(m) for m in result.scalars().all()]

        return PaginatedCourses(items=items, total=total, page=filters.page, page_size=filters.page_size)

    @staticmethod
    def _to_entity(model: CourseModel) -> Course:
        return Course(
            id=model.id,
            instructor_id=model.instructor_id,
            category_id=model.category_id,
            title=model.title,
            slug=model.slug,
            description=model.description,
            short_description=model.short_description,
            price=float(model.price),
            thumbnail_url=model.thumbnail_url,
            language=model.language,
            difficulty=model.difficulty,
            status=model.status,
            total_lessons=model.total_lessons,
            total_duration_seconds=model.total_duration_seconds,
            avg_rating=float(model.avg_rating),
            total_enrolled=model.total_enrolled,
            is_featured=model.is_featured,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )
    async def get_trending(self, limit: int = 10) -> list[Course]:
        """Top courses by enrollment in last 7 days via total_enrolled."""
        from datetime import timedelta
        from sqlalchemy import desc
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.session.execute(
            select(CourseModel)
            .where(
                CourseModel.status == "published",
                CourseModel.deleted_at.is_(None),
                CourseModel.updated_at >= cutoff,
            )
            .order_by(desc(CourseModel.total_enrolled))
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def reindex_search_vectors(self) -> int:
        """Refresh tsvector column for all courses."""
        result = await self.session.execute(
            text("""
                UPDATE courses
                SET search_vector = to_tsvector('english', title || ' ' || description)
                WHERE deleted_at IS NULL
            """)
        )
        await self.session.flush()
        return result.rowcount

class SQLAlchemyCategoryRepository(AbstractCategoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, category: Category) -> Category:
        model = CategoryModel(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            parent_id=category.parent_id,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, category_id: uuid.UUID) -> Category | None:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.id == category_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Category | None:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[Category]:
        result = await self.session.execute(select(CategoryModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            parent_id=model.parent_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def list_with_course_count(self) -> list[dict]:
        result = await self.session.execute(
            select(
                CategoryModel.id,
                CategoryModel.name,
                CategoryModel.slug,
                CategoryModel.description,
                CategoryModel.parent_id,
                func.count(CourseModel.id).label("course_count"),
            )
            .outerjoin(
                CourseModel,
                (CourseModel.category_id == CategoryModel.id) &
                (CourseModel.status == "published") &
                (CourseModel.deleted_at.is_(None)),
            )
            .group_by(CategoryModel.id)
            .order_by(CategoryModel.name)
        )
        rows = result.all()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "slug": r.slug,
                "description": r.description,
                "parent_id": str(r.parent_id) if r.parent_id else None,
                "course_count": r.course_count,
            }
            for r in rows
        ]