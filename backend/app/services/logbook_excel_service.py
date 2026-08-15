from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import PurePath
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.core import Event, EventStaff, User
from app.models.enums import LogbookAssignmentMode, LogbookInstanceStatus, LogbookVersionStatus, UserRole
from app.models.logbook import (
    LogbookAssignment, LogbookImportBatch, LogbookInstance, LogbookInstanceItem,
    LogbookTemplateVersion,
)
from app.models.enums import LogbookTemplateStatus
from app.services.logbook_service import audit
from app.core.permissions import can_manage_event

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_ROWS = 1000
MAX_DATES = 366
MAX_CELLS = 200_000
HEADER = "actividad"
MONTHS = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
          "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12}


@dataclass(frozen=True)
class ParsedActivity:
    source_row: int
    title: str


def _issue(code: str, message: str, *, row=None, column=None, value=None) -> dict:
    return {k: v for k, v in {"code": code, "message": message, "row": row,
                              "column": column, "value": value}.items() if v is not None}


def _infer_date(value, event: Event, epoch) -> tuple[date | None, str | None]:
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    if isinstance(value, (int, float)):
        try:
            return from_excel(value, epoch).date(), None
        except (TypeError, ValueError, OverflowError):
            return None, "Fecha Excel inválida"
    text = str(value or "").strip().lower().replace(".", "")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date(), None
        except ValueError:
            pass
    match = re.fullmatch(r"(\d{1,2})[-/ ]([a-záéíóú]{3,10})", text)
    if not match:
        return None, "Encabezado de fecha no reconocido"
    month = MONTHS.get(match.group(2)[:4].rstrip("t")) or MONTHS.get(match.group(2)[:3])
    if not month:
        return None, "Mes no reconocido"
    start, end = event.start_date.date(), event.end_date.date()
    candidates = []
    for year in range(start.year, end.year + 1):
        try:
            candidate = date(year, month, int(match.group(1)))
        except ValueError:
            return None, "Fecha inválida"
        if start <= candidate <= end:
            candidates.append(candidate)
    if len(candidates) != 1:
        return None, "El año no puede inferirse inequívocamente desde el evento"
    return candidates[0], None


def parse_xlsx(content: bytes, filename: str, event: Event) -> dict:
    errors, warnings = [], []
    safe_name = PurePath(filename or "planificacion.xlsx").name[:255]
    digest = hashlib.sha256(content).hexdigest()
    if not safe_name.lower().endswith(".xlsx"):
        return {"filename": safe_name, "file_sha256": digest, "warnings": [],
                "errors": [_issue("invalid_extension", "El archivo debe ser .xlsx")]}
    if len(content) > MAX_FILE_SIZE:
        return {"filename": safe_name, "file_sha256": digest, "warnings": [],
                "errors": [_issue("file_too_large", "El archivo excede 5 MB")]}
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
    except Exception:
        return {"filename": safe_name, "file_sha256": digest, "warnings": [],
                "errors": [_issue("corrupt_workbook", "El libro no es un XLSX válido")]}
    try:
        if not workbook.sheetnames:
            raise ValueError("empty")
        located = None
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(max_row=min(sheet.max_row, MAX_ROWS)):
                for cell in row:
                    if str(cell.value or "").strip().casefold() == HEADER:
                        located = sheet, cell.row, cell.column
                        break
                if located:
                    break
            if located:
                break
        if not located:
            errors.append(_issue("activity_header_missing", "No se encontró el encabezado Actividad"))
            return _result(safe_name, digest, None, [], [], errors, warnings)
        sheet, header_row, activity_col = located
        if sheet.max_row > MAX_ROWS or sheet.max_column - activity_col > MAX_DATES or sheet.max_row * sheet.max_column > MAX_CELLS:
            errors.append(_issue("limits_exceeded", "La hoja excede los límites permitidos"))
            return _result(safe_name, digest, sheet.title, [], [], errors, warnings)
        dates, seen_dates = [], {}
        for col in range(activity_col + 1, sheet.max_column + 1):
            raw = sheet.cell(header_row, col).value
            if raw is None or str(raw).strip() == "":
                continue
            parsed, reason = _infer_date(raw, event, workbook.epoch)
            if reason:
                errors.append(_issue("invalid_date", reason, row=header_row, column=col, value=str(raw)[:100]))
                continue
            if parsed in seen_dates:
                errors.append(_issue("duplicate_date", "Fecha duplicada", row=header_row, column=col, value=parsed.isoformat()))
            else:
                seen_dates[parsed] = col
                dates.append((parsed, col))
            if not (event.start_date.date() <= parsed <= event.end_date.date()):
                errors.append(_issue("date_outside_event", "Fecha fuera del evento", row=header_row, column=col, value=parsed.isoformat()))
        activities, seen_titles, days = [], {}, {day: [] for day, _ in dates}
        for row in range(header_row + 1, sheet.max_row + 1):
            title_raw = sheet.cell(row, activity_col).value
            values = [(day, col, sheet.cell(row, col).value) for day, col in dates]
            marked = any(str(value or "").strip().casefold() == "x" for _, _, value in values)
            title = str(title_raw or "").strip()
            if not title:
                if marked:
                    errors.append(_issue("missing_activity", "Fila programada sin actividad", row=row, column=activity_col))
                continue
            key = title.casefold()
            if key in seen_titles:
                warnings.append(_issue("duplicate_activity", f"Actividad duplicada; también aparece en fila {seen_titles[key]}", row=row, column=activity_col, value=title))
            else:
                seen_titles[key] = row
            activity = ParsedActivity(row, title[:180])
            activities.append(activity)
            for day, col, value in values:
                normalized = str(value or "").strip()
                if not normalized:
                    continue
                if normalized.casefold() == "x":
                    days[day].append(activity)
                else:
                    warnings.append(_issue("unexpected_value", "Se esperaba X o una celda vacía", row=row, column=col, value=normalized[:100]))
        scheduled = sum(map(len, days.values()))
        if not scheduled:
            errors.append(_issue("nothing_scheduled", "No hay actividades programadas"))
        for day, items in days.items():
            if not items:
                warnings.append(_issue("empty_date", "La fecha no contiene actividades", value=day.isoformat()))
        return _result(safe_name, digest, sheet.title, activities, days, errors, warnings)
    finally:
        workbook.close()


