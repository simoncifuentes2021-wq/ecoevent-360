from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from io import BytesIO
from uuid import UUID
from xml.sax.saxutils import escape

from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.core import Event, User
from app.models.enums import UserRole
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.schemas.purchase_order_schema import PurchaseOrderCreate, PurchaseOrderReceive
from app.services.file_storage_service import read_private_object_from_r2, read_stored_file, save_private_object

CENT = Decimal("0.01")


def _admin(user: User) -> None:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Solo administración puede gestionar órdenes de compra")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _apply_items(order: PurchaseOrder, items) -> None:
    order.items.clear()
    for index, data in enumerate(items, 1):
        quantity = Decimal(data.quantity)
        price = Decimal(data.unit_price)
        rate = Decimal(data.tax_rate)
        subtotal = _money(quantity * price)
        tax = _money(subtotal * rate / Decimal("100"))
        order.items.append(PurchaseOrderItem(
            line_number=index,
            description=data.description.strip(),
            unit=data.unit.strip(),
            quantity=quantity,
            received_quantity=Decimal("0"),
            unit_price=price,
            tax_rate=rate,
            line_subtotal=subtotal,
            line_tax=tax,
            line_total=subtotal + tax,
        ))
    order.subtotal = sum((item.line_subtotal for item in order.items), Decimal("0"))
    order.tax_total = sum((item.line_tax for item in order.items), Decimal("0"))
    order.total = order.subtotal + order.tax_total


def _load(db: Session, order_id: UUID) -> PurchaseOrder:
    order = db.scalar(select(PurchaseOrder).options(
        selectinload(PurchaseOrder.items), selectinload(PurchaseOrder.event)
    ).where(PurchaseOrder.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="No encontramos la orden de compra")
    return order


def _read(order: PurchaseOrder) -> dict:
    return {
        "id": order.id, "order_number": order.order_number, "version": order.version,
        "status": order.status, "event_id": order.event_id,
        "event_name_snapshot": order.event_name_snapshot, "purpose": order.purpose,
        "supplier_name": order.supplier_name, "supplier_rut": order.supplier_rut,
        "supplier_email": order.supplier_email, "supplier_phone": order.supplier_phone,
        "supplier_address": order.supplier_address, "delivery_address": order.delivery_address,
        "issue_date": order.issue_date, "required_date": order.required_date,
        "payment_terms": order.payment_terms, "notes": order.notes, "currency": order.currency,
        "subtotal": order.subtotal, "tax_total": order.tax_total, "total": order.total,
        "created_by": order.created_by, "approved_by": order.approved_by, "sent_by": order.sent_by,
        "approved_at": order.approved_at, "sent_at": order.sent_at,
        "cancelled_at": order.cancelled_at, "cancellation_reason": order.cancellation_reason,
        "created_at": order.created_at, "updated_at": order.updated_at,
        "items": [{"id": item.id, "line_number": item.line_number,
                   "description": item.description, "unit": item.unit,
                   "quantity": item.quantity, "received_quantity": item.received_quantity,
                   "unit_price": item.unit_price, "tax_rate": item.tax_rate,
                   "line_subtotal": item.line_subtotal, "line_tax": item.line_tax,
                   "line_total": item.line_total} for item in order.items],
    }


def list_orders(db: Session, user: User, *, status_filter: str | None, event_id: UUID | None,
                q: str | None, page: int, limit: int) -> tuple[list[dict], int]:
    _admin(user)
    stmt = select(PurchaseOrder)
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    if event_id:
        stmt = stmt.where(PurchaseOrder.event_id == event_id)
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where((PurchaseOrder.order_number.ilike(term)) | (PurchaseOrder.supplier_name.ilike(term)) | (PurchaseOrder.purpose.ilike(term)))
    count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.options(selectinload(PurchaseOrder.items)).order_by(
        PurchaseOrder.created_at.desc()
    ).offset((page - 1) * limit).limit(limit)).all()
    return [_read(row) for row in rows], int(count)


