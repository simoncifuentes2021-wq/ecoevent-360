from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import (
    CarbonFactor,
    CarbonRecord,
    EnergyRecord,
    Event,
    FuelRecord,
    User,
    WaterRecord,
)
from app.models.enums import EventStatus, UserRole
from app.schemas.carbon_schema import (
    CarbonFactorCreate,
    CarbonFactorUpdate,
    CarbonRecordCreate,
    CarbonRecordUpdate,
    EnergyRecordCreate,
    FuelRecordCreate,
    WaterRecordCreate,
)


def _get_event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def get_factor_or_404(db: Session, factor_id: UUID) -> CarbonFactor:
    factor = db.get(CarbonFactor, factor_id)
    if not factor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carbon factor not found")
    return factor


def get_record_or_404(db: Session, record_id: UUID) -> CarbonRecord:
    record = db.get(CarbonRecord, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carbon record not found")
    return record


def _ensure_can_view_carbon(db: Session, event_id: UUID, user: User) -> Event:
    event = _get_event_or_404(db, event_id)
    if user.role == UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def _ensure_can_manage_carbon(db: Session, event_id: UUID, user: User) -> Event:
    event = _get_event_or_404(db, event_id)
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def _validate_active_factor(db: Session, factor_id: UUID) -> CarbonFactor:
    factor = get_factor_or_404(db, factor_id)
    if not factor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Carbon factor is inactive",
        )
    return factor


def _validate_unit(factor: CarbonFactor, activity_unit: str) -> None:
    if activity_unit != factor.unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="activity_unit must match the carbon factor unit",
        )


