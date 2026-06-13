import asyncio
import uuid

from app.infrastructure.db.models.course import CategoryModel
from app.infrastructure.db.session import async_session_factory


CATEGORIES = [
    {"name": "Programming", "slug": "programming", "description": "Software development and coding"},
    {"name": "Data Science", "slug": "data-science", "description": "Data analysis and machine learning"},
    {"name": "Web Development", "slug": "web-development", "description": "Frontend and backend web dev"},
    {"name": "DevOps", "slug": "devops", "description": "CI/CD, cloud, and infrastructure"},
    {"name": "Cybersecurity", "slug": "cybersecurity", "description": "Security and ethical hacking"},
    {"name": "Mobile Development", "slug": "mobile-development", "description": "iOS and Android apps"},
    {"name": "Design", "slug": "design", "description": "UI/UX and graphic design"},
    {"name": "Business", "slug": "business", "description": "Entrepreneurship and management"},
]


async def seed():
    async with async_session_factory() as session:
        for cat in CATEGORIES:
            existing = await session.execute(
                __import__("sqlalchemy").select(CategoryModel).where(
                    CategoryModel.slug == cat["slug"]
                )
            )
            if not existing.scalar_one_or_none():
                session.add(CategoryModel(
                    id=uuid.uuid4(),
                    name=cat["name"],
                    slug=cat["slug"],
                    description=cat["description"],
                ))
        await session.commit()
        print(f"Seeded {len(CATEGORIES)} categories")


if __name__ == "__main__":
    asyncio.run(seed())