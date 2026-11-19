from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.api.deps_field_staff import get_current_field_staff, get_ready_field_staff
from app.core.config import settings
from app.core.rate_limit import enforce
from app.db.session import SessionLocal, get_db, set_field_staff_context, set_public_volunteer_context
from app.models.core import Evidence, User
from app.models.volunteers import FieldStaff, RecyclingActivation, Volunteer
from app.schemas.volunteer_schema import (
    ContributionCreate,
    FieldStaffCreate,
    FieldStaffLogin,
    FieldStaffPasswordChange,
    FieldStaffPortalUpdate,
    FieldStaffUpdate,
    FieldStaffVolunteerRegistration,
)
from app.services import volunteer_field_staff_service as service
from app.services import volunteer_service
from app.services.audit_log_service import create_audit_log
from app.services.file_storage_service import delete_stored_file, save_evidence_file
from app.services.volunteer_email_service import send_contribution_email, send_registration_email

logger = logging.getLogger(__name__)
router = APIRouter(tags=["volunteer field staff"])


def _field_contribution_email_job(contribution_id: UUID, context: dict, staff_id: UUID, event_id: UUID, activation_id: UUID) -> None:
    sent, error = send_contribution_email(context)
    try:
        with SessionLocal() as db:
            set_field_staff_context(db, field_staff_id=staff_id, event_id=event_id, activation_id=activation_id)
            token_hash = context["token_hash"]
            set_public_volunteer_context(db, token_hash=token_hash)
            volunteer_service.mark_contribution_email(db, contribution_id, sent=sent, error=error)
    except Exception:
        logger.exception("field_staff_contribution_email_status_update_failed")


def _field_registration_email_job(context: dict) -> None:
    sent, error = send_registration_email(context)
    if not sent:
        logger.warning("field_staff_registration_email_failed reason=%s", error)


