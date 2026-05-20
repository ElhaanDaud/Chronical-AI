from uuid import UUID

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr


class UserRead(schemas.BaseUser[UUID]):
    pass


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    model_config = {"extra": "forbid"}

    def create_update_dict(self) -> dict:
        return self.model_dump()

    def create_update_dict_superuser(self) -> dict:
        return self.model_dump()


class UserUpdate(schemas.BaseUserUpdate):
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
