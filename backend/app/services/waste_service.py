from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event, can_operate_event
from app.models.core import (
    Event,
    EventZone,
    Evidence,
    User,
    WasteCollectionPoint,
    WasteCollectionRecord,
    WasteRecord,
    WasteType,
)
from app.models.enums import EventStatus, UserRole, WasteDestination
from app.schemas.waste_schema import WasteRecordCreate, WasteRecordUpdate, WasteTypeCreate, WasteTypeUpdate

RECOVERED_DESTINATIONS = {
    WasteDestination.RECYCLING,
    WasteDestination.COMPOSTING,
    WasteDestination.RECOVERY,
}


def get_waste_type_or_404(db: Session, waste_type_id: UUID) -> WasteType:
    waste_type = db.get(WasteType, waste_type_id)
    if not waste_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste type not found")
    return waste_type


def get_waste_record_or_404(db: Session, record_id: UUID) -> WasteRecord:
    record = db.get(WasteRecord, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste record not found")
    return record


def _get_event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _ensure_unique_waste_type_name(
    db: Session, name: str, exclude_id: UUID | None = None
) -> None:
    filters = [func.lower(WasteType.name) == name.lower()]
    if exclude_id:
        filters.append(WasteType.id != exclude_id)
    exists = db.scalar(select(WasteType.id).where(*filters).limit(1))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Waste type name already exists",
        )


def _validate_zone(db: Session, event_id: UUID, zone_id: UUID | None) -> None:
    if zone_id is None:
        return
    zone = db.get(EventZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    if zone.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone does not belong to this event",
        )


def _validate_evidence(db: Session, event_id: UUID, evidence_id: UUID | None) -> None:
    if evidence_id is None:
        return
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    if evidence.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence does not belong to this event",
        )


def create_waste_type(db: Session, payload: WasteTypeCreate) -> WasteType:
    _ensure_unique_waste_type_name(db, payload.name)
    waste_type = WasteType(**payload.model_dump())
    db.add(waste_type)
    db.commit()
    db.refresh(waste_type)
    return waste_type


