from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.permissions import can_access_event, can_manage_event, can_operate_event
from app.db.session import set_public_volunteer_context
from app.models.core import Event, EventSession, EventStaff, Evidence, User, WasteType
from app.models.enums import UserRole
from app.models.volunteers import (
    FieldStaff,
    MaterialContribution,
    MaterialContributionItem,
    RecyclingActivation,
    Volunteer,
    VolunteerAccessToken,
    VolunteerActivation,
)
from app.schemas.volunteer_schema import (
    ContributionCreate,
    ContributionUpdate,
    PublicVolunteerRegistration,
    VolunteerActivationCreate,
    VolunteerActivationUpdate,
    VolunteerManualCreate,
    VolunteerUpdate,
)

CONSENT_VERSION = "greenway-volunteers-v1"
MAX_CONTRIBUTION_KG = Decimal("1000000.000")
CONSENT_TEXT = (
    "Acepto el registro de mis datos para gestionar mi participación en esta iniciativa "
    "y recibir información asociada a mis aportes."
)


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def email_lookup_hash(value: str) -> str:
    return hashlib.sha256(normalize_email(value).encode("utf-8")).hexdigest()


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    return digits or None


def calculate_contribution_total(weights: list[Decimal]) -> Decimal:
    if not weights:
        raise ValueError("La entrega debe incluir al menos un material")
    total = Decimal("0")
    for raw_weight in weights:
        weight = Decimal(raw_weight)
        if not weight.is_finite() or weight <= 0 or weight > MAX_CONTRIBUTION_KG:
            raise ValueError("Cada peso debe ser mayor que cero y no superar 1.000.000 kg")
        total += weight.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    total = total.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if total > MAX_CONTRIBUTION_KG:
        raise ValueError("El peso total de la entrega supera el máximo permitido")
    return total


def _can_manage(user: User, event_id: UUID, db: Session) -> bool:
    return can_manage_event(user, event_id, db)


def _can_record(user: User, event_id: UUID, db: Session) -> bool:
    if can_manage_event(user, event_id, db):
        return True
    if user.role == UserRole.WORKER and can_operate_event(user, event_id, db):
        return True
    if user.role == UserRole.LOGISTICS_OPERATOR and can_access_event(user, event_id, db):
        return db.scalar(
            select(EventStaff.id).where(EventStaff.event_id == event_id, EventStaff.user_id == user.id)
        ) is not None
    return False


def _activation_or_404(db: Session, activation_id: UUID, *, lock: bool = False) -> RecyclingActivation:
    stmt = select(RecyclingActivation).options(
        selectinload(RecyclingActivation.allowed_materials)
    ).where(RecyclingActivation.id == activation_id)
    if lock:
        stmt = stmt.with_for_update()
    activation = db.scalar(stmt)
    if activation is None:
        raise HTTPException(status_code=404, detail="No encontramos la activación")
    return activation


def _require_event_access(db: Session, user: User, event_id: UUID, *, manage: bool = False) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="No encontramos el evento")
    allowed = _can_manage(user, event_id, db) if manage else can_access_event(user, event_id, db)
    if not allowed:
        raise HTTPException(status_code=403, detail="No tienes acceso a este evento")
    return event


def list_activations(
    db: Session,
    user: User,
    *,
    event_id: UUID,
    activation_status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[dict]:
    _require_event_access(db, user, event_id)
    if not (_can_manage(user, event_id, db) or _can_record(user, event_id, db)):
        raise HTTPException(status_code=403, detail="No tienes permiso para gestionar activaciones")
    stmt = select(RecyclingActivation).options(
        selectinload(RecyclingActivation.event),
        selectinload(RecyclingActivation.allowed_materials),
    ).where(
        RecyclingActivation.event_id == event_id
    )
    if activation_status:
        stmt = stmt.where(RecyclingActivation.status == activation_status)
    if date_from:
        stmt = stmt.where(RecyclingActivation.starts_at >= date_from)
    if date_to:
        stmt = stmt.where(RecyclingActivation.starts_at < date_to)
    rows = db.scalars(stmt.order_by(RecyclingActivation.starts_at.desc())).all()
    output = []
    for activation in rows:
        if not (_can_manage(user, event_id, db) or _can_record(user, event_id, db)):
            continue
        output.append({
            "id": activation.id,
            "event_id": activation.event_id,
            "session_id": activation.session_id,
            "event_name": activation.event.name,
            "name": activation.name,
            "description": activation.description,
            "location_name": activation.location_name,
            "address": activation.address,
            "starts_at": activation.starts_at,
            "ends_at": activation.ends_at,
            "responsible_user_id": activation.responsible_user_id,
            "status": activation.status,
            "capacity": activation.capacity,
            "public_slug": activation.public_slug,
            "created_at": activation.created_at,
            "updated_at": activation.updated_at,
            "volunteer_count": db.scalar(select(func.count(VolunteerActivation.id)).where(
                VolunteerActivation.activation_id == activation.id,
                VolunteerActivation.status != "CANCELLED",
            )) or 0,
            "contribution_count": db.scalar(select(func.count(MaterialContribution.id)).where(
                MaterialContribution.activation_id == activation.id,
                MaterialContribution.status == "ACTIVE",
            )) or 0,
            "total_weight_kg": db.scalar(select(func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0)).where(
                MaterialContribution.activation_id == activation.id,
                MaterialContribution.status == "ACTIVE",
            )) or Decimal("0"),
            "allowed_material_ids": [material.id for material in activation.allowed_materials],
        })
    return output


