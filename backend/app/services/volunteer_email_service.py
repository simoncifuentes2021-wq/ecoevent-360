from __future__ import annotations

import html
import logging
from decimal import Decimal

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
RESEND_EMAILS_URL = "https://api.resend.com/emails"


def _kg(value: Decimal | str) -> str:
    return f"{Decimal(value):,.3f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")


def _deliver(payload: dict) -> tuple[bool, str | None]:
    if not settings.resend_api_key:
        logger.warning("volunteer_email_skipped reason=resend_not_configured")
        return False, "El correo no está configurado"
    try:
        response = httpx.post(
            RESEND_EMAILS_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        return True, None
    except Exception:
        logger.exception("volunteer_email_delivery_failed")
        return False, "El proveedor de correo no aceptó el mensaje"


def send_contribution_email(context: dict) -> tuple[bool, str | None]:
    recipient = context["recipient"]
    name = html.escape(context["volunteer_name"])
    activation = html.escape(context["activation_name"])
    event = html.escape(context["event_name"])
    rows_html = "".join(
        f"<tr><td style='padding:8px 0;border-bottom:1px solid #e2e8f0'>{html.escape(item['material'])}</td>"
        f"<td style='padding:8px 0;border-bottom:1px solid #e2e8f0;text-align:right'>{_kg(item['weight_kg'])} kg</td></tr>"
        for item in context["items"]
    )
    rows_text = "\n".join(f"{item['material']}: {_kg(item['weight_kg'])} kg" for item in context["items"])
    impact_url = html.escape(context["impact_url"], quote=True)
    payload = {
        "from": settings.email_from,
        "to": [recipient],
        "subject": f"Registramos tu aporte | {context['activation_name']}",
        "html": f"""<!doctype html><html lang='es'><body style='font-family:Arial,sans-serif;background:#f1f5f9;color:#0f172a;padding:24px'>
          <main style='max-width:600px;margin:auto;background:white;border-radius:16px;padding:28px'>
          <p style='color:#047857;font-weight:bold'>GREENWAY APP · RECICLAJE</p><h1 style='font-size:24px'>¡Gracias por participar, {name}!</h1>
          <p>Registramos tu aporte en <strong>{activation}</strong> · {event}.</p>
          <table style='width:100%;border-collapse:collapse'>{rows_html}</table>
          <p style='font-size:18px'><strong>Total de esta entrega: {_kg(context['total_weight_kg'])} kg</strong></p>
          <p>Tu aporte histórico: <strong>{_kg(context['accumulated_weight_kg'])} kg</strong></p>
          <p><a href='{impact_url}' style='display:inline-block;padding:12px 18px;background:#047857;color:white;border-radius:8px;text-decoration:none'>Ver mi aporte</a></p>
          <p style='font-size:12px;color:#64748b'>Este enlace privado permite consultar tu historial. No lo compartas.</p>
          </main></body></html>""",
        "text": (
            f"Hola, {context['volunteer_name']}. Registramos tu aporte en {context['activation_name']} ({context['event_name']}).\n\n"
            f"{rows_text}\n\nTotal de esta entrega: {_kg(context['total_weight_kg'])} kg\n"
            f"Tu aporte histórico: {_kg(context['accumulated_weight_kg'])} kg\n\n"
            f"Consulta tu historial privado: {context['impact_url']}\nNo compartas este enlace."
        ),
    }
    return _deliver(payload)


def send_registration_email(context: dict) -> tuple[bool, str | None]:
    name = html.escape(context["volunteer_name"])
    activation = html.escape(context["activation_name"])
    event = html.escape(context["event_name"])
    code = html.escape(context["volunteer_code"])
    impact_url = html.escape(context["impact_url"], quote=True)
    return _deliver({
        "from": settings.email_from,
        "to": [context["recipient"]],
        "subject": f"Inscripción confirmada | {context['activation_name']}",
        "html": f"""<!doctype html><html lang='es'><body style='font-family:Arial,sans-serif;background:#f1f5f9;color:#0f172a;padding:24px'>
          <main style='max-width:580px;margin:auto;background:white;border-radius:16px;padding:28px'>
          <p style='color:#047857;font-weight:bold'>GREENWAY APP</p><h1>¡Gracias por inscribirte, {name}!</h1>
          <p>Tu participación quedó registrada en <strong>{activation}</strong> · {event}.</p>
          <p>Tu código de voluntario es <strong>{code}</strong>.</p>
          <p><a href='{impact_url}'>Consulta tu historial de aportes</a></p>
          <p style='font-size:12px;color:#64748b'>El enlace de historial es privado. No lo compartas.</p>
          </main></body></html>""",
        "text": f"Hola, {context['volunteer_name']}. Tu inscripción en {context['activation_name']} quedó confirmada. Código: {context['volunteer_code']}. Historial privado: {context['impact_url']}",
    })