@router.get("/events/{event_id}/field-staff")
def list_field_staff(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.list_field_staff(db, event_id, user)


@router.get("/events/{event_id}/field-staff-portal")
def get_field_staff_portal_status(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return service.get_field_staff_portal_status(db, event_id, user)


@router.patch("/events/{event_id}/field-staff-portal")
def update_field_staff_portal_status(
    event_id: UUID,
    payload: FieldStaffPortalUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    previous = service.get_field_staff_portal_status(db, event_id, user)
    updated = service.update_field_staff_portal_status(
        db, event_id, enabled=payload.enabled, user=user
    )
    if previous["enabled"] != updated["enabled"]:
        create_audit_log(
            db,
            user=user,
            action="UPDATE",
            module="volunteers",
            entity_type="FieldStaffPortal",
            entity_id=event_id,
            event_id=event_id,
            old_data={"enabled": previous["enabled"]},
            new_data={"enabled": updated["enabled"]},
            request=request,
        )
    return updated


@router.post("/events/{event_id}/field-staff", status_code=201)
def create_field_staff(event_id: UUID, payload: FieldStaffCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.create_field_staff(db, event_id, payload, user)


@router.patch("/field-staff/{staff_id}")
def update_field_staff(staff_id: UUID, payload: FieldStaffUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.update_field_staff(db, staff_id, payload, user)


@router.post("/field-staff/{staff_id}/reset-password")
def reset_field_staff_password(staff_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.reset_field_staff_password(db, staff_id, user)


@router.post("/public/field-staff/login")
def login_field_staff(payload: FieldStaffLogin, request: Request, db: Session = Depends(get_db)):
    enforce(request, "volunteer-field-staff-login", str(payload.event_id), settings.rate_limit_public_submit)
    return service.login_field_staff(db, payload)


@router.get("/field-staff/me")
def get_field_staff_me(staff: FieldStaff = Depends(get_current_field_staff)):
    return service._staff_read(staff)


@router.post("/field-staff/me/password", status_code=204)
def change_field_staff_password(payload: FieldStaffPasswordChange, db: Session = Depends(get_db), staff: FieldStaff = Depends(get_current_field_staff)):
    service.change_field_staff_password(db, staff, payload.new_password)


@router.get("/field-staff/me/activations")
def list_my_activations(db: Session = Depends(get_db), staff: FieldStaff = Depends(get_ready_field_staff)):
    return service.current_staff_activations(db, staff)


@router.get("/field-staff/me/volunteers")
def search_my_event_volunteers(q: str, db: Session = Depends(get_db), staff: FieldStaff = Depends(get_ready_field_staff)):
    return service.search_event_volunteers(db, staff, q)


@router.get("/field-staff/me/volunteers/{volunteer_id}/history")
def get_volunteer_history(volunteer_id: UUID, db: Session = Depends(get_db), staff: FieldStaff = Depends(get_ready_field_staff)):
    return service.field_staff_volunteer_history(db, staff, volunteer_id)


@router.post("/field-staff/me/activations/{activation_id}/volunteers", status_code=201)
def register_volunteer(
    activation_id: UUID,
    payload: FieldStaffVolunteerRegistration,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    staff: FieldStaff = Depends(get_ready_field_staff),
):
    result = service.register_volunteer_at_activation(db, staff, activation_id, payload)
    email_status = "already_registered" if result["already_in_activation"] else "not_configured"
    if not result["already_in_activation"]:
        set_field_staff_context(
            db, field_staff_id=staff.id, event_id=staff.event_id, activation_id=activation_id
        )
        volunteer = db.get(Volunteer, result["id"])
        activation = db.scalar(
            select(RecyclingActivation)
            .options(selectinload(RecyclingActivation.event))
            .where(RecyclingActivation.id == activation_id)
        )
        if volunteer is None or not volunteer.email:
            email_status = "no_email"
        elif settings.resend_api_key and activation is not None:
            set_public_volunteer_context(db, email_hash=volunteer.email_lookup_hash)
            impact_url = volunteer_service._issue_access_token(db, volunteer.id)
            background_tasks.add_task(
                _field_registration_email_job,
                {
                    "recipient": volunteer.email,
                    "volunteer_name": volunteer.full_name,
                    "activation_name": activation.name,
                    "event_name": activation.event.name,
                    "volunteer_code": volunteer.unique_code,
                    "impact_url": impact_url,
                },
            )
            email_status = "queued"
    return {**result, "email_status": email_status}


@router.post("/field-staff/me/activations/{activation_id}/contributions", status_code=201)
def register_contribution(
    activation_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    payload_json: str = Form(..., alias="payload"),
    file: UploadFile = File(...),
    description: str | None = Form(default="Foto de evidencia del aporte", max_length=500),
    db: Session = Depends(get_db),
    staff: FieldStaff = Depends(get_ready_field_staff),
):
    try:
        payload = ContributionCreate.model_validate_json(payload_json)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Los datos del aporte no son válidos") from exc

    contribution, _impact_url, created = service.field_staff_contribution(
        db, staff, activation_id, payload, commit=False
    )
    if not created:
        db.rollback()
        return {
            "contribution_id": contribution.id,
            "total_weight_kg": contribution.total_weight_kg,
            "evidence_attached": True,
            "email_status": "already_processed",
            "duplicate": True,
        }

    file_url = None
    try:
        file_url, file_type = save_evidence_file(file)
        evidence = Evidence(
            event_id=staff.event_id,
            uploaded_by=None,
            file_url=file_url,
            file_type=file_type,
            description=(description or "Foto de evidencia del aporte").strip(),
            volunteer_contribution_id=contribution.id,
        )
        db.add(evidence)
        db.commit()
        db.refresh(contribution)
        db.refresh(evidence)
    except Exception as exc:
        db.rollback()
        if file_url:
            delete_stored_file(file_url)
        if isinstance(exc, HTTPException):
            raise
        logger.exception("field_staff_contribution_evidence_save_failed")
        raise HTTPException(status_code=500, detail="No pudimos guardar el aporte y su evidencia. Inténtalo nuevamente.") from exc

    impact_url = None
    email_status = "no_email" if not contribution.volunteer.email else "not_configured"
    if contribution.volunteer.email and settings.resend_api_key:
        set_public_volunteer_context(db, email_hash=contribution.volunteer.email_lookup_hash)
        impact_url = volunteer_service._issue_access_token(db, contribution.volunteer_id)
        email_status = "queued"
    if impact_url and settings.resend_api_key:
        context = volunteer_service.contribution_email_context(db, contribution, impact_url)
        context["token_hash"] = contribution.volunteer.email_lookup_hash
        background_tasks.add_task(
            _field_contribution_email_job,
            contribution.id,
            context,
            staff.id,
            staff.event_id,
            activation_id,
        )
    return {
        "contribution_id": contribution.id,
        "total_weight_kg": contribution.total_weight_kg,
        "evidence_id": evidence.id,
        "evidence_attached": True,
        "email_queued": bool(impact_url and settings.resend_api_key),
        "email_status": email_status,
        "duplicate": False,
    }