def create_activation(db: Session, payload: VolunteerActivationCreate, user: User) -> RecyclingActivation:
    _require_event_access(db, user, payload.event_id, manage=True)
    if payload.session_id:
        session = db.get(EventSession, payload.session_id)
        if not session or session.event_id != payload.event_id:
            raise HTTPException(status_code=400, detail="La sesión seleccionada no pertenece a este evento")
        if session.archived_at:
            raise HTTPException(status_code=400, detail="No se puede usar una sesión archivada")
    allowed_materials = _validate_activation_material_ids(db, payload.allowed_material_ids)
    slug = secrets.token_urlsafe(24)
    values = payload.model_dump(exclude={"allowed_material_ids"})
    activation = RecyclingActivation(
        **values, public_slug=slug, created_by=user.id, status="DRAFT",
        allowed_materials=allowed_materials,
    )
    db.add(activation)
    db.commit()
    db.refresh(activation)
    return activation


def update_activation(
    db: Session, activation_id: UUID, payload: VolunteerActivationUpdate, user: User
) -> RecyclingActivation:
    activation = _activation_or_404(db, activation_id)
    _require_event_access(db, user, activation.event_id, manage=True)
    values = payload.model_dump(exclude_unset=True)
    allowed_material_ids = values.pop("allowed_material_ids", None)
    if values.get("session_id"):
        session = db.get(EventSession, values["session_id"])
        if not session or session.event_id != activation.event_id or session.archived_at:
            raise HTTPException(status_code=400, detail="La sesión no pertenece al evento o está archivada")
    proposed_start = values.get("starts_at", activation.starts_at)
    proposed_end = values.get("ends_at", activation.ends_at)
    if proposed_end and proposed_end < proposed_start:
        raise HTTPException(status_code=400, detail="La fecha de término debe ser posterior al inicio")
    if allowed_material_ids is not None:
        activation.allowed_materials = _validate_activation_material_ids(db, allowed_material_ids)
    if values.get("status") == "ACTIVE" and not activation.allowed_materials:
        raise HTTPException(status_code=409, detail="Selecciona al menos un material reciclable antes de activar el punto")
    if values.get("status") in {"CANCELLED", "ARCHIVED"} and activation.status != values["status"]:
        if db.scalar(select(MaterialContribution.id).where(
            MaterialContribution.activation_id == activation.id,
            MaterialContribution.status == "ACTIVE",
        )):
            raise HTTPException(status_code=409, detail="La activación tiene aportes. Anúlala o ciérrala conservando el historial.")
    for key, value in values.items():
        setattr(activation, key, value)
    activation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(activation)
    return activation


def _validate_activation_material_ids(db: Session, material_ids: list[UUID]) -> list[WasteType]:
    unique_ids = set(material_ids)
    if len(unique_ids) != len(material_ids):
        raise HTTPException(status_code=422, detail="No repitas materiales en la activación")
    if not unique_ids:
        return []
    rows = list(db.scalars(select(WasteType).where(
        WasteType.id.in_(unique_ids), WasteType.is_recyclable.is_(True)
    )).all())
    if len(rows) != len(unique_ids):
        raise HTTPException(status_code=400, detail="Uno de los materiales no existe o no está marcado como reciclable")
    return rows


def get_public_activation(db: Session, slug: str) -> tuple[RecyclingActivation, Event]:
    activation = db.scalar(
        select(RecyclingActivation).options(selectinload(RecyclingActivation.event)).where(
            RecyclingActivation.public_slug == slug,
            RecyclingActivation.status == "ACTIVE",
        )
    )
    if activation is None:
        raise HTTPException(status_code=404, detail="Esta inscripción no está disponible")
    return activation, activation.event


def _capacity_count(db: Session, activation_id: UUID) -> int:
    return db.scalar(select(func.count(VolunteerActivation.id)).where(
        VolunteerActivation.activation_id == activation_id,
        VolunteerActivation.status != "CANCELLED",
    )) or 0


