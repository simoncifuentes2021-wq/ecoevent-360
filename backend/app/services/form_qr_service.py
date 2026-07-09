from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import can_access_event, can_manage_event
from app.models.core import BikeZoneRecord, EventForm, FormQRCode, User
from app.models.enums import EventFormType, UserRole
from app.schemas.event_form_schema import FormQRCodeCreate
from app.services import file_storage_service
from app.services.event_form_service import get_form_or_404
from app.utils.simple_qr import make_qr_png

QR_TYPES = {"FORM", "FORM_LANGUAGE", "BIKE_ZONE_PERSONAL"}
QR_UPLOAD_FOLDER = "qrcodes"
QR_CONTENT_TYPES = {"image/png": ".png"}
LOCAL_UPLOAD_ROOT = Path("uploads") / QR_UPLOAD_FOLDER


def create_form_qr(
    db: Session,
    form_id: UUID,
    payload: FormQRCodeCreate,
    user: User,
    public_base_url: str | None = None,
) -> FormQRCode:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_qr(db, form, user)
    qr_type = _validate_qr_type(payload.qr_type)
    language = _validate_language(form, qr_type, payload.language)
    target_url = _target_url(form, qr_type, language, public_base_url)
    existing = _find_existing(db, form.id, qr_type, language)
    if existing and not payload.force:
        if _sync_qr_target(existing, public_base_url):
            db.commit()
            db.refresh(existing)
        return existing
    png = _render_png(target_url)
    file_url, file_path = _save_png(png, form.public_slug, qr_type, language)
    if existing:
        _delete_qr_file(existing)
        existing.label = payload.label
        existing.target_url = target_url
        existing.file_url = file_url
        existing.file_path = file_path
        existing.format = "PNG"
        existing.created_by = user.id
        db.commit()
        db.refresh(existing)
        return existing
    qr = FormQRCode(
        form_id=form.id,
        event_id=form.event_id,
        session_id=form.session_id,
        label=payload.label,
        target_url=target_url,
        qr_type=qr_type,
        language=language,
        file_url=file_url,
        file_path=file_path,
        format="PNG",
        created_by=user.id,
    )
    db.add(qr)
    db.commit()
    db.refresh(qr)
    return qr


def list_form_qr_codes(db: Session, form_id: UUID, user: User, public_base_url: str | None = None) -> list[FormQRCode]:
    form = get_form_or_404(db, form_id)
    _ensure_can_view_qr(db, form, user)
    qr_codes = list(
        db.scalars(
            select(FormQRCode)
            .where(FormQRCode.form_id == form.id)
            .order_by(FormQRCode.created_at.desc())
        ).all()
    )
    changed = False
    for qr in qr_codes:
        changed = _sync_qr_target(qr, public_base_url) or changed
    if changed:
        db.commit()
        for qr in qr_codes:
            db.refresh(qr)
    return qr_codes


def get_qr_or_404(db: Session, qr_id: UUID) -> FormQRCode:
    qr = db.get(FormQRCode, qr_id)
    if not qr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR not found")
    return qr


def get_download_target(db: Session, qr_id: UUID, user: User) -> Path | str:
    qr = get_qr_or_404(db, qr_id)
    _ensure_can_access_event(db, qr.event_id, user)
    if qr.file_url and qr.file_url.startswith(("http://", "https://")):
        return qr.file_url
    path = Path(qr.file_path or qr.file_url or "")
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR file not found")
    return path


