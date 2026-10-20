from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from io import BytesIO
from decimal import Decimal, InvalidOperation
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import qrcode
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.permissions import can_manage_event, can_view_operational_event
from app.db.session import set_public_document_context
from app.models.core import Event, User
from app.models.documents import (
    DocumentEmployment,
    DocumentContractDefaults,
    EventEppTemplate,
    DocumentPerson,
    DocumentSignatureRequest,
    EppDelivery,
    EppDeliveryItem,
    ManagedDocument,
)
from app.models.enums import UserRole
from app.schemas.document_schema import (
    DocumentCreate,
    DocumentContractDefaults as DocumentContractDefaultsSchema,
    EventEppTemplateUpdate,
    DocumentUpdate,
    EppInput,
    EppWorkerAcknowledgement,
    RepresentativeSignatureSave as RepresentativeSignatureSaveSchema,
)
from app.services.document_email_service import (
    send_document_pair_email,
    send_document_signature_link_email,
    send_signed_document_bundle_email,
    send_signed_document_copy_email,
)
from app.services.document_people_service import normalize_person_name, normalize_rut
from app.services.document_storage_service import document_storage
from app.services.document_template_service import render_document_html
from app.services.report_pdf_service import render_html
from app.services.signature_provider import signature_provider

EPP_CATALOG = (
    ("JOCKEY", "Jockey"),
    ("GLOVES", "Guantes"),
    ("UV_SHIRT", "Polera con filtro UV"),
    ("REFLECTIVE_VEST", "Chaleco reflectante"),
    ("GOGGLES", "Antiparras"),
    ("SUNSCREEN", "Bloqueador solar"),
    ("WATER", "Agua"),
    ("EAR_PROTECTION", "Protectores auditivos"),
)
TOKEN_TTL_DAYS = 7
MAX_DOCUMENT_DATA_BYTES = 80_000
logger = logging.getLogger(__name__)
CONTRACT_DEFAULTS_KEY = "GREENWAY"
SIGNATURE_NOTICE = (
    "Firma dibujada en pantalla y asociada al documento y su historial. "
    "No es una firma electrónica avanzada ni incluye certificación de un proveedor."
)
ELECTRONIC_CONSENT_VERSION = "greenway-electronic-documents-v1"


def _electronic_consent_text(doc: ManagedDocument, email: str) -> str:
    return (
        f"Acepto expresamente que el documento «{doc.title}» se gestione y remita por medios "
        "electrónicos y que mi firma se registre mediante el trazo dibujado en pantalla. "
        "Entiendo que este método no es una firma electrónica avanzada ni está certificado "
        "por un proveedor. Solicito que la copia final firmada se envíe a mi correo "
        f"personal registrado: {email}. Entiendo que puedo solicitar la modalidad en papel "
        "si no acepto este procedimiento."
    )


def _clean_signature_png(data_url: str) -> str:
    header, separator, encoded = data_url.partition(",")
    if not separator or header != "data:image/png;base64" or len(encoded) > 160_000:
        raise HTTPException(status_code=422, detail="La firma debe ser un dibujo PNG válido")
    try:
        raw = base64.b64decode(encoded, validate=True)
        with Image.open(BytesIO(raw)) as image:
            if image.format != "PNG" or image.width < 20 or image.height < 10 or image.width > 2400 or image.height > 1200:
                raise ValueError("Invalid signature dimensions or format")
            image.load()
            rgba = image.convert("RGBA")
            if rgba.getchannel("A").getbbox() is None:
                raise ValueError("Empty signature image")
            output = BytesIO()
            rgba.save(output, format="PNG", optimize=True)
            clean = base64.b64encode(output.getvalue()).decode("ascii")
            if len(clean) > 120_000:
                raise ValueError("Signature image too large")
            return f"data:image/png;base64,{clean}"
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail="La firma está vacía o no es una imagen válida") from exc


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def signature_link(document_id: UUID, token: str, expires_at: datetime) -> dict:
    base = settings.resolved_documents_public_base_url
    parsed_base = urlsplit(base)
    if settings.app_env.lower() != "production" and (
        parsed_base.scheme != "http" or parsed_base.hostname not in {"localhost", "127.0.0.1"}
    ):
        raise RuntimeError("El portal documental local solo admite URLs localhost")
    url = f"{base}/public/documents#{token}"
    image = qrcode.make(url)
    output = __import__("io").BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return {
        "url": url,
        "expires_at": expires_at,
        "qr_data_url": f"data:image/png;base64,{encoded}",
        "signature_notice": SIGNATURE_NOTICE,
    }


def signature_bundle_link(tokens: list[str], expires_at: datetime) -> dict:
    """One portal URL that retains the two independently scoped signing tokens."""
    if len(tokens) != 2:
        raise ValueError("A document bundle must contain exactly two capabilities")
    base = settings.resolved_documents_public_base_url
    parsed_base = urlsplit(base)
    if settings.app_env.lower() != "production" and (
        parsed_base.scheme != "http" or parsed_base.hostname not in {"localhost", "127.0.0.1"}
    ):
        raise RuntimeError("El portal documental local solo admite URLs localhost")
    url = f"{base}/public/documents#bundle.{tokens[0]}.{tokens[1]}"
    image = qrcode.make(url)
    output = __import__("io").BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return {
        "url": url,
        "expires_at": expires_at,
        "qr_data_url": f"data:image/png;base64,{encoded}",
        "signature_notice": SIGNATURE_NOTICE,
    }


def _allowed(user: User, document: ManagedDocument, db: Session, *, write: bool = False) -> None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return
    event = db.get(Event, document.event_id) if document.event_id else None
    if user.role == UserRole.SUPERVISOR and event:
        if (
            can_manage_event(user, event.id, db)
            if write
            else can_view_operational_event(user, event, db)
        ):
            return
    raise HTTPException(status_code=403, detail="No tienes acceso a este documento")


def _admin_client_id(user: User, requested: UUID | None = None) -> UUID | None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return requested
    return None


def _person(db: Session, person_id: UUID) -> DocumentPerson:
    person = db.get(DocumentPerson, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person


def _validate_event(db: Session, user: User, event_id: UUID | None, client_id: UUID) -> None:
    if not event_id:
        return
    event = db.get(Event, event_id)
    if not event or event.client_id != client_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado para este cliente")
    if not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=403, detail="No tienes acceso a este evento")


def _bounded_data(value: dict) -> dict:
    if len(str(value).encode("utf-8")) > MAX_DOCUMENT_DATA_BYTES:
        raise HTTPException(
            status_code=422, detail="Los datos del documento son demasiado extensos"
        )
    return value


def _contract_defaults_row(db: Session, settings_key: str) -> dict:
    saved = db.get(DocumentContractDefaults, settings_key)
    return saved.defaults if saved else {}


def get_contract_defaults(db: Session, event_id: UUID | None = None) -> dict:
    defaults = _contract_defaults_row(db, CONTRACT_DEFAULTS_KEY)
    if event_id:
        defaults = {**defaults, **_contract_defaults_row(db, f"E:{event_id}")}
    return {
        "employer_name": defaults.get("employer_name", ""),
        "employer_rut": defaults.get("employer_rut", ""),
        "representative_name": defaults.get("representative_name", ""),
        "representative_rut": defaults.get("representative_rut", ""),
        "employer_address": defaults.get("employer_address", ""),
        "employer_commune": defaults.get("employer_commune", "Santiago"),
    }


def get_event_contract_defaults(db: Session, event_id: UUID) -> dict:
    override = _contract_defaults_row(db, f"E:{event_id}")
    return {
        **get_contract_defaults(db, event_id),
        "has_event_override": bool(override),
    }