def register_public_volunteer(
    db: Session, payload: PublicVolunteerRegistration
) -> tuple[Volunteer, RecyclingActivation, bool, str]:
    activation = db.scalar(select(RecyclingActivation).options(
        selectinload(RecyclingActivation.event)
    ).where(
        RecyclingActivation.public_slug == payload.activation_slug,
        RecyclingActivation.status == "ACTIVE",
    ).with_for_update())
    if activation is None:
        raise HTTPException(status_code=404, detail="Esta activación no está disponible")
    normalized_email = normalize_email(str(payload.email))
    lookup_hash = email_lookup_hash(normalized_email)
    now = datetime.now(timezone.utc)
    code = f"VOL-{secrets.token_hex(4).upper()}"
    result = db.execute(
        pg_insert(Volunteer)
        .values(
            full_name=payload.full_name,
            email=normalized_email,
            email_normalized=normalized_email,
            email_lookup_hash=lookup_hash,
            phone=payload.phone,
            phone_normalized=normalize_phone(payload.phone),
            organization=payload.organization.strip() if payload.organization else None,
            unique_code=code,
            status="ACTIVE",
            consent_accepted=True,
            consent_accepted_at=now,
            consent_version=CONSENT_VERSION,
            marketing_consent=payload.marketing_consent,
        )
        .on_conflict_do_nothing(index_elements=["email_normalized"])
        .returning(Volunteer.id)
    )
    volunteer_id = result.scalar_one_or_none()
    is_new = volunteer_id is not None
    if is_new:
        volunteer = db.get(Volunteer, volunteer_id)
    else:
        volunteer = db.scalar(select(Volunteer).where(Volunteer.email_normalized == normalized_email).with_for_update())
        if volunteer is None:
            db.rollback()
            raise HTTPException(status_code=409, detail="No se pudo completar la inscripción. Inténtalo nuevamente.")
        if volunteer.status != "ACTIVE":
            raise HTTPException(status_code=409, detail="Este registro de voluntario está inactivo. Contacta al equipo de la activación.")
    existing = db.scalar(select(VolunteerActivation).where(
        VolunteerActivation.volunteer_id == volunteer.id,
        VolunteerActivation.activation_id == activation.id,
    ))
    if existing is None:
        if activation.capacity and _capacity_count(db, activation.id) >= activation.capacity:
            db.rollback()
            raise HTTPException(status_code=409, detail="La activación alcanzó su capacidad de inscripción")
        db.add(VolunteerActivation(volunteer_id=volunteer.id, activation_id=activation.id))
    elif existing.status == "CANCELLED":
        existing.status = "REGISTERED"
        existing.registered_at = now
    # Do not reveal whether the submitted email belongs to an existing person.
    access_token = secrets.token_urlsafe(36)
    db.add(VolunteerAccessToken(
        volunteer_id=volunteer.id,
        token_hash=hashlib.sha256(access_token.encode()).hexdigest(),
        expires_at=now + timedelta(days=365),
    ))
    db.commit()
    impact_url = f"{_public_base_url()}/public/mi-aporte/{access_token}"
    return volunteer, activation, not is_new or existing is not None, impact_url


def create_staff_volunteer(
    db: Session,
    activation_id: UUID,
    payload: VolunteerManualCreate,
    user: User,
) -> tuple[Volunteer, bool]:
    activation = _activation_or_404(db, activation_id, lock=True)
    if not _can_record(user, activation.event_id, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para registrar participantes")
    if activation.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Solo puedes registrar personas en una activación activa")
    email = normalize_email(str(payload.email))
    lookup_hash = email_lookup_hash(email)
    set_public_volunteer_context(db, email_hash=lookup_hash)
    code = f"VOL-{secrets.token_hex(4).upper()}"
    now = datetime.now(timezone.utc)
    inserted_id = db.execute(
        pg_insert(Volunteer)
        .values(
            full_name=payload.full_name,
            email=email,
            email_normalized=email,
            email_lookup_hash=lookup_hash,
            phone=payload.phone,
            phone_normalized=normalize_phone(payload.phone),
            organization=payload.organization.strip() if payload.organization else None,
            unique_code=code,
            status="ACTIVE",
            consent_accepted=True,
            consent_accepted_at=now,
            consent_version=CONSENT_VERSION,
            marketing_consent=payload.marketing_consent,
        )
        .on_conflict_do_nothing(index_elements=["email_normalized"])
        .returning(Volunteer.id)
    ).scalar_one_or_none()
    volunteer = db.get(Volunteer, inserted_id) if inserted_id else db.scalar(
        select(Volunteer).where(Volunteer.email_normalized == email).with_for_update()
    )
    if volunteer is None:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo registrar al voluntario. Inténtalo nuevamente.")
    if volunteer.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="La ficha de esta persona está inactiva")
    registration = db.scalar(select(VolunteerActivation).where(
        VolunteerActivation.volunteer_id == volunteer.id,
        VolunteerActivation.activation_id == activation.id,
    ))
    already_in_activation = registration is not None and registration.status != "CANCELLED"
    if registration is None:
        if activation.capacity and _capacity_count(db, activation.id) >= activation.capacity:
            db.rollback()
            raise HTTPException(status_code=409, detail="La activación alcanzó su capacidad")
        db.add(VolunteerActivation(volunteer_id=volunteer.id, activation_id=activation.id))
    elif registration.status == "CANCELLED":
        registration.status = "REGISTERED"
        registration.registered_at = now
    if not volunteer.consent_accepted:
        volunteer.consent_accepted = True
        volunteer.consent_accepted_at = now
        volunteer.consent_version = CONSENT_VERSION
    db.commit()
    return volunteer, already_in_activation


def lookup_volunteer_for_activation(
    db: Session, activation_id: UUID, query: str, user: User
) -> dict | None:
    activation = _activation_or_404(db, activation_id)
    if not _can_record(user, activation.event_id, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para buscar participantes")
    value = query.strip()
    email_hash = email_lookup_hash(value) if "@" in value else None
    phone = normalize_phone(value) if not email_hash else None
    code = value.upper() if value.upper().startswith("VOL-") else None
    if not any((email_hash, phone, code)):
        return None
    set_public_volunteer_context(db, email_hash=email_hash, phone_normalized=phone, volunteer_code=code)
    filters = []
    if email_hash:
        filters.append(Volunteer.email_lookup_hash == email_hash)
    if phone:
        filters.append(Volunteer.phone_normalized == phone)
    if code:
        filters.append(Volunteer.unique_code == code)
    volunteer = db.scalar(select(Volunteer).where(or_(*filters), Volunteer.status == "ACTIVE"))
    if volunteer is None:
        return None
    already_in_activation = db.scalar(select(VolunteerActivation.id).where(
        VolunteerActivation.volunteer_id == volunteer.id,
        VolunteerActivation.activation_id == activation_id,
        VolunteerActivation.status != "CANCELLED",
    )) is not None
    event_weight = db.scalar(select(func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0)).join(
        RecyclingActivation, RecyclingActivation.id == MaterialContribution.activation_id
    ).where(MaterialContribution.volunteer_id == volunteer.id,
             MaterialContribution.status == "ACTIVE",
             RecyclingActivation.event_id == activation.event_id)) or Decimal("0")
    return {
        "id": volunteer.id,
        "full_name": volunteer.full_name,
        "unique_code": volunteer.unique_code,
        "already_in_activation": already_in_activation,
        "total_weight_kg_in_event": event_weight,
    }


