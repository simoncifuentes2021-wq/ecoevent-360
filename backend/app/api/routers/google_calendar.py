from datetime import UTC, datetime, timedelta
import logging
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db, set_rls_context
from app.models.core import User
from app.models.enums import UserRole
from app.models.google_calendar import GoogleCalendarConnection
from app.services.google_calendar_security import token_fernet

router = APIRouter(prefix="/integrations/google-calendar", tags=["integrations"])
logger = logging.getLogger(__name__)
_STATE_PURPOSE = "google_calendar_connect"
_EVENT_SCOPE = "https://www.googleapis.com/auth/calendar.events"
_SCOPES = f"openid email profile {_EVENT_SCOPE}"


def _configuration_missing() -> list[str]:
    return [
        name
        for name, value in (
            ("GOOGLE_CALENDAR_CLIENT_ID", settings.google_calendar_client_id),
            ("GOOGLE_CALENDAR_CLIENT_SECRET", settings.google_calendar_client_secret),
            ("GOOGLE_CALENDAR_REDIRECT_URI", settings.google_calendar_redirect_uri),
        )
        if not value
    ]


def _frontend_settings_url(result: str) -> str:
    return f"{settings.resolved_documents_public_base_url}/settings?google_calendar={result}"


@router.get("/status")
def connection_status(
    db: Session = Depends(get_db),
    _actor: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
) -> dict[str, object]:
    missing = _configuration_missing()
    connection = db.get(GoogleCalendarConnection, "primary")
    return {
        "configured": not missing,
        "missing_configuration": missing,
        "connected": connection is not None,
        "account_email": connection.account_email if connection else None,
        "connected_at": connection.connected_at.isoformat() if connection else None,
    }


@router.post("/connect")
def begin_connection(actor: User = Depends(require_roles(UserRole.SUPER_ADMIN))) -> dict[str, str]:
    missing = _configuration_missing()
    if missing:
        raise HTTPException(
            status_code=503,
            detail={"message": "Falta configurar las credenciales de Google Calendar en la API.", "missing": missing},
        )
    state = jwt.encode(
        {
            "sub": str(actor.id),
            "role": UserRole.SUPER_ADMIN.value,
            "purpose": _STATE_PURPOSE,
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    params = {
        "client_id": settings.google_calendar_client_id,
        "redirect_uri": settings.google_calendar_redirect_uri,
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent select_account",
        "include_granted_scopes": "true",
        "state": state,
    }
    return {"authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/callback", include_in_schema=False)
def complete_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        return RedirectResponse(_frontend_settings_url("cancelled"), status_code=303)
    if not code or not state or _configuration_missing():
        return RedirectResponse(_frontend_settings_url("error"), status_code=303)
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
        actor_id = payload.get("sub")
        if payload.get("purpose") != _STATE_PURPOSE or payload.get("role") != UserRole.SUPER_ADMIN.value or not actor_id:
            raise JWTError("Invalid OAuth state")
    except JWTError:
        return RedirectResponse(_frontend_settings_url("invalid_state"), status_code=303)

    try:
        actor_uuid = UUID(str(actor_id))
    except (TypeError, ValueError):
        return RedirectResponse(_frontend_settings_url("invalid_state"), status_code=303)
    set_rls_context(db, user_id=actor_uuid, role=UserRole.SUPER_ADMIN)
    try:
        with httpx.Client(timeout=20) as client:
            token_response = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_calendar_client_id,
                    "client_secret": settings.google_calendar_client_secret,
                    "redirect_uri": settings.google_calendar_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                logger.warning("Google Calendar OAuth completed without a refresh token")
                return RedirectResponse(_frontend_settings_url("missing_refresh_token"), status_code=303)
            profile_response = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            profile_response.raise_for_status()
            email = profile_response.json().get("email")
            if not email:
                raise ValueError("Google no informó el correo de la cuenta conectada.")
        encrypted = token_fernet().encrypt(refresh_token.encode()).decode()
        connection = db.get(GoogleCalendarConnection, "primary")
        if connection is None:
            connection = GoogleCalendarConnection(
                connection_key="primary",
                account_email=email,
                refresh_token_encrypted=encrypted,
                granted_scopes=token_data.get("scope", _SCOPES),
                connected_by=actor_uuid,
            )
            db.add(connection)
        else:
            connection.account_email = email
            connection.refresh_token_encrypted = encrypted
            connection.granted_scopes = token_data.get("scope", _SCOPES)
            connection.connected_by = actor_uuid
            connection.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
    except httpx.HTTPStatusError as exc:
        db.rollback()
        try:
            provider_error = exc.response.json().get("error", "provider_error")
        except ValueError:
            provider_error = "provider_error"
        logger.warning(
            "Google Calendar OAuth provider rejected a request (status=%s, error=%s)",
            exc.response.status_code,
            provider_error,
        )
        result = "invalid_client" if provider_error == "invalid_client" else "oauth_error"
        return RedirectResponse(_frontend_settings_url(result), status_code=303)
    except httpx.RequestError as exc:
        db.rollback()
        logger.warning("Google Calendar OAuth network request failed (%s)", type(exc).__name__)
        return RedirectResponse(_frontend_settings_url("oauth_error"), status_code=303)
    except (KeyError, ValueError, InvalidToken, HTTPException) as exc:
        db.rollback()
        logger.warning("Google Calendar OAuth callback could not finish (%s)", type(exc).__name__)
        return RedirectResponse(_frontend_settings_url("error"), status_code=303)
    return RedirectResponse(_frontend_settings_url("connected"), status_code=303)


@router.delete("/connection", status_code=204)
def disconnect(
    db: Session = Depends(get_db),
    _actor: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
) -> None:
    connection = db.get(GoogleCalendarConnection, "primary")
    if connection is None:
        return
    try:
        token = token_fernet().decrypt(connection.refresh_token_encrypted.encode()).decode()
        with httpx.Client(timeout=10) as client:
            client.post("https://oauth2.googleapis.com/revoke", data={"token": token})
    except (httpx.HTTPError, InvalidToken, HTTPException):
        pass
    db.delete(connection)
    db.commit()