def _result(filename, digest, sheet, activities, days, errors, warnings):
    dates = sorted(days) if isinstance(days, dict) else []
    scheduled = sum(len(value) for value in days.values()) if isinstance(days, dict) else 0
    return {"filename": filename, "file_sha256": digest, "sheet_name": sheet,
            "activities_count": len(activities), "dates_count": len(dates),
            "scheduled_items_count": scheduled,
            "instances_to_create": sum(bool(days[d]) for d in dates),
            "date_range": {"from": dates[0].isoformat(), "to": dates[-1].isoformat()} if dates else None,
            "warnings": warnings, "errors": errors,
            "days": [{"date": d.isoformat(), "activities": [{"source_row": a.source_row, "title": a.title} for a in days[d]]} for d in dates]}


def preview(db: Session, event_id: UUID, content: bytes, filename: str, current):
    if not can_manage_event(current, event_id, db):
        raise HTTPException(403, "Insufficient role")
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    return parse_xlsx(content, filename, event)


def import_xlsx(db: Session, event_id: UUID, content: bytes, filename: str, config, current):
    result = preview(db, event_id, content, filename, current)
    if result["errors"]:
        raise HTTPException(422, detail={"message": "Excel validation failed", **result})
    if result["file_sha256"] != config.file_sha256:
        raise HTTPException(409, "El archivo no coincide con el preview")
    version = db.get(LogbookTemplateVersion, config.template_version_id)
    if not version or version.status != LogbookVersionStatus.PUBLISHED or version.template.status == LogbookTemplateStatus.ARCHIVED:
        raise HTTPException(422, "Se requiere una versión publicada")
    staff = set(db.scalars(select(EventStaff.user_id).join(User).where(EventStaff.event_id == event_id, User.is_active.is_(True))).all())
    if not set(config.participant_ids) <= staff:
        raise HTTPException(422, "Todos los participantes deben pertenecer al evento")
    if config.supervisor_id:
        supervisor = db.scalar(select(User).join(EventStaff, EventStaff.user_id == User.id).where(EventStaff.event_id == event_id, User.id == config.supervisor_id, User.role == UserRole.SUPERVISOR, User.is_active.is_(True)))
        if not supervisor:
            raise HTTPException(422, "Supervisor inválido")
    try:
        zone = ZoneInfo(config.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(422, "Timezone inválida") from exc
    batch = LogbookImportBatch(event_id=event_id, original_filename=result["filename"], file_sha256=result["file_sha256"], sheet_name=result["sheet_name"], activities_count=result["activities_count"], dates_count=result["dates_count"], scheduled_items_count=result["scheduled_items_count"], instances_created=result["instances_to_create"], imported_by=current.id, configuration={"timezone": config.timezone, "participant_count": len(config.participant_ids), "client_visibility": config.client_visibility})
    db.add(batch)
    try:
        db.flush()
        created = []
        for day in result["days"]:
            if not day["activities"]:
                continue
            operational_date = date.fromisoformat(day["date"])
            opens_at = datetime.combine(operational_date, config.opens_at_local, zone).astimezone(timezone.utc)
            due_at = datetime.combine(operational_date, config.due_at_local, zone).astimezone(timezone.utc)
            if due_at <= opens_at:
                raise HTTPException(422, "La hora de vencimiento debe ser posterior a la apertura")
            instance = LogbookInstance(event_id=event_id, template_id=version.template_id, template_version_id=version.id, name=f"{config.base_name} · {operational_date:%d/%m/%Y}", operational_stage=version.template.operational_stage, assignment_mode=LogbookAssignmentMode.SHARED, opens_at=opens_at, due_at=due_at, supervisor_id=config.supervisor_id, status=LogbookInstanceStatus.SCHEDULED if opens_at > datetime.now(timezone.utc) else LogbookInstanceStatus.OPEN, client_visibility=config.client_visibility, created_by=current.id, occurrence_date=operational_date, import_batch_id=batch.id)
            db.add(instance)
            db.flush()
            for uid in config.participant_ids:
                db.add(LogbookAssignment(logbook_instance_id=instance.id, user_id=uid))
            for position, item in enumerate(day["activities"]):
                db.add(LogbookInstanceItem(instance_id=instance.id, title=item["title"], source_row=item["source_row"], position=position))
            created.append(instance.id)
        audit(db, current, "LOGBOOK_XLSX_IMPORTED", "LogbookImportBatch", batch.id, event_id=event_id, new={"instances_created": len(created), "file_sha256": result["file_sha256"]})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Este archivo ya fue importado para el evento") from exc
    except Exception:
        db.rollback()
        raise
    return {"batch_id": batch.id, "instances_created": len(created), "instance_ids": created}
