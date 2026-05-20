from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.exceptions import UserNotExists

from app.core.auth import (
    UserManager,
    current_active_user,
    fastapi_users,
    get_jwt_strategy,
    get_user_manager,
)
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth")

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(current_active_user)) -> User:
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    user_manager: UserManager = Depends(get_user_manager),
) -> TokenResponse:
    try:
        user = await user_manager.get_by_email(payload.email)
    except UserNotExists:
        user = None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LOGIN_BAD_CREDENTIALS",
        )
    verified, updated_hash = user_manager.password_helper.verify_and_update(
        payload.password,
        user.hashed_password,
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LOGIN_BAD_CREDENTIALS",
        )
    if updated_hash:
        user = await user_manager.user_db.update(
            user,
            {"hashed_password": updated_hash},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LOGIN_INACTIVE",
        )
    token = await get_jwt_strategy().write_token(user)
    return TokenResponse(access_token=token)
