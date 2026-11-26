from __future__ import annotations

import hashlib
import html
import base64
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import Client, Event, WasteCollectionRecord, WasteType, User
from app.models.documents import DocumentContractDefaults
from app.models.enums import UserRole
from app.models.disposal_certificate import WasteDisposalCertificate
from app.schemas.disposal_certificate_schema import DisposalCertificateCreate, DisposalCertificateDefaultsUpdate
from app.services.file_storage_service import delete_stored_file, read_stored_file, save_private_object
from app.services.managed_documents_service import _clean_signature_png, _contract_defaults_row, CONTRACT_DEFAULTS_KEY
from app.services.report_pdf_service import render_html

DEFAULT_DISPOSAL_DEFAULTS = {
    "issuer_name": "", "issuer_rut": "", "issuer_address": "",
    "introduction_template": "La empresa {issuer_name}, Rut {issuer_rut}, ubicada en {issuer_address}. Certifica que {recipient_name}, Rut {recipient_rut}. Entregó sus excedentes industriales provenientes del evento «{event_name}» según el siguiente detalle:",
    "treatment_description": "Estos residuos fueron dispuestos en forma sustentable, bajo la Resolución sanitaria del Seremi de Salud R.M. N° 057427*14.12.2017. Una vez separados, recolectados, limpiados y enfardados se transportaron a las plantas respectivas para dar inicio al reciclaje.",
    "closing_text": "Se extiende este certificado para los fines que estime convenientes.",
    "director_name": "", "director_role": "Director Greenway",
    "director_email": "gonzalo@greenwaycl.com", "director_phone": "+569 6 1253554",
    "signature_data_url": "",
}
DISPOSAL_DEFAULTS_KEY = "WASTE_DISPOSAL"


def get_disposal_defaults(db: Session) -> dict[str, str]:
    row = db.get(DocumentContractDefaults, DISPOSAL_DEFAULTS_KEY)
    saved = row.defaults if row else {}
    contract = _contract_defaults_row(db, CONTRACT_DEFAULTS_KEY)
    contract_signature = contract.get("representative_signature") or {}
    merged = {
        **DEFAULT_DISPOSAL_DEFAULTS,
        "issuer_name": contract.get("employer_name", ""),
        "issuer_rut": contract.get("employer_rut", ""),
        "issuer_address": ". ".join(filter(None, [str(contract.get("employer_address", "")).strip().rstrip("."), str(contract.get("employer_commune", "")).strip()])),
        "director_name": contract.get("representative_name", ""),
        "signature_data_url": contract_signature.get("signature_data_url", ""),
        **saved,
    }
    if "signature_data_url" not in saved:
        merged["signature_data_url"] = contract_signature.get("signature_data_url", "")
    merged["director_name"] = saved.get("director_name") or saved.get("signatory_name") or merged["director_name"]
    merged["director_role"] = saved.get("director_role") or saved.get("signatory_role") or merged["director_role"]
    merged["director_email"] = saved.get("director_email") or saved.get("signatory_email") or merged["director_email"]
    merged["director_phone"] = saved.get("director_phone") or saved.get("signatory_phone") or merged["director_phone"]
    if merged.get("director_name") and not (saved.get("director_email") or saved.get("signatory_email")):
        director_user = db.scalar(
            select(User)
            .where(func.lower(User.full_name) == merged["director_name"].strip().lower())
            .order_by(User.updated_at.desc())
            .limit(1)
        )
        if director_user:
            merged["director_email"] = director_user.email or merged["director_email"]
            if not (saved.get("director_phone") or saved.get("signatory_phone")):
                merged["director_phone"] = director_user.phone or merged["director_phone"]
    return merged


def save_disposal_defaults(db: Session, payload: DisposalCertificateDefaultsUpdate, user: User) -> dict[str, str]:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo administración puede editar los datos base del certificado")
    row = db.get(DocumentContractDefaults, DISPOSAL_DEFAULTS_KEY)
    if row is None:
        row = DocumentContractDefaults(settings_key=DISPOSAL_DEFAULTS_KEY)
        db.add(row)
    values = payload.model_dump(exclude_none=True)
    if values.get("signature_data_url"):
        values["signature_data_url"] = _clean_signature_png(values["signature_data_url"])
    row.defaults = {**(row.defaults or {}), **{key: value.strip() if isinstance(value, str) and key != "signature_data_url" else value for key, value in values.items()}}
    row.updated_by = user.id
    row.updated_at = datetime.utcnow()
    db.commit()
    return get_disposal_defaults(db)


