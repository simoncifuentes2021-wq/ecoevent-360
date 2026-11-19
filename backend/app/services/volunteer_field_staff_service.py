from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import set_field_staff_context, set_public_volunteer_context
from app.models.core import Event, User
from app.models.volunteers import (
    FieldStaff,
    FieldStaffActivation,
    MaterialContribution,
    RecyclingActivation,
    Volunteer,
    VolunteerActivation,
)
from app.schemas.volunteer_schema import (
    ContributionCreate,
    FieldStaffCreate,
    FieldStaffLogin,
    FieldStaffUpdate,
    FieldStaffVolunteerRegistration,
)
from app.services import volunteer_service as volunteers
from app.services.document_people_service import normalize_person_name, normalize_rut


def _display_rut(normalized: str) -> str:
    digits, verifier = normalized[:-1], normalized[-1]
    grouped = f"{int(digits):,}".replace(",", ".")
    return f"{grouped}-{verifier}"


def _staff_read(staff: FieldStaff) -> dict:
    assignments = sorted(staff.assignments, key=lambda row: row.activation.name.casefold())
    return {
        "id": staff.id,
        "event_id": staff.event_id,
        "full_name": staff.full_name,
        "rut": staff.rut,
        "active": staff.active,
        "must_change_password": staff.must_change_password,
        "activation_ids": [row.activation_id for row in assignments],
        "activation_names": [row.activation.name for row in assignments],
        "created_at": staff.created_at,
    }


def _validate_activation_ids(db: Session, event_id: UUID, activation_ids: list[UUID]) -> list[RecyclingActivation]:
    unique_ids = set(activation_ids)
    if len(unique_ids) != len(activation_ids):
        raise HTTPException(status_code=422, detail="No repitas puntos de activación")
    rows = list(db.scalars(select(RecyclingActivation).options(
        selectinload(RecyclingActivation.allowed_materials)
    ).where(RecyclingActivation.id.in_(unique_ids), RecyclingActivation.event_id == event_id)).all())
    if len(rows) != len(unique_ids):
        raise HTTPException(status_code=400, detail="Cada punto asignado debe pertenecer al evento seleccionado")
    return rows


def list_field_staff(db: Session, event_id: UUID, user: User) -> list[dict]:
    volunteers._require_event_access(db, user, event_id, manage=True)
    rows = db.scalars(select(FieldStaff).options(
        selectinload(FieldStaff.assignments).selectinload(FieldStaffActivation.activation)
    ).where(FieldStaff.event_id == event_id).order_by(FieldStaff.full_name)).unique().all()
    return [_staff_read(row) for row in rows]


def get_field_staff_portal_status(db: Session, event_id: UUID, user: User) -> dict:
    event = volunteers._require_event_access(db, user, event_id, manage=True)
    return {"event_id": event.id, "enabled": event.field_staff_portal_enabled}


def update_field_staff_portal_status(
    db: Session, event_id: UUID, *, enabled: bool, user: User
) -> dict:
    event = volunteers._require_event_access(db, user, event_id, manage=True)
    event.field_staff_portal_enabled = enabled
    event.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return {"event_id": event.id, "enabled": event.field_staff_portal_enabled}


def create_field_staff(db: Session, event_id: UUID, payload: FieldStaffCreate, user: User) -> dict:
    volunteers._require_event_access(db, user, event_id, manage=True)
    activations = _validate_activation_ids(db, event_id, payload.activation_ids)
    try:
        rut_normalized = normalize_rut(payload.rut)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    temporary_password = secrets.token_urlsafe(10)
    staff = FieldStaff(
        event_id=event_id,
        full_name=normalize_person_name(payload.full_name),
        rut=_display_rut(rut_normalized),
        rut_normalized=rut_normalized,
        password_hash=hash_password(temporary_password),
        active=True,
        must_change_password=True,
        created_by_user_id=user.id,
        assignments=[FieldStaffActivation(activation=activation) for activation in activations],
    )
    db.add(staff)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe personal con ese RUT en este evento") from exc
    db.refresh(staff)
    return {"staff": _staff_read(staff), "temporary_password": temporary_password}


