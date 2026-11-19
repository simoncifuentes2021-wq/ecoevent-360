from __future__ import annotations

import csv
import hashlib
import io
import logging
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.rate_limit import enforce
from app.db.session import SessionLocal, get_db, set_public_volunteer_context, set_rls_context
from app.models.core import Evidence, User
from app.models.enums import UserRole
from app.models.volunteers import MaterialContribution, RecyclingActivation, Volunteer
from app.schemas.volunteer_schema import (
    ContributionCreate,
    ContributionListRead,
    ContributionRead,
    ContributionUpdate,
    ContributionVoid,
    PublicActivationRead,
    PublicVolunteerImpactRead,
    PublicVolunteerRegistration,
    PublicVolunteerRegistrationRead,
    VolunteerActivationCreate,
    VolunteerActivationRead,
    VolunteerActivationUpdate,
    VolunteerDashboardRead,
    VolunteerImpactRead,
    VolunteerListResponse,
    VolunteerRead,
    VolunteerManualCreate,
    VolunteerResolveRead,
    VolunteerUpdate,
)
from app.schemas.waste_schema import WasteTypeRead
from app.services import volunteer_service as service
from app.services.audit_log_service import create_audit_log
from app.services.file_storage_service import delete_stored_file, read_stored_file, save_evidence_file
from app.services.volunteer_email_service import send_contribution_email, send_registration_email
from app.utils.simple_qr import make_qr_png

logger = logging.getLogger(__name__)
router = APIRouter(tags=["volunteers and recycling activations"])
public_router = APIRouter(prefix="/public/volunteer-activations", tags=["public volunteers"])
public_history_router = APIRouter(prefix="/public/volunteer-impact", tags=["public volunteer impact"])


def _email_contribution_job(
    contribution_id: UUID,
    context: dict,
    user_id: UUID,
    user_role: UserRole,
    client_id: UUID | None,
) -> None:
    sent, error = send_contribution_email(context)
    try:
        with SessionLocal() as db:
            set_rls_context(db, user_id=user_id, role=user_role, client_id=client_id)
            service.mark_contribution_email(db, contribution_id, sent=sent, error=error)
    except Exception:
        logger.exception("volunteer_contribution_email_status_update_failed")


def _registration_email_job(context: dict) -> None:
    send_registration_email(context)


def _activation_read(activation, event_name: str) -> dict:
    return {
        "id": activation.id,
        "event_id": activation.event_id,
        "session_id": activation.session_id,
        "event_name": event_name,
        "name": activation.name,
        "description": activation.description,
        "location_name": activation.location_name,
        "address": activation.address,
        "starts_at": activation.starts_at,
        "ends_at": activation.ends_at,
        "responsible_user_id": activation.responsible_user_id,
        "status": activation.status,
        "capacity": activation.capacity,
        "public_slug": activation.public_slug,
        "created_at": activation.created_at,
        "updated_at": activation.updated_at,
        "allowed_material_ids": [material.id for material in activation.allowed_materials],
    }