def _event(db: Session, event_id: UUID, user: User, *, manage: bool = False) -> tuple[Event, Client]:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento no encontrado")
    allowed = can_manage_event(user, event_id, db) if manage else can_access_event(user, event_id, db)
    if not allowed or not event.client:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a los certificados de este evento")
    return event, event.client


def _received_materials(db: Session, event_id: UUID) -> list[dict]:
    rows = db.execute(
        select(
            WasteType.id,
            WasteType.name,
            func.coalesce(func.sum(WasteCollectionRecord.weight_kg), 0),
            func.array_agg(WasteCollectionRecord.id),
        )
        .join(WasteCollectionRecord, WasteCollectionRecord.waste_type_id == WasteType.id)
        .where(WasteCollectionRecord.event_id == event_id)
        .group_by(WasteType.id, WasteType.name)
        .order_by(WasteType.name)
    ).all()
    return [
        {"waste_type_id": row[0], "name": row[1], "received_kg": Decimal(row[2]).quantize(Decimal("0.001")), "source_record_ids": row[3]}
        for row in rows
    ]


def _list_item(item: WasteDisposalCertificate) -> dict:
    snapshot = item.snapshot
    return {
        "id": item.id,
        "certificate_number": item.certificate_number,
        "certificate_date": item.certificate_date,
        "total_kg": snapshot["total_kg"],
        "recipient_name": snapshot["recipient_name"],
        "receiving_facility_name": snapshot.get("recipient_name", ""),
        "sha256": item.sha256,
        "generated_at": item.generated_at,
    }


def list_item(item: WasteDisposalCertificate) -> dict:
    return _list_item(item)


def get_context(db: Session, event_id: UUID, user: User) -> dict:
    event, client = _event(db, event_id, user)
    items = db.scalars(
        select(WasteDisposalCertificate)
        .where(WasteDisposalCertificate.event_id == event_id)
        .order_by(WasteDisposalCertificate.created_at.desc())
    ).all()
    return {
        "event_id": event.id,
        "event_name": event.name,
        "recipient_name": client.business_name,
        "recipient_rut": client.rut,
        "materials": _received_materials(db, event_id),
        "certificates": [_list_item(item) for item in items],
    }


def _e(value: object | None) -> str:
    return html.escape(str(value or ""), quote=True)


def _format_kg(value: object) -> str:
    normalized = Decimal(str(value)).normalize()
    return format(normalized, "f").replace(".", ",")


def _format_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    months = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    return f"{parsed.day} DE {months[parsed.month - 1].upper()} DE {parsed.year}."


def _safe_paragraph(value: str) -> str:
    return "<br>".join(_e(line) for line in value.splitlines())


def _introduction(snapshot: dict) -> str:
    template = snapshot["introduction_template"]
    values = {
        "issuer_name": snapshot.get("issuer_name", ""), "issuer_rut": snapshot.get("issuer_rut", ""),
        "issuer_address": snapshot.get("issuer_address", ""), "recipient_name": snapshot.get("recipient_name", ""),
        "recipient_rut": snapshot.get("recipient_rut", ""), "event_name": snapshot.get("event_name", ""),
        "receiving_facility_name": snapshot.get("receiving_facility_name", ""),
    }
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value or ""))
    return _safe_paragraph(template)