def save_contract_defaults(
    db: Session, payload: DocumentContractDefaultsSchema, user: User
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo admin puede editar los datos base del contrato")
    row = db.get(DocumentContractDefaults, CONTRACT_DEFAULTS_KEY)
    if row is None:
        row = DocumentContractDefaults(settings_key=CONTRACT_DEFAULTS_KEY)
        db.add(row)
    row.defaults = {
        **(row.defaults or {}),
        **{key: value.strip() for key, value in payload.model_dump().items()},
    }
    row.updated_by = user.id
    row.updated_at = datetime.utcnow()
    db.commit()
    return get_contract_defaults(db)


def get_representative_signature(db: Session, user: User) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo administración puede gestionar esta firma")
    defaults = _contract_defaults_row(db, CONTRACT_DEFAULTS_KEY)
    profile = defaults.get("representative_signature") or {}
    return {
        "configured": bool(profile.get("signature_data_url")),
        "signer_name": profile.get("signer_name"),
        "signer_rut": profile.get("signer_rut"),
        "signature_data_url": profile.get("signature_data_url"),
        "captured_at": profile.get("captured_at"),
    }


def save_representative_signature(
    db: Session,
    payload: RepresentativeSignatureSaveSchema,
    user: User,
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo administración puede gestionar esta firma")
    defaults = _contract_defaults_row(db, CONTRACT_DEFAULTS_KEY)
    signer_name = normalize_person_name(defaults.get("representative_name", ""))
    signer_rut = str(defaults.get("representative_rut", "")).strip()
    if not signer_name or not signer_rut:
        raise HTTPException(
            status_code=422,
            detail="Completa primero el nombre y RUT del representante legal en los datos base de Greenway",
        )
    try:
        normalize_rut(signer_rut)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="El RUT del representante legal no es válido") from exc

    row = db.get(DocumentContractDefaults, CONTRACT_DEFAULTS_KEY)
    if row is None:
        row = DocumentContractDefaults(settings_key=CONTRACT_DEFAULTS_KEY, defaults=defaults)
        db.add(row)
    row.defaults = {
        **(row.defaults or {}),
        "representative_signature": {
            "signer_name": signer_name,
            "signer_rut": signer_rut,
            "signature_data_url": _clean_signature_png(payload.signature_data_url),
            "captured_at": datetime.now(UTC).isoformat(),
            "captured_by": str(user.id),
        },
    }
    row.updated_by = user.id
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return get_representative_signature(db, user)


def delete_representative_signature(db: Session, user: User) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo administración puede gestionar esta firma")
    row = db.get(DocumentContractDefaults, CONTRACT_DEFAULTS_KEY)
    if row and "representative_signature" in (row.defaults or {}):
        row.defaults = {key: value for key, value in row.defaults.items() if key != "representative_signature"}
        row.updated_by = user.id
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
    return get_representative_signature(db, user)


def _signature_for_event(db: Session, event_id: UUID | None) -> dict:
    global_defaults = _contract_defaults_row(db, CONTRACT_DEFAULTS_KEY)
    profile = global_defaults.get("representative_signature") or {}
    if not profile.get("signature_data_url"):
        raise HTTPException(
            status_code=422,
            detail="Registra primero la firma dibujada del representante legal en los datos base de Greenway",
        )
    event_defaults = get_contract_defaults(db, event_id)
    try:
        current_rut = normalize_rut(event_defaults.get("representative_rut", ""))
        saved_rut = normalize_rut(profile.get("signer_rut", ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="El RUT del representante legal debe ser válido") from exc
    if (
        current_rut != saved_rut
        or normalize_person_name(event_defaults.get("representative_name", "")).casefold()
        != normalize_person_name(profile.get("signer_name", "")).casefold()
    ):
        raise HTTPException(
            status_code=422,
            detail="La firma guardada pertenece a otro representante. Registra nuevamente la firma del representante indicado para esta faena.",
        )
    return profile


def save_event_contract_defaults(
    db: Session,
    event_id: UUID,
    payload: DocumentContractDefaultsSchema,
    user: User,
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo administración puede editar los datos base del contrato")
    event = db.get(Event, event_id)
    if not event or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Faena no encontrada o sin acceso")
    key = f"E:{event_id}"
    row = db.get(DocumentContractDefaults, key)
    if row is None:
        row = DocumentContractDefaults(settings_key=key)
        db.add(row)
    row.defaults = {
        **(row.defaults or {}),
        **{key: value.strip() for key, value in payload.model_dump().items()},
    }
    row.updated_by = user.id
    row.updated_at = datetime.utcnow()
    db.commit()
    return get_event_contract_defaults(db, event_id)


def clear_event_contract_defaults(db: Session, event_id: UUID, user: User) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo administración puede editar los datos base del contrato")
    event = db.get(Event, event_id)
    if not event or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Faena no encontrada o sin acceso")
    row = db.get(DocumentContractDefaults, f"E:{event_id}")
    if row:
        db.delete(row)
        db.commit()
    return get_event_contract_defaults(db, event_id)


def get_event_epp_template(db: Session, event_id: UUID, user: User) -> dict:
    event = db.get(Event, event_id)
    if not event or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Evento no encontrado o sin acceso")
    saved = db.get(EventEppTemplate, event_id)
    items = saved.items if saved else [
        {"item_code": code, "label": label} for code, label in EPP_CATALOG
    ]
    return {"event_id": str(event_id), "items": items, "updated_at": saved.updated_at if saved else None}


def save_event_epp_template(
    db: Session, event_id: UUID, payload: EventEppTemplateUpdate, user: User
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo administración puede configurar los elementos EPP")
    event = db.get(Event, event_id)
    if not event or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Evento no encontrado o sin acceso")
    codes = [item.item_code for item in payload.items]
    if len(codes) != len(set(codes)):
        raise HTTPException(status_code=422, detail="No se permiten códigos EPP duplicados")
    items = [{"item_code": item.item_code, "label": item.label.strip()} for item in payload.items]
    if any(not item["label"] for item in items):
        raise HTTPException(status_code=422, detail="Cada elemento debe tener un nombre")
    saved = db.get(EventEppTemplate, event_id)
    if saved is None:
        saved = EventEppTemplate(event_id=event_id, items=items)
        db.add(saved)
    else:
        saved.items = items
        saved.updated_at = datetime.utcnow()
    saved.updated_by = user.id
    drafts = db.scalars(
        select(ManagedDocument)
        .options(selectinload(ManagedDocument.epp_delivery).selectinload(EppDelivery.items))
        .where(
            ManagedDocument.event_id == event_id,
            ManagedDocument.kind == "EPP",
            ManagedDocument.status == "DRAFT",
        )
    ).all()
    for document in drafts:
        delivery = document.epp_delivery
        if delivery is None:
            continue
        existing = {item.item_code: item for item in delivery.items}
        configured_codes = {item["item_code"] for item in items}
        for code, current in existing.items():
            if code not in configured_codes:
                db.delete(current)
        for configured in items:
            current = existing.get(configured["item_code"])
            if current:
                current.label = configured["label"]
            else:
                db.add(EppDeliveryItem(
                    delivery_id=delivery.id,
                    item_code=configured["item_code"],
                    label=configured["label"],
                    received_conformity=False,
                ))
    db.commit()
    result = get_event_epp_template(db, event_id, user)
    result["draft_documents_updated"] = len(drafts)
    return result


def _seed_epp(
    db: Session,
    delivery: EppDelivery,
    epp: EppInput | None,
    default_items: list[dict] | None = None,
) -> None:
    item_inputs = epp.items if epp else []
    if len({item.item_code for item in item_inputs}) != len(item_inputs):
        raise HTTPException(status_code=422, detail="No se permiten elementos EPP duplicados")
    if any(
        item.received_at and item.returned_at and item.returned_at < item.received_at
        for item in item_inputs
    ):
        raise HTTPException(
            status_code=422, detail="La devolución EPP no puede ser anterior a la recepción"
        )
    items = (
        [(item.item_code, item.label.strip(), item) for item in item_inputs]
        if item_inputs
        else [(item["item_code"], item["label"], None) for item in (default_items or [
            {"item_code": code, "label": label} for code, label in EPP_CATALOG
        ])]
    )
    for code, label, item in items:
        db.add(
            EppDeliveryItem(
                delivery_id=delivery.id,
                item_code=code,
                label=label,
                received_at=item.received_at if item else None,
                returned_at=item.returned_at if item else None,
                received_conformity=item.received_conformity if item else False,
            )
        )


def create_document(db: Session, payload: DocumentCreate, user: User) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=403, detail="Rol sin permiso para crear documentos")
    if not payload.event_id:
        raise HTTPException(status_code=422, detail="Los documentos deben quedar asociados a una faena/evento")
    event = db.get(Event, payload.event_id)
    if not event or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    client_id = event.client_id
    person = _person(db, payload.person_id)
    _validate_event(db, user, payload.event_id, client_id)
    employment = None
    if payload.employment_id:
        employment = db.scalar(
            select(DocumentEmployment).where(
                DocumentEmployment.id == payload.employment_id,
                DocumentEmployment.person_id == person.id,
                DocumentEmployment.client_id == client_id,
                DocumentEmployment.event_id == payload.event_id,
            )
        )
        if not employment:
            raise HTTPException(
                status_code=422, detail="La asignación no corresponde a esta persona"
            )
        if payload.event_id and employment.event_id not in (None, payload.event_id):
            raise HTTPException(status_code=422, detail="La asignación corresponde a otro evento")
    else:
        employment = db.scalar(
            select(DocumentEmployment)
            .where(
                DocumentEmployment.person_id == person.id,
                DocumentEmployment.event_id == payload.event_id,
            )
            .order_by(DocumentEmployment.created_at.desc())
            .limit(1)
        )
    if not employment:
        raise HTTPException(status_code=422, detail="La persona debe estar asignada a esta faena antes de crear documentos")
    if user.role == UserRole.SUPERVISOR and (
        not payload.event_id or not can_manage_event(user, payload.event_id, db)
    ):
        raise HTTPException(
            status_code=403, detail="El supervisor solo puede crear documentos del evento asignado"
        )
    data = _bounded_data(payload.data)
    if payload.kind == "EPP" and payload.epp is None:
        raise HTTPException(status_code=422, detail="Completa los datos del registro EPP")
    doc = ManagedDocument(
        client_id=client_id,
        person_id=person.id,
        employment_id=employment.id if employment else None,
        event_id=payload.event_id,
        created_by=user.id,
        kind=payload.kind,
        title=payload.title.strip(),
        data=data,
    )
    db.add(doc)
    db.flush()
    if payload.kind == "EPP":
        epp = payload.epp
        delivery = EppDelivery(
            client_id=client_id,
            document_id=doc.id,
            riohs_received=epp.riohs_received,
            eirl_completed=epp.eirl_completed,
            delivery_date=epp.delivery_date,
            supervisor_id=user.id if user.role == UserRole.SUPERVISOR else None,
        )
        db.add(delivery)
        db.flush()
        _seed_epp(db, delivery, epp, get_event_epp_template(db, event.id, user)["items"])
    db.commit()
    return get_document(db, doc.id, user)


def _epp_data(doc: ManagedDocument) -> dict | None:
    delivery = doc.epp_delivery
    if not delivery:
        return None
    # Older drafts may not have been frozen yet. EPP details are still valid
    # and must remain listable while those drafts await review.
    public_snapshot = dict(doc.frozen_snapshot or {})
    employer_signature = dict(public_snapshot.get("employer_signature") or {})
    employer_signature.pop("signature_data_url", None)
    if employer_signature:
        public_snapshot["employer_signature"] = employer_signature
    return {
        "riohs_received": delivery.riohs_received,
        "eirl_completed": delivery.eirl_completed,
        "delivery_date": delivery.delivery_date.isoformat() if delivery.delivery_date else None,
        "supervisor_id": delivery.supervisor_id,
        "items": [
            {
                "item_code": item.item_code,
                "label": item.label,
                "received_at": item.received_at.isoformat() if item.received_at else None,
                "returned_at": item.returned_at.isoformat() if item.returned_at else None,
                "received_conformity": item.received_conformity,
            }
            for item in delivery.items
        ],
    }


def _read(doc: ManagedDocument) -> dict:
    status = doc.status
    active_requests = [request for request in doc.signatures if not request.revoked_at]
    latest_request = max(active_requests, key=lambda request: request.created_at) if active_requests else None
    if status == "SENT":
        if latest_request:
            if latest_request.expires_at <= datetime.now(UTC).replace(tzinfo=None):
                status = "EXPIRED"
            elif latest_request.worker_signed_at:
                status = "PARTIALLY_SIGNED"
            elif latest_request.opened_at:
                status = "VIEWED"
    epp = _epp_data(doc)
    if epp and latest_request and latest_request.worker_form_data:
        worker_ack = latest_request.worker_form_data
        confirmed_codes = set(worker_ack.get("received_item_codes") or [])
        confirmed_date = str(worker_ack.get("confirmed_at") or "")[:10] or None
        epp["riohs_received"] = bool(worker_ack.get("riohs_received"))
        epp["eirl_completed"] = bool(worker_ack.get("eirl_completed"))
        for item in epp["items"]:
            item["received_conformity"] = item["item_code"] in confirmed_codes
            item["received_at"] = confirmed_date if item["item_code"] in confirmed_codes else None
        epp["delivery_date"] = confirmed_date
    return {
        "id": doc.id,
        "person_id": doc.person_id,
        "person_name": normalize_person_name(
            f"{doc.person.first_name} {doc.person.last_name}"
        ),
        "person_rut": doc.person.rut,
        "employment_id": doc.employment_id,
        "event_id": doc.event_id,
        "kind": doc.kind,
        "status": status,
        "title": doc.title,
        "data": doc.frozen_snapshot or doc.data,
        "epp": epp,
        "version": doc.version,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
        "completed_at": doc.completed_at,
        "can_edit": status in {"DRAFT", "READY"},
        "has_original_pdf": bool(doc.original_pdf_key),
        "has_signed_pdf": bool(doc.signed_pdf_key),
    }


def _document_query():
    return select(ManagedDocument).options(
        selectinload(ManagedDocument.person),
        selectinload(ManagedDocument.epp_delivery).selectinload(EppDelivery.items),
        selectinload(ManagedDocument.signatures),
    )


def get_document(db: Session, document_id: UUID, user: User) -> dict:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db)
    return _read(doc)


def list_documents(
    db: Session,
    user: User,
    *,
    event_id: UUID | None = None,
    kind: str | None = None,
    status: str | None = None,
    client_id: UUID | None = None,
) -> list[dict]:
    stmt = _document_query().order_by(ManagedDocument.updated_at.desc()).limit(500)
    if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        scoped_client_id = _admin_client_id(user, client_id)
        if scoped_client_id:
            stmt = stmt.where(ManagedDocument.client_id == scoped_client_id)
    elif user.role == UserRole.SUPERVISOR:
        if not event_id or not can_manage_event(user, event_id, db):
            raise HTTPException(status_code=403, detail="Selecciona un evento que tengas asignado")
        stmt = stmt.where(ManagedDocument.event_id == event_id)
    else:
        raise HTTPException(status_code=403, detail="Rol sin acceso al módulo Documentos")
    if event_id:
        stmt = stmt.where(ManagedDocument.event_id == event_id)
    if kind:
        stmt = stmt.where(ManagedDocument.kind == kind)
    if status and status != "EXPIRED":
        stmt = stmt.where(ManagedDocument.status == status)
    documents = [_read(doc) for doc in db.scalars(stmt).all()]
    if status == "EXPIRED":
        documents = [doc for doc in documents if doc["status"] == "EXPIRED"]
    return documents


def update_document(db: Session, document_id: UUID, payload: DocumentUpdate, user: User) -> dict:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db, write=True)
    if doc.status not in {"DRAFT", "READY"}:
        raise HTTPException(
            status_code=409, detail="Un documento enviado es inmutable; crea una nueva versión"
        )
    if payload.title is not None:
        doc.title = payload.title.strip()
    if payload.data is not None:
        doc.data = _bounded_data(payload.data)
    if payload.epp is not None:
        if not doc.epp_delivery:
            raise HTTPException(
                status_code=409, detail="El documento no tiene registro EPP asociado"
            )
        delivery = doc.epp_delivery
        delivery.riohs_received = payload.epp.riohs_received
        delivery.eirl_completed = payload.epp.eirl_completed
        delivery.delivery_date = payload.epp.delivery_date
        existing = {item.item_code: item for item in delivery.items}
        supplied = {item.item_code: item for item in payload.epp.items}
        if len(supplied) != len(payload.epp.items):
            raise HTTPException(status_code=422, detail="No se permiten elementos EPP duplicados")
        if any(
            item.received_at and item.returned_at and item.returned_at < item.received_at
            for item in payload.epp.items
        ):
            raise HTTPException(
                status_code=422, detail="La devolución EPP no puede ser anterior a la recepción"
            )
        for code, item_input in supplied.items():
            if code in existing:
                item = existing[code]
                item.label = item_input.label.strip()
                item.received_at, item.returned_at = item_input.received_at, item_input.returned_at
                item.received_conformity = item_input.received_conformity
            else:
                db.add(
                    EppDeliveryItem(
                        delivery_id=delivery.id,
                        item_code=code,
                        label=item_input.label,
                        received_at=item_input.received_at,
                        returned_at=item_input.returned_at,
                        received_conformity=item_input.received_conformity,
                    )
                )
        for code, item in existing.items():
            if code not in supplied:
                db.delete(item)
        if user.role == UserRole.SUPERVISOR:
            delivery.supervisor_id = user.id
    if doc.status == "READY":
        doc.status = "DRAFT"
    doc.updated_at = datetime.utcnow()
    db.commit()
    return get_document(db, doc.id, user)


def _snapshot(db: Session, doc: ManagedDocument) -> dict:
    person = doc.person
    employment = db.get(DocumentEmployment, doc.employment_id) if doc.employment_id else None
    event = db.get(Event, doc.event_id) if doc.event_id else None
    snapshot = {
        "document_id": str(doc.id),
        "kind": doc.kind,
        "title": doc.title,
        # El cliente contrata a Greenway para la faena; no es el empleador del trabajador.
        "employer_name": doc.data.get("employer_name")
        or ("Greenway" if doc.kind == "EPP" else None),
        "version": doc.version,
        "person": {
            "first_name": person.first_name,
            "last_name": person.last_name,
            "rut": person.rut,
            "address": person.address,
            "commune": person.commune,
            "email": person.email,
        },
        "employment": (
            {
                "position": employment.position,
                "area": employment.area,
                "start_date": employment.start_date.isoformat() if employment.start_date else None,
                "end_date": employment.end_date.isoformat() if employment.end_date else None,
                "remuneration": str(employment.remuneration)
                if employment.remuneration is not None
                else None,
                "workplace": employment.workplace,
                "duties": employment.duties,
            }
            if employment
            else {}
        ),
        "event": (
            {"name": event.name, "venue": event.location_name, "address": event.address}
            if event
            else None
        ),
        "data": doc.data,
        "epp": _epp_data(doc),
        "prepared_at": datetime.now(UTC).isoformat(),
        "signature_notice": SIGNATURE_NOTICE,
    }
    return snapshot


def _store_pdf(doc: ManagedDocument, content: bytes, variant: str) -> tuple[str, str]:
    return document_storage.store(doc.id, doc.version, variant, content)


def _read_pdf(key: str | None) -> bytes:
    if not key:
        raise HTTPException(status_code=404, detail="El PDF todavía no está generado")
    return document_storage.read(key)


def _apply_worker_epp_acknowledgments(snapshot: dict, worker_ack: dict) -> dict:
    """Overlay saved EPP acknowledgments onto a snapshot for preview or signing."""
    updated = dict(snapshot)
    epp = dict(updated.get("epp") or {})
    received_codes = set(worker_ack.get("received_item_codes") or [])
    received_date = str(worker_ack.get("confirmed_at") or "")[:10] or None
    epp["riohs_received"] = bool(worker_ack.get("riohs_received"))
    epp["eirl_completed"] = bool(worker_ack.get("eirl_completed"))
    epp["delivery_date"] = received_date
    epp["items"] = [
        {
            **item,
            "received_at": received_date if item.get("item_code") in received_codes else None,
            "received_conformity": item.get("item_code") in received_codes,
        }
        for item in epp.get("items", [])
    ]
    updated["epp"] = epp
    updated["worker_acknowledgments"] = worker_ack
    return updated


def preview_pdf(db: Session, document_id: UUID, user: User) -> bytes:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db)
    # Show the immutable final PDF when one exists, not a regenerated pre-signature preview.
    if doc.signed_pdf_key:
        return _read_pdf(doc.signed_pdf_key)

    snapshot = doc.frozen_snapshot or _snapshot(db, doc)
    signatures = {}
    worker_requests = [
        request
        for request in doc.signatures
        if not request.revoked_at and request.worker_signed_at
    ]
    if worker_requests:
        request = max(worker_requests, key=lambda item: item.created_at)
        worker_form_data = request.worker_form_data or {}
        signatures = {
            "worker_name": request.worker_signed_name,
            "worker_signed_at": request.worker_signed_at.isoformat(),
            "worker_signature_data_url": worker_form_data.get("worker_signature_data_url"),
            "electronic_consent_text": worker_form_data.get("electronic_consent_text"),
            "electronic_consent_version": worker_form_data.get("electronic_consent_version"),
            "electronic_consent_at": worker_form_data.get("electronic_consent_at"),
        }
        if doc.kind == "EPP":
            snapshot = _apply_worker_epp_acknowledgments(snapshot, worker_form_data)
    return render_html(render_document_html(snapshot, signatures))[0]