@router.get("/events/{event_id}/recycling-activations", response_model=list[VolunteerActivationRead])
def list_activations(
    event_id: UUID,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(DRAFT|ACTIVE|CLOSED|CANCELLED|ARCHIVED)$"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return service.list_activations(db, user, event_id=event_id, activation_status=status_filter, date_from=date_from, date_to=date_to)


@router.post("/events/{event_id}/recycling-activations", response_model=VolunteerActivationRead, status_code=status.HTTP_201_CREATED)
def create_activation(
    event_id: UUID,
    payload: VolunteerActivationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    if event_id != payload.event_id:
        raise HTTPException(status_code=400, detail="El evento de la ruta no coincide con el formulario")
    activation = service.create_activation(db, payload, user)
    event_name = service._require_event_access(db, user, event_id).name
    create_audit_log(db, user=user, action="CREATE", module="volunteers", entity_type="RecyclingActivation", entity_id=activation.id, event_id=event_id, new_data={"name": activation.name, "status": activation.status}, request=request)
    return _activation_read(activation, event_name)


@router.patch("/recycling-activations/{activation_id}", response_model=VolunteerActivationRead)
def update_activation(
    activation_id: UUID,
    payload: VolunteerActivationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    activation = service._activation_or_404(db, activation_id)
    old_data = {"name": activation.name, "status": activation.status, "starts_at": activation.starts_at}
    updated = service.update_activation(db, activation_id, payload, user)
    event_name = service._require_event_access(db, user, updated.event_id).name
    create_audit_log(db, user=user, action="UPDATE", module="volunteers", entity_type="RecyclingActivation", entity_id=activation_id, event_id=updated.event_id, old_data=old_data, new_data=payload.model_dump(exclude_unset=True, mode="json"), request=request)
    result = _activation_read(updated, event_name)
    counts = service.list_activations(db, user, event_id=updated.event_id, activation_status=None, date_from=None, date_to=None)
    return next((row for row in counts if row["id"] == updated.id), result)


@router.get("/events/{event_id}/waste-types", response_model=list[WasteTypeRead])
@router.get("/events/{event_id}/recyclable-materials", response_model=list[WasteTypeRead], include_in_schema=False)
def list_materials(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    service._require_event_access(db, user, event_id)
    if not (service._can_manage(user, event_id, db) or service._can_record(user, event_id, db)):
        raise HTTPException(status_code=403, detail="No tienes permiso para ver los materiales")
    return service.list_materials(db)


@router.get("/events/{event_id}/volunteers", response_model=VolunteerListResponse)
def list_volunteers(
    event_id: UUID,
    activation_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=180),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(ACTIVE|INACTIVE|ARCHIVED)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    items, total = service.list_volunteers(db, user, event_id=event_id, activation_id=activation_id, search=search, volunteer_status=status_filter, date_from=date_from, date_to=date_to, page=page, limit=limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.patch("/events/{event_id}/volunteers/{volunteer_id}", response_model=VolunteerRead)
def update_volunteer(
    event_id: UUID,
    volunteer_id: UUID,
    payload: VolunteerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    before = db.get(Volunteer, volunteer_id)
    old_data = {"full_name": before.full_name, "email": before.email, "phone": before.phone, "status": before.status} if before else None
    volunteer = service.update_volunteer(db, volunteer_id, payload, user, event_id)
    create_audit_log(db, user=user, action="UPDATE", module="volunteers", entity_type="Volunteer", entity_id=volunteer.id, event_id=event_id, old_data=old_data, new_data={key: value for key, value in payload.model_dump(exclude_unset=True, mode="json").items() if key != "email"}, request=request)
    return volunteer


@router.get("/events/{event_id}/volunteers/{volunteer_id}/impact", response_model=VolunteerImpactRead)
def get_volunteer_impact(
    event_id: UUID,
    volunteer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return service.volunteer_impact(db, volunteer_id, user, event_id=event_id)


@router.get("/recycling-activations/{activation_id}/volunteers/lookup", response_model=VolunteerResolveRead | None)
def lookup_volunteer(
    activation_id: UUID,
    q: str = Query(min_length=3, max_length=254),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return service.lookup_volunteer_for_activation(db, activation_id, q, user)


@router.post("/recycling-activations/{activation_id}/volunteers", response_model=VolunteerResolveRead, status_code=status.HTTP_201_CREATED)
def create_or_register_volunteer(
    activation_id: UUID,
    payload: VolunteerManualCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    volunteer, already_in_activation = service.create_staff_volunteer(db, activation_id, payload, user)
    activation = service._activation_or_404(db, activation_id)
    total_in_event = db.scalar(select(func.coalesce(func.sum(MaterialContribution.total_weight_kg), 0)).join(
        RecyclingActivation,
        RecyclingActivation.id == MaterialContribution.activation_id,
    ).where(MaterialContribution.volunteer_id == volunteer.id,
             MaterialContribution.status == "ACTIVE",
             RecyclingActivation.event_id == activation.event_id)) or 0
    create_audit_log(db, user=user, action="REGISTER", module="volunteers", entity_type="Volunteer", entity_id=volunteer.id, event_id=activation.event_id, metadata={"activation_id": str(activation_id), "consent_version": volunteer.consent_version}, request=request)
    return {"id": volunteer.id, "full_name": volunteer.full_name, "unique_code": volunteer.unique_code, "already_in_activation": already_in_activation, "total_weight_kg_in_event": total_in_event}


@router.get("/events/{event_id}/recycling-dashboard", response_model=VolunteerDashboardRead)
def get_dashboard(
    event_id: UUID,
    activation_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return service.dashboard(db, user, event_id=event_id, activation_id=activation_id, date_from=date_from, date_to=date_to)


@router.get("/events/{event_id}/recycling-impact")
def get_event_impact(
    event_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return service.event_impact(db, user, event_id, date_from=date_from, date_to=date_to)


@router.get("/events/{event_id}/contributions", response_model=ContributionListRead)
def list_contributions(
    event_id: UUID,
    activation_id: UUID | None = None,
    volunteer_id: UUID | None = None,
    material_id: UUID | None = None,
    registered_by: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(ACTIVE|VOID)$"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    items, total = service.list_contributions(db, user, event_id=event_id, activation_id=activation_id, volunteer_id=volunteer_id, material_id=material_id, registered_by=registered_by, status_filter=status_filter, date_from=date_from, date_to=date_to, page=page, limit=limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/recycling-activations/{activation_id}/contributions", response_model=ContributionRead, status_code=status.HTTP_201_CREATED)
def create_contribution(
    activation_id: UUID,
    payload: ContributionCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    contribution, impact_url, created = service.create_contribution(db, activation_id, payload, user)
    if created and impact_url and contribution.email_status == "PENDING":
        context = service.contribution_email_context(db, contribution, impact_url)
        background_tasks.add_task(_email_contribution_job, contribution.id, context, user.id, user.role, user.client_id)
    create_audit_log(db, user=user, action="CREATE", module="volunteers", entity_type="MaterialContribution", entity_id=contribution.id, event_id=contribution.activation.event_id, new_data={"total_weight_kg": str(contribution.total_weight_kg), "item_count": len(contribution.items), "status": contribution.status}, request=request)
    return service.serialize_contribution(db, service.get_contribution(db, contribution.id, user), user)


@router.get("/contributions/{contribution_id}", response_model=ContributionRead)
def get_contribution(
    contribution_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    contribution = service.get_contribution(db, contribution_id, user)
    return service.serialize_contribution(db, contribution, user)


@router.put("/contributions/{contribution_id}", response_model=ContributionRead)
def update_contribution(
    contribution_id: UUID,
    payload: ContributionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    contribution, before = service.update_contribution(db, contribution_id, payload, user)
    create_audit_log(db, user=user, action="UPDATE", module="volunteers", entity_type="MaterialContribution", entity_id=contribution.id, event_id=contribution.activation.event_id, old_data=before, new_data={"items": payload.model_dump(mode="json")["items"], "notes": payload.notes}, request=request)
    return service.serialize_contribution(db, service.get_contribution(db, contribution.id, user), user)


@router.post("/contributions/{contribution_id}/void", response_model=ContributionRead)
def void_contribution(
    contribution_id: UUID,
    payload: ContributionVoid,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    contribution = service.void_contribution(db, contribution_id, payload.reason, user)
    create_audit_log(db, user=user, action="VOID", module="volunteers", entity_type="MaterialContribution", entity_id=contribution.id, event_id=contribution.activation.event_id, new_data={"reason": payload.reason, "total_weight_kg": str(contribution.total_weight_kg)}, request=request)
    return service.serialize_contribution(db, service.get_contribution(db, contribution.id, user), user)


@router.post("/contributions/{contribution_id}/evidence", status_code=status.HTTP_201_CREATED)
def upload_contribution_evidence(
    contribution_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    description: str | None = Form(default=None, max_length=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    contribution = service.get_contribution(db, contribution_id, user)
    if contribution.status != "ACTIVE" or not service._can_record(user, contribution.activation.event_id, db):
        raise HTTPException(status_code=403, detail="No puedes agregar evidencia a esta entrega")
    file_url, file_type = save_evidence_file(file)
    evidence = Evidence(
        event_id=contribution.activation.event_id,
        uploaded_by=user.id,
        file_url=file_url,
        file_type=file_type,
        description=description,
        volunteer_contribution_id=contribution.id,
    )
    db.add(evidence)
    try:
        db.commit()
        db.refresh(evidence)
    except Exception:
        db.rollback()
        delete_stored_file(file_url)
        logger.exception("volunteer_contribution_evidence_metadata_failed")
        raise HTTPException(status_code=500, detail="No pudimos guardar la evidencia. Inténtalo nuevamente.")
    create_audit_log(db, user=user, action="CREATE", module="volunteers", entity_type="Evidence", entity_id=evidence.id, event_id=evidence.event_id, new_data={"contribution_id": contribution.id, "file_type": file_type}, request=request)
    return {"id": evidence.id, "description": evidence.description, "file_type": evidence.file_type, "created_at": evidence.created_at}


@router.get("/contributions/{contribution_id}/evidence")
def list_contribution_evidence(
    contribution_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    service.get_contribution(db, contribution_id, user)
    rows = db.scalars(select(Evidence).where(Evidence.volunteer_contribution_id == contribution_id).order_by(Evidence.created_at.desc())).all()
    return [{"id": row.id, "description": row.description, "file_type": row.file_type, "created_at": row.created_at} for row in rows]


@router.get("/contributions/{contribution_id}/evidence/{evidence_id}/file")
def download_contribution_evidence(
    contribution_id: UUID,
    evidence_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    service.get_contribution(db, contribution_id, user)
    evidence = db.scalar(select(Evidence).where(Evidence.id == evidence_id, Evidence.volunteer_contribution_id == contribution_id))
    if evidence is None:
        raise HTTPException(status_code=404, detail="No encontramos la evidencia")
    content, mime = read_stored_file(evidence.file_url)
    return Response(content=content, media_type=mime, headers={"Content-Disposition": "inline", "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/events/{event_id}/volunteer-contributions.csv")
def export_contributions_csv(
    event_id: UUID,
    activation_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    rows, total = service.list_contributions(db, user, event_id=event_id, activation_id=activation_id, volunteer_id=None, material_id=None, registered_by=None, status_filter="ACTIVE", date_from=date_from, date_to=date_to, page=1, limit=100)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    include_email = user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPERVISOR}
    writer.writerow(["Fecha", "Voluntario", "Correo", "Código", "Activación", "Material", "Peso kg", "Total entrega kg", "Encargado", "Estado"])
    pages = (total + 99) // 100
    for page in range(1, pages + 1):
        current, _ = (rows, total) if page == 1 else service.list_contributions(db, user, event_id=event_id, activation_id=activation_id, volunteer_id=None, material_id=None, registered_by=None, status_filter="ACTIVE", date_from=date_from, date_to=date_to, page=page, limit=100)
        for contribution in current:
            for item in contribution["items"]:
                writer.writerow([contribution["registered_at"].isoformat(), contribution["volunteer_name"], contribution["volunteer_email"] if include_email else "", contribution["volunteer_code"], contribution["activation_name"], item.material_name_snapshot, str(item.weight_kg), str(contribution["total_weight_kg"]), contribution["registered_by_name"] or "", contribution["status"]])
    filename = f"aportes-reciclaje-{event_id}.csv"
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/recycling-activations/{activation_id}/qr.png")
def get_activation_qr(
    activation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    activation = service._activation_or_404(db, activation_id)
    if not (service._can_manage(user, activation.event_id, db) or service._can_record(user, activation.event_id, db)):
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este código QR")
    url = f"{service._public_base_url()}/public/inscripcion-voluntarios/{activation.public_slug}"
    return Response(content=make_qr_png(url), media_type="image/png", headers={"Cache-Control": "private, no-store"})


@public_router.get("/{slug}", response_model=PublicActivationRead)
def public_activation(slug: str, request: Request, db: Session = Depends(get_db)):
    enforce(request, "volunteer-activation-read", slug, settings.rate_limit_public_read)
    set_public_volunteer_context(db, activation_slug=slug)
    activation, event = service.get_public_activation(db, slug)
    return {"name": activation.name, "description": activation.description, "event_name": event.name, "location_name": activation.location_name, "address": activation.address, "starts_at": activation.starts_at, "ends_at": activation.ends_at, "status": activation.status, "consent_text": service.CONSENT_TEXT, "consent_version": service.CONSENT_VERSION}


@public_router.post("/{slug}/register", response_model=PublicVolunteerRegistrationRead, status_code=status.HTTP_201_CREATED)
def register_volunteer(
    slug: str,
    payload: PublicVolunteerRegistration,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if slug != payload.activation_slug:
        raise HTTPException(status_code=400, detail="La activación de la ruta no coincide con el formulario")
    enforce(request, "volunteer-register", slug, settings.rate_limit_public_submit)
    email_hash = service.email_lookup_hash(str(payload.email))
    set_public_volunteer_context(db, activation_slug=slug, email_hash=email_hash)
    volunteer, activation, _already_registered, impact_url = service.register_public_volunteer(db, payload)
    if settings.resend_api_key:
        background_tasks.add_task(_registration_email_job, {
            "recipient": volunteer.email,
            "volunteer_name": volunteer.full_name,
            "activation_name": activation.name,
            "event_name": activation.event.name,
            "volunteer_code": volunteer.unique_code,
            "impact_url": impact_url,
        })
    return {
        "activation_name": activation.name,
        "message": "Recibimos tu inscripción. Si el correo está habilitado, recibirás allí la confirmación y el enlace privado a tu historial.",
    }


@public_history_router.get("/{token}", response_model=PublicVolunteerImpactRead)
def public_volunteer_impact(token: str, request: Request, db: Session = Depends(get_db)):
    enforce(request, "volunteer-impact-read", token, settings.rate_limit_public_read)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    set_public_volunteer_context(db, token_hash=token_hash)
    return service.public_impact(db, token)


@public_history_router.get("/{token}/evidence/{evidence_id}/file")
def public_volunteer_evidence(token: str, evidence_id: UUID, request: Request, db: Session = Depends(get_db)):
    enforce(request, "volunteer-impact-read", token, settings.rate_limit_public_read)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    set_public_volunteer_context(db, token_hash=token_hash)
    evidence = service.public_contribution_evidence(db, token, evidence_id)
    content, mime = read_stored_file(evidence.file_url)
    return Response(content=content, media_type=mime, headers={"Content-Disposition": "inline", "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
