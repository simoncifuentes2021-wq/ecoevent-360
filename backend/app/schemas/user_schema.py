from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole
    client_id: UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=50)
    role: UserRole | None = None
    client_id: UUID | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID | None = None
    full_name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    limit: int