def _document_completion_gaps(snapshot: dict) -> list[str]:
    person = snapshot.get("person") or {}
    employment = snapshot.get("employment") or {}
    event = snapshot.get("event") or {}
    data = snapshot.get("data") or {}
    missing: list[str] = []

    def require(value: object, label: str) -> None:
        if value is None or not str(value).strip():
            missing.append(label)

    require(person.get("first_name"), "Nombre del trabajador")
    require(person.get("last_name"), "Apellido del trabajador")
    require(person.get("rut"), "RUT del trabajador")
    require(person.get("email"), "Correo electrónico para enviar")
    for key, label in (("rut", "RUT del trabajador"),):
        value = person.get(key)
        if value:
            try:
                normalize_rut(str(value))
            except ValueError:
                missing.append(f"{label} inválido")
    if snapshot.get("kind") == "CONTRACT":
        for key, label in (
            ("contract_date", "Fecha del contrato"),
            ("employer_name", "Razón social del empleador"),
            ("employer_rut", "RUT del empleador"),
            ("representative_name", "Representante legal"),
            ("representative_rut", "RUT del representante"),
            ("employer_address", "Domicilio del empleador"),
        ):
            require(data.get(key), label)
        for key, label in (("employer_rut", "RUT del empleador"), ("representative_rut", "RUT del representante")):
            value = data.get(key)
            if value:
                try:
                    normalize_rut(str(value))
                except ValueError:
                    missing.append(f"{label} inválido")
        require(person.get("address"), "Domicilio del trabajador")
        require(person.get("commune"), "Comuna del trabajador")
        require(employment.get("position") or data.get("duties"), "Cargo / labores")
        require(employment.get("start_date"), "Fecha de inicio")
        require(employment.get("end_date"), "Fecha de término")
        require(employment.get("remuneration"), "Remuneración")
        remuneration = employment.get("remuneration")
        if remuneration is not None:
            try:
                if Decimal(str(remuneration)) < 0:
                    missing.append("Remuneración no puede ser negativa")
            except (InvalidOperation, ValueError):
                missing.append("Remuneración inválida")
        start_date, end_date = employment.get("start_date"), employment.get("end_date")
        if start_date and end_date and str(end_date) < str(start_date):
            missing.append("Rango de fechas incoherente")
        require(
            data.get("workplace") or event.get("venue") or event.get("address") or employment.get("workplace"),
            "Lugar / dependencias de trabajo",
        )
    elif snapshot.get("kind") == "EPP" and not (snapshot.get("epp") or {}).get("items"):
        missing.append("Al menos un elemento EPP configurado para la faena")
    return missing