def _public_base_url() -> str:
    if settings.app_env.lower() in {"local", "development", "dev"}:
        return (settings.public_app_url or "http://localhost:3001").rstrip("/")
    return (settings.public_app_url or settings.official_frontend_url).rstrip("/")


def list_materials(db: Session) -> list[WasteType]:
    """Return recyclable waste types from the canonical shared catalog."""
    return list(db.scalars(
        select(WasteType)
        .where(WasteType.is_recyclable.is_(True))
        .order_by(WasteType.name)
    ).all())


def list_volunteers(
    db: Session,
    user: User,
    *,
    event_id: UUID,
    activation_id: UUID | None,
    search: str | None,
    volunteer_status: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    limit: int,
) -> tuple[list[dict], int]:
    _require_event_access(db, user, event_id)
    if not (_can_manage(user, event_id, db) or _can_record(user, event_id, db)):
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar voluntarios")
    registration = select(
        VolunteerActivation.volunteer_id.label("volunteer_id"),
        func.min(VolunteerActivation.registered_at).label("registered_at"),
        func.count(func.distinct(VolunteerActivation.activation_id)).label("activation_count"),
    ).join(RecyclingActivation, RecyclingActivation.id == VolunteerActivation.activation_id).where(
        RecyclingActivation.event_id == event_id,
        VolunteerActivation.status != "CANCELLED",
    ).group_by(VolunteerActivation.volunteer_id).subquery()
    totals = select(
        MaterialContribution.volunteer_id.label("volunteer_id"),
        func.count(MaterialContribution.id).label("contribution_count"),
        func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0).label("total_weight_kg"),
    ).join(RecyclingActivation, RecyclingActivation.id == MaterialContribution.activation_id).where(
        RecyclingActivation.event_id == event_id,
        MaterialContribution.status == "ACTIVE",
    ).group_by(MaterialContribution.volunteer_id).subquery()
    stmt = select(Volunteer, registration.c.registered_at, registration.c.activation_count,
                  func.coalesce(totals.c.contribution_count, 0), func.coalesce(totals.c.total_weight_kg, 0))
    stmt = stmt.join(registration, registration.c.volunteer_id == Volunteer.id).outerjoin(
        totals, totals.c.volunteer_id == Volunteer.id
    )
    if activation_id:
        stmt = stmt.join(VolunteerActivation, and_(
            VolunteerActivation.volunteer_id == Volunteer.id,
            VolunteerActivation.activation_id == activation_id,
            VolunteerActivation.status != "CANCELLED",
        ))
    if volunteer_status:
        stmt = stmt.where(Volunteer.status == volunteer_status)
    if date_from:
        stmt = stmt.where(registration.c.registered_at >= datetime.combine(date_from, datetime.min.time(), timezone.utc))
    if date_to:
        stmt = stmt.where(registration.c.registered_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), timezone.utc))
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Volunteer.full_name.ilike(term), Volunteer.email.ilike(term),
                              Volunteer.phone.ilike(term), Volunteer.unique_code.ilike(term)))
    stmt = stmt.distinct()
    total = db.scalar(select(func.count()).select_from(
        stmt.with_only_columns(Volunteer.id).order_by(None).distinct().subquery()
    )) or 0
    rows = db.execute(stmt.order_by(registration.c.registered_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    can_see_contact = user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}
    return ([{
        "id": volunteer.id,
        "full_name": volunteer.full_name,
        "email": volunteer.email if can_see_contact else None,
        "phone": volunteer.phone if can_see_contact else None,
        "organization": volunteer.organization,
        "unique_code": volunteer.unique_code,
        "status": volunteer.status,
        "registered_at": registered_at,
        "activation_count": int(activation_count),
        "contribution_count": int(contribution_count),
        "total_weight_kg": total_weight,
    } for volunteer, registered_at, activation_count, contribution_count, total_weight in rows], total)


def update_volunteer(db: Session, volunteer_id: UUID, payload: VolunteerUpdate, user: User, event_id: UUID) -> Volunteer:
    _require_event_access(db, user, event_id, manage=True)
    volunteer = db.get(Volunteer, volunteer_id)
    if volunteer is None or not db.scalar(select(VolunteerActivation.id).join(
        RecyclingActivation, RecyclingActivation.id == VolunteerActivation.activation_id
    ).where(VolunteerActivation.volunteer_id == volunteer_id, RecyclingActivation.event_id == event_id)):
        raise HTTPException(status_code=404, detail="No encontramos al voluntario en este evento")
    values = payload.model_dump(exclude_unset=True)
    if "email" in values and values["email"]:
        normalized = normalize_email(str(values["email"]))
        duplicate = db.scalar(select(Volunteer.id).where(
            Volunteer.email_normalized == normalized, Volunteer.id != volunteer_id
        ))
        if duplicate:
            raise HTTPException(status_code=409, detail="Ya existe otro voluntario con ese correo")
        volunteer.email = normalized
        volunteer.email_normalized = normalized
        volunteer.email_lookup_hash = email_lookup_hash(normalized)
    for key in ("full_name", "phone", "organization", "status"):
        if key in values:
            setattr(volunteer, key, values[key])
    if "phone" in values:
        volunteer.phone_normalized = normalize_phone(values["phone"])
    volunteer.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(volunteer)
    return volunteer


def _make_contribution_items(
    db: Session,
    contribution: MaterialContribution,
    items,
    *,
    allowed_material_ids: set[UUID],
) -> Decimal:
    material_ids = {entry.material_id for entry in items}
    if not material_ids.issubset(allowed_material_ids):
        raise HTTPException(status_code=400, detail="La activación no recibe uno de los materiales seleccionados")
    materials = {
        item.id: item for item in db.scalars(select(WasteType).where(
            WasteType.id.in_(material_ids), WasteType.is_recyclable.is_(True)
        )).all()
    }
    if len(materials) != len(material_ids):
        raise HTTPException(status_code=400, detail="Uno de los materiales ya no está disponible")
    try:
        total = calculate_contribution_total([Decimal(entry.weight_kg) for entry in items])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    contribution.items.clear()
    # The table has a unique constraint on (contribution_id, material_id).
    # Flush the orphan deletions before inserting replacement rows, otherwise
    # correcting an item while keeping the same material can violate it.
    db.flush()
    for entry in items:
        weight = Decimal(entry.weight_kg).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        material = materials[entry.material_id]
        contribution.items.append(MaterialContributionItem(
            material_id=material.id,
            material_name_snapshot=material.name,
            unit_snapshot="kg",
            weight_kg=weight,
        ))
    contribution.total_weight_kg = total
    return total


def create_contribution(
    db: Session, activation_id: UUID, payload: ContributionCreate, user: User
) -> tuple[MaterialContribution, str | None, bool]:
    activation = _activation_or_404(db, activation_id, lock=True)
    if not _can_record(user, activation.event_id, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para registrar aportes en esta activación")
    if activation.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Solo se pueden registrar aportes en una activación activa")
    if payload.idempotency_key:
        duplicate = db.scalar(select(MaterialContribution).options(selectinload(MaterialContribution.items)).where(
            MaterialContribution.activation_id == activation.id,
            MaterialContribution.idempotency_key == payload.idempotency_key,
        ))
        if duplicate:
            return duplicate, None, False
    volunteer = db.get(Volunteer, payload.volunteer_id)
    if not volunteer or volunteer.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="No encontramos al voluntario activo")
    registration = db.scalar(select(VolunteerActivation).where(
        VolunteerActivation.volunteer_id == volunteer.id,
        VolunteerActivation.activation_id == activation.id,
    ))
    if registration is None:
        registration = VolunteerActivation(volunteer_id=volunteer.id, activation_id=activation.id)
        db.add(registration)
    elif registration.status == "CANCELLED":
        registration.status = "REGISTERED"
        registration.registered_at = datetime.now(timezone.utc)
    contribution = MaterialContribution(
        volunteer_id=volunteer.id,
        activation_id=activation.id,
        registered_by_user_id=user.id,
        notes=payload.notes,
        idempotency_key=payload.idempotency_key,
        email_status="PENDING" if volunteer.email else "SKIPPED",
    )
    db.add(contribution)
    db.flush()
    _make_contribution_items(
        db, contribution, payload.items,
        allowed_material_ids={material.id for material in activation.allowed_materials},
    )
    db.commit()
    db.refresh(contribution)
    db.refresh(volunteer)
    impact_url = None
    if volunteer.email:
        impact_url = _issue_access_token(db, volunteer.id)
    return contribution, impact_url, True


def _issue_access_token(db: Session, volunteer_id: UUID) -> str:
    raw = secrets.token_urlsafe(36)
    now = datetime.now(timezone.utc)
    db.add(VolunteerAccessToken(
        volunteer_id=volunteer_id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=now + timedelta(days=365),
    ))
    db.commit()
    return f"{_public_base_url()}/public/mi-aporte/{raw}"


def update_contribution(
    db: Session, contribution_id: UUID, payload: ContributionUpdate, user: User
) -> tuple[MaterialContribution, dict]:
    contribution = db.scalar(select(MaterialContribution).options(
        selectinload(MaterialContribution.items)
    ).where(MaterialContribution.id == contribution_id).with_for_update())
    if contribution is None:
        raise HTTPException(status_code=404, detail="No encontramos la entrega")
    if not _can_manage(user, contribution.activation.event_id, db):
        raise HTTPException(status_code=403, detail="Solo administración o supervisión puede corregir una entrega")
    if contribution.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Una entrega anulada no se puede editar")
    before = {
        "items": [{"material": item.material_name_snapshot, "weight_kg": str(item.weight_kg)} for item in contribution.items],
        "total_weight_kg": str(contribution.total_weight_kg),
        "notes": contribution.notes,
    }
    existing_material_ids = {item.material_id for item in contribution.items}
    total = _make_contribution_items(
        db, contribution, payload.items,
        allowed_material_ids={material.id for material in contribution.activation.allowed_materials}
        | existing_material_ids,
    )
    contribution.total_weight_kg = total
    contribution.notes = payload.notes
    contribution.updated_by_user_id = user.id
    contribution.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(contribution)
    return contribution, before


def void_contribution(db: Session, contribution_id: UUID, reason: str, user: User) -> MaterialContribution:
    contribution = db.scalar(select(MaterialContribution).where(MaterialContribution.id == contribution_id).with_for_update())
    if contribution is None:
        raise HTTPException(status_code=404, detail="No encontramos la entrega")
    if not _can_manage(user, contribution.activation.event_id, db):
        raise HTTPException(status_code=403, detail="Solo administración o supervisión puede anular una entrega")
    if contribution.status == "VOID":
        raise HTTPException(status_code=409, detail="La entrega ya está anulada")
    contribution.status = "VOID"
    contribution.void_reason = reason.strip()
    contribution.voided_by_user_id = user.id
    contribution.voided_at = datetime.now(timezone.utc)
    contribution.updated_at = contribution.voided_at
    db.commit()
    db.refresh(contribution)
    return contribution


def _contribution_dict(db: Session, contribution: MaterialContribution) -> dict:
    activation = contribution.activation
    event = activation.event
    recorder = db.get(User, contribution.registered_by_user_id) if contribution.registered_by_user_id else None
    field_staff = db.get(FieldStaff, contribution.registered_by_field_staff_id) if contribution.registered_by_field_staff_id else None
    return {
        "id": contribution.id,
        "volunteer_id": contribution.volunteer_id,
        "volunteer_name": contribution.volunteer.full_name,
        "volunteer_email": contribution.volunteer.email,
        "volunteer_code": contribution.volunteer.unique_code,
        "activation_id": activation.id,
        "activation_name": activation.name,
        "event_id": event.id,
        "event_name": event.name,
        "registered_by_user_id": contribution.registered_by_user_id,
        "registered_by_field_staff_id": contribution.registered_by_field_staff_id,
        "registered_by_name": recorder.full_name if recorder else field_staff.full_name if field_staff else None,
        "registered_at": contribution.registered_at,
        "notes": contribution.notes,
        "total_weight_kg": contribution.total_weight_kg,
        "status": contribution.status,
        "void_reason": contribution.void_reason,
        "voided_at": contribution.voided_at,
        "email_status": contribution.email_status,
        "items": contribution.items,
        "evidence_count": db.scalar(select(func.count(Evidence.id)).where(
            Evidence.volunteer_contribution_id == contribution.id
        )) or 0,
    }


def serialize_contribution(db: Session, contribution: MaterialContribution, user: User) -> dict:
    data = _contribution_dict(db, contribution)
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        data["volunteer_email"] = None
    return data


def list_contributions(
    db: Session,
    user: User,
    *,
    event_id: UUID,
    activation_id: UUID | None,
    volunteer_id: UUID | None,
    material_id: UUID | None,
    registered_by: UUID | None,
    status_filter: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    page: int,
    limit: int,
) -> tuple[list[dict], int]:
    _require_event_access(db, user, event_id)
    if not (_can_manage(user, event_id, db) or _can_record(user, event_id, db)):
        raise HTTPException(status_code=403, detail="No tienes permiso para ver estos aportes")
    stmt = select(MaterialContribution).join(
        RecyclingActivation, RecyclingActivation.id == MaterialContribution.activation_id
    ).where(RecyclingActivation.event_id == event_id)
    if activation_id:
        stmt = stmt.where(MaterialContribution.activation_id == activation_id)
    if volunteer_id:
        stmt = stmt.where(MaterialContribution.volunteer_id == volunteer_id)
    if material_id:
        stmt = stmt.join(MaterialContributionItem).where(MaterialContributionItem.material_id == material_id)
    if registered_by:
        stmt = stmt.where(MaterialContribution.registered_by_user_id == registered_by)
    if status_filter:
        stmt = stmt.where(MaterialContribution.status == status_filter)
    if date_from:
        stmt = stmt.where(MaterialContribution.registered_at >= date_from)
    if date_to:
        stmt = stmt.where(MaterialContribution.registered_at < date_to)
    count_stmt = select(func.count(func.distinct(MaterialContribution.id))).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.options(
        selectinload(MaterialContribution.items),
        selectinload(MaterialContribution.volunteer),
        selectinload(MaterialContribution.activation).selectinload(RecyclingActivation.event),
    ).order_by(MaterialContribution.registered_at.desc()).offset((page - 1) * limit).limit(limit)).unique().all()
    return [serialize_contribution(db, row, user) for row in rows], int(total)


