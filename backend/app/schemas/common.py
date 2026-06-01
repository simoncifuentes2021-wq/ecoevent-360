from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Timestamped(ORMModel):
    created_at: datetime
    updated_at: datetime


class AuthUserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: UserRole
    client_id: UUID | None = None


class MeResponse(AuthUserResponse):
    pass


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class LoginRequest(BaseModel):
    email: str
    password: str


class LogoutResponse(BaseModel):
    ok: bool = True
    message: str = "Token discarded by client"


AuthUser = AuthUserResponse
Token = TokenResponse