def _raise_if_document_incomplete(snapshot: dict, action: str) -> None:
    gaps = _document_completion_gaps(snapshot)
    if gaps:
        raise HTTPException(
            status_code=422,
            detail=f"Completa los datos obligatorios antes de {action}: {', '.join(gaps)}.",
        )


def prepare_document(db: Session, document_id: UUID, user: User) -> dict:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id).with_for_update())
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db, write=True)
    if doc.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Solo un borrador se puede preparar")
    snapshot = _snapshot(db, doc)
    _raise_if_document_incomplete(snapshot, "preparar o enviar el documento")
    render_html(render_document_html(snapshot))
    doc.status = "READY"
    doc.updated_at = datetime.utcnow()
    db.commit()
    return get_document(db, doc.id, user)


def send_for_signature(
    db: Session, document_id: UUID, user: User, *, bundle_id: UUID | None = None
) -> dict:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id).with_for_update())
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db, write=True)
    if doc.status not in {"READY", "SENT", "VIEWED"}:
        raise HTTPException(
            status_code=409, detail="El estado actual no permite enviar o reenviar este documento"
        )
    snapshot = doc.frozen_snapshot or _snapshot(db, doc)
    if doc.frozen_snapshot is None:
        _raise_if_document_incomplete(snapshot, "enviar el documento")
        profile = _signature_for_event(db, doc.event_id)
        snapshot["employer_signature"] = {
            "signer_name": profile["signer_name"],
            "signer_rut": profile["signer_rut"],
            "signature_data_url": profile["signature_data_url"],
            "applied_at": datetime.now(UTC).isoformat(),
        }
    pdf, _ = render_html(render_document_html(snapshot))
    key = doc.original_pdf_key
    checksum = doc.original_sha256
    if not key:
        key, checksum = _store_pdf(doc, pdf, "original")
        doc.original_pdf_key, doc.original_sha256 = key, checksum
    now = datetime.utcnow()
    for request in db.scalars(
        select(DocumentSignatureRequest).where(
            DocumentSignatureRequest.document_id == doc.id,
            DocumentSignatureRequest.revoked_at.is_(None),
        )
    ).all():
        request.revoked_at = now
    capability = signature_provider.create_signature_request(now, timedelta(days=TOKEN_TTL_DAYS))
    token, expiry = capability.token, capability.expires_at
    db.add(
        DocumentSignatureRequest(
            client_id=doc.client_id,
            document_id=doc.id,
            bundle_id=bundle_id,
            token_hash=capability.token_hash,
            expires_at=expiry,
            signature_provider=signature_provider.name,
        )
    )
    doc.frozen_snapshot = snapshot
    doc.status = "SENT"
    doc.updated_at = now
    db.commit()
    link = signature_link(doc.id, token, expiry)
    email_sent = False
    delivery_error = None
    if bundle_id is None:
        recipient = (doc.person.email or "").strip()
        if not recipient:
            delivery_error = "La persona no tiene un correo personal registrado. Puedes compartir el enlace de forma segura."
        else:
            event = db.get(Event, doc.event_id) if doc.event_id else None
            try:
                email_sent = send_document_signature_link_email(
                    recipient=recipient,
                    worker_name=normalize_person_name(f"{doc.person.first_name} {doc.person.last_name}"),
                    event_name=event.name if event else "Faena asignada",
                    document_title=doc.title,
                    portal_url=link["url"],
                    expires_at=expiry.strftime("%d-%m-%Y %H:%M UTC"),
                )
                if not email_sent:
                    delivery_error = (
                        "El enlace quedó preparado, pero el correo está deshabilitado fuera de producción."
                        if settings.app_env.lower() != "production"
                        else "El enlace quedó preparado, pero el proveedor no confirmó el correo."
                    )
            except Exception:
                logger.exception("Could not email signing link for document %s", doc.id)
                delivery_error = "El enlace quedó preparado, pero no se pudo enviar el correo. Reintenta el envío del enlace."
    return {
        "document": get_document(db, doc.id, user),
        "link": link,
        "recipient": (doc.person.email or "").strip() or None,
        "email_sent": email_sent,
        "delivery_error": delivery_error,
    }


