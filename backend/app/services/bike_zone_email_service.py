import base64
import html
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.utils.simple_qr import make_qr_png

logger = logging.getLogger(__name__)
RESEND_EMAILS_URL = "https://api.resend.com/emails"
QR_CONTENT_ID = "bike-zone-qr"


@dataclass(frozen=True)
class BikeZoneEmail:
    recipient: str
    participant_name: str | None
    event_name: str
    session_name: str | None
    code: str


def send_bike_zone_email(email: BikeZoneEmail) -> None:
    """Send the Bike Zone credential without affecting the form submission."""
    if not settings.resend_api_key:
        logger.warning("Bike Zone email skipped: RESEND_API_KEY is not configured")
        return

    try:
        target_url = f"{_public_app_url()}/bike-zone/{email.code}"
        qr_png = make_qr_png(target_url)
        payload = {
            "from": settings.email_from,
            "to": [email.recipient],
            "subject": f"Tu código Bike Zone | Greenway App — {email.event_name}",
            "html": _html_body(email, target_url),
            "text": _text_body(email, target_url),
            "attachments": [
                {
                    "content": base64.b64encode(qr_png).decode("ascii"),
                    "filename": f"bike-zone-{email.code}.png",
                    "content_type": "image/png",
                    "content_id": QR_CONTENT_ID,
                }
            ],
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                RESEND_EMAILS_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
            response.raise_for_status()
    except Exception:
        logger.exception("Could not send Bike Zone email to %s", email.recipient)


def _public_app_url() -> str:
    return (settings.public_app_url or settings.official_frontend_url).rstrip("/")


def _html_body(email: BikeZoneEmail, target_url: str) -> str:
    name = html.escape(email.participant_name or "Participante")
    event_name = html.escape(email.event_name or "Greenway App")
    session_name = html.escape(email.session_name or "")
    code = html.escape(email.code)
    safe_target = html.escape(target_url, quote=True)
    session_row = (
        f'<p style="margin:6px 0;color:#64748b;font-size:14px;">{session_name}</p>'
        if session_name
        else ""
    )
    return f"""
<!doctype html>
<html lang="es">
  <body style="margin:0;background:#f1f5f9;font-family:Arial,sans-serif;color:#0f172a;">
    <div style="max-width:600px;margin:0 auto;padding:32px 16px;">
      <div style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 8px 30px rgba(15,23,42,.10);">
        <div style="background:#047857;padding:28px 32px;color:#ffffff;">
          <p style="margin:0 0 8px;font-size:13px;letter-spacing:2px;text-transform:uppercase;opacity:.85;">Greenway App</p>
          <h1 style="margin:0;font-size:28px;">Tu acceso Bike Zone</h1>
        </div>
        <div style="padding:30px 32px;text-align:center;">
          <p style="margin:0;font-size:17px;">Hola, <strong>{name}</strong></p>
          <p style="margin:8px 0 0;color:#475569;">Este es tu código para <strong>{event_name}</strong>.</p>
          {session_row}
          <div style="margin:26px auto 20px;padding:18px;border:2px solid #a7f3d0;border-radius:16px;background:#ecfdf5;max-width:300px;">
            <p style="margin:0;color:#047857;font-size:12px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;">Código Bike Zone</p>
            <p style="margin:10px 0 0;color:#065f46;font-size:36px;font-weight:800;letter-spacing:5px;">{code}</p>
          </div>
          <p style="margin:0 0 12px;color:#475569;">También puedes presentar este código QR:</p>
          <img src="cid:{QR_CONTENT_ID}" alt="Código QR Bike Zone" width="220" height="220" style="display:block;margin:0 auto;width:220px;height:220px;" />
          <p style="margin:18px 0 0;font-size:13px;color:#64748b;">Si el QR no se muestra, usa el código escrito arriba.</p>
          <a href="{safe_target}" style="display:inline-block;margin-top:22px;padding:12px 18px;border-radius:10px;background:#059669;color:#ffffff;text-decoration:none;font-weight:bold;">Abrir mi código Bike Zone</a>
        </div>
        <div style="padding:18px 32px;background:#f8fafc;color:#64748b;font-size:12px;text-align:center;">
          Presenta este correo al equipo Bike Zone al llegar al evento.
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()


def _text_body(email: BikeZoneEmail, target_url: str) -> str:
    participant = email.participant_name or "Participante"
    session = f"\nProgramación: {email.session_name}" if email.session_name else ""
    return (
        f"Hola, {participant}.\n\n"
        f"Tu código Bike Zone para {email.event_name}.{session}\n\n"
        f"Código: {email.code}\n"
        f"Abre tu código: {target_url}\n\n"
        "También encontrarás un código QR en este correo."
    )
