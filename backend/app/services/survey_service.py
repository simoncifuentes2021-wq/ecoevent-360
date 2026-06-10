import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import Event, EventZone, Survey, SurveyImport, SurveyResponse, User
from app.models.enums import SurveyStatus, UserRole
from app.schemas.survey_schema import SurveyCreate, SurveyStatusUpdate, SurveyUpdate
from app.services.file_storage_service import save_survey_import_file


def get_survey_or_404(db: Session, survey_id: UUID) -> Survey:
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    return survey


def _get_event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _ensure_can_view_survey(db: Session, survey: Survey, current_user: User) -> None:
    if current_user.role == UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_access_event(current_user, survey.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_manage_event_survey(db: Session, event_id: UUID, current_user: User) -> None:
    _get_event_or_404(db, event_id)
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def create_survey(db: Session, event_id: UUID, payload: SurveyCreate, current_user: User) -> Survey:
    _ensure_can_manage_event_survey(db, event_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") is None:
        data.pop("status", None)
    survey = Survey(event_id=event_id, **data)
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


def list_event_surveys(
    db: Session,
    *,
    event_id: UUID,
    current_user: User,
    status_filter: SurveyStatus | None,
    page: int,
    limit: int,
) -> tuple[list[Survey], int]:
    _get_event_or_404(db, event_id)
    if current_user.role == UserRole.WORKER or not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = [Survey.event_id == event_id]
    if status_filter:
        filters.append(Survey.status == status_filter)
    total = db.scalar(select(func.count()).select_from(Survey).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Survey)
            .where(*filters)
            .order_by(Survey.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_survey(db: Session, survey_id: UUID, current_user: User) -> Survey:
    survey = get_survey_or_404(db, survey_id)
    _ensure_can_view_survey(db, survey, current_user)
    return survey


def update_survey(
    db: Session, survey_id: UUID, payload: SurveyUpdate, current_user: User
) -> Survey:
    survey = get_survey_or_404(db, survey_id)
    _ensure_can_manage_event_survey(db, survey.event_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    opens_at = data.get("opens_at", survey.opens_at)
    closes_at = data.get("closes_at", survey.closes_at)
    if opens_at and closes_at and opens_at >= closes_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="opens_at must be before closes_at",
        )
    for field, value in data.items():
        setattr(survey, field, value)
    survey.updated_at = datetime.utcnow()
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


def update_survey_status(
    db: Session, survey_id: UUID, payload: SurveyStatusUpdate, current_user: User
) -> Survey:
    survey = get_survey_or_404(db, survey_id)
    _ensure_can_manage_event_survey(db, survey.event_id, current_user)
    survey.status = payload.status
    survey.updated_at = datetime.utcnow()
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


def import_survey_csv(
    db: Session,
    *,
    survey_id: UUID,
    filename: str,
    content: bytes,
    current_user: User,
) -> SurveyImport:
    survey = get_survey_or_404(db, survey_id)
    _ensure_can_manage_event_survey(db, survey.event_id, current_user)

    file_url = _save_csv_file(filename, content)
    text = content.decode("utf-8-sig")
    rows = list(csv.DictReader(StringIO(text)))
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV has no rows")

    imported = SurveyImport(
        survey_id=survey_id,
        file_url=file_url,
        imported_rows=len(rows),
        imported_by=current_user.id,
    )
    db.add(imported)
    db.flush()

    for row in rows:
        response = _build_response_from_row(db, survey, row)
        db.add(response)

    db.commit()
    db.refresh(imported)
    return imported


def list_survey_responses(
    db: Session,
    *,
    survey_id: UUID,
    current_user: User,
    page: int,
    limit: int,
) -> tuple[list[SurveyResponse], int]:
    survey = get_survey_or_404(db, survey_id)
    _ensure_can_view_survey(db, survey, current_user)
    filters = [SurveyResponse.survey_id == survey_id]
    total = db.scalar(select(func.count()).select_from(SurveyResponse).where(*filters)) or 0
    items = list(
        db.scalars(
            select(SurveyResponse)
            .where(*filters)
            .order_by(SurveyResponse.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_survey_summary(db: Session, survey_id: UUID, current_user: User) -> dict:
    survey = get_survey_or_404(db, survey_id)
    _ensure_can_view_survey(db, survey, current_user)
    responses = list(
        db.scalars(select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)).all()
    )
    total = len(responses)
    return {
        "survey_id": survey_id,
        "event_id": survey.event_id,
        "responses_total": total,
        "avg_cleanliness_rating": _avg([item.cleanliness_rating for item in responses]),
        "avg_bathroom_rating": _avg([item.bathroom_rating for item in responses]),
        "avg_general_rating": _avg([item.general_rating for item in responses]),
        "separated_waste_percentage": _percentage([item.separated_waste for item in responses]),
        "would_recommend_percentage": _percentage([item.would_recommend for item in responses]),
    }


def _save_csv_file(filename: str, content: bytes) -> str:
    return save_survey_import_file(filename, content)


def _build_response_from_row(db: Session, survey: Survey, row: dict[str, str]) -> SurveyResponse:
    normalized = {_normalize_key(key): value for key, value in row.items()}
    zone_id = _parse_uuid(_pick(normalized, "zone_id", "zona_id"))
    if zone_id:
        zone = db.get(EventZone, zone_id)
        if not zone or zone.event_id != survey.event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV contains a zone_id that does not belong to the survey event",
            )
    return SurveyResponse(
        survey_id=survey.id,
        event_id=survey.event_id,
        zone_id=zone_id,
        response_external_id=_pick(normalized, "response_external_id", "id", "id_respuesta"),
        response_date=_parse_datetime(
            _pick(normalized, "response_date", "fecha", "timestamp", "marca_temporal")
        ),
        age_range=_pick(normalized, "age_range", "rango_edad", "edad"),
        origin_commune=_pick(normalized, "origin_commune", "comuna_origen", "comuna"),
        transport_mode=_pick(normalized, "transport_mode", "modo_transporte", "transporte"),
        cleanliness_rating=_parse_decimal(_pick(normalized, "cleanliness_rating", "limpieza")),
        bathroom_rating=_parse_decimal(_pick(normalized, "bathroom_rating", "banos", "baños")),
        recycling_visibility=_pick(normalized, "recycling_visibility", "visibilidad_reciclaje"),
        separated_waste=_parse_bool(_pick(normalized, "separated_waste", "separo_residuos")),
        general_rating=_parse_decimal(_pick(normalized, "general_rating", "evaluacion_general")),
        would_recommend=_parse_bool(_pick(normalized, "would_recommend", "recomendaria")),
        main_problem=_pick(normalized, "main_problem", "problema_principal"),
        comments=_pick(normalized, "comments", "comentarios"),
        raw_data=row,
    )


def _normalize_key(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )


def _pick(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(_normalize_key(key))
        if value not in (None, ""):
            return value
    return None


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID in CSV")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _parse_bool(value: str | None) -> bool | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "si", "sí", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def _avg(values: list[Decimal | None]) -> Decimal | None:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return (sum(numbers, Decimal("0")) / Decimal(len(numbers))).quantize(Decimal("0.01"))


def _percentage(values: list[bool | None]) -> Decimal | None:
    booleans = [value for value in values if value is not None]
    if not booleans:
        return None
    positives = sum(1 for value in booleans if value)
    return (Decimal(positives) / Decimal(len(booleans)) * Decimal("100")).quantize(Decimal("0.01"))
