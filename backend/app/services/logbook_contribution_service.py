from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import can_access_event, can_manage_event
from app.core.security import create_access_token, decode_access_token
from app.db.session import set_rls_context
from app.models.core import User
from app.models.enums import LogbookAssignmentStatus, UserRole
from app.models.logbook import (
    LogbookAssignment, LogbookContributionEvidence,
    LogbookInstanceItem, LogbookItemContribution,
)
from app.services.file_storage_service import read_stored_file, save_bytes_file
from app.services.logbook_service import audit, ensure_logbook_editable, validate_image_content

logger = logging.getLogger(__name__)


def _context(db: Session, item_id: UUID, current):
    item = db.get(LogbookInstanceItem, item_id)
    if not item:
        raise HTTPException(404, "Actividad no encontrada")
    assignment = db.scalar(select(LogbookAssignment).where(
        LogbookAssignment.logbook_instance_id == item.instance_id,
        LogbookAssignment.user_id == current.id,
    ))
    manager = can_manage_event(current, item.instance.event_id, db)
    if not assignment and not manager:
        raise HTTPException(403, "No participa en esta bitácora")
    return item, assignment, manager


def list_items(db: Session, instance_id: UUID, current):
    items = list(db.scalars(select(LogbookInstanceItem).where(
        LogbookInstanceItem.instance_id == instance_id
    ).order_by(LogbookInstanceItem.position)).all())
    if not items:
        raise HTTPException(404, "La bitácora no usa actividades materializadas")
    _context(db, items[0].id, current)
    contributions = list(db.scalars(select(LogbookItemContribution).join(LogbookInstanceItem).where(
        LogbookInstanceItem.instance_id == instance_id,
        LogbookItemContribution.deleted_at.is_(None),
    ).order_by(LogbookItemContribution.created_at)).all())
    by_item = {}
    author_names = dict(db.execute(select(User.id, User.full_name).where(
        User.id.in_({c.author_id for c in contributions})
    )).all()) if contributions else {}
    evidence_rows = list(db.scalars(select(LogbookContributionEvidence).join(
        LogbookItemContribution, LogbookItemContribution.id == LogbookContributionEvidence.contribution_id
    ).where(LogbookItemContribution.instance_id == instance_id,
            LogbookContributionEvidence.deleted_at.is_(None))).all())
    by_contribution = {}
    for evidence in evidence_rows:
        by_contribution.setdefault(evidence.contribution_id, []).append(evidence)
    for contribution in contributions:
        by_item.setdefault(contribution.instance_item_id, []).append({
            "id": contribution.id, "instance_item_id": contribution.instance_item_id,
            "assignment_id": contribution.assignment_id, "author_id": contribution.author_id,
            "author_name": author_names.get(contribution.author_id),
            "description": contribution.description, "version": contribution.version,
            "created_at": contribution.created_at, "updated_at": contribution.updated_at,
            "evidences": by_contribution.get(contribution.id, []),
        })
    return [{"id": item.id, "instance_id": item.instance_id, "title": item.title,
             "source_row": item.source_row, "position": item.position,
             "contributions": by_item.get(item.id, [])} for item in items]


def metrics(db: Session, instance_id: UUID, current):
    items = list_items(db, instance_id, current)
    contribution_count = sum(len(item["contributions"]) for item in items)
    with_activity = sum(bool(item["contributions"]) for item in items)
    participant_ids = {c["author_id"] for item in items for c in item["contributions"]}
    evidence_count = sum(len(c["evidences"]) for item in items for c in item["contributions"])
    assigned = db.scalar(select(func.count(LogbookAssignment.id)).where(
        LogbookAssignment.logbook_instance_id == instance_id,
        LogbookAssignment.status != LogbookAssignmentStatus.CANCELLED,
    )) or 0
    return {"total_activities": len(items), "activities_without_contributions": len(items) - with_activity,
            "activities_with_contributions": with_activity, "contributions_count": contribution_count,
            "participants_assigned": assigned, "participants_contributed": len(participant_ids),
            "evidences_count": evidence_count,
            "completion_percentage": round(with_activity * 100 / len(items), 2) if items else 0.0}


