import base64
import secrets
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event
from app.db.session import set_public_waste_context
from app.models.core import Event, EventWastePublicForm, EventZone, User, WasteCollectionPoint, WasteCollectionRecord, WasteType
from app.models.enums import EventStatus, UserRole
from app.models.environmental import WasteCollectionEquivalenceFactor
from app.schemas.collection_point_schema import CollectionPointCreate, CollectionPointUpdate, PublicWasteRecordCreate
from app.utils.simple_qr import make_qr_png


def _point_or_404(db: Session, point_id: UUID) -> WasteCollectionPoint:
    point = db.get(WasteCollectionPoint, point_id)
    if point is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Acopio no encontrado")
    return point


def _validate_zone(db: Session, event_id: UUID, zone_id: UUID | None) -> None:
    if zone_id is None:
        return
    zone = db.get(EventZone, zone_id)
    if zone is None or zone.event_id != event_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La zona debe pertenecer al mismo evento")


def _check_permission(user: User, event_id: UUID, db: Session, *, manage: bool = False) -> None:
    allowed = can_manage_event(user, event_id, db) if manage else can_access_event(user, event_id, db)
    if not allowed or user.role == UserRole.CLIENT and manage:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso insuficiente")


def _read_point(point: WasteCollectionPoint, record_count: int, total_kg: Decimal, base_url: str | None):
    from app.schemas.collection_point_schema import CollectionPointRead

    return CollectionPointRead.model_validate(point).model_copy(update={
        "record_count": record_count, "total_kg": total_kg,
        "public_url": None, "qr_data_url": None,
    })


def list_points(db: Session, event_id: UUID, user: User, base_url: str | None, include_inactive: bool = True):
    _check_permission(user, event_id, db, manage=True)
    stmt = select(WasteCollectionPoint).where(WasteCollectionPoint.event_id == event_id)
    if not include_inactive:
        stmt = stmt.where(WasteCollectionPoint.is_active.is_(True))
    points = db.scalars(stmt.order_by(WasteCollectionPoint.code)).all()
    totals = db.execute(
        select(
            WasteCollectionRecord.collection_point_id,
            func.count(WasteCollectionRecord.id),
            func.coalesce(func.sum(WasteCollectionRecord.weight_kg), 0),
        )
        .where(WasteCollectionRecord.event_id == event_id)
        .group_by(WasteCollectionRecord.collection_point_id)
    ).all()
    by_point = {point_id: (count, total) for point_id, count, total in totals}
    return [_read_point(point, *by_point.get(point.id, (0, Decimal("0"))), base_url) for point in points]


