from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.common import AuthUserResponse, LoginRequest, LogoutResponse, MeResponse, TokenResponse
from app.services.auth import authenticate_user, get_user_by_email, issue_token
from app.services.audit_log_service import create_audit_log

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
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, payload.email)
    if existing_user and not existing_user.is_active:
        create_audit_log(
            db,
            user=existing_user,
            action="LOGIN_FAILED",
            module="auth",
            status="FAILED",
            metadata={"email": payload.email, "reason": "inactive_user"},
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        create_audit_log(
            db,
            action="LOGIN_FAILED",
            module="auth",
            status="FAILED",
            metadata={"email": payload.email, "reason": "invalid_credentials"},
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    create_audit_log(
        db,
        user=user,
        action="LOGIN_SUCCESS",
        module="auth",
        status="SUCCESS",
        metadata={"email": user.email},
        request=request,
    )
    return TokenResponse(access_token=issue_token(user), user=auth_user_from_model(user))


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_active_user)):
    return auth_user_from_model(current_user)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    create_audit_log(
        db,
        user=current_user,
        action="LOGOUT",
        module="auth",
        status="SUCCESS",
        request=request,
    )
    return LogoutResponse()


@router.post("/refresh", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def refresh_token():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Refresh tokens are not implemented yet for the stateless JWT setup.",
    )