def list_factors(
    db: Session,
    *,
    q: str | None,
    is_active: bool | None,
    page: int,
    limit: int,
) -> tuple[list[CarbonFactor], int]:
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(
            CarbonFactor.name.ilike(pattern)
            | CarbonFactor.category.ilike(pattern)
            | CarbonFactor.unit.ilike(pattern)
        )
    if is_active is not None:
        filters.append(CarbonFactor.is_active == is_active)
    total = db.scalar(select(func.count()).select_from(CarbonFactor).where(*filters)) or 0
    items = list(
        db.scalars(
            select(CarbonFactor)
            .where(*filters)
            .order_by(CarbonFactor.category, CarbonFactor.name)
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def create_factor(db: Session, payload: CarbonFactorCreate) -> CarbonFactor:
    factor = CarbonFactor(**payload.model_dump(), is_active=True)
    db.add(factor)
    db.commit()
    db.refresh(factor)
    return factor


def update_factor(db: Session, factor_id: UUID, payload: CarbonFactorUpdate) -> CarbonFactor:
    factor = get_factor_or_404(db, factor_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(factor, field, value)
    db.add(factor)
    db.commit()
    db.refresh(factor)
    return factor


def deactivate_factor(db: Session, factor_id: UUID) -> CarbonFactor:
    factor = get_factor_or_404(db, factor_id)
    factor.is_active = False
    db.add(factor)
    db.commit()
    db.refresh(factor)
    return factor


def create_carbon_record(
    db: Session, event_id: UUID, payload: CarbonRecordCreate, current_user: User
) -> CarbonRecord:
    _ensure_can_manage_carbon(db, event_id, current_user)
    factor = _validate_active_factor(db, payload.factor_id)
    _validate_unit(factor, payload.activity_unit)
    emissions = payload.activity_value * factor.factor_kgco2e
    record = CarbonRecord(
        event_id=event_id,
        factor_id=factor.id,
        category=factor.category,
        description=payload.description,
        activity_value=payload.activity_value,
        activity_unit=payload.activity_unit,
        emissions_kgco2e=emissions,
        recorded_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_event_carbon_records(
    db: Session,
    *,
    event_id: UUID,
    current_user: User,
    page: int,
    limit: int,
) -> tuple[list[CarbonRecord], int]:
    _ensure_can_view_carbon(db, event_id, current_user)
    filters = [CarbonRecord.event_id == event_id]
    total = db.scalar(select(func.count()).select_from(CarbonRecord).where(*filters)) or 0
    items = list(
        db.scalars(
            select(CarbonRecord)
            .where(*filters)
            .order_by(CarbonRecord.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_carbon_record(db: Session, record_id: UUID, current_user: User) -> CarbonRecord:
    record = get_record_or_404(db, record_id)
    _ensure_can_view_carbon(db, record.event_id, current_user)
    return record


def update_carbon_record(
    db: Session, record_id: UUID, payload: CarbonRecordUpdate, current_user: User
) -> CarbonRecord:
    record = get_record_or_404(db, record_id)
    _ensure_can_manage_carbon(db, record.event_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    factor = _validate_active_factor(db, data.get("factor_id", record.factor_id))
    activity_unit = data.get("activity_unit", record.activity_unit)
    activity_value = data.get("activity_value", record.activity_value)
    _validate_unit(factor, activity_unit)
    for field, value in data.items():
        setattr(record, field, value)
    record.factor_id = factor.id
    record.category = factor.category
    record.activity_unit = activity_unit
    record.activity_value = activity_value
    record.emissions_kgco2e = activity_value * factor.factor_kgco2e
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_carbon_record(db: Session, record_id: UUID, current_user: User) -> None:
    record = get_record_or_404(db, record_id)
    event = _ensure_can_manage_carbon(db, record.event_id, current_user)
    if event.status in {EventStatus.FINISHED, EventStatus.REPORT_DELIVERED}:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can delete records from finished events",
            )
    db.delete(record)
    db.commit()


def get_carbon_summary(db: Session, event_id: UUID, current_user: User) -> dict:
    event = _ensure_can_view_carbon(db, event_id, current_user)
    records = list(
        db.scalars(
            select(CarbonRecord)
            .options(selectinload(CarbonRecord.factor))
            .where(CarbonRecord.event_id == event_id)
        ).all()
    )
    total = sum((record.emissions_kgco2e for record in records), Decimal("0"))
    attendees = event.real_attendees or event.estimated_attendees
    per_attendee = (total / Decimal(attendees)).quantize(Decimal("0.0001")) if attendees else None
    return {
        "event_id": event_id,
        "total_kgco2e": total,
        "total_tco2e": (total / Decimal("1000")).quantize(Decimal("0.0001")),
        "kgco2e_per_attendee": per_attendee,
        "by_category": _group_by_category(records),
        "by_scope": _group_by_scope(records),
        "by_factor": _group_by_factor(records),
    }


def _group_by_category(records: list[CarbonRecord]) -> list[dict]:
    totals: dict[str, Decimal] = {}
    for record in records:
        totals[record.category] = totals.get(record.category, Decimal("0")) + record.emissions_kgco2e
    return [{"id": None, "name": name, "total_kgco2e": total} for name, total in totals.items()]


def _group_by_scope(records: list[CarbonRecord]) -> list[dict]:
    totals: dict[str, Decimal] = {}
    for record in records:
        scope = record.factor.scope.value if record.factor and record.factor.scope else "Sin scope"
        totals[scope] = totals.get(scope, Decimal("0")) + record.emissions_kgco2e
    return [{"id": None, "name": name, "total_kgco2e": total} for name, total in totals.items()]


def _group_by_factor(records: list[CarbonRecord]) -> list[dict]:
    totals: dict[UUID, Decimal] = {}
    names: dict[UUID, str] = {}
    for record in records:
        totals[record.factor_id] = totals.get(record.factor_id, Decimal("0")) + record.emissions_kgco2e
        names[record.factor_id] = record.factor.name if record.factor else str(record.factor_id)
    return [
        {"id": factor_id, "name": names[factor_id], "total_kgco2e": total}
        for factor_id, total in totals.items()
    ]


def create_fuel_record(
    db: Session, event_id: UUID, payload: FuelRecordCreate, current_user: User
) -> FuelRecord:
    _ensure_can_manage_carbon(db, event_id, current_user)
    record = FuelRecord(event_id=event_id, recorded_by=current_user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_fuel_records(db: Session, event_id: UUID, current_user: User) -> list[FuelRecord]:
    _ensure_can_view_carbon(db, event_id, current_user)
    return list(db.scalars(select(FuelRecord).where(FuelRecord.event_id == event_id)).all())


def create_energy_record(
    db: Session, event_id: UUID, payload: EnergyRecordCreate, current_user: User
) -> EnergyRecord:
    _ensure_can_manage_carbon(db, event_id, current_user)
    record = EnergyRecord(event_id=event_id, recorded_by=current_user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_energy_records(db: Session, event_id: UUID, current_user: User) -> list[EnergyRecord]:
    _ensure_can_view_carbon(db, event_id, current_user)
    return list(db.scalars(select(EnergyRecord).where(EnergyRecord.event_id == event_id)).all())


def create_water_record(
    db: Session, event_id: UUID, payload: WaterRecordCreate, current_user: User
) -> WaterRecord:
    _ensure_can_manage_carbon(db, event_id, current_user)
    record = WaterRecord(event_id=event_id, recorded_by=current_user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_water_records(db: Session, event_id: UUID, current_user: User) -> list[WaterRecord]:
    _ensure_can_view_carbon(db, event_id, current_user)
    return list(db.scalars(select(WaterRecord).where(WaterRecord.event_id == event_id)).all())