def send_documents_together(
    db: Session,
    contract_id: UUID,
    epp_id: UUID,
    user: User,
    *,
    send_email: bool = True,
    email_idempotency_key: str | None = None,
) -> dict:
    contract = db.scalar(_document_query().where(ManagedDocument.id == contract_id))
    epp = db.scalar(_document_query().where(ManagedDocument.id == epp_id))
    if not contract or not epp:
        raise HTTPException(status_code=404, detail="No se encontraron ambos documentos")
    _allowed(user, contract, db, write=True)
    _allowed(user, epp, db, write=True)
    if contract.kind != "CONTRACT" or epp.kind != "EPP":
        raise HTTPException(status_code=422, detail="Selecciona un contrato y un documento EPP")
    if (
        contract.person_id != epp.person_id
        or contract.client_id != epp.client_id
        or contract.event_id is None
        or contract.event_id != epp.event_id
        or contract.employment_id != epp.employment_id
    ):
        raise HTTPException(
            status_code=422,
            detail="Los documentos deben ser de la misma persona, asignaciÃ³n y faena",
        )
    allowed_statuses = {"DRAFT", "READY", "SENT", "VIEWED"}
    if contract.status not in allowed_statuses or epp.status not in allowed_statuses:
        raise HTTPException(
            status_code=409,
            detail="Ambos documentos deben estar en borrador, listos o pendientes de firma",
        )
    recipient = (contract.person.email or "").strip()
    if not recipient:
        raise HTTPException(status_code=422, detail="La persona no tiene correo registrado")
    if settings.app_env.lower() == "production" and not settings.resend_api_key:
        raise HTTPException(status_code=503, detail="El servicio de correo no estÃ¡ configurado")

    for doc in (contract, epp):
        if doc.frozen_snapshot is None:
            _raise_if_document_incomplete(_snapshot(db, doc), "enviar ambos documentos")

    for doc in (contract, epp):
        if doc.status == "DRAFT":
            prepare_document(db, doc.id, user)
    bundle_id = uuid4()
    contract_sent = send_for_signature(db, contract.id, user, bundle_id=bundle_id)
    epp_sent = send_for_signature(db, epp.id, user, bundle_id=bundle_id)
    pair_link = signature_bundle_link(
        [contract_sent["link"]["url"].rsplit("#", 1)[1], epp_sent["link"]["url"].rsplit("#", 1)[1]],
        min(contract_sent["link"]["expires_at"], epp_sent["link"]["expires_at"]),
    )
    event = db.get(Event, contract.event_id)
    expires_at = min(
        contract_sent["link"]["expires_at"], epp_sent["link"]["expires_at"]
    ).strftime("%d-%m-%Y %H:%M UTC")
    email_sent = False
    delivery_error = None
    delivery_payload = {
        "recipient": recipient,
        "worker_name": normalize_person_name(
            f"{contract.person.first_name} {contract.person.last_name}"
        ),
        "event_name": event.name if event else "Faena asignada",
        "contract_title": contract.title,
        "portal_url": pair_link["url"],
        "epp_title": epp.title,
        "expires_at": expires_at,
    }
    if send_email:
        try:
            email_sent = send_document_pair_email(
                **delivery_payload, idempotency_key=email_idempotency_key
            )
        except Exception:
            logger.exception("Could not email document pair for document %s", contract.id)
            delivery_error = "No se pudo enviar el correo. Puedes compartir el enlace conjunto de forma segura."
    return {
        "recipient": recipient,
        "email_sent": email_sent,
        "delivery_error": delivery_error,
        "documents": [contract_sent["document"], epp_sent["document"]],
        "links": [pair_link],
        "delivery_payload": delivery_payload if not send_email else None,
    }