def update_field_staff(db: Session, staff_id: UUID, payload: FieldStaffUpdate, user: User) -> dict:
    staff = db.get(FieldStaff, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="No encontramos a este encargado")
    volunteers._require_event_access(db, user, staff.event_id, manage=True)
    values = payload.model_dump(exclude_unset=True)
    activation_ids = values.pop("activation_ids", None)
    if "full_name" in values and values["full_name"] is not None:
        staff.full_name = normalize_person_name(values["full_name"])
    if "rut" in values and values["rut"] is not None:
        try:
            normalized = normalize_rut(values["rut"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        staff.rut_normalized = normalized
        staff.rut = _display_rut(normalized)
    for key in ("active",):
        if key in values and values[key] is not None:
            setattr(staff, key, values[key])
    if activation_ids is not None:
        activations = _validate_activation_ids(db, staff.event_id, activation_ids)
        staff.assignments = [FieldStaffActivation(activation=activation) for activation in activations]
    staff.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe personal con ese RUT en este evento") from exc
    db.refresh(staff)
    return _staff_read(staff)


def reset_field_staff_password(db: Session, staff_id: UUID, user: User) -> dict:
    staff = db.get(FieldStaff, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="No encontramos a este encargado")
    volunteers._require_event_access(db, user, staff.event_id, manage=True)
    password = secrets.token_urlsafe(10)
    staff.password_hash = hash_password(password)
    staff.must_change_password = True
    staff.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"temporary_password": password}


def login_field_staff(db: Session, payload: FieldStaffLogin) -> dict:
    try:
        rut_normalized = normalize_rut(payload.rut)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="RUT o contraseña incorrectos") from exc
    set_field_staff_context(db, event_id=payload.event_id, rut_normalized=rut_normalized)
    staff = db.scalar(select(FieldStaff).where(
        FieldStaff.event_id == payload.event_id,
        FieldStaff.rut_normalized == rut_normalized,
    ))
    if staff is None or not staff.active or not verify_password(payload.password, staff.password_hash):
        raise HTTPException(status_code=401, detail="RUT o contraseña incorrectos")
    set_field_staff_context(db, field_staff_id=staff.id, event_id=staff.event_id)
    event = db.get(Event, staff.event_id)
    if event is None:
        raise HTTPException(status_code=401, detail="No encontramos el evento asociado a este acceso")
    if not event.field_staff_portal_enabled:
        raise HTTPException(
            status_code=403,
            detail="El acceso al formulario de terreno está desactivado por administración.",
        )
    token = create_access_token(
        {"sub": str(staff.id), "event_id": str(staff.event_id), "token_type": "field_staff"},
        expires_delta=timedelta(hours=8),
    )
    db.refresh(staff)
    return {"access_token": token, "token_type": "field_staff", "staff": _staff_read(staff), "event_name": event.name}


def change_field_staff_password(db: Session, staff: FieldStaff, new_password: str) -> None:
    staff.password_hash = hash_password(new_password)
    staff.must_change_password = False
    staff.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(staff)


def current_staff_activations(db: Session, staff: FieldStaff) -> list[dict]:
    rows = db.scalars(select(RecyclingActivation).options(
        selectinload(RecyclingActivation.event),
        selectinload(RecyclingActivation.allowed_materials),
    ).join(FieldStaffActivation, FieldStaffActivation.activation_id == RecyclingActivation.id).where(
        FieldStaffActivation.field_staff_id == staff.id,
        RecyclingActivation.status == "ACTIVE",
    ).order_by(RecyclingActivation.starts_at, RecyclingActivation.name)).unique().all()
    return [{
        "id": row.id,
        "event_id": row.event_id,
        "event_name": row.event.name,
        "name": row.name,
        "location_name": row.location_name,
        "starts_at": row.starts_at,
        "allowed_materials": [{"id": material.id, "name": material.name} for material in row.allowed_materials],
    } for row in rows]


def _require_assigned_activation(db: Session, staff: FieldStaff, activation_id: UUID) -> RecyclingActivation:
    activation = db.scalar(select(RecyclingActivation).options(
        selectinload(RecyclingActivation.allowed_materials)
    ).where(RecyclingActivation.id == activation_id, RecyclingActivation.event_id == staff.event_id))
    assigned = db.scalar(select(FieldStaffActivation.field_staff_id).where(
        FieldStaffActivation.field_staff_id == staff.id,
        FieldStaffActivation.activation_id == activation_id,
    ))
    if activation is None or assigned is None:
        raise HTTPException(status_code=404, detail="Este punto no está asignado a tu acceso")
    if activation.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Este punto no está recibiendo aportes actualmente")
    return activation


