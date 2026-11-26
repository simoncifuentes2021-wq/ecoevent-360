from datetime import UTC, date, datetime, timedelta
import hashlib
import logging
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.core import Event, EventStaff
from app.models.enums import EventStatus
from app.models.google_calendar import GoogleCalendarConnection
from app.services.google_calendar_security import token_fernet
from app.services.staff_invitation_email_service import send_staff_event_email

logger = logging.getLogger(__name__)
_CALENDAR_API = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_CHILE_TZ = ZoneInfo("America/Santiago")
_WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


class GoogleCalendarSyncError(Exception):
    pass


def _local_date(value: datetime) -> date:
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(_CHILE_TZ).date()


def _all_day_bounds(event: Event) -> tuple[str, str]:
    start = _local_date(event.start_date)
    inclusive_end = _local_date(event.end_date)
    return start.isoformat(), (max(start, inclusive_end) + timedelta(days=1)).isoformat()


def _format_spanish_date(value: date) -> str:
    return f"{_WEEKDAYS_ES[value.weekday()]} {value.day} de {_MONTHS_ES[value.month - 1]} de {value.year}"


def _event_description(event: Event) -> str:
    start = _local_date(event.start_date)
    end = _local_date(event.end_date)
    lines = [
        "APP GREENWAY",
        "Invitación para personal asignado",
        "",
        f"Evento: {event.name}",
        f"Cliente: {event.client.business_name}" if event.client else "",
        f"Fechas: {_format_spanish_date(start)}" if start == end else f"Fechas: {_format_spanish_date(start)} al {_format_spanish_date(end)}",
    ]
    lines = [line for line in lines if line]
    location = ", ".join(
        dict.fromkeys(
            part.strip()
            for part in (event.location_name, event.address, event.city, event.region)
            if part and part.strip()
        )
    )
    if location:
        lines.append(f"Lugar: {location}")
    if event.event_type:
        lines.append(f"Tipo de evento: {event.event_type.strip()}")
    if event.description and event.description.strip():
        lines.extend(("", "Información del evento", event.description.strip()))
    lines.extend(("", "Confirma tu asistencia respondiendo a esta invitación de Google Calendar."))
    return "\n".join(lines)


def _refresh_access_token(client: httpx.Client, connection: GoogleCalendarConnection) -> str:
    try:
        refresh_token = token_fernet().decrypt(connection.refresh_token_encrypted.encode()).decode()
    except Exception as exc:
        raise GoogleCalendarSyncError("No se pudo leer la autorización guardada. Desconecta y vuelve a conectar Google Calendar.") from exc

    try:
        response = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_calendar_client_id,
                "client_secret": settings.google_calendar_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        data = response.json()
    except (httpx.RequestError, ValueError) as exc:
        raise GoogleCalendarSyncError("No se pudo conectar con Google para renovar la autorización.") from exc
    if response.is_error or not data.get("access_token"):
        if data.get("error") == "invalid_grant":
            raise GoogleCalendarSyncError("La autorización de Google venció. Reconecta la cuenta desde Configuración.")
        raise GoogleCalendarSyncError("Google rechazó la autorización. Reconecta la cuenta desde Configuración.")
    return str(data["access_token"])


def _event_payload(event: Event, assignments: list[EventStaff]) -> dict[str, object]:
    start, end = _all_day_bounds(event)
    location_parts = [event.location_name, event.address, event.city, event.region]
    location = ", ".join(dict.fromkeys(part.strip() for part in location_parts if part and part.strip()))
    attendees = []
    seen = set()
    for assignment in assignments:
        email = (assignment.user.email if assignment.user else "").strip().lower()
        if email and email not in seen:
            attendees.append({"email": email})
            seen.add(email)
    payload: dict[str, object] = {
        "summary": f"App Greenway | {event.name}",
        "description": _event_description(event),
        "start": {"date": start},
        "end": {"date": end},
        "attendees": attendees,
    }
    if location:
        payload["location"] = location
    return payload