def _public_request(db: Session, token: str) -> DocumentSignatureRequest:
    token_hash = token_digest(token)
    set_public_document_context(db, token_hash)
    request = db.scalar(
        select(DocumentSignatureRequest).where(DocumentSignatureRequest.token_hash == token_hash)
    )
    if not request or request.revoked_at or request.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=404, detail="El enlace no es válido o venció")
    return request


def open_public_document(db: Session, token: str, rut: str) -> dict:
    request = _public_request(db, token)
    doc = db.scalar(_document_query().where(ManagedDocument.id == request.document_id))
    if not doc:
        raise HTTPException(status_code=404, detail="El enlace no es válido o venció")
    try:
        normalized = normalize_rut(rut)
    except ValueError:
        normalized = ""
    if not hmac.compare_digest(normalized, doc.person.rut_normalized):
        raise HTTPException(status_code=403, detail="No fue posible validar la identidad")
    request.opened_at = request.opened_at or datetime.utcnow()
    db.flush()
    db.execute(
        select(func.app_record_public_document_audit(doc.id, "DOCUMENT_PUBLIC_OPENED"))
    )
    db.commit()
    status = doc.status if request.worker_signed_at and doc.status == "COMPLETED" else (
        "PARTIALLY_SIGNED" if request.worker_signed_at else "VIEWED"
    )
    public_snapshot = dict(doc.frozen_snapshot or {})
    employer_signature = dict(public_snapshot.get("employer_signature") or {})
    employer_signature.pop("signature_data_url", None)
    if employer_signature:
        public_snapshot["employer_signature"] = employer_signature
    return {
        "id": str(doc.id),
        "title": doc.title,
        "kind": doc.kind,
        "person_name": normalize_person_name(
            f"{doc.person.first_name} {doc.person.last_name}"
        ),
        "snapshot": public_snapshot,
        "status": status,
        "worker_signed": bool(request.worker_signed_at),
        "worker_form_data": {
            key: value
            for key, value in (request.worker_form_data or {}).items()
            if key in {
                "riohs_received", "eirl_completed", "items_reviewed", "received_item_codes",
                "worker_name", "confirmed_at", "worker_review_confirmed", "worker_review_confirmed_at",
                "electronic_consent", "electronic_consent_text",
                "electronic_consent_version", "electronic_consent_at", "electronic_consent_email",
                "signed_copy_email_sent_at", "signed_copy_email_status", "signed_copy_email_error",
            }
        },
        "worker_signature_present": bool(
            (request.worker_form_data or {}).get("worker_signature_data_url")
        ),
        "worker_email": doc.person.email,
        "electronic_consent_text": _electronic_consent_text(doc, doc.person.email or "correo personal registrado"),
        "electronic_consent_version": ELECTRONIC_CONSENT_VERSION,
        "signed_copy_email_sent": bool((request.worker_form_data or {}).get("signed_copy_email_sent_at")),
        "signed_copy_email_error": (request.worker_form_data or {}).get("signed_copy_email_error"),
        "signature_notice": SIGNATURE_NOTICE,
    }


def preview_public_document_pdf(db: Session, token: str, rut: str) -> bytes:
    request = _public_request(db, token)
    doc = db.scalar(_document_query().where(ManagedDocument.id == request.document_id))
    if not doc or not doc.frozen_snapshot:
        raise HTTPException(status_code=404, detail="El enlace no es válido o venció")
    try:
        normalized = normalize_rut(rut)
    except ValueError:
        normalized = ""
    if not hmac.compare_digest(normalized, doc.person.rut_normalized):
        raise HTTPException(status_code=403, detail="No fue posible validar la identidad")
    if doc.signed_pdf_key:
        return _read_pdf(doc.signed_pdf_key)
    return render_html(render_document_html(doc.frozen_snapshot))[0]


