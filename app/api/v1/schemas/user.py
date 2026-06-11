from typing import Any
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    is_verified: bool
    avatar_url: str | None


class UpdateProfileRequest(BaseModel):
    bio: str | None = None
    expertise: str | None = None
    website: str | None = None
    social_links: dict[str, Any] | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class InstructorApplyResponse(BaseModel):
    message: str
    role: str