import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.models.user import User


auth_bearer_transport = BearerTransport(tokenUrl="api/auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.auth_secret,
        lifetime_seconds=settings.auth_access_token_ttl_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=auth_bearer_transport,
    get_strategy=get_jwt_strategy,
)


async def get_user_db(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, uuid.UUID], None]:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth_secret
    verification_token_secret = settings.auth_secret


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, uuid.UUID] = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
