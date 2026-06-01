from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.common import AuthUserResponse, LoginRequest, LogoutResponse, MeResponse, TokenResponse
from app.services.auth import authenticate_user, get_user_by_email, issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


def auth_user_from_model(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        client_id=user.client_id,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, payload.email)
    if existing_user and not existing_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=issue_token(user), user=auth_user_from_model(user))


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_active_user)):
    return auth_user_from_model(current_user)


@router.post("/logout", response_model=LogoutResponse)
def logout(_: User = Depends(get_current_active_user)):
    return LogoutResponse()


@router.post("/refresh", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def refresh_token():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Refresh tokens are not implemented yet for the stateless JWT setup.",
    )
