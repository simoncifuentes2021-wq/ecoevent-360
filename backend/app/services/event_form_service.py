import csv
import re
import secrets
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import (
    BikeZoneRecord,
    Event,
    EventForm,
    EventSession,
    FormAnswer,
    FormField,
    FormFieldOption,
    FormFieldOptionTranslation,
    FormFieldTranslation,
    FormResponse,
    User,
)
from app.models.enums import BikeZoneStatus, EventFormStatus, EventFormType, FormFieldType, UserRole
from app.schemas.event_form_schema import EventFormCreate, EventFormUpdate, FormFieldCreate, FormFieldUpdate, FormResponseCreate
from app.services.event_session_service import ensure_session_belongs_to_event

OPTION_FIELD_TYPES = {FormFieldType.SELECT, FormFieldType.MULTI_SELECT, FormFieldType.RADIO}
PERSONAL_KEYS = {"full_name", "name", "email", "phone", "telefono", "respondent_name", "respondent_email", "respondent_phone"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s-]{5,24}$")
SUBMIT_LABELS = {
    "es": "Enviar encuesta",
    "en": "Submit survey",
    "pt": "Enviar pesquisa",
    "ko": "설문 제출",
}


def _event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _ensure_can_view_event(db: Session, event_id: UUID, user: User) -> None:
    _event_or_404(db, event_id)
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_manage_event(db: Session, event_id: UUID, user: User) -> None:
    _event_or_404(db, event_id)
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _load_form_query():
    return select(EventForm).options(
        selectinload(EventForm.event),
        selectinload(EventForm.session),
        selectinload(EventForm.fields).selectinload(FormField.options).selectinload(FormFieldOption.translations),
        selectinload(EventForm.fields).selectinload(FormField.translations),
    )


def get_form_or_404(db: Session, form_id: UUID) -> EventForm:
    form = db.scalar(_load_form_query().where(EventForm.id == form_id))
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")
    return form


def get_public_form_or_404(db: Session, slug: str) -> EventForm:
    form = db.scalar(_load_form_query().where(EventForm.public_slug == slug, EventForm.status != EventFormStatus.ARCHIVED))
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")
    return form


def create_form(db: Session, event_id: UUID, payload: EventFormCreate, user: User) -> EventForm:
    _ensure_can_manage_event(db, event_id, user)
    ensure_session_belongs_to_event(db, payload.session_id, event_id)
    data = payload.model_dump(exclude={"generate_template"})
    if not data.get("public_slug"):
        data["public_slug"] = _unique_slug(db, payload.title)
    else:
        data["public_slug"] = _slugify(data["public_slug"])
    if data.get("status") is None:
        data.pop("status", None)
    form = EventForm(event_id=event_id, created_by=user.id, **data)
    db.add(form)
    db.flush()
    if payload.generate_template:
        _create_template_fields(db, form)
    db.commit()
    return get_form_or_404(db, form.id)