def get_contribution(db: Session, contribution_id: UUID, user: User) -> MaterialContribution:
    contribution = db.scalar(select(MaterialContribution).options(
        selectinload(MaterialContribution.items), selectinload(MaterialContribution.volunteer),
        selectinload(MaterialContribution.activation).selectinload(RecyclingActivation.event),
    ).where(MaterialContribution.id == contribution_id))
    if contribution is None:
        raise HTTPException(status_code=404, detail="No encontramos la entrega")
    if user.role == UserRole.CLIENT or not can_access_event(user, contribution.activation.event_id, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar esta entrega")
    return contribution


def _impact_data(db: Session, volunteer: Volunteer, *, event_id: UUID | None = None) -> dict:
    stmt = select(MaterialContribution).options(
        selectinload(MaterialContribution.items),
        selectinload(MaterialContribution.activation).selectinload(RecyclingActivation.event),
    ).where(MaterialContribution.volunteer_id == volunteer.id, MaterialContribution.status == "ACTIVE")
    if event_id:
        stmt = stmt.join(RecyclingActivation).where(RecyclingActivation.event_id == event_id)
    contributions = db.scalars(stmt.order_by(MaterialContribution.registered_at.desc())).unique().all()
    material_totals: dict[str, Decimal] = {}
    public_rows = []
    for contribution in contributions:
        item_rows = []
        for item in contribution.items:
            material_totals[item.material_name_snapshot] = material_totals.get(item.material_name_snapshot, Decimal("0")) + item.weight_kg
            item_rows.append({"material": item.material_name_snapshot, "weight_kg": item.weight_kg, "unit": item.unit_snapshot})
        evidence_rows = db.execute(select(Evidence.id, Evidence.description, Evidence.file_type).where(
            Evidence.volunteer_contribution_id == contribution.id
        ).order_by(Evidence.created_at.desc())).all()
        public_rows.append({
            "id": contribution.id,
            "activation": contribution.activation.name,
            "event": contribution.activation.event.name,
            "registered_at": contribution.registered_at,
            "total_weight_kg": contribution.total_weight_kg,
            "items": item_rows,
            "evidences": [{"id": row.id, "description": row.description, "file_type": row.file_type} for row in evidence_rows],
        })
    total = sum((row.total_weight_kg for row in contributions), Decimal("0"))
    activation_count = db.scalar(select(func.count(func.distinct(MaterialContribution.activation_id))).where(
        MaterialContribution.volunteer_id == volunteer.id,
        MaterialContribution.status == "ACTIVE",
        *([MaterialContribution.activation_id.in_(select(RecyclingActivation.id).where(RecyclingActivation.event_id == event_id))] if event_id else []),
    )) or 0
    return {
        "full_name": volunteer.full_name,
        "total_weight_kg": total,
        "activation_count": int(activation_count),
        "contribution_count": len(contributions),
        "material_totals": material_totals,
        "contributions": public_rows,
    }


def volunteer_impact(db: Session, volunteer_id: UUID, user: User, *, event_id: UUID) -> dict:
    _require_event_access(db, user, event_id)
    volunteer = db.get(Volunteer, volunteer_id)
    if volunteer is None or not db.scalar(select(VolunteerActivation.id).join(
        RecyclingActivation, RecyclingActivation.id == VolunteerActivation.activation_id
    ).where(VolunteerActivation.volunteer_id == volunteer_id, RecyclingActivation.event_id == event_id)):
        raise HTTPException(status_code=404, detail="No encontramos al voluntario en este evento")
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el historial personal")
    data = _impact_data(db, volunteer, event_id=event_id)
    data.update({
        "email": volunteer.email,
        "phone": volunteer.phone,
        "unique_code": volunteer.unique_code,
        "first_contribution_at": db.scalar(select(func.min(MaterialContribution.registered_at)).where(
            MaterialContribution.volunteer_id == volunteer.id, MaterialContribution.status == "ACTIVE"
        )),
        "last_contribution_at": db.scalar(select(func.max(MaterialContribution.registered_at)).where(
            MaterialContribution.volunteer_id == volunteer.id, MaterialContribution.status == "ACTIVE"
        )),
    })
    return data


def public_impact(db: Session, raw_token: str) -> dict:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(select(VolunteerAccessToken).where(
        VolunteerAccessToken.token_hash == token_hash,
        VolunteerAccessToken.revoked_at.is_(None),
        VolunteerAccessToken.expires_at > datetime.now(timezone.utc),
    ))
    if token is None:
        raise HTTPException(status_code=404, detail="El enlace de historial expiró o ya no está disponible")
    volunteer = db.get(Volunteer, token.volunteer_id)
    if volunteer is None or volunteer.status == "ARCHIVED":
        raise HTTPException(status_code=404, detail="El historial ya no está disponible")
    return _impact_data(db, volunteer)


def public_contribution_evidence(db: Session, raw_token: str, evidence_id: UUID) -> Evidence:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(select(VolunteerAccessToken).where(
        VolunteerAccessToken.token_hash == token_hash,
        VolunteerAccessToken.revoked_at.is_(None),
        VolunteerAccessToken.expires_at > datetime.now(timezone.utc),
    ))
    if token is None:
        raise HTTPException(status_code=404, detail="El enlace de historial expiró o ya no está disponible")
    evidence = db.scalar(select(Evidence).join(
        MaterialContribution, Evidence.volunteer_contribution_id == MaterialContribution.id
    ).where(Evidence.id == evidence_id, MaterialContribution.volunteer_id == token.volunteer_id,
            MaterialContribution.status == "ACTIVE"))
    if evidence is None:
        raise HTTPException(status_code=404, detail="No encontramos esta evidencia en tu historial")
    return evidence


def dashboard(
    db: Session,
    user: User,
    *,
    event_id: UUID,
    activation_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict:
    _require_event_access(db, user, event_id)
    if not (_can_manage(user, event_id, db) or _can_record(user, event_id, db)):
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar las métricas")
    activation_filter = [RecyclingActivation.event_id == event_id]
    if activation_id:
        activation_filter.append(RecyclingActivation.id == activation_id)
    contribution_filter = [MaterialContribution.status == "ACTIVE", *activation_filter]
    if date_from:
        contribution_filter.append(MaterialContribution.registered_at >= date_from)
    if date_to:
        contribution_filter.append(MaterialContribution.registered_at < date_to)
    total_weight = db.scalar(select(func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0)).join(
        RecyclingActivation
    ).where(*contribution_filter)) or Decimal("0")
    contribution_count = db.scalar(select(func.count(MaterialContribution.id)).join(
        RecyclingActivation
    ).where(*contribution_filter)) or 0
    active_activations = db.scalar(select(func.count(RecyclingActivation.id)).where(
        *activation_filter, RecyclingActivation.status == "ACTIVE"
    )) or 0
    unique_volunteers = db.scalar(select(func.count(func.distinct(MaterialContribution.volunteer_id))).join(
        RecyclingActivation
    ).where(*contribution_filter)) or 0
    participations = db.scalar(select(func.count(VolunteerActivation.id)).join(
        RecyclingActivation
    ).where(*activation_filter, VolunteerActivation.status != "CANCELLED")) or 0
    by_date_rows = db.execute(select(
        func.date(MaterialContribution.registered_at).label("date"),
        func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0).label("kg"),
        func.count(MaterialContribution.id).label("contributions"),
    ).join(RecyclingActivation).where(*contribution_filter).group_by(func.date(MaterialContribution.registered_at)).order_by(func.date(MaterialContribution.registered_at))).all()
    by_activation_rows = db.execute(select(
        RecyclingActivation.id, RecyclingActivation.name,
        func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0).label("kg"),
        func.count(MaterialContribution.id).label("contributions"),
    ).join(MaterialContribution, MaterialContribution.activation_id == RecyclingActivation.id).where(
        *contribution_filter
    ).group_by(RecyclingActivation.id, RecyclingActivation.name).order_by(func.sum(MaterialContribution.total_weight_kg).desc())).all()
    by_material_rows = db.execute(select(
        MaterialContributionItem.material_name_snapshot,
        func.coalesce(func.sum(MaterialContributionItem.weight_kg), 0).label("kg"),
    ).join(MaterialContribution).join(RecyclingActivation).where(*contribution_filter).group_by(
        MaterialContributionItem.material_name_snapshot
    ).order_by(func.sum(MaterialContributionItem.weight_kg).desc())).all()
    new_volunteers_rows = db.execute(select(
        func.date(VolunteerActivation.registered_at).label("date"),
        func.count(func.distinct(VolunteerActivation.volunteer_id)).label("volunteers"),
    ).join(RecyclingActivation).where(*activation_filter, VolunteerActivation.status != "CANCELLED").group_by(
        func.date(VolunteerActivation.registered_at)
    ).order_by(func.date(VolunteerActivation.registered_at))).all()
    return {
        "unique_volunteers": int(unique_volunteers),
        "participations": int(participations),
        "contributions": int(contribution_count),
        "total_weight_kg": total_weight,
        "active_activations": int(active_activations),
        "average_per_volunteer_kg": (total_weight / unique_volunteers).quantize(Decimal("0.001")) if unique_volunteers else Decimal("0"),
        "by_date": [{"date": str(row.date), "kg": row.kg, "contributions": int(row.contributions)} for row in by_date_rows],
        "by_activation": [{"id": str(row.id), "name": row.name, "kg": row.kg, "contributions": int(row.contributions)} for row in by_activation_rows],
        "by_material": [{"material": row.material_name_snapshot, "kg": row.kg} for row in by_material_rows],
        "new_volunteers_by_date": [{"date": str(row.date), "volunteers": int(row.volunteers)} for row in new_volunteers_rows],
    }


