from __future__ import annotations

import html
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_overdue_checklist_email(*, recipient: str, name: str, event_name: str, title: str, due_at: str) -> bool:
    if not settings.resend_api_key:
        logger.error("field_checklist_reminder_failed reason=resend_not_configured recipient=%s", recipient)
        return False

    safe_name, safe_event, safe_title = map(html.escape, (name, event_name, title))
    payload = {
        "from": settings.email_from,
        "to": [recipient],
        "subject": f"Actividad pendiente: {title}",
        "html": (
            "<!doctype html><html lang='es'><body style='font-family:Arial,sans-serif;background:#f1f5f9;color:#0f172a;padding:24px'>"
            "<main style='max-width:600px;margin:auto;background:white;border-radius:16px;padding:28px'>"
            "<p style='color:#047857;font-weight:bold'>GREENWAY · CHECKLIST DE TERRENO</p>"
            f"<h2>Hola, {safe_name}</h2><p>Esta actividad de <strong>{safe_event}</strong> sigue pendiente:</p>"
            f"<p style='padding:14px;background:#f8fafc;border-radius:10px'><strong>{safe_title}</strong><br>"
            f"Hora programada: {html.escape(due_at)}</p><p>Cuando puedas, actualiza su estado en Greenway.</p>"
            "</main></body></html>"
        ),
        "text": f"Hola, {name}. La actividad '{title}' de {event_name} sigue pendiente. Hora programada: {due_at}. Actualiza su estado en Greenway.",
    }
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("field_checklist_reminder_delivery_failed recipient=%s", recipient)
        return False
