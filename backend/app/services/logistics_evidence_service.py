from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event
from app.models.core import (
    LogisticsEvidence,
    LogisticsOrder,
    LogisticsOrderItem,
    PurchaseRequest,
    PurchaseRequestItem,
    StockMovement,
    User,
    WarehouseUser,
)
from app.models.enums import LogisticsEvidenceStage, LogisticsOrderStatus, UserRole
from app.services.file_storage_service import delete_stored_file, save_order_evidence_file


def get_logistics_evidence_or_404(db: Session, evidence_id: UUID) -> LogisticsEvidence:
    evidence = db.get(LogisticsEvidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics evidence not found")
    return evidence


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _warehouse_assignment(db: Session, user: User, warehouse_id: UUID) -> WarehouseUser | None:
    if user.role != UserRole.LOGISTICS_OPERATOR:
        return None
    return db.scalar(
        select(WarehouseUser).where(
            WarehouseUser.user_id == user.id,
            WarehouseUser.warehouse_id == warehouse_id,
        )
    )


def _can_view_order(db: Session, user: User, order: LogisticsOrder) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return can_access_event(user, order.event_id, db)
    if user.role == UserRole.LOGISTICS_OPERATOR:
        return order.assigned_operator_id == user.id
    return False


def _can_upload_order(db: Session, user: User, order: LogisticsOrder) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    return user.role == UserRole.LOGISTICS_OPERATOR and order.assigned_operator_id == user.id


def _can_view_purchase(db: Session, user: User, purchase: PurchaseRequest) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR and purchase.event_id:
        return can_access_event(user, purchase.event_id, db)
    if user.role == UserRole.LOGISTICS_OPERATOR:
        if purchase.logistics_order_id:
            order = db.get(LogisticsOrder, purchase.logistics_order_id)
            if order and order.assigned_operator_id == user.id:
                return True
        if purchase.warehouse_id:
            assignment = _warehouse_assignment(db, user, purchase.warehouse_id)
            return bool(assignment and assignment.can_view_stock)
    return False


def _can_upload_purchase(db: Session, user: User, purchase: PurchaseRequest) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.LOGISTICS_OPERATOR:
        if purchase.logistics_order_id:
            order = db.get(LogisticsOrder, purchase.logistics_order_id)
            if order and order.assigned_operator_id == user.id:
                return True
        if purchase.warehouse_id:
            assignment = _warehouse_assignment(db, user, purchase.warehouse_id)
            return bool(assignment and assignment.can_manage_stock)
    return False


def _can_view_stock_movement(db: Session, user: User, movement: StockMovement) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.LOGISTICS_OPERATOR:
        assignment = _warehouse_assignment(db, user, movement.warehouse_id)
        return bool(assignment and assignment.can_view_stock)
    return False


def _can_upload_stock_movement(db: Session, user: User, movement: StockMovement) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.LOGISTICS_OPERATOR:
        assignment = _warehouse_assignment(db, user, movement.warehouse_id)
        return bool(assignment and assignment.can_manage_stock)
    return False


def _ensure_no_worker_or_client(user: User) -> None:
    if user.role in {UserRole.WORKER, UserRole.CLIENT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _save_file(file: UploadFile) -> tuple[str, str, int]:
    file_url, file_type, size_bytes = save_order_evidence_file("logistics-evidences", file)
    if size_bytes <= 0:
        delete_stored_file(file_url)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File cannot be empty")
    return file_url, file_type, size_bytes


def _create_evidence(
    db: Session,
    *,
    user: User,
    file: UploadFile,
    stage: LogisticsEvidenceStage,
    notes: str | None,
    event_id: UUID | None = None,
    logistics_order_id: UUID | None = None,
    logistics_order_item_id: UUID | None = None,
    purchase_request_id: UUID | None = None,
    purchase_request_item_id: UUID | None = None,
    stock_movement_id: UUID | None = None,
    warehouse_id: UUID | None = None,
) -> LogisticsEvidence:
    file_url, file_type, size_bytes = _save_file(file)
    evidence = LogisticsEvidence(
        event_id=event_id,
        logistics_order_id=logistics_order_id,
        logistics_order_item_id=logistics_order_item_id,
        purchase_request_id=purchase_request_id,
        purchase_request_item_id=purchase_request_item_id,
        stock_movement_id=stock_movement_id,
        warehouse_id=warehouse_id,
        evidence_stage=stage,
        file_url=file_url,
        file_name=file.filename,
        file_type=file_type,
        mime_type=file_type,
        size_bytes=size_bytes,
        notes=_clean_text(notes),
        uploaded_by=user.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def create_order_evidence(
    db: Session,
    *,
    order_id: UUID,
    stage: LogisticsEvidenceStage,
    notes: str | None,
    file: UploadFile,
    user: User,
) -> LogisticsEvidence:
    _ensure_no_worker_or_client(user)
    order = db.get(LogisticsOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order not found")
    if not _can_upload_order(db, user, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return _create_evidence(
        db,
        user=user,
        file=file,
        stage=stage,
        notes=notes,
        event_id=order.event_id,
        logistics_order_id=order.id,
        warehouse_id=order.warehouse_id,
    )


def create_order_item_evidence(
    db: Session,
    *,
    item_id: UUID,
    stage: LogisticsEvidenceStage,
    notes: str | None,
    file: UploadFile,
    user: User,
) -> LogisticsEvidence:
    _ensure_no_worker_or_client(user)
    item = db.get(LogisticsOrderItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order item not found")
    order = db.get(LogisticsOrder, item.order_id)
    if not order or not _can_upload_order(db, user, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return _create_evidence(
        db,
        user=user,
        file=file,
        stage=stage,
        notes=notes,
        event_id=order.event_id,
        logistics_order_id=order.id,
        logistics_order_item_id=item.id,
        warehouse_id=order.warehouse_id,
    )


def create_purchase_evidence(
    db: Session,
    *,
    purchase_request_id: UUID,
    purchase_request_item_id: UUID | None,
    stage: LogisticsEvidenceStage,
    notes: str | None,
    file: UploadFile,
    user: User,
) -> LogisticsEvidence:
    _ensure_no_worker_or_client(user)
    purchase = db.get(PurchaseRequest, purchase_request_id)
    if not purchase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request not found")
    if purchase_request_item_id:
        item = db.get(PurchaseRequestItem, purchase_request_item_id)
        if not item or item.purchase_request_id != purchase.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase item does not belong to request")
    if not _can_upload_purchase(db, user, purchase):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return _create_evidence(
        db,
        user=user,
        file=file,
        stage=stage,
        notes=notes,
        event_id=purchase.event_id,
        logistics_order_id=purchase.logistics_order_id,
        purchase_request_id=purchase.id,
        purchase_request_item_id=purchase_request_item_id,
        warehouse_id=purchase.warehouse_id,
    )


def create_stock_movement_evidence(
    db: Session,
    *,
    movement_id: UUID,
    stage: LogisticsEvidenceStage,
    notes: str | None,
    file: UploadFile,
    user: User,
) -> LogisticsEvidence:
    _ensure_no_worker_or_client(user)
    movement = db.get(StockMovement, movement_id)
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock movement not found")
    if not _can_upload_stock_movement(db, user, movement):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return _create_evidence(
        db,
        user=user,
        file=file,
        stage=stage,
        notes=notes,
        stock_movement_id=movement.id,
        warehouse_id=movement.warehouse_id,
    )


def _list(
    db: Session,
    *,
    user: User,
    filters: list,
    page: int,
    limit: int,
) -> tuple[list[LogisticsEvidence], int]:
    _ensure_no_worker_or_client(user)
    total = db.scalar(select(func.count()).select_from(LogisticsEvidence).where(*filters)) or 0
    items = list(
        db.scalars(
            select(LogisticsEvidence)
            .where(*filters)
            .order_by(LogisticsEvidence.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def list_order_evidences(
    db: Session,
    *,
    order_id: UUID,
    stage: LogisticsEvidenceStage | None,
    include_items: bool,
    user: User,
    page: int,
    limit: int,
) -> tuple[list[LogisticsEvidence], int]:
    order = db.get(LogisticsOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order not found")
    if not _can_view_order(db, user, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if include_items:
        order_item_ids = select(LogisticsOrderItem.id).where(LogisticsOrderItem.order_id == order_id)
        filters = [
            or_(
                LogisticsEvidence.logistics_order_id == order_id,
                LogisticsEvidence.logistics_order_item_id.in_(order_item_ids),
            )
        ]
    else:
        filters = [
            LogisticsEvidence.logistics_order_id == order_id,
            LogisticsEvidence.logistics_order_item_id.is_(None),
        ]
    if stage:
        filters.append(LogisticsEvidence.evidence_stage == stage)
    return _list(db, user=user, filters=filters, page=page, limit=limit)


def list_order_item_evidences(
    db: Session,
    *,
    item_id: UUID,
    stage: LogisticsEvidenceStage | None,
    user: User,
    page: int,
    limit: int,
) -> tuple[list[LogisticsEvidence], int]:
    item = db.get(LogisticsOrderItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order item not found")
    order = db.get(LogisticsOrder, item.order_id)
    if not order or not _can_view_order(db, user, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = [LogisticsEvidence.logistics_order_item_id == item_id]
    if stage:
        filters.append(LogisticsEvidence.evidence_stage == stage)
    return _list(db, user=user, filters=filters, page=page, limit=limit)


def list_purchase_evidences(
    db: Session,
    *,
    purchase_request_id: UUID,
    stage: LogisticsEvidenceStage | None,
    user: User,
    page: int,
    limit: int,
) -> tuple[list[LogisticsEvidence], int]:
    purchase = db.get(PurchaseRequest, purchase_request_id)
    if not purchase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request not found")
    if not _can_view_purchase(db, user, purchase):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = [LogisticsEvidence.purchase_request_id == purchase_request_id]
    if stage:
        filters.append(LogisticsEvidence.evidence_stage == stage)
    return _list(db, user=user, filters=filters, page=page, limit=limit)


def list_stock_movement_evidences(
    db: Session,
    *,
    movement_id: UUID,
    stage: LogisticsEvidenceStage | None,
    user: User,
    page: int,
    limit: int,
) -> tuple[list[LogisticsEvidence], int]:
    movement = db.get(StockMovement, movement_id)
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock movement not found")
    if not _can_view_stock_movement(db, user, movement):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = [LogisticsEvidence.stock_movement_id == movement_id]
    if stage:
        filters.append(LogisticsEvidence.evidence_stage == stage)
    return _list(db, user=user, filters=filters, page=page, limit=limit)


def list_event_logistics_evidences(
    db: Session,
    *,
    event_id: UUID,
    stage: LogisticsEvidenceStage | None,
    user: User,
    page: int,
    limit: int,
) -> tuple[list[LogisticsEvidence], int]:
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = [LogisticsEvidence.event_id == event_id]
    if stage:
        filters.append(LogisticsEvidence.evidence_stage == stage)
    return _list(db, user=user, filters=filters, page=page, limit=limit)


def delete_logistics_evidence(db: Session, evidence_id: UUID, user: User) -> None:
    evidence = get_logistics_evidence_or_404(db, evidence_id)
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN} and evidence.uploaded_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if evidence.logistics_order_id:
        order = db.get(LogisticsOrder, evidence.logistics_order_id)
        if order and order.status == LogisticsOrderStatus.CLOSED and user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete evidence from closed order")
    file_url = evidence.file_url
    db.delete(evidence)
    db.commit()
    delete_stored_file(file_url)
