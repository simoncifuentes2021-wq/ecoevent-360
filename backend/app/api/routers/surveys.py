from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.models.enums import SurveyStatus
from app.schemas.survey_schema import (
    SurveyCreate,
    SurveyImportRead,
    SurveyListResponse,
    SurveyRead,
    SurveyResponseListResponse,
    SurveyStatusUpdate,
    SurveySummaryRead,
    SurveyUpdate,
)
from app.services import survey_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["surveys"])


@router.post(
    "/events/{event_id}/surveys",
    response_model=SurveyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_survey(
    event_id: UUID,
    payload: SurveyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    survey = survey_service.create_survey(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="SURVEY_CREATED",
        module="surveys",
        entity_type="Survey",
        entity_id=survey.id,
        event_id=survey.event_id,
        new_data=serialize_model_for_audit(survey),
        request=request,
    )
    return survey


@router.get("/events/{event_id}/surveys", response_model=SurveyListResponse)
def list_event_surveys(
    event_id: UUID,
    status_filter: SurveyStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = survey_service.list_event_surveys(
        db,
        event_id=event_id,
        current_user=current_user,
        status_filter=status_filter,
        page=page,
        limit=limit,
    )
    return SurveyListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/surveys/{survey_id}", response_model=SurveyRead)
def get_survey(
    survey_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return survey_service.get_survey(db, survey_id, current_user)


@router.patch("/surveys/{survey_id}", response_model=SurveyRead)
def update_survey(
    survey_id: UUID,
    payload: SurveyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = survey_service.get_survey(db, survey_id, current_user)
    old_data = serialize_model_for_audit(before)
    survey = survey_service.update_survey(db, survey_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="SURVEY_UPDATED",
        module="surveys",
        entity_type="Survey",
        entity_id=survey.id,
        event_id=survey.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(survey),
        request=request,
    )
    return survey


@router.patch("/surveys/{survey_id}/status", response_model=SurveyRead)
def update_survey_status(
    survey_id: UUID,
    payload: SurveyStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = survey_service.get_survey(db, survey_id, current_user)
    old_status = before.status
    survey = survey_service.update_survey_status(db, survey_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="SURVEY_CLOSED" if survey.status == SurveyStatus.CLOSED else "SURVEY_UPDATED",
        module="surveys",
        entity_type="Survey",
        entity_id=survey.id,
        event_id=survey.event_id,
        old_data={"status": old_status},
        new_data={"status": survey.status},
        request=request,
    )
    return survey


@router.post(
    "/surveys/{survey_id}/import-csv",
    response_model=SurveyImportRead,
    status_code=status.HTTP_201_CREATED,
)
async def import_survey_csv(
    survey_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}:
        # Google Sheets CSV exports often arrive as text/csv, but curl and browsers vary.
        if not (file.filename or "").lower().endswith(".csv"):
            from fastapi import HTTPException

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be CSV")
    content = await file.read()
    imported = survey_service.import_survey_csv(
        db,
        survey_id=survey_id,
        filename=file.filename or "google-sheets-export.csv",
        content=content,
        current_user=current_user,
    )
    survey = survey_service.get_survey(db, survey_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="SURVEY_CSV_IMPORTED",
        module="surveys",
        entity_type="SurveyImport",
        entity_id=imported.id,
        event_id=survey.event_id,
        metadata={
            "survey_id": survey_id,
            "filename": file.filename,
            "imported_rows": imported.imported_rows,
        },
        request=request,
    )
    return imported


@router.get("/surveys/{survey_id}/responses", response_model=SurveyResponseListResponse)
def list_survey_responses(
    survey_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = survey_service.list_survey_responses(
        db, survey_id=survey_id, current_user=current_user, page=page, limit=limit
    )
    return SurveyResponseListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/surveys/{survey_id}/summary", response_model=SurveySummaryRead)
def get_survey_summary(
    survey_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return survey_service.get_survey_summary(db, survey_id, current_user)