def event_impact(db: Session, user: User, event_id: UUID, *, date_from: datetime | None, date_to: datetime | None) -> dict:
    return dashboard(db, user, event_id=event_id, activation_id=None, date_from=date_from, date_to=date_to)


def contribution_email_context(db: Session, contribution: MaterialContribution, impact_url: str) -> dict:
    contribution = get_contribution_admin(db, contribution.id)
    return {
        "recipient": contribution.volunteer.email,
        "volunteer_name": contribution.volunteer.full_name,
        "activation_name": contribution.activation.name,
        "event_name": contribution.activation.event.name,
        "registered_at": contribution.registered_at,
        "items": [{"material": item.material_name_snapshot, "weight_kg": item.weight_kg} for item in contribution.items],
        "total_weight_kg": contribution.total_weight_kg,
        "accumulated_weight_kg": _impact_data(db, contribution.volunteer)["total_weight_kg"],
        "impact_url": impact_url,
    }


def get_contribution_admin(db: Session, contribution_id: UUID) -> MaterialContribution:
    return db.scalar(select(MaterialContribution).options(
        selectinload(MaterialContribution.items),
        selectinload(MaterialContribution.volunteer),
        selectinload(MaterialContribution.activation).selectinload(RecyclingActivation.event),
    ).where(MaterialContribution.id == contribution_id))


def mark_contribution_email(db: Session, contribution_id: UUID, *, sent: bool, error: str | None = None) -> None:
    contribution = db.get(MaterialContribution, contribution_id)
    if not contribution:
        return
    contribution.email_status = "SENT" if sent else "FAILED"
    contribution.email_sent_at = datetime.now(timezone.utc) if sent else None
    contribution.email_error = (error or "No se pudo entregar el correo")[:240] if not sent else None
    db.commit()