def _mark_assignments(assignments: list[EventStaff], status: str, error: str | None = None) -> None:
    sent_at = datetime.now(UTC).replace(tzinfo=None) if status == "SENT" else None
    for assignment in assignments:
        assignment.calendar_invitation_status = status
        assignment.calendar_invitation_error = error
        assignment.calendar_invitation_sent_at = sent_at


def _send_resend_notices(db: Session, event: Event, assignments: list[EventStaff]) -> dict[str, int]:
    accepted = 0
    failed = 0
    skipped = 0
    for assignment in assignments:
        if assignment.resend_invitation_status == "ACCEPTED":
            skipped += 1
            continue
        email_status, resend_id, error = send_staff_event_email(event, assignment)
        assignment.resend_invitation_status = email_status
        assignment.resend_invitation_id = resend_id
        assignment.resend_invitation_error = error
        assignment.resend_invitation_accepted_at = (
            datetime.now(UTC).replace(tzinfo=None) if email_status == "ACCEPTED" else None
        )
        accepted += email_status == "ACCEPTED"
        failed += email_status == "ERROR"
    db.commit()
    return {"accepted": accepted, "failed": failed, "skipped": skipped}


def _sync_result(
    *, calendar_ok: bool, calendar_message: str, email_summary: dict[str, int], count: int
) -> dict[str, object]:
    accepted = email_summary["accepted"]
    failed = email_summary["failed"]
    if accepted and failed:
        email_message = f"Resend aceptó {accepted} correo(s) y rechazó {failed}."
    elif accepted and email_summary["skipped"]:
        email_message = (
            f"Resend aceptó {accepted} correo(s) nuevo(s); "
            f"{email_summary['skipped']} ya estaban aceptados y no se duplicaron."
        )
    elif accepted:
        email_message = f"Resend aceptó el correo de aviso para {accepted} persona(s)."
    elif failed:
        email_message = f"Resend no pudo aceptar el correo de {failed} persona(s)."
    elif email_summary["skipped"]:
        email_message = "El aviso por Resend ya había sido aceptado; no se duplicó."
    else:
        email_message = "No había correos pendientes para Resend."
    return {
        "ok": calendar_ok and failed == 0,
        "calendar_ok": calendar_ok,
        "resend_ok": failed == 0,
        "message": f"{calendar_message} {email_message}",
        "count": count,
        "resend_accepted_count": accepted,
        "resend_failed_count": failed,
        "resend_skipped_count": email_summary["skipped"],
    }


def _safe_google_error(response: httpx.Response) -> str:
    logger.warning("Google Calendar API rejected event sync (status=%s)", response.status_code)
    if response.status_code in {401, 403}:
        return "Google rechazó el acceso. Reconecta la cuenta desde Configuración."
    if response.status_code == 404:
        return "El evento ya no está disponible en Google Calendar. Vuelve a intentar el envío."
    if response.status_code == 429 or response.status_code >= 500:
        return "Google Calendar está temporalmente ocupado. Puedes reintentar el envío."
    return "Google Calendar no pudo actualizar este evento. Revisa los datos e inténtalo de nuevo."


