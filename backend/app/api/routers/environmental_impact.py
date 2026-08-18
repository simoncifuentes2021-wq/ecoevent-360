from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.environmental_schema import (
    EcoEquivalenceCreate,
    EcoEquivalenceRead,
    EcoEquivalenceUpdate,
    EnvironmentalActionCreate,
    EnvironmentalActionList,
    EnvironmentalActionRead,
    EnvironmentalActionUpdate,
    EnvironmentalFactorCreate,
    EnvironmentalFactorRead,
    EnvironmentalFactorUpdate,
    EnvironmentalMethodologyCreate,
    EnvironmentalMethodologyRead,
    EnvironmentalMethodologyUpdate,
    EnvironmentalMetricRead,
    EnvironmentalSummary,
    MetricOverride,
)
from app.services import environmental_calculation_service as calculations
from app.services import environmental_catalog_service as catalog
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["environmental impact"])


@router.get("/events/{event_id}/environmental-actions", response_model=EnvironmentalActionList)
def list_actions(
    event_id: UUID,
    session_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    items, total = calculations.list_actions(db, event_id, session_id, user)
    return EnvironmentalActionList(items=items, total=total)


@router.post(
    "/events/{event_id}/environmental-actions",
    response_model=EnvironmentalActionRead,
    status_code=201,
)
def create_action(
    event_id: UUID,
    payload: EnvironmentalActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = calculations.create_action(db, event_id, payload, user)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_ACTION_CREATED",
        module="environmental_impact",
        entity_type="EnvironmentalAction",
        entity_id=item.id,
        event_id=event_id,
        new_data=serialize_model_for_audit(item),
        metadata={"session_id": item.session_id},
        request=request,
    )
    return item


@router.get(
    "/events/{event_id}/environmental-actions/{action_id}", response_model=EnvironmentalActionRead
)
def get_action(
    event_id: UUID,
    action_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return calculations.get_action(db, event_id, action_id, user)


@router.patch(
    "/events/{event_id}/environmental-actions/{action_id}", response_model=EnvironmentalActionRead
)
def update_action(
    event_id: UUID,
    action_id: UUID,
    payload: EnvironmentalActionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    old = serialize_model_for_audit(calculations.get_action(db, event_id, action_id, user))
    item = calculations.update_action(db, event_id, action_id, payload, user)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_ACTION_UPDATED",
        module="environmental_impact",
        entity_type="EnvironmentalAction",
        entity_id=item.id,
        event_id=event_id,
        old_data=old,
        new_data=serialize_model_for_audit(item),
        metadata={"session_id": item.session_id},
        request=request,
    )
    return item


@router.delete("/events/{event_id}/environmental-actions/{action_id}", status_code=204)
def delete_action(
    event_id: UUID,
    action_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    old = serialize_model_for_audit(calculations.get_action(db, event_id, action_id, user))
    calculations.delete_action(db, event_id, action_id, user)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_ACTION_DELETED",
        module="environmental_impact",
        entity_type="EnvironmentalAction",
        entity_id=action_id,
        event_id=event_id,
        old_data=old,
        request=request,
    )
    return Response(status_code=204)


@router.post(
    "/events/{event_id}/environmental-actions/{action_id}/calculate",
    response_model=EnvironmentalActionRead,
)
def calculate(
    event_id: UUID,
    action_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = calculations.calculate(db, event_id, action_id, user)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_CALCULATION_RECALCULATED",
        module="environmental_impact",
        entity_type="EnvironmentalAction",
        entity_id=item.id,
        event_id=event_id,
        metadata={"session_id": item.session_id, "status": item.status},
        request=request,
    )
    return item


@router.patch(
    "/events/{event_id}/environmental-actions/{action_id}/metrics/{metric_id}/override",
    response_model=EnvironmentalMetricRead,
)
def override(
    event_id: UUID,
    action_id: UUID,
    metric_id: UUID,
    payload: MetricOverride,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = calculations.override_metric(db, event_id, action_id, metric_id, payload, user)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_OVERRIDE_APPLIED",
        module="environmental_impact",
        entity_type="EnvironmentalActionMetric",
        entity_id=item.id,
        event_id=event_id,
        new_data={"reported_value": item.reported_value, "override_reason": item.override_reason},
        request=request,
    )
    return item


@router.get("/events/{event_id}/environmental-impact/summary", response_model=EnvironmentalSummary)
def summary(
    event_id: UUID,
    session_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return calculations.summary(db, event_id, session_id, user)


@router.get(
    "/environmental-impact/factors",
    response_model=list[EnvironmentalFactorRead],
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR))
    ],
)
def factors(db: Session = Depends(get_db)):
    return catalog.list_factors(db)


@router.post(
    "/environmental-impact/factors",
    response_model=EnvironmentalFactorRead,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_factor(
    payload: EnvironmentalFactorCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = catalog.create_factor(db, payload)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_FACTOR_CREATED",
        module="environmental_impact",
        entity_type="EnvironmentalFactor",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.patch(
    "/environmental-impact/factors/{item_id}",
    response_model=EnvironmentalFactorRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_factor(
    item_id: UUID,
    payload: EnvironmentalFactorUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = catalog.update_factor(db, item_id, payload)
    action = (
        "ENVIRONMENTAL_FACTOR_DEACTIVATED"
        if payload.is_active is False
        else "ENVIRONMENTAL_FACTOR_UPDATED"
    )
    create_audit_log(
        db,
        user=user,
        action=action,
        module="environmental_impact",
        entity_type="EnvironmentalFactor",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.get(
    "/environmental-impact/methodologies",
    response_model=list[EnvironmentalMethodologyRead],
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR))
    ],
)
def methodologies(db: Session = Depends(get_db)):
    return catalog.list_methodologies(db)


@router.post(
    "/environmental-impact/methodologies",
    response_model=EnvironmentalMethodologyRead,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_methodology(
    payload: EnvironmentalMethodologyCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = catalog.create_methodology(db, payload)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_METHODOLOGY_CREATED",
        module="environmental_impact",
        entity_type="EnvironmentalMethodology",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.patch(
    "/environmental-impact/methodologies/{item_id}",
    response_model=EnvironmentalMethodologyRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_methodology(
    item_id: UUID,
    payload: EnvironmentalMethodologyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = catalog.update_methodology(db, item_id, payload)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_METHODOLOGY_UPDATED",
        module="environmental_impact",
        entity_type="EnvironmentalMethodology",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.get(
    "/environmental-impact/equivalences",
    response_model=list[EcoEquivalenceRead],
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR))
    ],
)
def equivalences(db: Session = Depends(get_db)):
    return catalog.list_equivalences(db)


@router.post(
    "/environmental-impact/equivalences",
    response_model=EcoEquivalenceRead,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_equivalence(
    payload: EcoEquivalenceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = catalog.create_equivalence(db, payload)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_EQUIVALENCE_CREATED",
        module="environmental_impact",
        entity_type="EcoEquivalenceFactor",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.patch(
    "/environmental-impact/equivalences/{item_id}",
    response_model=EcoEquivalenceRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_equivalence(
    item_id: UUID,
    payload: EcoEquivalenceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = catalog.update_equivalence(db, item_id, payload)
    create_audit_log(
        db,
        user=user,
        action="ENVIRONMENTAL_EQUIVALENCE_UPDATED",
        module="environmental_impact",
        entity_type="EcoEquivalenceFactor",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item