def _pdf_html(snapshot: dict) -> str:
    material_rows = "".join(
        "<tr><td>" + _e(row["name"]) + "</td><td class='number'>" + _e(_format_kg(row["final_weight_kg"])) + " kg</td></tr>"
        for row in snapshot["materials"]
    )
    logo_path = Path(__file__).resolve().parents[1] / "assets" / "greenway-disposal-logo.png"
    logo_url = "data:image/png;base64," + base64.b64encode(logo_path.read_bytes()).decode("ascii")
    signature = snapshot.get("signature_data_url")
    signature_html = (
        f"<img class='signature-image' src='{_e(signature)}' alt='Firma del director Greenway'>"
        if signature else ""
    )
    return f"""<!doctype html><html lang='es'><meta charset='utf-8'><style>
      @page {{ size: letter; margin: 24mm 19mm 22mm; }}
      * {{ box-sizing: border-box; }} body {{ font-family: Arial, sans-serif; color:#858585; font-size:10pt; line-height:1.45; position:relative; }}
      .brand {{ text-align:center; margin:9mm 0 3mm; }} .brand img {{ width:48mm; height:auto; }}
      h1 {{ text-align:center; color:#0074d9; font-family: Georgia, serif; font-size:16pt; font-weight:400; margin:0 0 3mm; }}
      .date {{ margin-bottom:4mm; text-transform:uppercase; }} .intro {{ margin:0 0 4mm; }}
      table {{ border-collapse:collapse; width:56%; margin:0 auto 4mm; font-size:9.5pt; line-height:1.2; }} td {{ padding:0.8mm 5mm; }}
      tbody {{ font-weight:600; }} tbody tr:nth-child(even) {{ background:#bfe0f6; }} .number {{ text-align:right; white-space:nowrap; }}
      tfoot td {{ border-top:1px solid #1388ed; border-bottom:1px solid #1388ed; font-weight:bold; font-size:11pt; }}
      .note {{ margin:2.5mm 0; }} .signature {{ margin:8mm auto 0; text-align:center; width:75%; break-inside:avoid; page-break-inside:avoid; }}
      .signature-image {{ display:block; width:38mm; height:17mm; object-fit:contain; margin:0 auto 1mm; }}
      .director {{ color:#858585; line-height:1.5; }} .director a {{ color:#0074d9; }}
      .footer-address {{ position:fixed; bottom:0; left:0; right:0; background:#0074d9; color:white; padding:2mm 3mm; font-size:9pt; }}
    </style><body><div class='brand'><img src='{logo_url}' alt='Greenway'></div><h1>CERTIFICADO DE DISPOSICIÓN FINAL</h1>
      <div class='date'>{_e(snapshot['certificate_city'])}, {_e(_format_date(snapshot['certificate_date']))}</div>
      <p class='intro'>{_introduction(snapshot)}</p>
      <table><tbody>{material_rows}</tbody><tfoot><tr><td>TOTAL</td><td class='number'>{_e(_format_kg(snapshot['total_kg']))} Kg</td></tr></tfoot></table>
      <p class='note'>{_safe_paragraph(snapshot['treatment_description'])}</p>
      {f"<p class='note'>{_safe_paragraph(snapshot['closing_text'])}</p>" if snapshot.get('closing_text') else ""}
      <div class='signature'>{signature_html}<div class='director'><strong>{_e(snapshot['director_name'])}</strong><br>{_e(snapshot['director_role'])}<br><a href='mailto:{_e(snapshot['director_email'])}'>{_e(snapshot['director_email'])}</a><br>{_e(snapshot['director_phone'])}</div></div>
      <div class='footer-address'>{_e(snapshot['issuer_address'].rstrip('.'))}.</div>
      </body></html>"""