def create(db: Session, item_id: UUID, payload, current):
    item, assignment, _ = _context(db, item_id, current)
    if not assignment:
        raise HTTPException(403, "Solo participantes pueden registrar aportes")
    ensure_logbook_editable(item.instance, assignment)
    contribution = LogbookItemContribution(instance_item_id=item.id, assignment_id=assignment.id,
                                            instance_id=item.instance_id,
                                            author_id=current.id, description=payload.description.strip())
    db.add(contribution)
    if assignment.status.value == "PENDING":
        assignment.status = type(assignment.status).IN_PROGRESS
        assignment.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(contribution)
    audit(db, current, "LOGBOOK_CONTRIBUTION_CREATED", "LogbookItemContribution", contribution.id,
          event_id=item.instance.event_id, new={"version": contribution.version})
    return contribution


def update(db: Session, contribution_id: UUID, payload, current):
    contribution, item, assignment = _own_contribution(db, contribution_id, current, editable=True)
    if payload.version != contribution.version:
        raise HTTPException(409, "El aporte fue modificado; recargue e intente nuevamente")
    contribution.description = payload.description.strip()
    contribution.version += 1
    db.commit()
    db.refresh(contribution)
    audit(db, current, "LOGBOOK_CONTRIBUTION_UPDATED", "LogbookItemContribution", contribution.id,
          event_id=item.instance.event_id, new={"version": contribution.version})
    return contribution


def save(db: Session, item_id: UUID, payload, current):
    """Compatibility for clients predating the contribution timeline API."""
    if payload.version is None:
        return create(db, item_id, payload, current)
    item, assignment, _ = _context(db, item_id, current)
    if not assignment:
        raise HTTPException(403, "Solo participantes pueden registrar aportes")
    contribution = db.scalar(select(LogbookItemContribution).where(
        LogbookItemContribution.instance_item_id == item.id,
        LogbookItemContribution.assignment_id == assignment.id,
        LogbookItemContribution.deleted_at.is_(None),
        LogbookItemContribution.version == payload.version,
    ).order_by(LogbookItemContribution.created_at.desc()).limit(1))
    if not contribution:
        raise HTTPException(409, "El aporte fue modificado; recargue e intente nuevamente")
    return update(db, contribution.id, payload, current)


def remove(db: Session, contribution_id: UUID, version: int, current):
    contribution = db.get(LogbookItemContribution, contribution_id)
    if not contribution or contribution.deleted_at is not None:
        raise HTTPException(404, "Aporte no encontrado")
    item, assignment, _ = _context(db, contribution.instance_item_id, current)
    if contribution.author_id != current.id or not assignment or contribution.assignment_id != assignment.id:
        raise HTTPException(403, "No puede eliminar el aporte de otro participante")
    ensure_logbook_editable(item.instance, assignment)
    if contribution.version != version:
        raise HTTPException(409, "El aporte fue modificado")
    contribution.deleted_at = datetime.now(timezone.utc)
    contribution.version += 1
    db.commit()
    audit(db, current, "LOGBOOK_CONTRIBUTION_DELETED", "LogbookItemContribution",
          contribution.id, event_id=item.instance.event_id, new={"version": contribution.version})


def _own_contribution(db, contribution_id, current, *, editable=False):
    contribution = db.get(LogbookItemContribution, contribution_id)
    if not contribution or contribution.deleted_at is not None:
        raise HTTPException(404, "Aporte no encontrado")
    item, assignment, manager = _context(db, contribution.instance_item_id, current)
    owner = bool(assignment and contribution.assignment_id == assignment.id and contribution.author_id == current.id)
    if editable:
        if not owner:
            raise HTTPException(403, "Solo el autor puede modificar evidencias del aporte")
        ensure_logbook_editable(item.instance, assignment)
    elif not owner and not manager:
        raise HTTPException(403, "No puede acceder a esta evidencia")
    return contribution, item, assignment


