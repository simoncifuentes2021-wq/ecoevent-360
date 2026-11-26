from __future__ import annotations

from datetime import UTC, date, datetime
import html
import logging
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings
from app.models.core import Event, EventStaff

logger = logging.getLogger(__name__)
_RESEND_EMAILS_URL = "https://api.resend.com/emails"
_CHILE_TZ = ZoneInfo("America/Santiago")
_WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def send_staff_event_email(event: Event, assignment: EventStaff) -> tuple[str, str | None, str | None]:
    """Send a direct event assignment notice and return status, provider ID, and safe error."""
    recipient = (assignment.user.email if assignment.user else "").strip()
    if not recipient:
        return "ERROR", None, "La persona no tiene un correo electrónico registrado."
    if not settings.resend_api_key:
        return "ERROR", None, "Resend no está configurado en el backend."

    start = _local_date(event.start_date)
    end = _local_date(event.end_date)
    date_range = _format_spanish_date(start) if start == end else f"{_format_spanish_date(start)} al {_format_spanish_date(end)}"
    client_name = event.client.business_name if event.client else None
    location = ", ".join(
        dict.fromkeys(
            value.strip()
            for value in (event.location_name, event.address, event.city, event.region)
            if value and value.strip()
        )
    )
    shift = ""
    if assignment.shift_start and assignment.shift_end:
        shift = f"{assignment.shift_start:%d-%m-%Y %H:%M} a {assignment.shift_end:%d-%m-%Y %H:%M}"
    elif assignment.shift_start:
        shift = f"Desde {assignment.shift_start:%d-%m-%Y %H:%M}"
    elif assignment.shift_end:
        shift = f"Hasta {assignment.shift_end:%d-%m-%Y %H:%M}"

    name = assignment.user.full_name if assignment.user else "Hola"
    details = [
        ("Evento", event.name),
        ("Cliente", client_name),
        ("Fechas", date_range),
        ("Lugar", location),
        ("Tu función", assignment.role_in_event),
        ("Horario asignado", shift),
    ]
    rows_html = "".join(
        f"<tr><td style='padding:8px 0;color:#64748b;vertical-align:top'>{html.escape(label)}</td>"
        f"<td style='padding:8px 0 8px 16px;font-weight:600'>{html.escape(str(value))}</td></tr>"
        for label, value in details
        if value
    )
    description = (event.description or "").strip()
    description_html = (
        f"<p style='margin:20px 0 0;color:#475569;white-space:pre-line'>{html.escape(description)}</p>"
        if description
        else ""
    )
    safe_name = html.escape(name or "Hola")
    safe_event = html.escape(event.name)
    payload = {
        "from": settings.email_from,
        "to": [recipient],
        "subject": f"Asignación de evento | Greenway App · {event.name}",
        "html": (
            "<!doctype html><html lang='es'><body style='margin:0;background:#f1f5f9;font-family:Arial,sans-serif;color:#0f172a'>"
            "<main style='max-width:620px;margin:24px auto;padding:0 16px'>"
            "<section style='overflow:hidden;border:1px solid #dbe4e8;border-radius:18px;background:#fff'>"
            "<header style='padding:24px 28px;background:#087f68;color:#fff'>"
            "<p style='margin:0 0 8px;font-size:12px;font-weight:bold;letter-spacing:2px'>GREENWAY APP</p>"
            "<h1 style='margin:0;font-size:24px'>Te asignaron a un evento</h1></header>"
            f"<div style='padding:26px 28px'><p style='margin:0 0 18px'>Hola <strong>{safe_name}</strong>, tienes una nueva asignación:</p>"
            f"<h2 style='margin:0 0 12px;font-size:20px'>{safe_event}</h2>"
            f"<table style='width:100%;border-collapse:collapse'>{rows_html}</table>{description_html}"
            "<p style='margin:22px 0 0;padding:14px;border-radius:10px;background:#ecfdf5;color:#065f46;font-size:14px'>"
            "También se solicitó a Google Calendar que agregue este evento a tu calendario. Este correo es un aviso directo de Greenway App.</p>"
            "</div><footer style='padding:16px 28px;background:#f8fafc;color:#64748b;font-size:12px'>Greenway App · Organización de eventos</footer>"
            "</section></main></body></html>"
        ),
        "text": _text_body(name, details, description),
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                _RESEND_EMAILS_URL,
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Idempotency-Key": f"event-staff-invitation/{assignment.id}",
                },
                json=payload,
            )
            response.raise_for_status()
            response_id = response.json().get("id")
        logger.info("staff_event_email_accepted assignment_id=%s resend_id=%s", assignment.id, response_id)
        return "ACCEPTED", str(response_id) if response_id else None, None
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "staff_event_email_rejected assignment_id=%s status=%s",
            assignment.id,
            exc.response.status_code,
        )
        if exc.response.status_code in {429, 500, 502, 503, 504}:
            return "ERROR", None, "Resend está temporalmente ocupado; puedes reintentar el envío."
        return "ERROR", None, "Resend rechazó el correo; revisa el destinatario y la configuración del remitente."
    except (httpx.RequestError, ValueError):
        logger.exception("staff_event_email_failed assignment_id=%s", assignment.id)
        return "ERROR", None, "No se pudo confirmar el correo con Resend; puedes reintentar el envío."
    except Exception:
        logger.exception("staff_event_email_preparation_failed assignment_id=%s", assignment.id)
        return "ERROR", None, "No se pudo preparar el correo; puedes reintentar el envío."


def _text_body(name: str, details: list[tuple[str, str | None]], description: str) -> str:
    lines = [f"Hola {name or 'Hola'}, te asignaron a un evento de Greenway App:", ""]
    lines.extend(f"{label}: {value}" for label, value in details if value)
    if description:
        lines.extend(("", "Información del evento", description))
    lines.extend(("", "También se solicitó a Google Calendar que agregue este evento a tu calendario."))
    return "\n".join(lines)


def _local_date(value: datetime) -> date:
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(_CHILE_TZ).date()


def _format_spanish_date(value: date) -> str:
    return f"{_WEEKDAYS_ES[value.weekday()]} {value.day} de {_MONTHS_ES[value.month - 1]} de {value.year}"