def _build_snapshot(db: Session, event_id: UUID, user: User, payload: DisposalCertificateCreate, certificate_number: str) -> dict:
    event, client = _event(db, event_id, user, manage=True)
    defaults = get_disposal_defaults(db)
    recipient_name = (payload.recipient_name or client.business_name or "").strip()
    recipient_rut = (payload.recipient_rut if payload.recipient_rut is not None else client.rut) or ""
    event_name = (payload.event_name or event.name or "").strip()
    if not recipient_name or not event_name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Completa el nombre de la empresa y el evento que aparecerán en el certificado")
    if not defaults.get("issuer_name") or not defaults.get("issuer_rut") or not defaults.get("issuer_address"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Completa los datos de Greenway en Documentos antes de emitir certificados")
    if not defaults.get("director_name") or not defaults.get("signature_data_url"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Registra el director y su firma en Documentos antes de emitir certificados")
    if not defaults.get("introduction_template", "").strip():
        raise HTTPException(status.HTTP_409_CONFLICT, "Completa la introducción del certificado en Documentos")
    if not defaults.get("treatment_description", "").strip():
        raise HTTPException(status.HTTP_409_CONFLICT, "Completa el texto de disposición final en Documentos")
    available = {row["waste_type_id"]: row for row in _received_materials(db, event_id)}
    if not available:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este evento aún no tiene residuos registrados en acopios")
    materials = []
    for item in payload.materials:
        received = available.get(item.waste_type_id)
        if received is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El material no tiene registros en este evento")
        final_weight = item.final_weight_kg.quantize(Decimal("0.001"))
        if final_weight > received["received_kg"]:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"La cantidad de {received['name']} supera lo registrado en acopios ({received['received_kg']} kg)",
            )
        materials.append({"waste_type_id": str(item.waste_type_id), "name": received["name"], "final_weight_kg": str(final_weight), "received_kg": str(received["received_kg"]), "source_record_ids": [str(record_id) for record_id in received["source_record_ids"]]})

    total = sum((Decimal(row["final_weight_kg"]) for row in materials), Decimal("0")).quantize(Decimal("0.001"))
    certificate_date = datetime.now(ZoneInfo("America/Santiago")).date()
    return {
        "certificate_number": certificate_number,
        "certificate_date": certificate_date.isoformat(),
        "certificate_city": (event.city or "Santiago").upper(),
        "introduction_template": defaults["introduction_template"],
        "event_id": str(event.id),
        "event_name": event_name,
        "recipient_name": recipient_name,
        "recipient_rut": recipient_rut.strip(),
        "issuer_name": defaults["issuer_name"],
        "issuer_rut": defaults["issuer_rut"],
        "issuer_address": defaults["issuer_address"],
        "director_name": defaults["director_name"],
        "director_role": defaults["director_role"],
        "director_email": defaults["director_email"],
        "director_phone": defaults["director_phone"],
        "signature_data_url": defaults["signature_data_url"],
        "treatment_description": defaults["treatment_description"],
        "closing_text": defaults["closing_text"],
        "materials": materials,
        "total_kg": str(total),
        "confirmed_by": str(user.id),
        "confirmed_by_name": user.full_name,
    }


def preview_certificate(db: Session, event_id: UUID, user: User, payload: DisposalCertificateCreate) -> bytes:
    snapshot = _build_snapshot(db, event_id, user, payload, "VISTA PREVIA")
    pdf, _pages = render_html(_pdf_html(snapshot))
    return pdf


def create_certificate(db: Session, event_id: UUID, user: User, payload: DisposalCertificateCreate) -> WasteDisposalCertificate:
    certificate_id = uuid4()
    certificate_number = f"CDF-{datetime.now(ZoneInfo('America/Santiago')).year}-{certificate_id.hex[:8].upper()}"
    snapshot = _build_snapshot(db, event_id, user, payload, certificate_number)
    try:
        pdf, _pages = render_html(_pdf_html(snapshot))
        digest = hashlib.sha256(pdf).hexdigest()
        snapshot["sha256"] = digest
        key = f"private/waste-certificates/{event_id}/{certificate_id}.pdf"
        save_private_object(key, pdf, content_type="application/pdf")
        item = WasteDisposalCertificate(
            id=certificate_id,
            event_id=event_id,
            certificate_number=certificate_number,
            certificate_date=date.fromisoformat(snapshot["certificate_date"]),
            snapshot=snapshot,
            storage_key=key,
            sha256=digest,
            file_size=len(pdf),
            generated_by=user.id,
            evidence_id=None,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    except Exception:
        db.rollback()
        if "key" in locals():
            delete_stored_file(key)
        raise


def get_pdf(db: Session, certificate_id: UUID, user: User) -> tuple[WasteDisposalCertificate, bytes]:
    item = db.get(WasteDisposalCertificate, certificate_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificado no encontrado")
    _event(db, item.event_id, user)
    content, mime = read_stored_file(item.storage_key)
    if mime != "application/pdf" or hashlib.sha256(content).hexdigest() != item.sha256:
        raise HTTPException(status.HTTP_409_CONFLICT, "El archivo del certificado no coincide con su huella de integridad")
    return item, content