def sync_event_calendar(db: Session, event_id) -> dict[str, object]:
    event = db.scalar(
        select(Event)
        .options(
            selectinload(Event.client),
            selectinload(Event.staff_assignments).selectinload(EventStaff.user),
        )
        .where(Event.id == event_id)
    )
    if event is None:
        return {"ok": False, "message": "No se encontró el evento."}
    assignments = list(event.staff_assignments)
    connection = db.get(GoogleCalendarConnection, "primary")

    if event.status == EventStatus.CANCELLED:
        if not event.google_calendar_event_id:
            _mark_assignments(assignments, "CANCELLED")
            db.commit()
            return {"ok": True, "message": "El evento no tenía una invitación activa."}
        if connection is None:
            error = "El evento se canceló, pero Google Calendar está desconectado. Reconecta para avisar a las personas invitadas."
            _mark_assignments(assignments, "ERROR", error)
            db.commit()
            return {"ok": False, "message": error}
        try:
            with httpx.Client(timeout=20) as client:
                token = _refresh_access_token(client, connection)
                response = client.delete(
                    f"{_CALENDAR_API}/{event.google_calendar_event_id}",
                    params={"sendUpdates": "all"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code not in {200, 204, 404}:
                    raise GoogleCalendarSyncError(_safe_google_error(response))
            event.google_calendar_event_id = None
            _mark_assignments(assignments, "CANCELLED")
            db.commit()
            return {"ok": True, "message": "Se canceló la invitación de Google Calendar."}
        except (GoogleCalendarSyncError, httpx.RequestError) as exc:
            error = str(exc) if isinstance(exc, GoogleCalendarSyncError) else "No se pudo conectar con Google Calendar. Puedes reintentar."
            _mark_assignments(assignments, "ERROR", error)
            db.commit()
            return {"ok": False, "message": error}

    if not assignments:
        if event.google_calendar_event_id and connection:
            try:
                with httpx.Client(timeout=20) as client:
                    token = _refresh_access_token(client, connection)
                    response = client.delete(
                        f"{_CALENDAR_API}/{event.google_calendar_event_id}",
                        params={"sendUpdates": "all"},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if response.status_code not in {200, 204, 404}:
                        raise GoogleCalendarSyncError(_safe_google_error(response))
                event.google_calendar_event_id = None
                db.commit()
            except (GoogleCalendarSyncError, httpx.RequestError) as exc:
                return {"ok": False, "message": str(exc) if isinstance(exc, GoogleCalendarSyncError) else "No se pudo actualizar Google Calendar."}
        return {"ok": True, "message": "No hay personal asignado para invitar."}

    email_summary = _send_resend_notices(db, event, assignments)

    if connection is None:
        error = "Google Calendar no está conectado. Conecta la cuenta en Configuración y reintenta."
        _mark_assignments(assignments, "PENDING", error)
        db.commit()
        return _sync_result(calendar_ok=False, calendar_message=error, email_summary=email_summary, count=len(assignments))

    try:
        payload = _event_payload(event, assignments)
        client_name = event.client.business_name if event.client else None
        if client_name:
            payload["summary"] = f"App Greenway · {client_name} · {event.name}"
        deterministic_id = hashlib.sha256(f"ecoevent360:{event.id}".encode()).hexdigest()[:40]
        headers: dict[str, str]
        with httpx.Client(timeout=25) as client:
            token = _refresh_access_token(client, connection)
            headers = {"Authorization": f"Bearer {token}"}
            if event.google_calendar_event_id:
                response = client.patch(
                    f"{_CALENDAR_API}/{event.google_calendar_event_id}",
                    params={"sendUpdates": "all"},
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 404:
                    event.google_calendar_event_id = None
                elif response.is_error:
                    raise GoogleCalendarSyncError(_safe_google_error(response))

            if not event.google_calendar_event_id:
                payload["id"] = deterministic_id
                response = client.post(
                    _CALENDAR_API,
                    params={"sendUpdates": "all"},
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 409:
                    response = client.patch(
                        f"{_CALENDAR_API}/{deterministic_id}",
                        params={"sendUpdates": "all"},
                        headers=headers,
                        json={key: value for key, value in payload.items() if key != "id"},
                    )
                if response.is_error:
                    raise GoogleCalendarSyncError(_safe_google_error(response))
                remote = response.json()
                event.google_calendar_event_id = str(remote.get("id") or deterministic_id)

        _mark_assignments(assignments, "SENT")
        db.commit()
        return _sync_result(
            calendar_ok=True,
            calendar_message="Invitación solicitada a Google Calendar.",
            email_summary=email_summary,
            count=len(assignments),
        )
    except GoogleCalendarSyncError as exc:
        error = str(exc)
    except httpx.RequestError as exc:
        logger.warning("Google Calendar event request failed (%s)", type(exc).__name__)
        error = "No se pudo conectar con Google Calendar. Puedes reintentar el envío."
    except ValueError:
        logger.warning("Google Calendar returned an unreadable event response")
        error = "Google Calendar respondió con un resultado inesperado. Puedes reintentar el envío."

    _mark_assignments(assignments, "ERROR", error)
    db.commit()
    return _sync_result(calendar_ok=False, calendar_message=error, email_summary=email_summary, count=len(assignments))
