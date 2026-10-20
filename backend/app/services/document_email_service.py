from __future__ import annotations

import html
import logging
import base64

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
RESEND_EMAILS_URL = "https://api.resend.com/emails"


def _resolve_recipient(recipient: str) -> str | None:
    if settings.app_env.lower() == "production":
        return recipient
    if not settings.documents_allow_local_emails:
        logger.info("Document email skipped outside production")
        return None
    test_recipient = (settings.documents_local_email_recipient or "").strip()
    if not test_recipient:
        raise RuntimeError(
            "DOCUMENTS_LOCAL_EMAIL_RECIPIENT debe configurarse para probar correos en local"
        )
    return test_recipient


def send_document_pair_email(
    *,
    recipient: str,
    worker_name: str,
    event_name: str,
    contract_title: str,
    portal_url: str,
    epp_title: str,
    expires_at: str,
    idempotency_key: str | None = None,
) -> bool:
    """Send both private document links in one email; never email local-only URLs."""
    delivery_recipient = _resolve_recipient(recipient)
    if not delivery_recipient:
        return False
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY no está configurada para enviar documentos")

    safe_worker = html.escape(worker_name)
    safe_event = html.escape(event_name)
    safe_contract_title = html.escape(contract_title)
    safe_epp_title = html.escape(epp_title)
    safe_portal_url = html.escape(portal_url, quote=True)
    subject = f"Documentos de contratación | Greenway App · {event_name}"
    body = f"""
<!doctype html><html lang="es"><body style="margin:0;background:#f1f5f9;font-family:Arial,sans-serif;color:#0f172a">
<main style="max-width:620px;margin:24px auto;background:#fff;border-radius:18px;overflow:hidden">
  <header style="padding:28px;background:#065f46;color:#fff"><p style="margin:0;font-size:12px;letter-spacing:2px">GREENWAY APP</p><h1 style="margin:10px 0 0;font-size:24px">Tus documentos de contratación</h1></header>
  <section style="padding:28px"><p>Hola <strong>{safe_worker}</strong>,</p><p>Para la faena <strong>{safe_event}</strong>, revisa y completa el contrato y la recepción EPP desde un solo portal:</p>
    <article style="margin:18px 0;padding:22px;border:1px solid #dbe3ea;border-radius:12px"><h2 style="font-size:16px;margin-top:0">{safe_contract_title} + {safe_epp_title}</h2><p style="color:#475569">Valida tu RUT una sola vez y gestiona cada documento en el mismo acceso.</p><a href="{safe_portal_url}" style="display:inline-block;padding:12px 18px;background:#047857;color:#fff;text-decoration:none;border-radius:8px">Abrir mis documentos</a></article>
    <p style="font-size:13px;color:#64748b">Este enlace personal solicita validar tu RUT y vence el {html.escape(expires_at)}. No lo compartas.</p>
  </section><footer style="padding:18px 28px;background:#f8fafc;color:#64748b;font-size:12px;text-align:center">Greenway App · Firma electrónica simulada; no equivale a una firma electrónica legal.</footer>
</main></body></html>""".strip()
    text_body = (
        f"Hola {worker_name}. Para la faena {event_name}, gestiona {contract_title} y {epp_title} desde un solo portal: {portal_url}\n\n"
        f"El enlace es personal, solicita validar tu RUT y vence el {expires_at}."
    )
    with httpx.Client(timeout=20.0) as client:
        headers = {"Authorization": f"Bearer {settings.resend_api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        response = client.post(
            RESEND_EMAILS_URL,
            headers=headers,
            json={
                "from": settings.email_from,
                "to": [delivery_recipient],
                "subject": subject,
                "html": body,
                "text": text_body,
            },
        )
        response.raise_for_status()
    logger.info("Document pair accepted by Resend")
    return True