def search_event_volunteers(db: Session, staff: FieldStaff, query: str) -> list[dict]:
    value = query.strip()
    if len(value) < 2:
        raise HTTPException(status_code=422, detail="Escribe al menos dos caracteres para buscar")
    pattern = f"%{value}%"
    registration_exists = select(VolunteerActivation.id).join(
        RecyclingActivation, RecyclingActivation.id == VolunteerActivation.activation_id
    ).where(
        VolunteerActivation.volunteer_id == Volunteer.id,
        VolunteerActivation.status != "CANCELLED",
        RecyclingActivation.event_id == staff.event_id,
    ).exists()
    rows = db.scalars(select(Volunteer).where(
        registration_exists,
        Volunteer.status == "ACTIVE",
        or_(Volunteer.full_name.ilike(pattern), Volunteer.email.ilike(pattern),
            Volunteer.phone.ilike(pattern), Volunteer.unique_code.ilike(pattern)),
    ).order_by(Volunteer.full_name).limit(20)).all()
    output = []
    for volunteer in rows:
        total = db.scalar(select(func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0)).join(
            RecyclingActivation, RecyclingActivation.id == MaterialContribution.activation_id
        ).where(
            MaterialContribution.volunteer_id == volunteer.id,
            MaterialContribution.status == "ACTIVE",
            RecyclingActivation.event_id == staff.event_id,
        )) or Decimal("0")
        activation_names = list(db.scalars(select(RecyclingActivation.name).join(
            VolunteerActivation, VolunteerActivation.activation_id == RecyclingActivation.id
        ).where(
            VolunteerActivation.volunteer_id == volunteer.id,
            VolunteerActivation.status != "CANCELLED",
            RecyclingActivation.event_id == staff.event_id,
        ).order_by(RecyclingActivation.name)).all())
        output.append({
            "id": volunteer.id,
            "full_name": volunteer.full_name,
            "unique_code": volunteer.unique_code,
            "total_weight_kg_in_event": total,
            "activation_names": activation_names,
        })
    return output


def register_volunteer_at_activation(
    db: Session,
    staff: FieldStaff,
    activation_id: UUID,
    payload: FieldStaffVolunteerRegistration,
) -> dict:
    activation = _require_assigned_activation(db, staff, activation_id)
    set_field_staff_context(db, field_staff_id=staff.id, event_id=staff.event_id, activation_id=activation.id)
    now = datetime.now(timezone.utc)
    if payload.volunteer_id:
        volunteer = db.scalar(select(Volunteer).where(
            Volunteer.id == payload.volunteer_id,
            Volunteer.status == "ACTIVE",
            select(VolunteerActivation.id).join(
                RecyclingActivation, RecyclingActivation.id == VolunteerActivation.activation_id
            ).where(
                VolunteerActivation.volunteer_id == Volunteer.id,
                VolunteerActivation.status != "CANCELLED",
                RecyclingActivation.event_id == staff.event_id,
            ).exists(),
        ))
        if volunteer is None:
            raise HTTPException(status_code=404, detail="No encontramos a esta persona en el evento")
    else:
        email = volunteers.normalize_email(str(payload.email))
        email_hash = volunteers.email_lookup_hash(email)
        set_public_volunteer_context(db, email_hash=email_hash)
        code = f"VOL-{secrets.token_hex(4).upper()}"
        volunteer_id = db.execute(pg_insert(Volunteer).values(
            full_name=normalize_person_name(payload.full_name or ""),
            email=email,
            email_normalized=email,
            email_lookup_hash=email_hash,
            phone=payload.phone,
            phone_normalized=volunteers.normalize_phone(payload.phone),
            organization=payload.organization.strip() if payload.organization else None,
            unique_code=code,
            status="ACTIVE",
            consent_accepted=True,
            consent_accepted_at=now,
            consent_version=volunteers.CONSENT_VERSION,
            marketing_consent=payload.marketing_consent,
        ).on_conflict_do_nothing(index_elements=["email_normalized"]).returning(Volunteer.id)).scalar_one_or_none()
        volunteer = db.get(Volunteer, volunteer_id) if volunteer_id else db.scalar(
            select(Volunteer).where(Volunteer.email_normalized == email).with_for_update()
        )
        if volunteer is None or volunteer.status != "ACTIVE":
            db.rollback()
            raise HTTPException(status_code=409, detail="No se pudo reutilizar la ficha. Contacta a administración.")
    registration = db.scalar(select(VolunteerActivation).where(
        VolunteerActivation.volunteer_id == volunteer.id,
        VolunteerActivation.activation_id == activation.id,
    ))
    already = registration is not None and registration.status != "CANCELLED"
    if registration is None:
        if activation.capacity and volunteers._capacity_count(db, activation.id) >= activation.capacity:
            db.rollback()
            raise HTTPException(status_code=409, detail="Este punto alcanzó su capacidad de inscripción")
        db.add(VolunteerActivation(volunteer_id=volunteer.id, activation_id=activation.id))
    elif registration.status == "CANCELLED":
        registration.status = "REGISTERED"
        registration.registered_at = now
    db.commit()
    total = db.scalar(select(func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0)).join(
        RecyclingActivation, RecyclingActivation.id == MaterialContribution.activation_id
    ).where(
        MaterialContribution.volunteer_id == volunteer.id,
        MaterialContribution.status == "ACTIVE",
        RecyclingActivation.event_id == staff.event_id,
    )) or Decimal("0")
    return {
        "id": volunteer.id,
        "full_name": volunteer.full_name,
        "unique_code": volunteer.unique_code,
        "already_in_activation": already,
        "total_weight_kg_in_event": total,
    }


