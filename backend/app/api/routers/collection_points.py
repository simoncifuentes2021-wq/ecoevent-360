from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.rate_limit import enforce
from app.db.session import get_db
from app.models.core import User
from app.schemas.collection_point_schema import (
    CollectionPointCreate, CollectionPointRead, CollectionPointUpdate,
    EventWastePublicFormRead,
    PublicCollectionPointRead, PublicWasteBatchRequest, PublicWasteBatchResponse,
    PublicWasteCollectionRecordRead, WasteCollectionRecordRead, WasteCollectionSummaryRead,
)
from app.services import collection_point_service as service
from app.services.audit_log_service import create_audit_log

router = APIRouter(tags=["waste collection points"])
public_router = APIRouter(prefix="/public/waste-collection-points", tags=["public waste"])
public_forms_router = APIRouter(prefix="/public/waste-forms", tags=["public waste"])


def _public_base_url() -> str:
    if settings.app_env.lower() in {"local", "development", "dev"}:
        return "http://localhost:3000"
    return (settings.public_app_url or settings.official_frontend_url).rstrip("/")


@router.get("/events/{event_id}/waste-collection-points", response_model=list[CollectionPointRead])
def list_points(event_id: UUID, include_inactive: bool = Query(default=True), db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.list_points(db, event_id, user, _public_base_url(), include_inactive)


@router.post("/events/{event_id}/waste-collection-points", response_model=CollectionPointRead, status_code=status.HTTP_201_CREATED)
def create_point(event_id: UUID, payload: CollectionPointCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    point = service.create_point(db, event_id, payload, user, _public_base_url())
    create_audit_log(db, user=user, action="CREATE", module="waste", entity_type="WasteCollectionPoint", entity_id=point.id, event_id=event_id, new_data=payload.model_dump(mode="json"), request=request)
    return point


@router.get("/waste-collection-points/{point_id}", response_model=CollectionPointRead)
def get_point(point_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    point = service._point_or_404(db, point_id)
    result = service.list_points(db, point.event_id, user, _public_base_url())
    return next(item for item in result if item.id == point_id)


@router.patch("/waste-collection-points/{point_id}", response_model=CollectionPointRead)
def update_point(point_id: UUID, payload: CollectionPointUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    before = service._point_or_404(db, point_id)
    old_data = {"code": before.code, "name": before.name, "is_active": before.is_active, "zone_id": before.zone_id}
    point = service.update_point(db, point_id, payload, user, _public_base_url())
    create_audit_log(db, user=user, action="UPDATE", module="waste", entity_type="WasteCollectionPoint", entity_id=point_id, event_id=point.event_id, old_data=old_data, new_data=payload.model_dump(exclude_unset=True, mode="json"), request=request)
    return point


@router.get("/events/{event_id}/waste-collection-summary", response_model=WasteCollectionSummaryRead)
def get_collection_summary(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.collection_summary(db, event_id, user)


@router.get("/events/{event_id}/waste-public-form", response_model=EventWastePublicFormRead)
def get_public_form(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.read_event_form(db, event_id, user, _public_base_url())


@router.patch("/events/{event_id}/waste-public-form/{action}", response_model=EventWastePublicFormRead)
def update_public_form(event_id: UUID, action: str, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    actions = {"activate": "ACTIVE", "close": "CLOSED", "regenerate-token": "REGENERATE"}
    if action not in actions:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Acción no encontrada")
    return service.set_event_form_status(db, event_id, user, actions[action], _public_base_url())


@router.get("/events/{event_id}/waste-collection-records")
def list_collection_records(
    event_id: UUID,
    collection_point_id: UUID | None = None,
    waste_type_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = Query(default=None, max_length=160),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(get_current_active_user),
):
    return service.list_collection_records(
        db, event_id, user, collection_point_id=collection_point_id, waste_type_id=waste_type_id,
        date_from=date_from, date_to=date_to, search=search, page=page, limit=limit,
    )


@router.get("/waste-collection-records/{record_id}", response_model=WasteCollectionRecordRead)
def get_collection_record(record_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.get_collection_record(db, record_id, user)


@public_router.get("/{token}", response_model=PublicCollectionPointRead)
def read_public_point(token: str, request: Request, db: Session = Depends(get_db)):
    enforce(request, "waste-point-read", token, settings.rate_limit_public_read)
    return service.public_point(db, token)


@public_router.post("/{token}/records", response_model=PublicWasteBatchResponse, status_code=status.HTTP_201_CREATED)
def submit_public_records(token: str, payload: PublicWasteBatchRequest, request: Request, db: Session = Depends(get_db)):
    enforce(request, "waste-point-submit", token, settings.rate_limit_public_submit)
    accepted, rejected = service.submit_public_records(db, token, payload.items)
    return PublicWasteBatchResponse(
        synced=[PublicWasteCollectionRecordRead.model_validate(item) for item in accepted],
        rejected=rejected,
    )


@public_forms_router.get("/{token}", response_model=PublicCollectionPointRead)
def read_event_waste_form(token: str, request: Request, db: Session = Depends(get_db)):
    enforce(request, "waste-form-read", token, settings.rate_limit_public_read)
    return service.public_point(db, token)


@public_forms_router.post("/{token}/records", response_model=PublicWasteBatchResponse, status_code=status.HTTP_201_CREATED)
def submit_event_waste_records(token: str, payload: PublicWasteBatchRequest, request: Request, db: Session = Depends(get_db)):
    enforce(request, "waste-form-submit", token, settings.rate_limit_public_submit)
    accepted, rejected = service.submit_public_records(db, token, payload.items)
    return PublicWasteBatchResponse(synced=[PublicWasteCollectionRecordRead.model_validate(item) for item in accepted], rejected=rejected)
