import base64
import hashlib

from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.core.config import settings


def token_fernet() -> Fernet:
    configured = settings.google_calendar_token_encryption_key
    if configured:
        try:
            return Fernet(configured.encode())
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="La clave de protección de Google Calendar no es válida.",
            ) from exc
    derived = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))