def list_event_forms(
    db: Session,
    event_id: UUID,
    user: User,
    session_id: UUID | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[EventForm], int]:
    _ensure_can_view_event(db, event_id, user)
    ensure_session_belongs_to_event(db, session_id, event_id)
    filters = [EventForm.event_id == event_id, EventForm.status != EventFormStatus.ARCHIVED]
    if session_id:
        filters.append(EventForm.session_id == session_id)
    total = db.scalar(select(func.count()).select_from(EventForm).where(*filters)) or 0
    items = list(
        db.scalars(
            _load_form_query()
            .where(*filters)
            .order_by(EventForm.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_form(db: Session, form_id: UUID, user: User) -> EventForm:
    form = get_form_or_404(db, form_id)
    _ensure_can_view_event(db, form.event_id, user)
    return form


def update_form(db: Session, form_id: UUID, payload: EventFormUpdate, user: User) -> EventForm:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    data = payload.model_dump(exclude_unset=True)
    if "session_id" in data:
        ensure_session_belongs_to_event(db, data["session_id"], form.event_id)
    if "public_slug" in data and data["public_slug"]:
        data["public_slug"] = _slugify(data["public_slug"])
    for field, value in data.items():
        setattr(form, field, value)
    form.updated_at = datetime.utcnow()
    db.add(form)
    db.commit()
    return get_form_or_404(db, form.id)


def publish_form(db: Session, form_id: UUID, user: User) -> EventForm:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    form.status = EventFormStatus.ACTIVE
    form.updated_at = datetime.utcnow()
    db.commit()
    return get_form_or_404(db, form.id)


def close_form(db: Session, form_id: UUID, user: User) -> EventForm:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    form.status = EventFormStatus.CLOSED
    form.updated_at = datetime.utcnow()
    db.commit()
    return get_form_or_404(db, form.id)


def archive_form(db: Session, form_id: UUID, user: User) -> None:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    form.status = EventFormStatus.ARCHIVED
    form.updated_at = datetime.utcnow()
    db.commit()


def add_field(db: Session, form_id: UUID, payload: FormFieldCreate, user: User) -> FormField:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    _validate_options(payload.field_type, payload.options)
    field = FormField(form_id=form_id, **payload.model_dump(exclude={"options", "translations"}))
    db.add(field)
    db.flush()
    _replace_options(db, field, payload.options)
    _replace_field_translations(db, field, payload.translations)
    db.commit()
    db.refresh(field)
    return field


def list_fields(db: Session, form_id: UUID, user: User) -> list[FormField]:
    form = get_form_or_404(db, form_id)
    _ensure_can_view_event(db, form.event_id, user)
    return [field for field in form.fields if field.is_active]


def update_field(db: Session, form_id: UUID, field_id: UUID, payload: FormFieldUpdate, user: User) -> FormField:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    field = _field_or_404(db, field_id, form_id)
    data = payload.model_dump(exclude_unset=True, exclude={"options", "translations"})
    field_type = data.get("field_type", field.field_type)
    options = payload.options if payload.options is not None else None
    if options is not None:
        _validate_options(field_type, options)
    for name, value in data.items():
        setattr(field, name, value)
    if options is not None:
        _replace_options(db, field, options)
    if payload.translations is not None:
        _replace_field_translations(db, field, payload.translations)
    field.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(field)
    return field


def delete_field(db: Session, form_id: UUID, field_id: UUID, user: User) -> None:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    field = _field_or_404(db, field_id, form_id)
    has_answers = db.scalar(select(func.count()).select_from(FormAnswer).where(FormAnswer.field_id == field.id)) or 0
    if has_answers:
        field.is_active = False
        field.updated_at = datetime.utcnow()
        db.add(field)
    else:
        db.delete(field)
    db.commit()


def reorder_fields(db: Session, form_id: UUID, field_ids: list[UUID], user: User) -> list[FormField]:
    form = get_form_or_404(db, form_id)
    _ensure_can_manage_event(db, form.event_id, user)
    fields = {field.id: field for field in form.fields}
    for index, field_id in enumerate(field_ids):
        if field_id in fields:
            fields[field_id].sort_order = index
            fields[field_id].updated_at = datetime.utcnow()
            db.add(fields[field_id])
    db.commit()
    return list_fields(db, form_id, user)


def public_form_payload(form: EventForm, lang: str | None) -> dict:
    _ensure_form_open(form)
    needs_language = form.requires_language_selection and not lang
    language = lang or form.default_language
    if language not in (form.available_languages or []):
        language = form.default_language
    fields = [] if needs_language else [_public_field(field, language, form.default_language, form.form_type) for field in form.fields if field.is_active]
    return {
        "title": form.title,
        "description": form.description,
        "form_type": form.form_type,
        "public_slug": form.public_slug,
        "banner_url": form.banner_url,
        "primary_logo_url": form.primary_logo_url,
        "secondary_logo_url": form.secondary_logo_url,
        "primary_color": form.primary_color,
        "show_event_name": form.show_event_name,
        "show_session_name": form.show_session_name,
        "event_name": form.event.name if form.event and form.show_event_name else None,
        "session_name": form.session.name if form.session and form.show_session_name else None,
        "venue_name": _venue_name(form),
        "default_language": form.default_language,
        "available_languages": form.available_languages,
        "requires_language_selection": form.requires_language_selection,
        "language": None if needs_language else language,
        "needs_language_selection": needs_language,
        "submit_label": SUBMIT_LABELS.get(language, SUBMIT_LABELS["es"]),
        "fields": fields,
    }


def submit_public_form(db: Session, slug: str, payload: FormResponseCreate) -> tuple[FormResponse, str | None]:
    form = get_public_form_or_404(db, slug)
    _ensure_form_open(form)
    language = payload.language if payload.language in (form.available_languages or []) else form.default_language
    answers = payload.answers or {}
    fields = [field for field in form.fields if field.is_active]
    field_by_key = {field.field_key: field for field in fields}
    unknown = set(answers) - set(field_by_key)
    if unknown:
        _raise_field_errors([{"field_key": key, "message": "Campo no reconocido"} for key in sorted(unknown)])
    normalized_answers: list[tuple[FormField, dict]] = []
    raw_data = {}
    errors = []
    for field in fields:
        value = answers.get(field.field_key)
        try:
            normalized = _normalize_answer(field, value)
        except ValueError as exc:
            errors.append({"field_key": field.field_key, "message": str(exc)})
            continue
        if field.is_required and normalized["empty"]:
            errors.append({"field_key": field.field_key, "message": "Este campo es obligatorio"})
            continue
        if not normalized["empty"]:
            normalized_answers.append((field, normalized))
            raw_data[field.field_key] = normalized["raw"]
    if errors:
        _raise_field_errors(errors)

    response = FormResponse(
        form_id=form.id,
        event_id=form.event_id,
        session_id=form.session_id,
        language=language,
        raw_data=raw_data,
        metadata_=payload.metadata or {},
        respondent_name=str(raw_data.get("full_name") or raw_data.get("name") or "")[:180] or None,
        respondent_email=str(raw_data.get("email") or "")[:180] or None,
        respondent_phone=str(raw_data.get("phone") or "")[:60] or None,
        response_code=_response_code(db),
    )
    db.add(response)
    db.flush()
    for field, item in normalized_answers:
        db.add(FormAnswer(response_id=response.id, field_id=field.id, **item["columns"]))
    bike_code = None
    if form.form_type == EventFormType.BIKE_ZONE_REGISTRATION:
        bike_code = _bike_code(db)
        db.add(BikeZoneRecord(response_id=response.id, event_id=form.event_id, session_id=form.session_id, code=bike_code))
    db.commit()
    db.refresh(response)
    return response, bike_code


def list_responses(db: Session, form_id: UUID, user: User) -> list[FormResponse]:
    form = get_form_or_404(db, form_id)
    _ensure_can_view_event(db, form.event_id, user)
    if user.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return list(
        db.scalars(
            select(FormResponse)
            .options(selectinload(FormResponse.answers))
            .where(FormResponse.form_id == form_id)
            .order_by(FormResponse.submitted_at.desc())
        ).all()
    )


def get_response(db: Session, form_id: UUID, response_id: UUID, user: User) -> FormResponse:
    form = get_form_or_404(db, form_id)
    _ensure_can_view_event(db, form.event_id, user)
    if user.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    response = db.scalar(
        select(FormResponse)
        .options(selectinload(FormResponse.answers))
        .where(FormResponse.id == response_id, FormResponse.form_id == form_id)
    )
    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    return response


def summary(db: Session, form_id: UUID, user: User) -> dict:
    form = get_form_or_404(db, form_id)
    _ensure_can_view_event(db, form.event_id, user)
    responses = list(db.scalars(select(FormResponse).where(FormResponse.form_id == form_id)).all())
    response_ids = [item.id for item in responses]
    answers = []
    if response_ids:
        answers = list(
            db.execute(
                select(FormField.analytics_key, FormField.field_key, FormAnswer.value_text, FormAnswer.value_number, FormAnswer.value_boolean, FormAnswer.value_json)
                .join(FormField, FormField.id == FormAnswer.field_id)
                .where(FormAnswer.response_id.in_(response_ids))
            ).all()
        )
    grouped = defaultdict(list)
    for analytics_key, field_key, text, number, boolean, json_value in answers:
        key = analytics_key or field_key
        value = json_value if json_value is not None else number if number is not None else boolean if boolean is not None else text
        grouped[key].append(value)
    bike_total = db.scalar(select(func.count()).select_from(BikeZoneRecord).where(BikeZoneRecord.response_id.in_(response_ids))) if response_ids else 0
    bike_in = db.scalar(select(func.count()).select_from(BikeZoneRecord).where(BikeZoneRecord.response_id.in_(response_ids), BikeZoneRecord.status.in_({BikeZoneStatus.CHECKED_IN, BikeZoneStatus.CHECKED_OUT}))) if response_ids else 0
    bike_out = db.scalar(select(func.count()).select_from(BikeZoneRecord).where(BikeZoneRecord.response_id.in_(response_ids), BikeZoneRecord.status == BikeZoneStatus.CHECKED_OUT)) if response_ids else 0
    ratings = [float(value) for value in grouped.get("general_rating", []) if _is_number(value)]
    recommends = grouped.get("would_recommend", [])
    return {
        "form_id": form_id,
        "total_responses": len(responses),
        "responses_by_session": _bucket([str(item.session_id or "Evento") for item in responses]),
        "responses_by_day": _bucket([item.submitted_at.date().isoformat() for item in responses]),
        "responses_by_language": _bucket([item.language for item in responses]),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "recommendation_rate": _rate([bool(value) for value in recommends if value is not None]),
        "transport_modes": _bucket(_flatten(grouped.get("transport_mode", []))),
        "countries": _bucket(_flatten(grouped.get("country", []) + grouped.get("country_origin", []))),
        "regions": _bucket(_flatten(grouped.get("residence_region", []))),
        "main_problems": _bucket(_flatten(grouped.get("main_problem", []))),
        "bike_zone_total": bike_total or 0,
        "bike_zone_checked_in": bike_in or 0,
        "bike_zone_checked_out": bike_out or 0,
        "comments_sample": [] if user.role == UserRole.CLIENT else [str(value) for value in grouped.get("comments", []) if value][:5],
    }


def export_csv(db: Session, form_id: UUID, user: User) -> str:
    if user.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    form = get_form(db, form_id, user)
    responses = list_responses(db, form_id, user)
    fields = [field for field in form.fields if field.is_active]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["submitted_at", "language", *[field.field_key for field in fields]])
    writer.writeheader()
    for response in responses:
        row = {"submitted_at": response.submitted_at.isoformat(), "language": response.language, **response.raw_data}
        writer.writerow(row)
    return output.getvalue()


def _field_or_404(db: Session, field_id: UUID, form_id: UUID) -> FormField:
    field = db.get(FormField, field_id)
    if not field or field.form_id != form_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return field


def _replace_options(db: Session, field: FormField, options: list) -> None:
    for option in list(field.options):
        db.delete(option)
    db.flush()
    for item in options:
        option = FormFieldOption(field_id=field.id, label=item.label, value=item.value, sort_order=item.sort_order)
        db.add(option)
        db.flush()
        for language, label in (item.translations or {}).items():
            db.add(FormFieldOptionTranslation(option_id=option.id, language=language, label=label))


def _replace_field_translations(db: Session, field: FormField, translations: dict | None) -> None:
    for item in list(field.translations):
        db.delete(item)
    db.flush()
    for language, data in (translations or {}).items():
        db.add(
            FormFieldTranslation(
                field_id=field.id,
                language=language,
                label=str(data.get("label") or field.label),
                help_text=data.get("help_text"),
                placeholder=data.get("placeholder"),
            )
        )


def _validate_options(field_type: FormFieldType, options: list) -> None:
    if field_type in OPTION_FIELD_TYPES and not options:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This field type requires options")


def _public_field(field: FormField, language: str, default_language: str, form_type: EventFormType) -> dict:
    translation = next((item for item in field.translations if item.language == language), None)
    default_translation = next((item for item in field.translations if item.language == default_language), None)
    fallback_label = _default_field_label(form_type, field.field_key, language)
    fallback_default_label = _default_field_label(form_type, field.field_key, default_language)
    return {
        "label": translation.label if translation else fallback_label or (default_translation.label if default_translation else None) or fallback_default_label or field.label,
        "field_key": field.field_key,
        "field_type": field.field_type,
        "help_text": translation.help_text if translation else (default_translation.help_text if default_translation else None) or field.help_text,
        "placeholder": translation.placeholder if translation else (default_translation.placeholder if default_translation else None) or field.placeholder,
        "is_required": field.is_required,
        "sort_order": field.sort_order,
        "min_value": field.min_value,
        "max_value": field.max_value,
        "max_length": field.max_length,
        "options": [_public_option(option, language, default_language, form_type, field.field_key) for option in field.options],
    }


def _public_option(option: FormFieldOption, language: str, default_language: str, form_type: EventFormType, field_key: str) -> dict:
    translation = next((item for item in option.translations if item.language == language), None)
    default_translation = next((item for item in option.translations if item.language == default_language), None)
    fallback_label = _default_option_label(form_type, field_key, option.value, language)
    fallback_default_label = _default_option_label(form_type, field_key, option.value, default_language)
    return {
        "label": translation.label if translation else fallback_label or (default_translation.label if default_translation else None) or fallback_default_label or option.label,
        "value": option.value,
        "sort_order": option.sort_order,
    }


def _ensure_form_open(form: EventForm) -> None:
    now = datetime.utcnow()
    if form.status != EventFormStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Form is not active")
    if form.opens_at and now < form.opens_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Form is not open yet")
    if form.closes_at and now > form.closes_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Form is closed")


def _normalize_answer(field: FormField, value) -> dict:
    empty = value is None or value == "" or value == []
    columns = {"value_text": None, "value_number": None, "value_boolean": None, "value_date": None, "value_json": None}
    if empty:
        return {"empty": True, "raw": value, "columns": columns}
    try:
        if field.field_type in {FormFieldType.NUMBER, FormFieldType.RATING_1_5, FormFieldType.RATING_1_7}:
            number = Decimal(str(value))
            if field.field_type == FormFieldType.NUMBER:
                if field.min_value is not None and number < field.min_value:
                    raise ValueError("El valor es menor al mínimo permitido")
                if field.max_value is not None and number > field.max_value:
                    raise ValueError("El valor supera el máximo permitido")
            if field.field_type == FormFieldType.RATING_1_5 and not Decimal("1") <= number <= Decimal("5"):
                raise ValueError("La calificación debe estar entre 1 y 5")
            if field.field_type == FormFieldType.RATING_1_7 and not Decimal("1") <= number <= Decimal("7"):
                raise ValueError("La calificación debe estar entre 1 y 7")
            columns["value_number"] = number
        elif field.field_type in {FormFieldType.CHECKBOX, FormFieldType.YES_NO}:
            if not isinstance(value, bool):
                raise ValueError("Debe ser verdadero o falso")
            columns["value_boolean"] = _to_bool(value)
        elif field.field_type == FormFieldType.DATE:
            columns["value_date"] = date.fromisoformat(str(value))
        elif field.field_type == FormFieldType.MULTI_SELECT:
            if not isinstance(value, list):
                raise ValueError("Debe seleccionar una o más opciones válidas")
            _validate_option_value(field, value)
            columns["value_json"] = value
        elif field.field_type in OPTION_FIELD_TYPES:
            _validate_option_value(field, [str(value)])
            columns["value_text"] = str(value)
        elif field.field_type == FormFieldType.EMAIL:
            text = _validate_text(value, field)
            if not EMAIL_RE.match(text):
                raise ValueError("Correo inválido")
            columns["value_text"] = text
        elif field.field_type == FormFieldType.PHONE:
            text = _validate_text(value, field)
            if not PHONE_RE.match(text):
                raise ValueError("Teléfono inválido")
            columns["value_text"] = text
        elif field.field_type == FormFieldType.FILE:
            raise ValueError("El campo de archivo no está soportado en formularios públicos")
        else:
            text = _validate_text(value, field)
            columns["value_text"] = text
    except InvalidOperation:
        raise ValueError("Valor inválido")
    except ValueError as exc:
        if str(exc):
            raise
        raise ValueError("Valor inválido") from exc
    return {"empty": False, "raw": value, "columns": columns}


def _validate_option_value(field: FormField, values: list[str]) -> None:
    valid = {option.value for option in field.options}
    if any(value not in valid for value in values):
        raise ValueError("Debe seleccionar una opción válida")


def _validate_text(value, field: FormField) -> str:
    if not isinstance(value, str):
        raise ValueError("Debe ser texto")
    text = value.strip()
    if field.max_length and len(text) > field.max_length:
        raise ValueError(f"Debe tener máximo {field.max_length} caracteres")
    return text


def _raise_field_errors(errors: list[dict]) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "si", "sí", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError


def _create_template_fields(db: Session, form: EventForm) -> None:
    for item in _template(form):
        field = FormField(form_id=form.id, **{key: value for key, value in item.items() if key not in {"options", "translations"}})
        db.add(field)
        db.flush()
        _replace_options(db, field, item.get("options", []))
        _replace_field_translations(db, field, item.get("translations"))


def _template(form: EventForm) -> list[dict]:
    if form.form_type == EventFormType.TRANSPORT_SURVEY:
        return _transport_template(form)
    if form.form_type == EventFormType.BIKE_ZONE_REGISTRATION:
        return [
            _field("Nombre completo", "full_name", FormFieldType.TEXT, True, 0),
            _field("Email", "email", FormFieldType.EMAIL, True, 1),
            _field("Teléfono", "phone", FormFieldType.PHONE, True, 2),
            _field("Marca de bicicleta", "bike_brand", FormFieldType.TEXT, True, 3),
            _field("Modelo de bicicleta", "bike_model", FormFieldType.TEXT, True, 4),
            _field("Color de bicicleta", "bike_color", FormFieldType.TEXT, True, 5),
            _field("Región de residencia", "residence_region", FormFieldType.TEXT, True, 6, analytics_key="residence_region"),
            _field("Número de ticket", "event_ticket_number", FormFieldType.TEXT, True, 7),
            _field("Comentarios", "comments", FormFieldType.TEXTAREA, False, 8, analytics_key="comments"),
        ]
    if form.form_type == EventFormType.EXPERIENCE_SURVEY:
        return [
            _field("Evaluación general", "general_rating", FormFieldType.RATING_1_7, True, 0, analytics_key="general_rating"),
            _field("Limpieza", "cleanliness_rating", FormFieldType.RATING_1_7, False, 1, analytics_key="cleanliness_rating"),
            _field("Baños", "bathroom_rating", FormFieldType.RATING_1_7, False, 2, analytics_key="bathroom_rating"),
            _field("¿Recomendarías el evento?", "would_recommend", FormFieldType.YES_NO, False, 3, analytics_key="would_recommend"),
            _field("Problema principal", "main_problem", FormFieldType.SELECT, False, 4, analytics_key="main_problem", options=["baños", "basura", "filas", "señalética", "accesos", "seguridad", "ninguno", "otro"]),
            _field("Comentarios", "comments", FormFieldType.TEXTAREA, False, 5, analytics_key="comments"),
        ]
    return []


DEFAULT_FIELD_TRANSLATIONS = {
    EventFormType.TRANSPORT_SURVEY: {
        "event_name": {"es": "Nombre del evento", "en": "Event name", "pt": "Nome do evento", "ko": "이벤트 이름"},
        "venue_name": {"es": "Nombre del venue / recinto", "en": "Venue", "pt": "Local / recinto", "ko": "장소"},
        "full_name": {"es": "Nombre completo", "en": "Full name", "pt": "Nome completo", "ko": "성명"},
        "company": {"es": "Empresa", "en": "Company", "pt": "Empresa", "ko": "회사"},
        "country_origin": {"es": "País de origen", "en": "Country of origin", "pt": "País de origem", "ko": "출신 국가"},
        "transport_mode": {"es": "Tipo de transporte utilizado para llegar", "en": "Type of transport used to arrive", "pt": "Tipo de transporte utilizado para chegar", "ko": "이용한 교통수단"},
    },
    EventFormType.BIKE_ZONE_REGISTRATION: {
        "full_name": {"es": "Nombre completo", "en": "Full name", "pt": "Nome completo", "ko": "성명"},
        "email": {"es": "Email", "en": "Email", "pt": "Email", "ko": "이메일"},
        "phone": {"es": "Teléfono", "en": "Phone", "pt": "Telefone", "ko": "전화번호"},
        "bike_brand": {"es": "Marca de bicicleta", "en": "Bike brand", "pt": "Marca da bicicleta", "ko": "자전거 브랜드"},
        "bike_model": {"es": "Modelo de bicicleta", "en": "Bike model", "pt": "Modelo da bicicleta", "ko": "자전거 모델"},
        "bike_color": {"es": "Color de bicicleta", "en": "Bike color", "pt": "Cor da bicicleta", "ko": "자전거 색상"},
        "residence_region": {"es": "Región de residencia", "en": "Region of residence", "pt": "Região de residência", "ko": "거주 지역"},
        "event_ticket_number": {"es": "Número de ticket", "en": "Ticket number", "pt": "Número do ingresso", "ko": "티켓 번호"},
        "comments": {"es": "Comentarios", "en": "Comments", "pt": "Comentários", "ko": "의견"},
    },
    EventFormType.EXPERIENCE_SURVEY: {
        "general_rating": {"es": "Evaluación general", "en": "Overall rating", "pt": "Avaliação geral", "ko": "전체 평가"},
        "cleanliness_rating": {"es": "Limpieza", "en": "Cleanliness", "pt": "Limpeza", "ko": "청결도"},
        "bathroom_rating": {"es": "Baños", "en": "Bathrooms", "pt": "Banheiros", "ko": "화장실"},
        "would_recommend": {"es": "¿Recomendarías el evento?", "en": "Would you recommend the event?", "pt": "Você recomendaria o evento?", "ko": "이 행사를 추천하시겠습니까?"},
        "main_problem": {"es": "Problema principal", "en": "Main problem", "pt": "Principal problema", "ko": "주요 문제"},
        "comments": {"es": "Comentarios", "en": "Comments", "pt": "Comentários", "ko": "의견"},
    },
}


DEFAULT_OPTION_TRANSLATIONS = {
    "auto": {"es": "Auto", "en": "Car", "pt": "Carro", "ko": "자동차"},
    "metro": {"es": "Metro", "en": "Metro", "pt": "Metrô", "ko": "지하철"},
    "bus": {"es": "Bus", "en": "Bus", "pt": "Ônibus", "ko": "버스"},
    "bicicleta": {"es": "Bicicleta", "en": "Bicycle", "pt": "Bicicleta", "ko": "자전거"},
    "caminando": {"es": "Caminando", "en": "Walking", "pt": "Caminhando", "ko": "도보"},
    "app_transporte": {"es": "App de transporte", "en": "Ride-hailing app", "pt": "Aplicativo de transporte", "ko": "차량 호출 앱"},
    "otro": {"es": "Otro", "en": "Other", "pt": "Outro", "ko": "기타"},
    "basura": {"es": "Basura", "en": "Waste", "pt": "Lixo", "ko": "쓰레기"},
    "filas": {"es": "Filas", "en": "Lines", "pt": "Filas", "ko": "대기줄"},
    "accesos": {"es": "Accesos", "en": "Access", "pt": "Acessos", "ko": "입장 동선"},
    "seguridad": {"es": "Seguridad", "en": "Security", "pt": "Segurança", "ko": "보안"},
    "ninguno": {"es": "Ninguno", "en": "None", "pt": "Nenhum", "ko": "없음"},
}


def _default_field_label(form_type: EventFormType, field_key: str, language: str) -> str | None:
    return DEFAULT_FIELD_TRANSLATIONS.get(form_type, {}).get(field_key, {}).get(language)


def _default_option_label(form_type: EventFormType, field_key: str, value: str, language: str) -> str | None:
    return DEFAULT_OPTION_TRANSLATIONS.get(value, {}).get(language)


def _transport_template(form: EventForm) -> list[dict]:
    event_name = form.event.name if form.event else ""
    venue = _venue_name(form)
    translations = {
        "event_name": {"es": "Nombre del evento", "en": "Event name", "pt": "Nome do evento", "ko": "이벤트 이름"},
        "venue_name": {"es": "Nombre del venue / recinto", "en": "Venue", "pt": "Local / recinto", "ko": "장소"},
        "full_name": {"es": "Nombre completo", "en": "Full name", "pt": "Nome completo", "ko": "성명"},
        "company": {"es": "Empresa", "en": "Company", "pt": "Empresa", "ko": "회사"},
        "country_origin": {"es": "País de origen", "en": "Country of origin", "pt": "País de origem", "ko": "출신 국가"},
        "transport_mode": {"es": "Tipo de transporte utilizado para llegar", "en": "Type of transport used to arrive", "pt": "Tipo de transporte utilizado para chegar", "ko": "이용한 교통수단"},
    }
    return [
        _field("Nombre del evento", "event_name", FormFieldType.TEXT, False, 0, placeholder=event_name, translations=translations["event_name"]),
        _field("Nombre del venue / recinto", "venue_name", FormFieldType.TEXT, False, 1, placeholder=venue, translations=translations["venue_name"]),
        _field("Nombre completo", "full_name", FormFieldType.TEXT, False, 2, translations=translations["full_name"]),
        _field("Empresa", "company", FormFieldType.TEXT, False, 3, translations=translations["company"]),
        _field("País de origen", "country_origin", FormFieldType.TEXT, True, 4, analytics_key="country_origin", translations=translations["country_origin"]),
        _field(
            "Tipo de transporte utilizado para llegar",
            "transport_mode",
            FormFieldType.SELECT,
            True,
            5,
            analytics_key="transport_mode",
            options=["auto", "metro", "bus", "bicicleta", "caminando", "app_transporte", "otro"],
            translations=translations["transport_mode"],
        ),
    ]


def _field(label, key, field_type, required, order, *, analytics_key=None, options=None, placeholder=None, translations=None):
    data = {
        "label": label,
        "field_key": key,
        "field_type": field_type,
        "is_required": required,
        "sort_order": order,
        "analytics_key": analytics_key,
        "placeholder": placeholder,
        "options": [],
        "translations": None,
    }
    if options:
        data["options"] = [type("Option", (), {"label": value.replace("_", " ").title(), "value": value, "sort_order": idx, "translations": None}) for idx, value in enumerate(options)]
    if translations:
        data["translations"] = {lang: {"label": text, "help_text": None, "placeholder": placeholder} for lang, text in translations.items()}
    return data


def _venue_name(form: EventForm) -> str | None:
    return (form.session.venue_name if form.session and form.session.venue_name else None) or (form.event.location_name if form.event else None)


def _unique_slug(db: Session, title: str) -> str:
    base = _slugify(title)
    slug = base
    index = 2
    while db.scalar(select(EventForm.id).where(EventForm.public_slug == slug)):
        slug = f"{base}-{index}"
        index += 1
    return slug


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or secrets.token_hex(4)


def _response_code(db: Session) -> str:
    while True:
        code = f"FR-{secrets.token_hex(4).upper()}"
        if not db.scalar(select(FormResponse.id).where(FormResponse.response_code == code)):
            return code


def _bike_code(db: Session) -> str:
    while True:
        code = f"BZ-{secrets.token_hex(3).upper()}"
        if not db.scalar(select(BikeZoneRecord.id).where(BikeZoneRecord.code == code)):
            return code


def _bucket(values: list) -> list[dict]:
    return [{"name": str(name), "value": count} for name, count in Counter(value for value in values if value not in (None, "")).most_common()]


def _flatten(values: list) -> list:
    flattened = []
    for value in values:
        if isinstance(value, list):
            flattened.extend(value)
        else:
            flattened.append(value)
    return flattened


def _rate(values: list[bool]) -> float | None:
    if not values:
        return None
    return round(sum(1 for value in values if value) / len(values) * 100, 2)


def _is_number(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