def upload_evidence(db: Session, contribution_id: UUID, file: UploadFile, current):
    contribution, item, assignment = _own_contribution(db, contribution_id, current, editable=True)
    current_count = db.scalar(select(func.count(LogbookContributionEvidence.id)).where(
        LogbookContributionEvidence.contribution_id == contribution.id,
        LogbookContributionEvidence.deleted_at.is_(None))) or 0
    if current_count >= 5:
        raise HTTPException(422, "Máximo de 5 evidencias alcanzado")
    content = file.file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(413, f"El archivo excede {settings.max_upload_size_mb} MB")
    mime = file.content_type or ""
    validate_image_content(content, mime)
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime]
    original = Path(file.filename or f"evidence{extension}").name[:255]
    try:
        storage_key = save_bytes_file("logbook-contributions", content, content_type=mime,
                                      allowed_content_types={mime: extension}, original_filename=original)
    except Exception as exc:
        logger.exception("Contribution evidence storage failed contribution_id=%s", contribution.id)
        raise HTTPException(503, "No se pudo almacenar la fotografía. Inténtalo nuevamente.") from exc
    evidence = LogbookContributionEvidence(
        contribution_id=contribution.id, event_id=item.instance.event_id,
        instance_id=item.instance_id, instance_item_id=item.id, assignment_id=assignment.id,
        uploaded_by=current.id, mime_type=mime, file_size=len(content),
        original_filename=original, storage_key=storage_key)
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    audit(db, current, "LOGBOOK_CONTRIBUTION_EVIDENCE_UPLOADED", "LogbookContributionEvidence",
          evidence.id, event_id=item.instance.event_id,
          metadata={"mime_type": mime, "file_size": len(content)})
    return evidence


def evidence_access(db: Session, evidence_id: UUID, current):
    evidence = db.get(LogbookContributionEvidence, evidence_id)
    if not evidence or evidence.deleted_at is not None:
        raise HTTPException(404, "Evidencia no encontrada")
    contribution, item, assignment = _own_contribution(db, evidence.contribution_id, current)
    if current.role == UserRole.CLIENT:
        raise HTTPException(403, "Evidencia privada")
    if current.role in {UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}:
        if not assignment or contribution.assignment_id != assignment.id:
            raise HTTPException(403, "Evidencia privada")
    elif not can_access_event(current, item.instance.event_id, db):
        raise HTTPException(403, "Evidencia privada")
    token = create_access_token({"scope": "logbook_contribution_evidence", "evidence_id": str(evidence.id),
                                 "actor_id": str(current.id), "actor_role": current.role.value,
                                 "actor_client_id": str(current.client_id) if current.client_id else None},
                                expires_delta=timedelta(minutes=5))
    return {"url": f"/api/v1/logbook-contribution-evidences/{evidence.id}/content?token={token}", "expires_in": 300}


def evidence_content(db: Session, evidence_id: UUID, token: str):
    try:
        payload = decode_access_token(token)
        if payload.get("scope") != "logbook_contribution_evidence" or payload.get("evidence_id") != str(evidence_id):
            raise ValueError
        actor_id, actor_role = UUID(payload["actor_id"]), UserRole(payload["actor_role"])
        actor_client = UUID(payload["actor_client_id"]) if payload.get("actor_client_id") else None
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(403, "Token de evidencia inválido") from exc
    set_rls_context(db, user_id=actor_id, role=actor_role, client_id=actor_client)
    evidence = db.get(LogbookContributionEvidence, evidence_id)
    if not evidence or evidence.deleted_at is not None:
        raise HTTPException(404, "Evidencia no encontrada")
    return (*read_stored_file(evidence.storage_key), evidence.original_filename)


def delete_evidence(db: Session, evidence_id: UUID, current):
    evidence = db.get(LogbookContributionEvidence, evidence_id)
    if not evidence or evidence.deleted_at is not None:
        raise HTTPException(404, "Evidencia no encontrada")
    _, item, _ = _own_contribution(db, evidence.contribution_id, current, editable=True)
    if evidence.uploaded_by != current.id:
        raise HTTPException(403, "Solo quien subió la evidencia puede eliminarla")
    evidence.deleted_at = datetime.now(timezone.utc)
    db.commit()
    audit(db, current, "LOGBOOK_CONTRIBUTION_EVIDENCE_DELETED", "LogbookContributionEvidence",
          evidence.id, event_id=item.instance.event_id, new={"deleted": True})