def create_order(db: Session, payload: PurchaseOrderCreate, user: User) -> dict:
    _admin(user)
    event = db.get(Event, payload.event_id) if payload.event_id else None
    if payload.event_id and event is None:
        raise HTTPException(status_code=404, detail="No encontramos el evento seleccionado")
    sequence = db.scalar(select(func.nextval(text("purchase_order_number_seq"))))
    order = PurchaseOrder(
        order_number=f"OC-{date.today().year}-{int(sequence):06d}",
        event_id=event.id if event else None,
        event_name_snapshot=event.name if event else None,
        purpose=payload.purpose.strip(), supplier_name=payload.supplier_name.strip(),
        supplier_rut=payload.supplier_rut, supplier_email=str(payload.supplier_email) if payload.supplier_email else None,
        supplier_phone=payload.supplier_phone, supplier_address=payload.supplier_address,
        delivery_address=payload.delivery_address, issue_date=payload.issue_date,
        required_date=payload.required_date, payment_terms=payload.payment_terms,
        notes=payload.notes, currency=payload.currency, created_by=user.id,
    )
    _apply_items(order, payload.items)
    db.add(order)
    db.commit()
    return _read(_load(db, order.id))


def get_order(db: Session, order_id: UUID, user: User) -> dict:
    _admin(user)
    return _read(_load(db, order_id))


def update_order(db: Session, order_id: UUID, payload: PurchaseOrderCreate, user: User) -> dict:
    _admin(user)
    order = _load(db, order_id)
    if order.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Solo se pueden modificar órdenes en borrador")
    event = db.get(Event, payload.event_id) if payload.event_id else None
    if payload.event_id and event is None:
        raise HTTPException(status_code=404, detail="No encontramos el evento seleccionado")
    order.event_id = event.id if event else None
    order.event_name_snapshot = event.name if event else None
    for field in ("purpose", "supplier_name", "supplier_rut", "supplier_email", "supplier_phone", "supplier_address", "delivery_address", "issue_date", "required_date", "payment_terms", "notes", "currency"):
        value = getattr(payload, field)
        setattr(order, field, str(value) if field == "supplier_email" and value else value.strip() if isinstance(value, str) else value)
    order.version += 1
    order.pdf_storage_key = None
    order.pdf_sha256 = None
    order.pdf_version = None
    _apply_items(order, payload.items)
    db.commit()
    return _read(_load(db, order.id))


def change_status(db: Session, order_id: UUID, action: str, user: User) -> dict:
    _admin(user)
    order = _load(db, order_id)
    now = datetime.utcnow()
    if action == "approve" and order.status == "DRAFT":
        order.status, order.approved_by, order.approved_at = "APPROVED", user.id, now
    elif action == "send" and order.status == "APPROVED":
        order.status, order.sent_by, order.sent_at = "SENT", user.id, now
    else:
        raise HTTPException(status_code=409, detail="La acción no corresponde al estado actual de la orden")
    order.updated_at = now
    db.commit()
    return _read(_load(db, order.id))


def receive_order(db: Session, order_id: UUID, payload: PurchaseOrderReceive, user: User) -> dict:
    _admin(user)
    order = _load(db, order_id)
    if order.status not in {"SENT", "PARTIALLY_RECEIVED"}:
        raise HTTPException(status_code=409, detail="Solo puedes registrar recepción de una orden enviada")
    by_id = {item.id: item for item in order.items}
    for update in payload.items:
        item = by_id.get(update.item_id)
        if item is None:
            raise HTTPException(status_code=400, detail="Una línea no pertenece a esta orden")
        next_qty = item.received_quantity + update.received_quantity
        if next_qty > item.quantity:
            raise HTTPException(status_code=400, detail=f"La recepción de {item.description} supera la cantidad ordenada")
        item.received_quantity = next_qty
    order.status = "RECEIVED" if all(item.received_quantity >= item.quantity for item in order.items) else "PARTIALLY_RECEIVED"
    if payload.notes:
        order.notes = f"{order.notes or ''}\nRecepción: {payload.notes}".strip()
    order.updated_at = datetime.utcnow()
    db.commit()
    return _read(_load(db, order.id))


