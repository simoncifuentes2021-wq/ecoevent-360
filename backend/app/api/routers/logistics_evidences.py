from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.models.enums import LogisticsEvidenceStage
from app.schemas.logistics_evidence_schema import LogisticsEvidenceListResponse, LogisticsEvidenceRead
from app.services import logistics_evidence_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["logistics evidences"])


def _list_response(items, total: int, page: int, limit: int) -> LogisticsEvidenceListResponse:
    return LogisticsEvidenceListResponse(items=items, total=total, page=page, limit=limit)


@router.post(
    "/logistics-orders/{order_id}/evidences",
    response_model=LogisticsEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_order_evidence(
    order_id: UUID,
    request: Request,
    evidence_stage: LogisticsEvidenceStage = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = logistics_evidence_service.create_order_evidence(
        db, order_id=order_id, stage=evidence_stage, notes=notes, file=file, user=current_user
    )
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_EVIDENCE_UPLOADED",
        module="logistics_evidences",
        entity_type="LogisticsEvidence",
        entity_id=evidence.id,
        event_id=evidence.event_id,
        new_data=serialize_model_for_audit(evidence),
        request=request,
    )
    return evidence


@router.get("/logistics-orders/{order_id}/evidences", response_model=LogisticsEvidenceListResponse)
def list_order_evidences(
    order_id: UUID,
    evidence_stage: LogisticsEvidenceStage | None = Query(default=None),
    include_items: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_evidence_service.list_order_evidences(
        db,
        order_id=order_id,
        stage=evidence_stage,
        include_items=include_items,
        user=current_user,
        page=page,
        limit=limit,
    )
    return _list_response(items, total, page, limit)


@router.post(
    "/logistics-order-items/{item_id}/evidences",
    response_model=LogisticsEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_order_item_evidence(
    item_id: UUID,
    request: Request,
    evidence_stage: LogisticsEvidenceStage = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = logistics_evidence_service.create_order_item_evidence(
        db, item_id=item_id, stage=evidence_stage, notes=notes, file=file, user=current_user
    )
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ITEM_EVIDENCE_UPLOADED",
        module="logistics_evidences",
        entity_type="LogisticsEvidence",
        entity_id=evidence.id,
        event_id=evidence.event_id,
        new_data=serialize_model_for_audit(evidence),
        request=request,
    )
    return evidence


@router.get("/logistics-order-items/{item_id}/evidences", response_model=LogisticsEvidenceListResponse)
def list_order_item_evidences(
    item_id: UUID,
    evidence_stage: LogisticsEvidenceStage | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_evidence_service.list_order_item_evidences(
        db, item_id=item_id, stage=evidence_stage, user=current_user, page=page, limit=limit
    )
    return _list_response(items, total, page, limit)


@router.post(
    "/purchase-requests/{purchase_request_id}/evidences",
    response_model=LogisticsEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_purchase_evidence(
    purchase_request_id: UUID,
    request: Request,
    evidence_stage: LogisticsEvidenceStage = Form(...),
    purchase_request_item_id: UUID | None = Form(default=None),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = logistics_evidence_service.create_purchase_evidence(
        db,
        purchase_request_id=purchase_request_id,
        purchase_request_item_id=purchase_request_item_id,
        stage=evidence_stage,
        notes=notes,
        file=file,
        user=current_user,
    )
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_EVIDENCE_UPLOADED",
        module="logistics_evidences",
        entity_type="LogisticsEvidence",
        entity_id=evidence.id,
        event_id=evidence.event_id,
        new_data=serialize_model_for_audit(evidence),
        request=request,
    )
    return evidence


@router.get("/purchase-requests/{purchase_request_id}/evidences", response_model=LogisticsEvidenceListResponse)
def list_purchase_evidences(
    purchase_request_id: UUID,
    evidence_stage: LogisticsEvidenceStage | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_evidence_service.list_purchase_evidences(
        db, purchase_request_id=purchase_request_id, stage=evidence_stage, user=current_user, page=page, limit=limit
    )
    return _list_response(items, total, page, limit)


@router.post(
    "/stock/movements/{movement_id}/evidences",
    response_model=LogisticsEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement_evidence(
    movement_id: UUID,
    request: Request,
    evidence_stage: LogisticsEvidenceStage = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = logistics_evidence_service.create_stock_movement_evidence(
        db, movement_id=movement_id, stage=evidence_stage, notes=notes, file=file, user=current_user
    )
    create_audit_log(
        db,
        user=current_user,
        action="STOCK_MOVEMENT_EVIDENCE_UPLOADED",
        module="logistics_evidences",
        entity_type="LogisticsEvidence",
        entity_id=evidence.id,
        new_data=serialize_model_for_audit(evidence),
        request=request,
    )
    return evidence


@router.get("/stock/movements/{movement_id}/evidences", response_model=LogisticsEvidenceListResponse)
def list_stock_movement_evidences(
    movement_id: UUID,
    evidence_stage: LogisticsEvidenceStage | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_evidence_service.list_stock_movement_evidences(
        db, movement_id=movement_id, stage=evidence_stage, user=current_user, page=page, limit=limit
    )
    return _list_response(items, total, page, limit)


@router.get("/events/{event_id}/logistics-evidences", response_model=LogisticsEvidenceListResponse)
def list_event_logistics_evidences(
    event_id: UUID,
    evidence_stage: LogisticsEvidenceStage | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_evidence_service.list_event_logistics_evidences(
        db, event_id=event_id, stage=evidence_stage, user=current_user, page=page, limit=limit
    )
    return _list_response(items, total, page, limit)


@router.delete("/logistics-evidences/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_logistics_evidence(
    evidence_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = logistics_evidence_service.get_logistics_evidence_or_404(db, evidence_id)
    event_id = evidence.event_id
    old_data = serialize_model_for_audit(evidence)
    logistics_evidence_service.delete_logistics_evidence(db, evidence_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_EVIDENCE_DELETED",
        module="logistics_evidences",
        entity_type="LogisticsEvidence",
        entity_id=evidence_id,
        event_id=event_id,
        old_data=old_data,
        request=request,
    )
