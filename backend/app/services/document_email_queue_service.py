from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.permissions import can_view_operational_event
from app.db.session import SessionLocal, engine, set_rls_context
from app.models.documents import (
    DocumentEmailBatch,
    DocumentEmailBatchItem,
    ManagedDocument,
)
from app.models.core import Event, User
from app.models.enums import UserRole
from app.schemas.document_schema import DocumentBatchSendPair
from app.services import document_email_service, managed_documents_service

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
SEND_INTERVAL_SECONDS = 1.0
PROCESSING_LEASE = timedelta(minutes=15)
_WORKER_ADVISORY_LOCK = 741_905_228


def _access_batch(db: Session, batch: DocumentEmailBatch, user: User) -> None:
    event = db.get(Event, batch.event_id)
    if not event or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Lote no encontrado o sin acceso")


def create_batch(
    db: Session,
    *,
    batch_id: UUID,
    event_id: UUID,
    pairs: list[DocumentBatchSendPair],
    user: User,
) -> dict:
    existing = db.get(DocumentEmailBatch, batch_id)
    if existing:
        if existing.created_by != user.id:
            raise HTTPException(status_code=404, detail="Lote no encontrado")
        _access_batch(db, existing, user)
        return get_batch(db, batch_id, user)

    event = db.get(Event, event_id)
    if not event or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Faena no encontrada o sin acceso")
    if settings.app_env.lower() == "production" and not settings.resend_api_key:
        raise HTTPException(status_code=503, detail="El servicio de correo no está configurado")

    contract_ids = [pair.contract_document_id for pair in pairs]
    if len(set(contract_ids)) != len(contract_ids):
        raise HTTPException(status_code=422, detail="La selección contiene personas repetidas")

    db.add(
        DocumentEmailBatch(
            id=batch_id,
            client_id=event.client_id,
            event_id=event.id,
            created_by=user.id,
            total_count=0,
        )
    )
    db.flush()
    queued_count = 0
    for pair in pairs:
        contract = db.scalar(
            select(ManagedDocument)
            .options(joinedload(ManagedDocument.person))
            .where(ManagedDocument.id == pair.contract_document_id)
        )
        epp = db.get(ManagedDocument, pair.epp_document_id)
        if not contract or not epp:
            raise HTTPException(status_code=404, detail="No se encontraron ambos documentos de una persona")
        managed_documents_service._allowed(user, contract, db, write=True)
        managed_documents_service._allowed(user, epp, db, write=True)
        if contract.signature_method == "PAPER" or epp.signature_method == "PAPER":
            raise HTTPException(status_code=409, detail=f"{contract.person.first_name} tiene documentos reservados para firma en papel; no se enviarán electrónicamente.")
        if contract.kind != "CONTRACT" or epp.kind != "EPP":
            raise HTTPException(status_code=422, detail="Cada conjunto requiere contrato y EPP")
        if (
            contract.person_id != epp.person_id
            or contract.client_id != epp.client_id
            or contract.event_id != event_id
            or epp.event_id != event_id
            or contract.employment_id != epp.employment_id
        ):
            raise HTTPException(status_code=422, detail="Los documentos deben corresponder a la misma persona y faena seleccionada")
        if not (contract.person.email or "").strip():
            raise HTTPException(status_code=422, detail=f"{contract.person.first_name} no tiene correo registrado")
        allowed_statuses = {"DRAFT", "READY", "SENT", "VIEWED"}
        if contract.status not in allowed_statuses or epp.status not in allowed_statuses:
            raise HTTPException(status_code=409, detail=f"Los documentos de {contract.person.first_name} no están disponibles para enviar")
        for doc in (contract, epp):
            if doc.frozen_snapshot is None:
                managed_documents_service._raise_if_document_incomplete(
                    managed_documents_service._snapshot(db, doc), "enviar ambos documentos"
                )

        already_queued = db.scalar(
            select(DocumentEmailBatchItem.id).where(
                DocumentEmailBatchItem.contract_document_id == contract.id,
                DocumentEmailBatchItem.epp_document_id == epp.id,
                DocumentEmailBatchItem.status.in_(("QUEUED", "PROCESSING", "SENDING", "RETRYING")),
            )
        )
        if already_queued:
            continue
        db.add(
            DocumentEmailBatchItem(
                batch_id=batch_id,
                client_id=event.client_id,
                event_id=event.id,
                contract_document_id=contract.id,
                epp_document_id=epp.id,
                created_by=user.id,
                status="QUEUED",
                next_attempt_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        queued_count += 1

    batch = db.get(DocumentEmailBatch, batch_id)
    batch.total_count = len(pairs)
    if queued_count == 0:
        batch.status = "COMPLETED"
    batch.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return get_batch(db, batch_id, user)


def _batch_payload(item: DocumentEmailBatchItem, db: Session) -> dict:
    contract = db.scalar(
        select(ManagedDocument)
        .options(joinedload(ManagedDocument.person))
        .where(ManagedDocument.id == item.contract_document_id)
    )
    result = item.result or {}
    links = result.get("links") or []
    return {
        "id": str(item.id),
        "contract_id": str(item.contract_document_id),
        "epp_id": str(item.epp_document_id),
        "person_name": (
            f"{contract.person.first_name} {contract.person.last_name}" if contract else "Persona"
        ),
        "email": contract.person.email if contract else None,
        "status": item.status,
        "attempt_count": item.attempt_count,
        "error": item.error,
        "result": {
            "recipient": result.get("recipient"),
            "email_sent": item.status == "SENT",
            "delivery_error": item.error or result.get("delivery_error"),
            "documents": [],
            "links": links,
        } if result else None,
    }


def get_batch(db: Session, batch_id: UUID, user: User) -> dict:
    batch = db.get(DocumentEmailBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    _access_batch(db, batch, user)
    items = db.scalars(
        select(DocumentEmailBatchItem)
        .where(DocumentEmailBatchItem.batch_id == batch_id)
        .order_by(DocumentEmailBatchItem.created_at, DocumentEmailBatchItem.id)
    ).all()
    counts = {status: sum(item.status == status for item in items) for status in (
        "QUEUED", "PROCESSING", "SENDING", "RETRYING", "SENT", "PREPARED", "FAILED"
    )}
    active = counts["QUEUED"] + counts["PROCESSING"] + counts["SENDING"] + counts["RETRYING"]
    failed = counts["FAILED"]
    if active:
        batch.status = "PROCESSING" if counts["PROCESSING"] or counts["SENDING"] else "QUEUED"
    elif failed:
        batch.status = "COMPLETED_WITH_ERRORS"
    else:
        batch.status = "COMPLETED"
    batch.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return {
        "id": str(batch.id),
        "event_id": str(batch.event_id),
        "status": batch.status,
        "total": len(items),
        "queued": counts["QUEUED"] + counts["RETRYING"],
        "processing": counts["PROCESSING"] + counts["SENDING"],
        "sent": counts["SENT"],
        "prepared": counts["PREPARED"],
        "failed": failed,
        "skipped": max(batch.total_count - len(items), 0),
        "created_at": batch.created_at.isoformat(),
        "items": [_batch_payload(item, db) for item in items],
    }


def retry_failed(db: Session, batch_id: UUID, item_ids: list[UUID], user: User) -> dict:
    batch = db.get(DocumentEmailBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    _access_batch(db, batch, user)
    rows = db.scalars(
        select(DocumentEmailBatchItem).where(
            DocumentEmailBatchItem.batch_id == batch_id,
            DocumentEmailBatchItem.id.in_(item_ids),
            DocumentEmailBatchItem.status == "FAILED",
        )
    ).all()
    for item in rows:
        item.status = "QUEUED" if item.delivery_payload is None else "RETRYING"
        item.attempt_count = 0
        item.next_attempt_at = datetime.now(UTC).replace(tzinfo=None)
        item.locked_at = None
        item.error = None
    batch.status = "QUEUED" if rows else batch.status
    batch.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return get_batch(db, batch_id, user)


def _store_failure(db: Session, item: DocumentEmailBatchItem, error: str, *, retryable: bool) -> None:
    item.error = error[:2000]
    item.locked_at = None
    if retryable and item.attempt_count < MAX_ATTEMPTS:
        item.status = "RETRYING"
        item.next_attempt_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            seconds=min(30 * (2 ** max(item.attempt_count - 1, 0)), 900)
        )
    else:
        item.status = "FAILED"
    item.updated_at = datetime.now(UTC).replace(tzinfo=None)


def process_next_item() -> bool:
    """Claim one durable queue item. A PostgreSQL advisory lock serializes all app instances."""
    db = SessionLocal()
    lock_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    lock_acquired = False
    try:
        set_rls_context(db, user_id=UUID(int=0), role=UserRole.SUPER_ADMIN)
        lock_acquired = bool(lock_connection.scalar(select(func.pg_try_advisory_lock(_WORKER_ADVISORY_LOCK))))
        if not lock_acquired:
            return False
        try:
            now = datetime.now(UTC).replace(tzinfo=None)
            item = db.scalar(
                select(DocumentEmailBatchItem)
                .where(
                    or_(
                        (
                            DocumentEmailBatchItem.status.in_(("QUEUED", "RETRYING"))
                            & (DocumentEmailBatchItem.next_attempt_at <= now)
                        ),
                        (
                            DocumentEmailBatchItem.status.in_(("PROCESSING", "SENDING"))
                            & (DocumentEmailBatchItem.locked_at <= now - PROCESSING_LEASE)
                        ),
                    )
                )
                .order_by(DocumentEmailBatchItem.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if item is None:
                return False
            item.status = "SENDING" if item.delivery_payload else "PROCESSING"
            item.attempt_count += 1
            item.locked_at = now
            item.updated_at = now
            db.commit()
            item_id = item.id
            created_by = item.created_by
            contract_id = item.contract_document_id
            epp_id = item.epp_document_id
            delivery_payload = item.delivery_payload

            actor = db.get(User, created_by)
            if not actor or not actor.is_active:
                current = db.get(DocumentEmailBatchItem, item_id)
                _store_failure(db, current, "El usuario que inició el lote ya no está activo.", retryable=False)
                db.commit()
                return True
            set_rls_context(db, user_id=actor.id, role=actor.role, client_id=actor.client_id)

            if delivery_payload:
                if (
                    settings.app_env.lower() != "production"
                    and not settings.documents_allow_local_emails
                ):
                    item.status = "PREPARED"
                    item.error = "Correo real deshabilitado en este entorno; el enlace quedó preparado."
                    item.result = {**(item.result or {}), "delivery_error": item.error}
                    item.delivery_payload = None
                    item.locked_at = None
                    item.updated_at = datetime.now(UTC).replace(tzinfo=None)
                    db.commit()
                    return True
                if not settings.resend_api_key:
                    _store_failure(db, item, "RESEND_API_KEY no está configurada.", retryable=True)
                    db.commit()
                    return True
                try:
                    document_email_service.send_document_pair_email(
                        **delivery_payload, idempotency_key=f"document-batch/{item_id}"
                    )
                    item.status = "SENT"
                    item.error = None
                    item.result = {**(item.result or {}), "email_sent": True}
                    item.delivery_payload = None
                    item.locked_at = None
                    item.updated_at = datetime.now(UTC).replace(tzinfo=None)
                    db.commit()
                except Exception as exc:
                    logger.warning("Document email batch delivery attempt failed (%s)", type(exc).__name__)
                    retryable = not isinstance(exc, HTTPException) or exc.status_code >= 500
                    _store_failure(db, item, "Resend no confirmó el correo; se reintentará automáticamente." if retryable else "Resend rechazó el correo; revisa el destinatario y la configuración.", retryable=retryable)
                    db.commit()
                return True

            result = managed_documents_service.send_documents_together(
                db, contract_id, epp_id, actor, send_email=False
            )
            links = [
                {"url": link["url"], "expires_at": link["expires_at"].isoformat()}
                for link in result["links"]
            ]
            item.result = {
                "recipient": result["recipient"],
                "links": links,
                "delivery_error": None,
            }
            item.delivery_payload = result["delivery_payload"]
            item.status = "RETRYING"
            item.locked_at = None
            item.next_attempt_at = datetime.now(UTC).replace(tzinfo=None)
            item.updated_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
            return True
        except HTTPException as exc:
            if "item_id" in locals():
                item = db.get(DocumentEmailBatchItem, item_id)
                if item:
                    _store_failure(db, item, str(exc.detail), retryable=exc.status_code >= 500)
                    db.commit()
                    return True
            raise
        except Exception as exc:
            logger.exception("Document email queue worker failed")
            if "item_id" in locals():
                item = db.get(DocumentEmailBatchItem, item_id)
                if item:
                    retryable = not isinstance(exc, HTTPException) or exc.status_code >= 500
                    _store_failure(db, item, "Error inesperado procesando el envío; se reintentará automáticamente.", retryable=retryable)
                    db.commit()
                    return True
            raise
        finally:
            pass
    finally:
        if lock_acquired:
            try:
                lock_connection.scalar(select(func.pg_advisory_unlock(_WORKER_ADVISORY_LOCK)))
            finally:
                lock_connection.close()
        else:
            lock_connection.close()
        db.close()


def queue_worker_loop(stop_event) -> None:
    while not stop_event.is_set():
        worked = False
        try:
            worked = process_next_item()
        except Exception:
            logger.exception("Document email queue polling failed")
        stop_event.wait(SEND_INTERVAL_SECONDS if worked else 2.0)