def sign_public_document(
    db: Session,
    token: str,
    rut: str,
    worker_name: str,
    accepted: bool,
    electronic_consent: bool,
    epp_acknowledgments: EppWorkerAcknowledgement | None = None,
    worker_signature_data_url: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    if not accepted:
        raise HTTPException(status_code=422, detail="Debes confirmar que revisaste el documento")
    if not electronic_consent:
        raise HTTPException(status_code=422, detail="Debes aceptar expresamente la gestión y firma electrónica")
    request = _public_request(db, token)
    doc = db.scalar(
        _document_query().where(ManagedDocument.id == request.document_id).with_for_update()
    )
    if not doc or not doc.frozen_snapshot:
        raise HTTPException(status_code=404, detail="El enlace no es válido o venció")
    if not doc.person.email or not doc.person.email.strip():
        raise HTTPException(status_code=422, detail="No hay un correo personal registrado para enviarte la copia firmada")
    if not worker_signature_data_url:
        raise HTTPException(status_code=422, detail="Dibuja tu firma antes de confirmar el documento")
    worker_signature_data_url = _clean_signature_png(worker_signature_data_url)
    try:
        normalized = normalize_rut(rut)
    except ValueError:
        normalized = ""
    expected_name = normalize_person_name(
        f"{doc.person.first_name} {doc.person.last_name}"
    )
    if (
        not hmac.compare_digest(normalized, doc.person.rut_normalized)
        or normalize_person_name(worker_name).casefold() != expected_name.casefold()
    ):
        raise HTTPException(status_code=403, detail="No fue posible validar la identidad")
    if doc.kind == "EPP":
        if not epp_acknowledgments:
            raise HTTPException(status_code=422, detail="Confirma la recepciÃ³n de los elementos EPP")
        if not epp_acknowledgments.riohs_received or not epp_acknowledgments.eirl_completed:
            raise HTTPException(status_code=422, detail="La confirmaciÃ³n debe incluir la recepciÃ³n del RIOHS y la informaciÃ³n EIRL")
        if not epp_acknowledgments.items_reviewed:
            raise HTTPException(status_code=422, detail="Confirma que leÃ­ste el documento y recibiste conforme todos los elementos")
        if len(epp_acknowledgments.received_item_codes) != len(set(epp_acknowledgments.received_item_codes)):
            raise HTTPException(status_code=422, detail="Duplicate EPP confirmation code")
        epp_data = (doc.frozen_snapshot or {}).get("epp") or {}
        expected_codes = {
            str(item.get("item_code"))
            for item in epp_data.get("items", [])
        }
        if set(epp_acknowledgments.received_item_codes) != expected_codes:
            raise HTTPException(status_code=422, detail="Confirma todos los elementos EPP registrados como entregados")
        request.worker_form_data = {
            **(request.worker_form_data or {}),
            **epp_acknowledgments.model_dump(),
            "worker_name": expected_name,
            "confirmed_at": datetime.utcnow().isoformat(),
        }
    elif epp_acknowledgments:
        raise HTTPException(status_code=422, detail="Este documento no requiere confirmaciones EPP")
    if request.worker_signed_at:
        return {
            "status": _read(doc)["status"],
            "email_sent": bool((request.worker_form_data or {}).get("signed_copy_email_sent_at")),
            "signature_notice": SIGNATURE_NOTICE,
        }
    now = datetime.now(UTC).replace(tzinfo=None)
    consent_text = _electronic_consent_text(doc, doc.person.email.strip())
    request.worker_signed_at = now
    request.worker_signed_name = expected_name
    request.worker_form_data = {
        **(request.worker_form_data or {}),
        "worker_signature_data_url": worker_signature_data_url,
        "worker_review_confirmed": True,
        "worker_review_confirmed_at": now.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "electronic_consent": True,
        "electronic_consent_text": consent_text,
        "electronic_consent_version": ELECTRONIC_CONSENT_VERSION,
        "electronic_consent_at": now.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "electronic_consent_email": doc.person.email.strip(),
        "original_pdf_sha256_at_consent": doc.original_sha256,
        "worker_signature_sha256": hashlib.sha256(worker_signature_data_url.encode("utf-8")).hexdigest(),
        "client_ip": (client_ip or "")[:45] or None,
        "user_agent": (user_agent or "")[:500] or None,
    }
    snapshot = dict(doc.frozen_snapshot or {})
    if doc.kind == "EPP":
        snapshot = _apply_worker_epp_acknowledgments(snapshot, request.worker_form_data)
    signatures = {
        "worker_name": expected_name,
        "worker_signed_at": now.replace(tzinfo=UTC).isoformat(),
        "worker_signature_data_url": worker_signature_data_url,
        "supervisor_name": (snapshot.get("employer_signature") or {}).get("signer_name"),
        "supervisor_signed_at": (snapshot.get("employer_signature") or {}).get("applied_at"),
        "employer_signature_data_url": (snapshot.get("employer_signature") or {}).get("signature_data_url"),
        "electronic_consent_text": consent_text,
        "electronic_consent_version": ELECTRONIC_CONSENT_VERSION,
        "electronic_consent_at": now.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
    }
    pdf, _ = render_html(render_document_html(snapshot, signatures))
    signed_key, signed_checksum = _store_pdf(doc, pdf, "signed")
    doc.signed_pdf_key = signed_key
    doc.signed_sha256 = signed_checksum
    doc.status = "COMPLETED"
    doc.completed_at = now
    doc.updated_at = now
    db.flush()
    db.execute(
        select(func.app_record_public_document_audit(doc.id, "DOCUMENT_WORKER_SIGNED"))
    )
    db.commit()
    email_sent = False
    delivery_error = None
    set_public_document_context(db, request.token_hash)
    if request.bundle_id:
        bundle_requests = db.scalars(
            select(DocumentSignatureRequest)
            .where(DocumentSignatureRequest.bundle_id == request.bundle_id)
            .order_by(DocumentSignatureRequest.id)
            .with_for_update()
        ).all()
        if not all(item.worker_signed_at for item in bundle_requests):
            delivery_error = (
                "Tu firma quedó registrada. Cuando completes la firma del otro documento, "
                "te enviaremos un solo correo con ambas copias finales."
            )
            request.worker_form_data = {
                **(request.worker_form_data or {}),
                "signed_copy_email_status": "WAITING_FOR_BUNDLE",
                "signed_copy_email_error": delivery_error,
                "signed_pdf_sha256": signed_checksum,
            }
            db.commit()
        elif not any(
            (item.worker_form_data or {}).get("signed_copy_email_sent_at")
            for item in bundle_requests
        ):
            try:
                email_sent = _send_signed_bundle_copy(db, bundle_requests)
                delivery_error = None if email_sent else (
                    "Ambos documentos están firmados, pero el correo automático está deshabilitado fuera de producción."
                    if settings.app_env.lower() != "production"
                    else "Ambos documentos están firmados, pero el proveedor no confirmó el correo. Reintenta desde Documentos."
                )
            except Exception:
                logger.exception("Could not email signed document bundle %s", request.bundle_id)
                delivery_error = "Ambos documentos están firmados, pero no se pudo enviar el correo. Reintenta desde Documentos."
            _record_bundle_email_result(db, bundle_requests, email_sent, delivery_error)
        else:
            email_sent = True
            delivery_error = None
    else:
        try:
            email_sent = _send_signed_copy_for_document(
                doc,
                event_name=str((snapshot.get("event") or {}).get("name") or "Faena asignada"),
            )
            delivery_error = None if email_sent else (
                "La firma quedó completada, pero el envío automático de correo está deshabilitado fuera de producción."
                if settings.app_env.lower() != "production"
                else "La firma quedó completada, pero el proveedor no confirmó el envío. Reintenta desde Documentos."
            )
        except Exception:
            logger.exception("Could not email signed document copy for %s", doc.id)
            delivery_error = "La firma quedó completada, pero no se pudo enviar el correo. Reintenta desde Documentos."
        request.worker_form_data = {
            **(request.worker_form_data or {}),
            "signed_copy_email_sent_at": datetime.now(UTC).isoformat().replace("+00:00", "Z") if email_sent else None,
            "signed_copy_email_status": "SENT" if email_sent else "FAILED",
            "signed_copy_email_error": delivery_error,
            "signed_pdf_sha256": signed_checksum,
        }
        db.commit()
    return {
        "status": "COMPLETED",
        "email_sent": email_sent,
        "delivery_error": delivery_error,
        "signature_notice": SIGNATURE_NOTICE,
    }


def _send_signed_copy(db: Session, document_id: UUID) -> bool:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id))
    if not doc or doc.status != "COMPLETED" or not doc.signed_pdf_key:
        raise HTTPException(status_code=409, detail="El documento no tiene una copia final firmada")
    event = db.get(Event, doc.event_id) if doc.event_id else None
    return _send_signed_copy_for_document(doc, event_name=event.name if event else "Faena asignada")


def _send_signed_copy_for_document(doc: ManagedDocument, *, event_name: str) -> bool:
    if doc.status != "COMPLETED" or not doc.signed_pdf_key:
        raise HTTPException(status_code=409, detail="El documento no tiene una copia final firmada")
    recipient = (doc.person.email or "").strip()
    if not recipient:
        raise HTTPException(status_code=422, detail="La persona no tiene un correo personal registrado")
    return send_signed_document_copy_email(
        recipient=recipient,
        worker_name=normalize_person_name(f"{doc.person.first_name} {doc.person.last_name}"),
        document_title=doc.title,
        event_name=event_name,
        pdf_content=_read_pdf(doc.signed_pdf_key),
        filename=f"greenway-documento-{doc.id}-v{doc.version}-firmado.pdf",
    )


def _send_signed_bundle_copy(
    db: Session, requests: list[DocumentSignatureRequest]
) -> bool:
    documents = [
        db.scalar(_document_query().where(ManagedDocument.id == item.document_id))
        for item in requests
    ]
    if len(documents) != 2 or any(
        not doc or doc.status != "COMPLETED" or not doc.signed_pdf_key for doc in documents
    ):
        raise HTTPException(status_code=409, detail="Ambos documentos deben estar firmados para enviar la copia conjunta")
    valid_documents = [doc for doc in documents if doc is not None]
    first = valid_documents[0]
    recipient = (first.person.email or "").strip()
    if not recipient:
        raise HTTPException(status_code=422, detail="La persona no tiene un correo personal registrado")
    if any((doc.person.email or "").strip().casefold() != recipient.casefold() for doc in valid_documents):
        raise HTTPException(status_code=409, detail="Los documentos no tienen el mismo correo de destino")
    event = db.get(Event, first.event_id) if first.event_id else None
    return send_signed_document_bundle_email(
        recipient=recipient,
        worker_name=normalize_person_name(f"{first.person.first_name} {first.person.last_name}"),
        event_name=event.name if event else "Faena asignada",
        attachments=[
            {
                "title": doc.title,
                "filename": f"greenway-documento-{doc.id}-v{doc.version}-firmado.pdf",
                "content": _read_pdf(doc.signed_pdf_key),
            }
            for doc in valid_documents
        ],
    )


def _record_bundle_email_result(
    db: Session,
    requests: list[DocumentSignatureRequest],
    sent: bool,
    error: str | None,
) -> None:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z") if sent else None
    for item in requests:
        item.worker_form_data = {
            **(item.worker_form_data or {}),
            "signed_copy_email_sent_at": now,
            "signed_copy_email_status": "SENT" if sent else "FAILED",
            "signed_copy_email_error": error,
            "signed_pdf_sha256": (
                item.document.signed_sha256 if item.document else None
            ),
        }
    db.commit()