def create_point(db: Session, event_id: UUID, payload: CollectionPointCreate, user: User, base_url: str | None):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento no encontrado")
    _check_permission(user, event_id, db, manage=True)
    _validate_zone(db, event_id, payload.zone_id)
    data = payload.model_dump()
    data["code"] = data["code"].strip()
    data["name"] = data["name"].strip()
    if not data["code"] or not data["name"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Código y nombre son obligatorios")
    allowed_ids = data.pop("allowed_waste_type_ids", [])
    point = WasteCollectionPoint(event_id=event_id, qr_token=secrets.token_urlsafe(32), **data)
    point.allowed_waste_types = _waste_types_by_ids(db, allowed_ids)
    db.add(point)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código ya existe en este evento") from exc
    db.refresh(point)
    return _read_point(point, 0, Decimal("0"), base_url)


def update_point(db: Session, point_id: UUID, payload: CollectionPointUpdate, user: User, base_url: str | None):
    point = _point_or_404(db, point_id)
    _check_permission(user, point.event_id, db, manage=True)
    data = payload.model_dump(exclude_unset=True)
    allowed_ids = data.pop("allowed_waste_type_ids", None)
    for field in ("code", "name"):
        if field in data and data[field] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{field} no puede ser nulo")
        if field in data:
            data[field] = data[field].strip()
            if not data[field]:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{field} es obligatorio")
    if "zone_id" in data:
        _validate_zone(db, point.event_id, data["zone_id"])
    if allowed_ids is not None:
        point.allowed_waste_types = _waste_types_by_ids(db, allowed_ids)
    for field, value in data.items():
        setattr(point, field, value)
    point.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código ya existe en este evento") from exc
    db.refresh(point)
    count, total = db.execute(select(func.count(WasteCollectionRecord.id), func.coalesce(func.sum(WasteCollectionRecord.weight_kg), 0)).where(WasteCollectionRecord.collection_point_id == point.id)).one()
    return _read_point(point, count, total, base_url)


def _waste_types_by_ids(db: Session, ids: list[UUID]) -> list[WasteType]:
    types = db.scalars(select(WasteType).where(WasteType.id.in_(set(ids)))).all() if ids else []
    if len(types) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Uno o más materiales no existen")
    return types


def _form_by_token(db: Session, token: str, *, active: bool = True) -> EventWastePublicForm | None:
    query = select(EventWastePublicForm).where(EventWastePublicForm.token == token)
    if active:
        query = query.where(EventWastePublicForm.status == "ACTIVE")
    return db.scalar(query)


def _ensure_form(db: Session, event_id: UUID) -> EventWastePublicForm:
    form = db.scalar(select(EventWastePublicForm).where(EventWastePublicForm.event_id == event_id))
    if form is None:
        form = EventWastePublicForm(event_id=event_id, token=secrets.token_urlsafe(32), status="DRAFT")
        db.add(form)
        db.commit()
        db.refresh(form)
    return form


def read_event_form(db: Session, event_id: UUID, user: User, base_url: str | None):
    _check_permission(user, event_id, db)
    if db.get(Event, event_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento no encontrado")
    form = _ensure_form(db, event_id)
    public_url = f"{base_url.rstrip('/')}/acopios/{form.token}" if base_url else None
    return {"event_id": event_id, "token": form.token, "status": form.status,
            "opened_at": form.opened_at, "closed_at": form.closed_at,
            "public_url": public_url,
            "qr_data_url": "data:image/png;base64," + base64.b64encode(make_qr_png(public_url)).decode("ascii") if public_url else None}


def set_event_form_status(db: Session, event_id: UUID, user: User, status_value: str, base_url: str | None):
    _check_permission(user, event_id, db, manage=True)
    form = _ensure_form(db, event_id)
    now = datetime.now(timezone.utc)
    if status_value == "ACTIVE":
        form.status = "ACTIVE"
        form.opened_at = now
        form.closed_at = None
    elif status_value == "CLOSED":
        form.status = "CLOSED"
        form.closed_at = now
    elif status_value == "REGENERATE":
        form.token = secrets.token_urlsafe(32)
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Acción no válida")
    form.updated_at = now.replace(tzinfo=None)
    db.commit()
    return read_event_form(db, event_id, user, base_url)


def public_point(db: Session, token: str):
    set_public_waste_context(db, token)
    form = _form_by_token(db, token, active=False)
    if form is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Formulario no disponible")
    if form.status != "ACTIVE":
        raise HTTPException(status.HTTP_410_GONE, "El registro de residuos de este evento está cerrado.")
    event = db.get(Event, form.event_id)
    if event is None or event.status in {EventStatus.QUOTE, EventStatus.CANCELLED, EventStatus.REPORT_DELIVERED}:
        raise HTTPException(status.HTTP_410_GONE, "Evento no disponible")
    points = db.scalars(select(WasteCollectionPoint).where(WasteCollectionPoint.event_id == event.id, WasteCollectionPoint.is_active.is_(True)).order_by(WasteCollectionPoint.code)).all()
    return {"event_id": event.id, "event_name": event.name, "form_status": form.status,
            "collection_points": [{"id": point.id, "code": point.code, "name": point.name,
                "allowed_waste_types": [{"id": item.id, "name": item.name, "is_recyclable": item.is_recyclable} for item in sorted(point.allowed_waste_types, key=lambda item: item.name)]}
                for point in points]}


def submit_public_records(db: Session, token: str, records: list[PublicWasteRecordCreate]):
    set_public_waste_context(db, token)
    form = _form_by_token(db, token, active=False)
    if form is None:
        raise HTTPException(status.HTTP_410_GONE, "Formulario no disponible o cerrado")
    if form.status == "DRAFT":
        raise HTTPException(status.HTTP_410_GONE, "Formulario no disponible o cerrado")
    event = db.get(Event, form.event_id)
    if event is None or event.status in {EventStatus.QUOTE, EventStatus.CANCELLED, EventStatus.REPORT_DELIVERED}:
        raise HTTPException(status.HTTP_410_GONE, "Evento no disponible")
    accepted, rejected = [], []
    for item in records:
        recorded_at = item.recorded_at.replace(tzinfo=timezone.utc) if item.recorded_at.tzinfo is None else item.recorded_at.astimezone(timezone.utc)
        existing = db.scalar(select(WasteCollectionRecord).where(WasteCollectionRecord.client_generated_id == item.client_generated_id))
        if existing:
            if existing.event_id == event.id and existing.collection_point_id == item.collection_point_id:
                accepted.append(existing)
            else:
                rejected.append({"client_generated_id": str(item.client_generated_id), "reason": "El identificador ya pertenece a otro acopio"})
            continue
        point = db.get(WasteCollectionPoint, item.collection_point_id)
        if point is None or point.event_id != event.id or not point.is_active:
            rejected.append({"client_generated_id": str(item.client_generated_id), "reason": "COLLECTION_POINT_INACTIVE"})
            continue
        if not any(waste_type.id == item.waste_type_id for waste_type in point.allowed_waste_types):
            rejected.append({"client_generated_id": str(item.client_generated_id), "reason": "WASTE_TYPE_NOT_ALLOWED"})
            continue
        closed_at = form.closed_at.replace(tzinfo=timezone.utc) if form.closed_at and form.closed_at.tzinfo is None else form.closed_at
        if form.status == "CLOSED" and closed_at and recorded_at > closed_at:
            rejected.append({"client_generated_id": str(item.client_generated_id), "reason": "FORM_CLOSED_AFTER_RECORD"})
            continue
        if db.get(WasteType, item.waste_type_id) is None:
            rejected.append({"client_generated_id": str(item.client_generated_id), "reason": "Tipo de residuo no válido"})
            continue
        record = WasteCollectionRecord(
            event_id=point.event_id, collection_point_id=point.id, waste_type_id=item.waste_type_id,
            weight_kg=item.weight_kg, submitter_name=item.submitter_name,
            submitter_rut=item.submitter_rut, client_generated_id=item.client_generated_id,
            device_id=item.device_id,
            recorded_at=recorded_at,
            synced_at=datetime.now(timezone.utc),
        )
        try:
            with db.begin_nested():
                db.add(record)
                db.flush()
            accepted.append(record)
        except IntegrityError:
            duplicate = db.scalar(select(WasteCollectionRecord).where(WasteCollectionRecord.client_generated_id == item.client_generated_id))
            if duplicate and duplicate.collection_point_id == point.id:
                accepted.append(duplicate)
            else:
                rejected.append({"client_generated_id": str(item.client_generated_id), "reason": "No se pudo guardar el registro"})
    db.commit()
    set_public_waste_context(db, token)
    for record in accepted:
        db.refresh(record)
    return accepted, rejected


def _mask_rut(value: str) -> str:
    normalized = value.replace(".", "").replace("-", "").replace(" ", "")
    return f"***{normalized[-4:-1]}-{normalized[-1]}" if len(normalized) >= 2 else "***"


def list_collection_records(
    db: Session, event_id: UUID, user: User, *, collection_point_id: UUID | None = None,
    waste_type_id: UUID | None = None, date_from: datetime | None = None,
    date_to: datetime | None = None, search: str | None = None, page: int = 1, limit: int = 50,
):
    _check_permission(user, event_id, db)
    filters = [WasteCollectionRecord.event_id == event_id]
    if collection_point_id:
        filters.append(WasteCollectionRecord.collection_point_id == collection_point_id)
    if waste_type_id:
        filters.append(WasteCollectionRecord.waste_type_id == waste_type_id)
    if date_from:
        filters.append(WasteCollectionRecord.recorded_at >= date_from)
    if date_to:
        filters.append(WasteCollectionRecord.recorded_at <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(WasteCollectionRecord.submitter_name.ilike(pattern))
    base = select(WasteCollectionRecord).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        select(WasteCollectionRecord, WasteCollectionPoint, WasteType)
        .join(WasteCollectionPoint, WasteCollectionRecord.collection_point_id == WasteCollectionPoint.id)
        .join(WasteType, WasteCollectionRecord.waste_type_id == WasteType.id)
        .where(*filters)
        .order_by(WasteCollectionRecord.recorded_at.desc(), WasteCollectionRecord.created_at.desc())
        .offset((page - 1) * limit).limit(limit)
    ).all()
    items = [{
        "id": record.id, "event_id": record.event_id, "collection_point_id": point.id,
        "collection_point_code": point.code, "collection_point_name": point.name,
        "waste_type_id": material.id, "waste_type_name": material.name,
        "weight_kg": record.weight_kg, "submitter_name": record.submitter_name,
        "submitter_rut_masked": _mask_rut(record.submitter_rut),
        "client_generated_id": record.client_generated_id, "device_id": record.device_id,
        "recorded_at": record.recorded_at, "synced_at": record.synced_at,
    } for record, point, material in rows]
    return {"items": items, "total": total, "page": page, "limit": limit}


def get_collection_record(db: Session, record_id: UUID, user: User):
    row = db.execute(
        select(WasteCollectionRecord, WasteCollectionPoint, WasteType)
        .join(WasteCollectionPoint, WasteCollectionRecord.collection_point_id == WasteCollectionPoint.id)
        .join(WasteType, WasteCollectionRecord.waste_type_id == WasteType.id)
        .where(WasteCollectionRecord.id == record_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de acopio no encontrado")
    record, point, material = row
    _check_permission(user, record.event_id, db)
    return {
        "id": record.id, "event_id": record.event_id, "collection_point_id": point.id,
        "collection_point_code": point.code, "collection_point_name": point.name,
        "waste_type_id": material.id, "waste_type_name": material.name,
        "weight_kg": record.weight_kg, "submitter_name": record.submitter_name,
        "submitter_rut_masked": _mask_rut(record.submitter_rut),
        "client_generated_id": record.client_generated_id, "device_id": record.device_id,
        "recorded_at": record.recorded_at, "synced_at": record.synced_at,
    }


def collection_summary(db: Session, event_id: UUID, user: User):
    _check_permission(user, event_id, db)
    total_kg, records_count, unique_submitters = db.execute(select(
        func.coalesce(func.sum(WasteCollectionRecord.weight_kg), 0),
        func.count(WasteCollectionRecord.id),
        func.count(func.distinct(WasteCollectionRecord.submitter_rut)),
    ).where(WasteCollectionRecord.event_id == event_id)).one()
    recyclable_kg = db.scalar(select(
        func.coalesce(func.sum(WasteCollectionRecord.weight_kg), 0)
    ).join(WasteType, WasteType.id == WasteCollectionRecord.waste_type_id)
        .where(WasteCollectionRecord.event_id == event_id, WasteType.is_recyclable.is_(True))) or Decimal("0")
    active_points = db.scalar(select(func.count(WasteCollectionPoint.id)).where(
        WasteCollectionPoint.event_id == event_id, WasteCollectionPoint.is_active.is_(True)
    )) or 0
    by_type = db.execute(select(
        WasteType.id, WasteType.name, WasteType.is_recyclable, func.coalesce(func.sum(WasteCollectionRecord.weight_kg), 0),
        func.count(WasteCollectionRecord.id),
    ).join(WasteCollectionRecord, WasteCollectionRecord.waste_type_id == WasteType.id)
        .where(WasteCollectionRecord.event_id == event_id).group_by(WasteType.id, WasteType.name, WasteType.is_recyclable)
        .order_by(func.sum(WasteCollectionRecord.weight_kg).desc())).all()
    by_point = db.execute(select(
        WasteCollectionPoint.id, WasteCollectionPoint.code, WasteCollectionPoint.name,
        func.coalesce(func.sum(WasteCollectionRecord.weight_kg), 0), func.count(WasteCollectionRecord.id),
    ).outerjoin(WasteCollectionRecord, WasteCollectionRecord.collection_point_id == WasteCollectionPoint.id)
        .where(WasteCollectionPoint.event_id == event_id)
        .group_by(WasteCollectionPoint.id, WasteCollectionPoint.code, WasteCollectionPoint.name)
        .order_by(WasteCollectionPoint.code)).all()
    weights_by_type = {row[0]: row[3] for row in by_type}
    eco_equivalences = []
    if total_kg > 0:
        factors = db.scalars(
            select(WasteCollectionEquivalenceFactor).where(
                WasteCollectionEquivalenceFactor.is_active.is_(True)
            ).order_by(WasteCollectionEquivalenceFactor.kind, WasteCollectionEquivalenceFactor.name)
        ).all()
        for factor in factors:
            source_kg = (
                total_kg if factor.kind == "FAMILY_DAYS"
                else weights_by_type.get(factor.waste_type_id, Decimal("0"))
            )
            if source_kg <= 0:
                continue
            value = (Decimal(source_kg) / factor.reference_kg).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
            eco_equivalences.append({
                "kind": factor.kind,
                "waste_type_name": factor.waste_type.name if factor.waste_type else None,
                "name": factor.name,
                "value": value,
                "unit": factor.display_unit,
                "reference_kg": factor.reference_kg,
            })
    return {
        "event_id": event_id, "total_kg": total_kg, "recyclable_kg": recyclable_kg,
        "records_count": records_count,
        "active_points": active_points, "unique_submitters": unique_submitters,
        "by_type": [{"id": row[0], "name": row[1], "is_recyclable": bool(row[2]), "total_kg": row[3], "records_count": row[4]} for row in by_type],
        "by_point": [{"id": row[0], "code": row[1], "name": row[2], "total_kg": row[3], "records_count": row[4]} for row in by_point],
        "eco_equivalences": eco_equivalences,
    }