def send_document_signature_link_email(
    *, recipient: str, worker_name: str, event_name: str, document_title: str,
    portal_url: str, expires_at: str,
) -> bool:
    """Email the private signing link for one document."""
    delivery_recipient = _resolve_recipient(recipient)
    if not delivery_recipient:
        return False
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY no está configurada para enviar documentos")

    safe_worker = html.escape(worker_name)
    safe_event = html.escape(event_name)
    safe_title = html.escape(document_title)
    safe_url = html.escape(portal_url, quote=True)
    safe_expiry = html.escape(expires_at)
    payload = {
        "from": settings.email_from,
        "to": [delivery_recipient],
        "subject": f"Documento pendiente de firma | Greenway App · {event_name}",
        "html": (
            "<!doctype html><html lang=\"es\"><body style=\"margin:0;background:#f1f5f9;font-family:Arial,sans-serif;color:#0f172a\">"
            "<main style=\"max-width:620px;margin:24px auto;background:#fff;border-radius:18px;overflow:hidden\">"
            "<header style=\"padding:28px;background:#065f46;color:#fff\"><p style=\"margin:0;font-size:12px;letter-spacing:2px\">GREENWAY APP</p><h1 style=\"margin:10px 0 0;font-size:24px\">Documento para revisar y firmar</h1></header>"
            f"<section style=\"padding:28px\"><p>Hola <strong>{safe_worker}</strong>,</p>"
            f"<p>Tienes un documento pendiente para la faena <strong>{safe_event}</strong>.</p>"
            f"<article style=\"margin:18px 0;padding:22px;border:1px solid #dbe3ea;border-radius:12px\"><h2 style=\"font-size:16px;margin-top:0\">{safe_title}</h2>"
            f"<a href=\"{safe_url}\" style=\"display:inline-block;padding:12px 18px;background:#047857;color:#fff;text-decoration:none;border-radius:8px\">Revisar y firmar documento</a></article>"
            f"<p style=\"font-size:13px;color:#64748b\">Este enlace es personal, solicita validar tu RUT y vence el {safe_expiry}. No lo compartas.</p>"
            "</section><footer style=\"padding:18px 28px;background:#f8fafc;color:#64748b;font-size:12px;text-align:center\">Greenway App</footer></main></body></html>"
        ),
        "text": (
            f"Hola {worker_name}. Tienes un documento pendiente de revisar y firmar: {document_title}, "
            f"para {event_name}. Abre este enlace personal: {portal_url}. Vence el {expires_at}."
        ),
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            RESEND_EMAILS_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
        )
        response.raise_for_status()
    logger.info("Single document signature link accepted by Resend")
    return True


def send_signed_document_copy_email(
    *, recipient: str, worker_name: str, document_title: str, event_name: str,
    pdf_content: bytes, filename: str,
) -> bool:
    """Email the immutable, completed PDF to the worker's personal email."""
    delivery_recipient = _resolve_recipient(recipient)
    if not delivery_recipient:
        return False
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY no está configurada para enviar documentos")
    safe_name = html.escape(worker_name)
    safe_title = html.escape(document_title)
    safe_event = html.escape(event_name)
    text_body = (
        f"Hola {worker_name}. Adjuntamos la copia final firmada de {document_title} "
        f"para {event_name}. Conserva este correo y el archivo PDF adjunto."
    )
    payload = {
        "from": settings.email_from,
        "to": [delivery_recipient],
        "subject": f"Copia firmada: {document_title} | Greenway App",
        "html": (
            "<!doctype html><html lang=\"es\"><body style=\"font-family:Arial,sans-serif;color:#0f172a\">"
            f"<h2>Documento firmado</h2><p>Hola <strong>{safe_name}</strong>,</p>"
            f"<p>Adjuntamos la copia final de <strong>{safe_title}</strong> para la faena "
            f"<strong>{safe_event}</strong>.</p><p>Guarda este correo y el PDF adjunto.</p>"
            "<p style=\"color:#64748b;font-size:12px\">Greenway App</p></body></html>"
        ),
        "text": text_body,
        "attachments": [{
            "filename": filename,
            "content_type": "application/pdf",
            "content": base64.b64encode(pdf_content).decode("ascii"),
        }],
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            RESEND_EMAILS_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
        )
        response.raise_for_status()
    logger.info("Signed document copy accepted by Resend")
    return True


def send_signed_document_bundle_email(
    *, recipient: str, worker_name: str, event_name: str, attachments: list[dict[str, object]],
) -> bool:
    """Send a single email containing every final PDF in a signed document bundle."""
    delivery_recipient = _resolve_recipient(recipient)
    if not delivery_recipient:
        return False
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY no está configurada para enviar documentos")
    safe_name = html.escape(worker_name)
    safe_event = html.escape(event_name)
    titles = [str(item["title"]) for item in attachments]
    safe_titles = ", ".join(html.escape(title) for title in titles)
    payload = {
        "from": settings.email_from,
        "to": [delivery_recipient],
        "subject": f"Tus documentos firmados | Greenway App · {event_name}",
        "html": (
            "<!doctype html><html lang=\"es\"><body style=\"font-family:Arial,sans-serif;color:#0f172a\">"
            f"<h2>Documentos firmados</h2><p>Hola <strong>{safe_name}</strong>,</p>"
            f"<p>Adjuntamos en este único correo tus documentos finales de la faena "
            f"<strong>{safe_event}</strong>: {safe_titles}.</p>"
            "<p>Conserva este correo y los archivos PDF adjuntos.</p>"
            "<p style=\"color:#64748b;font-size:12px\">Greenway App</p></body></html>"
        ),
        "text": (
            f"Hola {worker_name}. Adjuntamos en este correo tus documentos firmados "
            f"para {event_name}: {', '.join(titles)}. Conserva los archivos PDF adjuntos."
        ),
        "attachments": [
            {
                "filename": str(item["filename"]),
                "content_type": "application/pdf",
                "content": base64.b64encode(bytes(item["content"])).decode("ascii"),
            }
            for item in attachments
        ],
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            RESEND_EMAILS_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
        )
        response.raise_for_status()
    logger.info("Signed document bundle accepted by Resend")
    return True