def resend_signed_copy(db: Session, document_id: UUID, user: User) -> dict:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db, write=True)
    if doc.status != "COMPLETED" or not doc.signed_pdf_key:
        raise HTTPException(status_code=409, detail="Solo se puede reenviar la copia final de un documento completado")
    latest_request = max(doc.signatures, key=lambda item: item.created_at) if doc.signatures else None
    if latest_request and latest_request.bundle_id:
        bundle_requests = db.scalars(
            select(DocumentSignatureRequest)
            .where(DocumentSignatureRequest.bundle_id == latest_request.bundle_id)
            .order_by(DocumentSignatureRequest.id)
            .with_for_update()
        ).all()
        if len(bundle_requests) != 2 or any(not item.worker_signed_at for item in bundle_requests):
            raise HTTPException(status_code=409, detail="La copia conjunta se envía cuando ambos documentos estén firmados")
        try:
            sent = _send_signed_bundle_copy(db, bundle_requests)
            error = None if sent else "El correo automático está deshabilitado fuera de producción."
        except Exception:
            logger.exception("Could not resend signed document bundle %s", latest_request.bundle_id)
            sent = False
            error = "No se pudo reenviar el correo conjunto. Inténtalo nuevamente."
        _record_bundle_email_result(db, bundle_requests, sent, error)
        return {"email_sent": sent, "recipient": doc.person.email, "documents_included": 2}
    sent = _send_signed_copy(db, doc.id)
    if doc.signatures:
        latest = max(doc.signatures, key=lambda item: item.created_at)
        latest.worker_form_data = {
            **(latest.worker_form_data or {}),
            "signed_copy_email_sent_at": datetime.now(UTC).isoformat().replace("+00:00", "Z") if sent else None,
            "signed_copy_email_status": "SENT" if sent else "FAILED",
            "signed_copy_email_error": None if sent else "El proveedor de correo no confirmó el envío.",
        }
        db.commit()
    return {"email_sent": sent, "recipient": doc.person.email}


def supervisor_sign(db: Session, document_id: UUID, user: User) -> dict:
    doc = db.scalar(_document_query().where(ManagedDocument.id == document_id).with_for_update())
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db, write=True)
    if _read(doc)["status"] != "PARTIALLY_SIGNED":
        raise HTTPException(
            status_code=409, detail="El documento debe estar firmado por el trabajador primero"
        )
    request = db.scalar(
        select(DocumentSignatureRequest)
        .where(
            DocumentSignatureRequest.document_id == doc.id,
            DocumentSignatureRequest.worker_signed_at.is_not(None),
            DocumentSignatureRequest.supervisor_signed_at.is_(None),
            DocumentSignatureRequest.revoked_at.is_(None),
        )
        .order_by(DocumentSignatureRequest.created_at.desc())
        .with_for_update()
    )
    if not request:
        raise HTTPException(
            status_code=409, detail="No existe una solicitud válida para completar la firma"
        )
    signatures = {
        "worker_name": request.worker_signed_name,
        "worker_signed_at": request.worker_signed_at.isoformat()
        if request.worker_signed_at
        else None,
        "worker_signature_data_url": (request.worker_form_data or {}).get("worker_signature_data_url"),
        "supervisor_name": (doc.frozen_snapshot or {}).get("employer_signature", {}).get("signer_name") or user.full_name,
        "supervisor_signed_at": datetime.utcnow().isoformat(),
        "employer_signature_data_url": (doc.frozen_snapshot or {}).get("employer_signature", {}).get("signature_data_url"),
    }
    snapshot = dict(doc.frozen_snapshot or {})
    if doc.kind == "EPP" and request.worker_form_data:
        worker_ack = request.worker_form_data
        snapshot = _apply_worker_epp_acknowledgments(snapshot, worker_ack)
    pdf, _ = render_html(render_document_html(snapshot, signatures))
    key, checksum = _store_pdf(doc, pdf, "signed")
    request.supervisor_signed_at = datetime.utcnow()
    request.supervisor_signed_by = user.id
    doc.signed_pdf_key, doc.signed_sha256 = key, checksum
    doc.status, doc.completed_at, doc.updated_at = "COMPLETED", datetime.utcnow(), datetime.utcnow()
    db.commit()
    return get_document(db, doc.id, user)


def download_document(db: Session, document_id: UUID, user: User, *, signed: bool = False) -> bytes:
    doc = db.get(ManagedDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db)
    return _read_pdf(doc.signed_pdf_key if signed else doc.original_pdf_key)


def cancel_document(db: Session, document_id: UUID, user: User) -> dict:
    doc = db.get(ManagedDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, doc, db, write=True)
    if doc.status in {"COMPLETED", "CANCELLED", "SUPERSEDED"}:
        raise HTTPException(status_code=409, detail="El documento ya no se puede cancelar")
    now = datetime.utcnow()
    doc.status, doc.updated_at = "CANCELLED", now
    for request in db.scalars(
        select(DocumentSignatureRequest).where(
            DocumentSignatureRequest.document_id == doc.id,
            DocumentSignatureRequest.revoked_at.is_(None),
        )
    ):
        request.revoked_at = now
    db.commit()
    return get_document(db, doc.id, user)


def create_new_version(db: Session, document_id: UUID, user: User) -> dict:
    old = db.scalar(_document_query().where(ManagedDocument.id == document_id).with_for_update())
    if not old:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _allowed(user, old, db, write=True)
    if _read(old)["status"] not in {"SENT", "VIEWED", "PARTIALLY_SIGNED", "COMPLETED", "EXPIRED"}:
        raise HTTPException(
            status_code=409, detail="Solo un documento enviado admite una nueva versión"
        )
    old.status = "SUPERSEDED"
    for request in db.scalars(
        select(DocumentSignatureRequest).where(
            DocumentSignatureRequest.document_id == old.id,
            DocumentSignatureRequest.revoked_at.is_(None),
        )
    ):
        request.revoked_at = datetime.utcnow()
    new = ManagedDocument(
        client_id=old.client_id,
        person_id=old.person_id,
        employment_id=old.employment_id,
        event_id=old.event_id,
        created_by=user.id,
        kind=old.kind,
        status="DRAFT",
        title=old.title,
        data=old.data,
        version=old.version + 1,
        supersedes_document_id=old.id,
    )
    db.add(new)
    db.flush()
    if old.kind == "EPP" and old.epp_delivery:
        _copy_epp_delivery(db, old.epp_delivery, new.id, old.client_id)
    db.commit()
    return get_document(db, new.id, user)


def _copy_epp_delivery(
    db: Session, source: EppDelivery, new_document_id: UUID, client_id: UUID
) -> EppDelivery:
    delivery = EppDelivery(
        client_id=client_id,
        document_id=new_document_id,
        # A new version is a new acknowledgment cycle. Keep the inventory and
        # delivery dates, but never carry the worker's confirmations forward.
        riohs_received=False,
        eirl_completed=False,
        delivery_date=source.delivery_date,
        supervisor_id=source.supervisor_id,
        items=[
            EppDeliveryItem(
                item_code=item.item_code,
                label=item.label,
                received_at=item.received_at,
                returned_at=item.returned_at,
                received_conformity=False,
            )
            for item in source.items
        ],
    )
    db.add(delivery)
    db.flush()
    return delivery


def summary(
    db: Session, user: User, *, event_id: UUID | None = None, client_id: UUID | None = None
) -> dict:
    docs = list_documents(db, user, event_id=event_id, client_id=client_id)
    people_stmt = select(func.count(func.distinct(DocumentPerson.id))).join(
        DocumentEmployment, DocumentEmployment.person_id == DocumentPerson.id
    )
    if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        scoped_client_id = _admin_client_id(user, client_id)
        if scoped_client_id:
            people_stmt = people_stmt.where(DocumentEmployment.client_id == scoped_client_id)
    if event_id:
        people_stmt = people_stmt.where(DocumentEmployment.event_id == event_id)
    people_count = db.scalar(people_stmt) or 0
    incomplete_epp = sum(
        1
        for d in docs
        if d["kind"] == "EPP"
        and (not d["epp"] or not d["epp"]["riohs_received"] or not d["epp"]["eirl_completed"])
    )
    return {
        "people": people_count,
        "documents": len(docs),
        "pending": sum(
            d["status"] in {"DRAFT", "READY", "SENT", "VIEWED", "PARTIALLY_SIGNED"} for d in docs
        ),
        "completed": sum(d["status"] == "COMPLETED" for d in docs),
        "incomplete_epp": incomplete_epp,
    }
