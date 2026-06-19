import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.course import CourseResponse, PaginatedCoursesResponse
from app.core.deps import require_role
from app.domain.entities.user import UserRole
from app.domain.interfaces.course_repository import CourseFilters
from app.infrastructure.db.repositories.course_repository import (
    SQLAlchemyCategoryRepository,
    SQLAlchemyCourseRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.redis.client import get_redis

router = APIRouter(tags=["Search"])

SEARCH_CACHE_TTL = 60 * 5  # 5 минут
TRENDING_CACHE_KEY = "courses:trending"
TRENDING_CACHE_TTL = 60 * 60  # 1 час


def _to_response(course) -> CourseResponse:
    return CourseResponse(
        id=str(course.id),
        instructor_id=str(course.instructor_id),
        category_id=str(course.category_id) if course.category_id else None,
        title=course.title,
        slug=course.slug,
        description=course.description,
        short_description=course.short_description,
        price=course.price,
        thumbnail_url=course.thumbnail_url,
        language=course.language,
        difficulty=course.difficulty.value,
        status=course.status.value,
        total_lessons=course.total_lessons,
        total_duration_seconds=course.total_duration_seconds,
        avg_rating=course.avg_rating,
        total_enrolled=course.total_enrolled,
        is_featured=course.is_featured,
    )


@router.get("/search", response_model=PaginatedCoursesResponse)
async def search_courses(
    q: str | None = Query(None),
    category: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_rating: float | None = Query(None, ge=0, le=5),
    level: str | None = Query(None),
    sort: str = Query("newest", pattern="^(newest|rating|enrolled|price_asc|price_desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    # Redis cache key
    cache_key = f"search:{q}:{category}:{min_price}:{max_price}:{min_rating}:{level}:{sort}:{page}:{page_size}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    filters = CourseFilters(
        query=q,
        category_slug=category,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        language=None,
        difficulty=level,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    repo = SQLAlchemyCourseRepository(db)
    result = await repo.list_published(filters)

    response = PaginatedCoursesResponse(
        items=[_to_response(c) for c in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )

    # Cache top 100 unique queries
    total_keys = await redis.keys("search:*")
    if len(total_keys) < 100:
        await redis.setex(cache_key, SEARCH_CACHE_TTL, json.dumps(response.model_dump()))

    return response


@router.get("/courses/trending", response_model=list[CourseResponse])
async def get_trending_courses(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cached = await redis.get(TRENDING_CACHE_KEY)
    if cached:
        return json.loads(cached)

    repo = SQLAlchemyCourseRepository(db)
    courses = await repo.get_trending(limit=10)
    result = [_to_response(c) for c in courses]

    await redis.setex(
        TRENDING_CACHE_KEY,
        TRENDING_CACHE_TTL,
        json.dumps([r.model_dump() for r in result]),
    )
    return result


@router.get("/categories", response_model=list[dict])
async def get_categories_with_count(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache_key = "categories:with_count"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    repo = SQLAlchemyCategoryRepository(db)
    categories = await repo.list_with_course_count()

    # Build tree structure
    by_id = {c["id"]: {**c, "children": []} for c in categories}
    tree = []
    for c in by_id.values():
        if c["parent_id"] and c["parent_id"] in by_id:
            by_id[c["parent_id"]]["children"].append(c)
        else:
            tree.append(c)

    await redis.setex(cache_key, 60 * 10, json.dumps(tree))
    return tree


@router.post("/admin/search/reindex", dependencies=[Depends(require_role([UserRole.ADMIN]))])
async def reindex_search(db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyCourseRepository(db)
    count = await repo.reindex_search_vectors()
    return {"reindexed": count}