import uuid as uuid_lib

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.user import (
    ChangePasswordRequest,
    InstructorApplyResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.application.services.user_service import UserService
from app.core.deps import get_current_user
from app.core.exceptions import (
    InvalidCredentialsError,
    raise_400,
    raise_404,
)
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.instructor_repository import InstructorProfileData
from app.infrastructure.db.repositories.instructor_repository import SQLAlchemyInstructorRepository
from app.infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.storage.minio_client import ensure_buckets, upload_avatar

router = APIRouter(prefix="/users", tags=["Users"])


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return _user_to_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_instructor and any(
        v is not None for v in [body.bio, body.expertise, body.website, body.social_links]
    ):
        repo = SQLAlchemyInstructorRepository(db)
        profile = await repo.get_by_user_id(current_user.id)
        if profile:
            await repo.update(
                current_user.id,
                InstructorProfileData(
                    bio=body.bio,
                    expertise=body.expertise,
                    website=body.website,
                    social_links=body.social_links,
                ),
            )
    return _user_to_response(current_user)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ensure_buckets()
    file_data = await file.read()
    try:
        avatar_url = await upload_avatar(file_data, file.content_type, current_user.id)
    except ValueError as e:
        raise_400(str(e))

    service = UserService(SQLAlchemyUserRepository(db))
    updated = await service.update_avatar(current_user.id, avatar_url)
    return _user_to_response(updated)


@router.post("/me/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(SQLAlchemyUserRepository(db))
    try:
        await service.change_password(current_user.id, body.old_password, body.new_password)
    except InvalidCredentialsError as e:
        raise_400(e.message)


@router.post("/me/instructor-apply", response_model=InstructorApplyResponse)
async def apply_for_instructor(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_instructor:
        raise_400("Already an instructor")

    user_repo = SQLAlchemyUserRepository(db)
    instructor_repo = SQLAlchemyInstructorRepository(db)
    current_user.role = UserRole.INSTRUCTOR
    await user_repo.update(current_user)
    await instructor_repo.create(current_user.id)

    return InstructorApplyResponse(message="Instructor role granted", role="instructor")


@router.get("/{user_id}/public")
async def get_public_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = uuid_lib.UUID(user_id)
    except ValueError:
        raise_400("Invalid user ID format")

    repo = SQLAlchemyUserRepository(db)
    instructor_repo = SQLAlchemyInstructorRepository(db)

    user = await repo.get_by_id(uid)
    if not user or not user.is_instructor:
        raise_404("Instructor not found")

    profile = await instructor_repo.get_by_user_id(uid)
    return {
        "id": str(user.id),
        "email": user.email,
        "avatar_url": user.avatar_url,
        "bio": profile.bio if profile else None,
        "expertise": profile.expertise if profile else None,
        "website": profile.website if profile else None,
        "social_links": profile.social_links if profile else {},
    }