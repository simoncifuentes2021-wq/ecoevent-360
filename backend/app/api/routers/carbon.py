from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.carbon_schema import (
    CarbonFactorCreate,
    CarbonFactorListResponse,
    CarbonFactorRead,
    CarbonFactorUpdate,
    CarbonRecordCreate,
    CarbonRecordListResponse,
    CarbonRecordRead,
    CarbonRecordUpdate,
    CarbonSummaryRead,
    EnergyRecordCreate,
    EnergyRecordRead,
    FuelRecordCreate,
    FuelRecordRead,
    WaterRecordCreate,
    WaterRecordRead,
)
from app.services import carbon_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["carbon"])


@router.get(
    "/carbon-factors",
    response_model=CarbonFactorListResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR))],
)
def list_carbon_factors(
    q: str | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = carbon_service.list_factors(
        db, q=q, is_active=is_active, page=page, limit=limit
    )
    return CarbonFactorListResponse(items=items, total=total, page=page, limit=limit)


@router.post(
    "/carbon-factors",
    response_model=CarbonFactorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_carbon_factor(
    payload: CarbonFactorCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    factor = carbon_service.create_factor(db, payload)
    create_audit_log(
        db,
        user=current_user,
        action="CARBON_FACTOR_CREATED",
        module="carbon",
        entity_type="CarbonFactor",
        entity_id=factor.id,
        new_data=serialize_model_for_audit(factor),
        request=request,
    )
    return factor


@router.get(
    "/carbon-factors/{factor_id}",
    response_model=CarbonFactorRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR))],
)
def get_carbon_factor(factor_id: UUID, db: Session = Depends(get_db)):
    return carbon_service.get_factor_or_404(db, factor_id)


@router.patch(
    "/carbon-factors/{factor_id}",
    response_model=CarbonFactorRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_carbon_factor(
    factor_id: UUID,
    payload: CarbonFactorUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = carbon_service.get_factor_or_404(db, factor_id)
    old_data = serialize_model_for_audit(before)
    factor = carbon_service.update_factor(db, factor_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="CARBON_FACTOR_UPDATED",
        module="carbon",
        entity_type="CarbonFactor",
        entity_id=factor.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(factor),
        request=request,
    )
    return factor


@router.delete(
    "/carbon-factors/{factor_id}",
    response_model=CarbonFactorRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_carbon_factor(
    factor_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = carbon_service.get_factor_or_404(db, factor_id)
    old_data = serialize_model_for_audit(before)
    factor = carbon_service.deactivate_factor(db, factor_id)
    create_audit_log(
        db,
        user=current_user,
        action="CARBON_FACTOR_DEACTIVATED",
        module="carbon",
        entity_type="CarbonFactor",
        entity_id=factor.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(factor),
        request=request,
    )
    return factor


@router.post(
    "/events/{event_id}/carbon-records",
    response_model=CarbonRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_carbon_record(
    event_id: UUID,
    payload: CarbonRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = carbon_service.create_carbon_record(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="CARBON_RECORD_CREATED",
        module="carbon",
        entity_type="CarbonRecord",
        entity_id=record.id,
        event_id=record.event_id,
        new_data=serialize_model_for_audit(record),
        metadata={
            "factor_id": record.factor_id,
            "activity_value": record.activity_value,
            "emissions_kgco2e": record.emissions_kgco2e,
        },
        request=request,
    )
    return record


@router.get("/events/{event_id}/carbon-records", response_model=CarbonRecordListResponse)
def list_event_carbon_records(
    event_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = carbon_service.list_event_carbon_records(
        db, event_id=event_id, current_user=current_user, page=page, limit=limit
    )
    return CarbonRecordListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/carbon-records/{record_id}", response_model=CarbonRecordRead)
def get_carbon_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return carbon_service.get_carbon_record(db, record_id, current_user)


@router.patch("/carbon-records/{record_id}", response_model=CarbonRecordRead)
def update_carbon_record(
    record_id: UUID,
    payload: CarbonRecordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = carbon_service.get_carbon_record(db, record_id, current_user)
    old_data = serialize_model_for_audit(before)
    record = carbon_service.update_carbon_record(db, record_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="CARBON_RECORD_UPDATED",
        module="carbon",
        entity_type="CarbonRecord",
        entity_id=record.id,
        event_id=record.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(record),
        request=request,
    )
    return record


@router.delete("/carbon-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_carbon_record(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = carbon_service.get_carbon_record(db, record_id, current_user)
    event_id = record.event_id
    old_data = serialize_model_for_audit(record)
    carbon_service.delete_carbon_record(db, record_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="CARBON_RECORD_DELETED_OR_VOIDED",
        module="carbon",
        entity_type="CarbonRecord",
        entity_id=record_id,
        event_id=event_id,
        old_data=old_data,
        request=request,
    )


@router.get("/events/{event_id}/carbon-summary", response_model=CarbonSummaryRead)
def get_carbon_summary(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return carbon_service.get_carbon_summary(db, event_id, current_user)


@router.post(
    "/events/{event_id}/fuel-records",
    response_model=FuelRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_fuel_record(
    event_id: UUID,
    payload: FuelRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = carbon_service.create_fuel_record(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="FUEL_RECORD_CREATED",
        module="operations",
        entity_type="FuelRecord",
        entity_id=record.id,
        event_id=record.event_id,
        new_data=serialize_model_for_audit(record),
        request=request,
    )
    return record


@router.get("/events/{event_id}/fuel-records", response_model=list[FuelRecordRead])
def list_fuel_records(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return carbon_service.list_fuel_records(db, event_id, current_user)


@router.post(
    "/events/{event_id}/energy-records",
    response_model=EnergyRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_energy_record(
    event_id: UUID,
    payload: EnergyRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = carbon_service.create_energy_record(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ENERGY_RECORD_CREATED",
        module="operations",
        entity_type="EnergyRecord",
        entity_id=record.id,
        event_id=record.event_id,
        new_data=serialize_model_for_audit(record),
        request=request,
    )
    return record


@router.get("/events/{event_id}/energy-records", response_model=list[EnergyRecordRead])
def list_energy_records(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return carbon_service.list_energy_records(db, event_id, current_user)


@router.post(
    "/events/{event_id}/water-records",
    response_model=WaterRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_water_record(
    event_id: UUID,
    payload: WaterRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = carbon_service.create_water_record(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="WATER_RECORD_CREATED",
        module="operations",
        entity_type="WaterRecord",
        entity_id=record.id,
        event_id=record.event_id,
        new_data=serialize_model_for_audit(record),
        request=request,
    )
    return record


@router.get("/events/{event_id}/water-records", response_model=list[WaterRecordRead])
def list_water_records(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return carbon_service.list_water_records(db, event_id, current_user)