def list_waste_types(
    db: Session, *, q: str | None, page: int, limit: int
) -> tuple[list[WasteType], int]:
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(WasteType.name.ilike(pattern))
    total = db.scalar(select(func.count()).select_from(WasteType).where(*filters)) or 0
    items = list(
        db.scalars(
            select(WasteType)
            .where(*filters)
            .order_by(WasteType.name)
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def update_waste_type(db: Session, waste_type_id: UUID, payload: WasteTypeUpdate) -> WasteType:
    waste_type = get_waste_type_or_404(db, waste_type_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        _ensure_unique_waste_type_name(db, data["name"], exclude_id=waste_type_id)
    for field, value in data.items():
        setattr(waste_type, field, value)
    db.add(waste_type)
    db.commit()
    db.refresh(waste_type)
    return waste_type


def delete_waste_type(db: Session, waste_type_id: UUID) -> None:
    waste_type = get_waste_type_or_404(db, waste_type_id)
    used = db.scalar(
        select(WasteRecord.id).where(WasteRecord.waste_type_id == waste_type_id).limit(1)
    )
    if used:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete waste type used by waste records",
        )
    db.delete(waste_type)
    db.commit()


def create_waste_record(
    db: Session, event_id: UUID, payload: WasteRecordCreate, current_user: User
) -> WasteRecord:
    _get_event_or_404(db, event_id)
    if not can_operate_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if current_user.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    get_waste_type_or_404(db, payload.waste_type_id)
    _validate_zone(db, event_id, payload.zone_id)
    _validate_evidence(db, event_id, payload.evidence_id)

    data = payload.model_dump(exclude_unset=True)
    if data.get("recorded_at") is None:
        data.pop("recorded_at", None)
    record = WasteRecord(event_id=event_id, recorded_by=current_user.id, **data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_event_waste_records(
    db: Session,
    *,
    event_id: UUID,
    current_user: User,
    page: int,
    limit: int,
) -> tuple[list[WasteRecord], int]:
    _get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = [WasteRecord.event_id == event_id]
    total = db.scalar(select(func.count()).select_from(WasteRecord).where(*filters)) or 0
    items = list(
        db.scalars(
            select(WasteRecord)
            .options(selectinload(WasteRecord.recorder))
            .where(*filters)
            .order_by(WasteRecord.recorded_at.desc(), WasteRecord.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_waste_record(db: Session, record_id: UUID, current_user: User) -> WasteRecord:
    record = db.scalar(
        select(WasteRecord)
        .options(selectinload(WasteRecord.recorder))
        .where(WasteRecord.id == record_id)
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste record not found")
    if not can_access_event(current_user, record.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return record


def update_waste_record(
    db: Session, record_id: UUID, payload: WasteRecordUpdate, current_user: User
) -> WasteRecord:
    record = get_waste_record_or_404(db, record_id)
    if not can_manage_event(current_user, record.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    data = payload.model_dump(exclude_unset=True)
    if "waste_type_id" in data:
        get_waste_type_or_404(db, data["waste_type_id"])
    if "zone_id" in data:
        _validate_zone(db, record.event_id, data["zone_id"])
    if "evidence_id" in data:
        _validate_evidence(db, record.event_id, data["evidence_id"])
    for field, value in data.items():
        setattr(record, field, value)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_waste_record(db: Session, record_id: UUID, current_user: User) -> None:
    record = get_waste_record_or_404(db, record_id)
    event = _get_event_or_404(db, record.event_id)
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if event.status in {EventStatus.FINISHED, EventStatus.REPORT_DELIVERED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete waste records from finished or delivered events",
        )
    db.delete(record)
    db.commit()


def get_waste_summary(db: Session, event_id: UUID, current_user: User) -> dict:
    _get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    # Keep the two sources aggregated separately. Joining raw records together
    # would multiply rows when an event has multiple records in both tables.
    records = list(db.scalars(select(WasteRecord).where(WasteRecord.event_id == event_id)).all())
    direct_kg = sum((record.weight_kg for record in records), Decimal("0"))
    total_collection_kg, collection_count = db.execute(
        select(
            func.coalesce(func.sum(WasteCollectionRecord.weight_kg), Decimal("0")),
            func.count(WasteCollectionRecord.id),
        ).where(WasteCollectionRecord.event_id == event_id)
    ).one()
    direct_count = len(records)
    total_kg = direct_kg + total_collection_kg

    def percentage(weight: Decimal) -> Decimal:
        return (weight / total_kg * Decimal("100")).quantize(Decimal("0.01")) if total_kg else Decimal("0")

    by_type: dict[UUID | None, dict] = {}
    for item in _group_by_type(db, records):
        by_type[item["id"]] = {
            "id": item["id"],
            "waste_type_id": item["id"],
            "name": item["name"],
            "total_kg": item["total_kg"],
            "collection_points_kg": Decimal("0"),
            "direct_kg": item["total_kg"],
            "percentage": Decimal("0"),
        }
    collection_by_type = db.execute(
        select(WasteType.id, WasteType.name, func.sum(WasteCollectionRecord.weight_kg))
        .join(WasteCollectionRecord, WasteCollectionRecord.waste_type_id == WasteType.id)
        .where(WasteCollectionRecord.event_id == event_id)
        .group_by(WasteType.id, WasteType.name)
    ).all()
    for waste_type_id, name, weight in collection_by_type:
        item = by_type.setdefault(waste_type_id, {
            "id": waste_type_id,
            "waste_type_id": waste_type_id,
            "name": name,
            "total_kg": Decimal("0"),
            "collection_points_kg": Decimal("0"),
            "direct_kg": Decimal("0"),
            "percentage": Decimal("0"),
        })
        item["total_kg"] += weight
        item["collection_points_kg"] += weight
    for item in by_type.values():
        item["percentage"] = percentage(item["total_kg"])
    by_type_sorted = sorted(by_type.values(), key=lambda item: item["total_kg"], reverse=True)
    waste_types_count = len({waste_type_id for waste_type_id in by_type if waste_type_id is not None})

    by_collection_point = [
        {
            "collection_point_id": collection_point_id,
            "code": code,
            "name": name,
            "weight_kg": weight,
        }
        for collection_point_id, code, name, weight in db.execute(
            select(
                WasteCollectionPoint.id,
                WasteCollectionPoint.code,
                WasteCollectionPoint.name,
                func.sum(WasteCollectionRecord.weight_kg),
            )
            .join(WasteCollectionRecord, WasteCollectionRecord.collection_point_id == WasteCollectionPoint.id)
            .where(WasteCollectionRecord.event_id == event_id)
            .group_by(WasteCollectionPoint.id, WasteCollectionPoint.code, WasteCollectionPoint.name)
            .order_by(func.sum(WasteCollectionRecord.weight_kg).desc())
        ).all()
    ]
    top_waste_type = by_type_sorted[0] if by_type_sorted else None
    top_collection_point = by_collection_point[0] if by_collection_point else None

    recovered_kg = sum(
        (record.weight_kg for record in records if record.destination in RECOVERED_DESTINATIONS),
        Decimal("0"),
    )
    landfill_kg = sum(
        (record.weight_kg for record in records if record.destination == WasteDestination.LANDFILL),
        Decimal("0"),
    )
    special_disposal_kg = sum(
        (
            record.weight_kg
            for record in records
            if record.destination == WasteDestination.SPECIAL_DISPOSAL
        ),
        Decimal("0"),
    )
    recovery_percentage = percentage(recovered_kg)
    by_destination = _group_by_destination(records)
    if collection_count:
        by_destination.append({"id": None, "name": "Acopios Greenway (origen de registro)", "total_kg": total_collection_kg})
    by_destination.sort(key=lambda item: item["total_kg"], reverse=True)
    by_zone = {item["id"]: item for item in _group_by_zone(db, records)}
    collection_by_zone = db.execute(
        select(WasteCollectionPoint.zone_id, EventZone.name, func.sum(WasteCollectionRecord.weight_kg))
        .select_from(WasteCollectionRecord)
        .join(WasteCollectionPoint, WasteCollectionPoint.id == WasteCollectionRecord.collection_point_id)
        .outerjoin(EventZone, EventZone.id == WasteCollectionPoint.zone_id)
        .where(WasteCollectionRecord.event_id == event_id)
        .group_by(WasteCollectionPoint.zone_id, EventZone.name)
    ).all()
    for zone_id, zone_name, weight in collection_by_zone:
        if zone_id in by_zone:
            by_zone[zone_id]["total_kg"] += weight
        else:
            by_zone[zone_id] = {"id": zone_id, "name": zone_name or "Sin zona", "total_kg": weight}
    by_zone_sorted = list(by_zone.values())
    by_zone_sorted.sort(key=lambda item: (item["name"] == "Sin zona", -item["total_kg"]))

    return {
        "event_id": event_id,
        "total_kg": total_kg,
        "records_count": direct_count + collection_count,
        "total_event_kg": total_kg,
        "collection_points": {
            "weight_kg": total_collection_kg,
            "percentage": percentage(total_collection_kg),
            "records_count": collection_count,
        },
        "direct_records": {
            "weight_kg": direct_kg,
            "percentage": percentage(direct_kg),
            "records_count": direct_count,
        },
        "total_records": direct_count + collection_count,
        "waste_types_count": waste_types_count,
        "top_waste_type": top_waste_type,
        "top_collection_point": top_collection_point,
        "by_source": [
            {"source": "COLLECTION_POINT", "weight_kg": total_collection_kg, "percentage": percentage(total_collection_kg)},
            {"source": "DIRECT", "weight_kg": direct_kg, "percentage": percentage(direct_kg)},
        ],
        "by_collection_point": by_collection_point,
        "recovered_kg": recovered_kg,
        "landfill_kg": landfill_kg,
        "special_disposal_kg": special_disposal_kg,
        "recovery_percentage": recovery_percentage,
        "by_type": by_type_sorted,
        "by_destination": by_destination,
        "by_zone": by_zone_sorted,
    }


def _group_by_type(db: Session, records: list[WasteRecord]) -> list[dict]:
    waste_type_ids = {record.waste_type_id for record in records if record.waste_type_id}
    waste_types = {
        item.id: item.name
        for item in db.scalars(select(WasteType).where(WasteType.id.in_(waste_type_ids))).all()
    } if waste_type_ids else {}
    totals: dict[UUID | None, Decimal] = {}
    for record in records:
        totals[record.waste_type_id] = totals.get(record.waste_type_id, Decimal("0")) + record.weight_kg
    return [
        {"id": waste_type_id, "name": waste_types.get(waste_type_id, "Sin tipo"), "total_kg": total}
        for waste_type_id, total in totals.items()
    ]


def _group_by_destination(records: list[WasteRecord]) -> list[dict]:
    totals: dict[WasteDestination, Decimal] = {}
    for record in records:
        totals[record.destination] = totals.get(record.destination, Decimal("0")) + record.weight_kg
    return [
        {"id": None, "name": destination.value, "total_kg": total}
        for destination, total in totals.items()
    ]


def _group_by_zone(db: Session, records: list[WasteRecord]) -> list[dict]:
    zone_ids = {record.zone_id for record in records if record.zone_id}
    zones = {
        item.id: item.name
        for item in db.scalars(select(EventZone).where(EventZone.id.in_(zone_ids))).all()
    } if zone_ids else {}
    totals: dict[UUID | None, Decimal] = {}
    for record in records:
        totals[record.zone_id] = totals.get(record.zone_id, Decimal("0")) + record.weight_kg
    return [
        {"id": zone_id, "name": zones.get(zone_id, "Sin zona"), "total_kg": total}
        for zone_id, total in totals.items()
    ]
