import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InstructorProfileData:
    bio: str | None = None
    expertise: str | None = None
    website: str | None = None
    social_links: dict | None = None


class AbstractInstructorRepository(ABC):

    @abstractmethod
    async def get_by_user_id(self, user_id: uuid.UUID) -> "InstructorProfileData | None":
        ...

    @abstractmethod
    async def create(self, user_id: uuid.UUID) -> "InstructorProfileData":
        ...

    @abstractmethod
    async def update(self, user_id: uuid.UUID, data: "InstructorProfileData") -> "InstructorProfileData":
        ...