def get_download_path(db: Session, qr_id: UUID, user: User) -> Path:
    target = get_download_target(db, qr_id, user)
    if isinstance(target, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR file is stored remotely")
    return target


def delete_qr(db: Session, qr_id: UUID, user: User) -> None:
    qr = get_qr_or_404(db, qr_id)
    _ensure_can_manage_event(db, qr.event_id, user)
    _delete_qr_file(qr)
    db.delete(qr)
    db.commit()


def create_bike_zone_qr(
    db: Session,
    code: str,
    user: User,
    force: bool = False,
    public_base_url: str | None = None,
) -> FormQRCode:
    record = db.scalar(select(BikeZoneRecord).where(BikeZoneRecord.code == code.strip().upper()))
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bike Zone code not found")
    _ensure_can_manage_event(db, record.event_id, user)
    if not record.response or not record.response.form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")
    form = record.response.form
    if form.form_type != EventFormType.BIKE_ZONE_REGISTRATION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Form is not Bike Zone")
    target_url = f"{_public_app_url(public_base_url)}/bike-zone/{record.code}"
    existing = db.scalar(
        select(FormQRCode).where(
            FormQRCode.form_id == form.id,
            FormQRCode.qr_type == "BIKE_ZONE_PERSONAL",
            FormQRCode.language == record.code,
        )
    )
    if existing and not force:
        return existing
    png = _render_png(target_url)
    file_url, file_path = _save_png(png, record.code.lower(), "BIKE_ZONE_PERSONAL", None)
    if existing:
        _delete_qr_file(existing)
        existing.target_url = target_url
        existing.file_url = file_url
        existing.file_path = file_path
        existing.created_by = user.id
        db.commit()
        db.refresh(existing)
        return existing
    qr = FormQRCode(
        form_id=form.id,
        event_id=record.event_id,
        session_id=record.session_id,
        label=f"QR Bike Zone {record.code}",
        target_url=target_url,
        qr_type="BIKE_ZONE_PERSONAL",
        language=record.code,
        file_url=file_url,
        file_path=file_path,
        format="PNG",
        created_by=user.id,
    )
    db.add(qr)
    db.commit()
    db.refresh(qr)
    return qr


def _validate_qr_type(qr_type: str) -> str:
    normalized = (qr_type or "FORM").upper()
    if normalized not in QR_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid QR type")
    if normalized == "BIKE_ZONE_PERSONAL":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use the Bike Zone QR endpoint")
    return normalized


def _validate_language(form: EventForm, qr_type: str, language: str | None) -> str | None:
    if qr_type == "FORM":
        return None
    if qr_type == "FORM_LANGUAGE":
        if not language:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="language is required")
        if language not in (form.available_languages or []):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="language is not available for this form")
        return language
    return language


def _target_url(form: EventForm, qr_type: str, language: str | None, public_base_url: str | None = None) -> str:
    base = f"{_public_app_url(public_base_url)}/f/{form.public_slug}"
    if qr_type == "FORM_LANGUAGE" and language:
        return f"{base}?{urlencode({'lang': language})}"
    return base


def _public_app_url(public_base_url: str | None = None) -> str:
    return (settings.public_app_url or public_base_url or "http://localhost:3000").rstrip("/")


def _sync_qr_target(qr: FormQRCode, public_base_url: str | None = None) -> bool:
    if not settings.public_app_url and not public_base_url:
        return False
    if qr.qr_type == "BIKE_ZONE_PERSONAL":
        if not qr.language:
            return False
        target_url = f"{_public_app_url(public_base_url)}/bike-zone/{qr.language}"
        asset_slug = qr.language.lower()
    else:
        target_url = _target_url(qr.form, qr.qr_type, qr.language, public_base_url)
        asset_slug = qr.form.public_slug
    if qr.target_url == target_url:
        return False
    png = _render_png(target_url)
    file_url, file_path = _save_png(png, asset_slug, qr.qr_type, qr.language)
    _delete_qr_file(qr)
    qr.target_url = target_url
    qr.file_url = file_url
    qr.file_path = file_path
    qr.format = "PNG"
    return True


def _render_png(target_url: str) -> bytes:
    try:
        return make_qr_png(target_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _save_png(content: bytes, slug: str, qr_type: str, language: str | None) -> tuple[str, str | None]:
    safe_slug = "".join(char for char in slug.lower() if char.isalnum() or char in {"-", "_"}) or "form"
    suffix = f"-{language}" if language else ""
    filename = f"{safe_slug}-{qr_type.lower()}{suffix}-{uuid4().hex[:10]}.png"
    if settings.use_r2_storage:
        file_url = file_storage_service.save_bytes_file(
            QR_UPLOAD_FOLDER,
            content,
            content_type="image/png",
            allowed_content_types=QR_CONTENT_TYPES,
            original_filename=filename,
        )
        return file_url, None
    LOCAL_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    path = LOCAL_UPLOAD_ROOT / filename
    path.write_bytes(content)
    return path.as_posix(), path.as_posix()


def _find_existing(db: Session, form_id: UUID, qr_type: str, language: str | None) -> FormQRCode | None:
    filters = [FormQRCode.form_id == form_id, FormQRCode.qr_type == qr_type]
    filters.append(FormQRCode.language.is_(None) if language is None else FormQRCode.language == language)
    return db.scalar(select(FormQRCode).where(*filters))


def _delete_qr_file(qr: FormQRCode) -> None:
    if qr.file_url and qr.file_url.startswith(("http://", "https://")):
        file_storage_service.delete_stored_file(qr.file_url)
        return
    path = Path(qr.file_path or qr.file_url or "")
    if path.is_file():
        path.unlink(missing_ok=True)


def _ensure_can_view_qr(db: Session, form: EventForm, user: User) -> None:
    _ensure_can_access_event(db, form.event_id, user)


def _ensure_can_manage_qr(db: Session, form: EventForm, user: User) -> None:
    _ensure_can_manage_event(db, form.event_id, user)


def _ensure_can_access_event(db: Session, event_id: UUID, user: User) -> None:
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_manage_event(db: Session, event_id: UUID, user: User) -> None:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