def cancel_order(db: Session, order_id: UUID, reason: str, user: User) -> dict:
    _admin(user)
    order = _load(db, order_id)
    if order.status not in {"DRAFT", "APPROVED", "SENT"}:
        raise HTTPException(status_code=409, detail="Esta orden ya no se puede cancelar")
    order.status, order.cancelled_at = "CANCELLED", datetime.utcnow()
    order.cancellation_reason = reason.strip()
    order.updated_at = order.cancelled_at
    db.commit()
    return _read(_load(db, order.id))


def render_pdf(db: Session, order_id: UUID, user: User) -> tuple[bytes, str]:
    _admin(user)
    order = _load(db, order_id)
    if order.pdf_storage_key and order.pdf_version == order.version:
        reader = read_private_object_from_r2 if settings.use_r2_storage else read_stored_file
        content, _ = reader(order.pdf_storage_key)
        return content, order.order_number
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=18*mm, leftMargin=18*mm, topMargin=17*mm, bottomMargin=17*mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("ORDEN DE COMPRA", styles["Title"]), Paragraph(f"<b>{order.order_number}</b> · Versión {order.version}", styles["Heading2"]), Spacer(1, 5*mm)]
    story.extend([
        Paragraph(f"<b>Proveedor:</b> {escape(order.supplier_name)}", styles["BodyText"]),
        Paragraph(f"<b>RUT:</b> {escape(order.supplier_rut or '—')} · <b>Correo:</b> {escape(order.supplier_email or '—')} · <b>Teléfono:</b> {escape(order.supplier_phone or '—')}", styles["BodyText"]),
        Paragraph(f"<b>Dirección:</b> {escape(order.supplier_address or '—')}", styles["BodyText"]),
        Paragraph(f"<b>Fecha:</b> {order.issue_date.strftime('%d-%m-%Y')} · <b>Entrega:</b> {order.required_date.strftime('%d-%m-%Y') if order.required_date else 'Por coordinar'}", styles["BodyText"]),
        Paragraph(f"<b>Evento:</b> {escape(order.event_name_snapshot or 'Compra general')}", styles["BodyText"]),
        Paragraph(f"<b>Finalidad:</b> {escape(order.purpose)}", styles["BodyText"]), Spacer(1, 5*mm),
    ])
    rows = [["Detalle", "Cant.", "Unidad", "P. unitario", "Impuesto", "Total"]]
    for item in order.items:
        rows.append([Paragraph(escape(item.description), getSampleStyleSheet()["BodyText"]), f"{item.quantity:g}", escape(item.unit), f"{order.currency} {item.unit_price:,.0f}", f"{item.tax_rate:g}%", f"{order.currency} {item.line_total:,.0f}"])
    table = Table(rows, colWidths=[60*mm, 16*mm, 20*mm, 30*mm, 20*mm, 34*mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d765f")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#cbd5e1")), ("VALIGN", (0,0), (-1,-1), "TOP"), ("FONTSIZE", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("TOPPADDING", (0,0), (-1,-1), 7)]))
    story.extend([table, Spacer(1, 5*mm), Paragraph(f"Subtotal: {order.currency} {order.subtotal:,.0f}", styles["BodyText"]), Paragraph(f"Impuestos: {order.currency} {order.tax_total:,.0f}", styles["BodyText"]), Paragraph(f"<b>Total: {order.currency} {order.total:,.0f}</b>", styles["Heading2"])])
    if order.delivery_address:
        story.append(Paragraph(f"<b>Dirección de entrega:</b> {escape(order.delivery_address)}", styles["BodyText"]))
    if order.payment_terms:
        story.append(Paragraph(f"<b>Condiciones de pago:</b> {escape(order.payment_terms)}", styles["BodyText"]))
    if order.notes:
        story.append(Paragraph(f"<b>Notas:</b> {escape(order.notes)}", styles["BodyText"]))
    doc.build(story)
    content = buffer.getvalue()
    key = f"{settings.r2_private_prefix.strip('/')}/purchase-orders/{order.order_number}/v{order.version}.pdf"
    order.pdf_storage_key = save_private_object(key, content, content_type="application/pdf")
    order.pdf_sha256 = sha256(content).hexdigest()
    order.pdf_version = order.version
    order.updated_at = datetime.utcnow()
    db.commit()
    return content, order.order_number
