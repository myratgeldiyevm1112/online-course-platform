import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.instructor_repository import (
    AbstractInstructorRepository,
    InstructorProfileData,
)
from app.infrastructure.db.models.user import InstructorProfileModel


class SQLAlchemyInstructorRepository(AbstractInstructorRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> InstructorProfileData | None:
        result = await self.session.execute(
            select(InstructorProfileModel).where(
                InstructorProfileModel.user_id == user_id
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_data(model)

    async def create(self, user_id: uuid.UUID) -> InstructorProfileData:
        model = InstructorProfileModel(user_id=user_id)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_data(model)

    async def update(self, user_id: uuid.UUID, data: InstructorProfileData) -> InstructorProfileData:
        result = await self.session.execute(
            select(InstructorProfileModel).where(
                InstructorProfileModel.user_id == user_id
            )
        )
        model = result.scalar_one()
        if data.bio is not None:
            model.bio = data.bio
        if data.expertise is not None:
            model.expertise = data.expertise
        if data.website is not None:
            model.website = data.website
        if data.social_links is not None:
            model.social_links = data.social_links
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_data(model)

    @staticmethod
    def _to_data(model: InstructorProfileModel) -> InstructorProfileData:
        return InstructorProfileData(
            bio=model.bio,
            expertise=model.expertise,
            website=model.website,
            social_links=model.social_links,
        )