def field_staff_contribution(
    db: Session,
    staff: FieldStaff,
    activation_id: UUID,
    payload: ContributionCreate,
    *,
    commit: bool = True,
) -> tuple[MaterialContribution, str | None, bool]:
    activation = _require_assigned_activation(db, staff, activation_id)
    set_field_staff_context(db, field_staff_id=staff.id, event_id=staff.event_id, activation_id=activation.id)
    if payload.idempotency_key:
        duplicate = db.scalar(select(MaterialContribution).options(
            selectinload(MaterialContribution.items)
        ).where(MaterialContribution.activation_id == activation.id,
                MaterialContribution.idempotency_key == payload.idempotency_key))
        if duplicate:
            return duplicate, None, False
    volunteer = db.get(Volunteer, payload.volunteer_id)
    registered = db.scalar(select(VolunteerActivation.id).where(
        VolunteerActivation.volunteer_id == payload.volunteer_id,
        VolunteerActivation.activation_id == activation.id,
        VolunteerActivation.status != "CANCELLED",
    ))
    if volunteer is None or volunteer.status != "ACTIVE" or registered is None:
        raise HTTPException(status_code=404, detail="Registra primero a esta persona en el punto seleccionado")
    contribution = MaterialContribution(
        volunteer_id=volunteer.id,
        activation_id=activation.id,
        registered_by_field_staff_id=staff.id,
        notes=payload.notes,
        idempotency_key=payload.idempotency_key,
        email_status="PENDING" if volunteer.email else "SKIPPED",
    )
    db.add(contribution)
    db.flush()
    volunteers._make_contribution_items(
        db, contribution, payload.items,
        allowed_material_ids={material.id for material in activation.allowed_materials},
    )
    if not commit:
        return contribution, None, True
    db.commit()
    db.refresh(contribution)
    impact_url = None
    if volunteer.email:
        set_public_volunteer_context(db, email_hash=volunteer.email_lookup_hash)
        impact_url = volunteers._issue_access_token(db, volunteer.id)
    return contribution, impact_url, True


def field_staff_volunteer_history(db: Session, staff: FieldStaff, volunteer_id: UUID) -> dict:
    registration = db.scalar(select(VolunteerActivation.id).join(
        RecyclingActivation, RecyclingActivation.id == VolunteerActivation.activation_id
    ).where(
        VolunteerActivation.volunteer_id == volunteer_id,
        VolunteerActivation.status != "CANCELLED",
        RecyclingActivation.event_id == staff.event_id,
    ))
    volunteer = db.get(Volunteer, volunteer_id)
    if registration is None or volunteer is None:
        raise HTTPException(status_code=404, detail="No encontramos a esta persona en el evento")
    rows = db.execute(select(
        MaterialContribution,
        RecyclingActivation.name,
        User.full_name,
        FieldStaff.full_name,
    ).join(RecyclingActivation, RecyclingActivation.id == MaterialContribution.activation_id)
      .outerjoin(User, User.id == MaterialContribution.registered_by_user_id)
      .outerjoin(FieldStaff, FieldStaff.id == MaterialContribution.registered_by_field_staff_id)
      .options(selectinload(MaterialContribution.items))
      .where(MaterialContribution.volunteer_id == volunteer_id,
             RecyclingActivation.event_id == staff.event_id)
      .order_by(MaterialContribution.registered_at.desc())).all()
    activation_names = list(db.scalars(select(RecyclingActivation.name).join(
        VolunteerActivation, VolunteerActivation.activation_id == RecyclingActivation.id
    ).where(
        VolunteerActivation.volunteer_id == volunteer_id,
        VolunteerActivation.status != "CANCELLED",
        RecyclingActivation.event_id == staff.event_id,
    ).order_by(RecyclingActivation.name)).all())
    return {
        "volunteer": {"id": volunteer.id, "full_name": volunteer.full_name, "unique_code": volunteer.unique_code},
        "activation_names": activation_names,
        "total_weight_kg": sum((row[0].total_weight_kg for row in rows if row[0].status == "ACTIVE"), Decimal("0")),
        "contributions": [{
            "id": contribution.id,
            "activation_name": activation_name,
            "registered_at": contribution.registered_at,
            "registered_by_name": staff_name or user_name or "Registro de terreno",
            "status": contribution.status,
            "total_weight_kg": contribution.total_weight_kg,
            "items": [{"material": item.material_name_snapshot, "weight_kg": item.weight_kg, "unit": item.unit_snapshot} for item in contribution.items],
        } for contribution, activation_name, user_name, staff_name in rows],
    }
