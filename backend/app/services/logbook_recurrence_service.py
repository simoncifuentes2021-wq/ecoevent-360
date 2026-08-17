import calendar
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event
from app.core.time import chile_today
from app.models.audit_log import AuditLog
from app.models.core import Event, EventStaff, EventZone, User
from app.models.enums import (
    LogbookAssignmentStatus,
    LogbookInstanceStatus,
    LogbookRecurrenceEndMode,
    LogbookRecurrenceExceptionType,
    LogbookRecurrenceFrequency,
    LogbookRecurrenceStatus,
    LogbookTemplateStatus,
    LogbookVersionStatus,
    UserRole,
)
from app.models.logbook import (
    LogbookAssignment,
    LogbookEvidence,
    LogbookInstance,
    LogbookRecurrenceException,
    LogbookRecurrenceParticipant,
    LogbookRecurrenceSeries,
    LogbookResponse,
    LogbookReviewHistory,
    LogbookTemplateVersion,
)

logger = logging.getLogger(__name__)
MAX_OCCURRENCES = 500
PREGENERATE_LIMIT = 100
WINDOW_WEEKS = 12


def fail(status: int, detail: str):
    raise HTTPException(status_code=status, detail=detail)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        fail(422, "Unknown IANA timezone")


def _valid_local_datetime(day: date, local_time, timezone: str) -> datetime:
    zone = _zone(timezone)
    local = datetime.combine(day, local_time).replace(tzinfo=zone, fold=0)
    round_trip = local.astimezone(UTC).astimezone(zone)
    if round_trip.replace(tzinfo=None) != local.replace(tzinfo=None):
        fail(422, f"Local time does not exist in {timezone} on {day.isoformat()}")
    return local.astimezone(UTC)


def calculate_occurrence_dates(rule, *, limit: int = MAX_OCCURRENCES) -> tuple[list[date], bool]:
    """Calculate dates without persistence. Monthly dates absent in a month are skipped."""
    if limit < 1 or limit > MAX_OCCURRENCES:
        fail(422, f"limit must be between 1 and {MAX_OCCURRENCES}")
    dates: list[date] = []
    cursor = rule.start_date
    wanted_count = rule.max_occurrences if rule.end_mode == LogbookRecurrenceEndMode.COUNT else None
    end_date = rule.end_date if rule.end_mode == LogbookRecurrenceEndMode.END_DATE else None

    def accepted(candidate: date) -> bool:
        return not end_date or candidate <= end_date

    if rule.frequency == LogbookRecurrenceFrequency.DAILY:
        while accepted(cursor) and (wanted_count is None or len(dates) < wanted_count):
            dates.append(cursor)
            if len(dates) > limit:
                break
            cursor += timedelta(days=rule.interval)
    elif rule.frequency == LogbookRecurrenceFrequency.WEEKLY:
        weekdays = set(rule.weekdays or [])
        while accepted(cursor) and (wanted_count is None or len(dates) < wanted_count):
            week_delta = (cursor - rule.start_date).days // 7
            if week_delta % rule.interval == 0 and cursor.weekday() in weekdays:
                dates.append(cursor)
                if len(dates) > limit:
                    break
            cursor += timedelta(days=1)
    else:
        month_index = rule.start_date.year * 12 + rule.start_date.month - 1
        day_of_month = rule.day_of_month or rule.start_date.day
        while wanted_count is None or len(dates) < wanted_count:
            year, month_zero = divmod(month_index, 12)
            month = month_zero + 1
            if day_of_month <= calendar.monthrange(year, month)[1]:
                candidate = date(year, month, day_of_month)
                if candidate >= rule.start_date:
                    if not accepted(candidate):
                        break
                    dates.append(candidate)
                    if len(dates) > limit:
                        break
            month_index += rule.interval
            if end_date and date(year, month, 1) > end_date:
                break
    truncated = len(dates) > limit
    return dates[:limit], truncated


def preview(payload):
    _valid_local_datetime(payload.start_date, payload.opens_at_local, payload.timezone)
    _valid_local_datetime(payload.start_date, payload.due_at_local, payload.timezone)
    dates, truncated = calculate_occurrence_dates(payload, limit=payload.limit)
    return {"dates": dates, "truncated": truncated}


def _audit(db: Session, series, action: str, actor, *, instance_id=None, metadata=None):
    clean = {k: v for k, v in (metadata or {}).items() if k not in {"storage_key", "token", "url"}}
    db.add(AuditLog(
        user_id=actor.id if actor else None, event_id=series.event_id, action=action,
        module="logbooks", entity_type="LogbookRecurrenceSeries",
        entity_id=instance_id or series.id, metadata_=clean,
        description="Operación de recurrencia de bitácora.",
    ))


def _validate_scope(db: Session, event_id: UUID, payload, current):
    if current.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPERVISOR} or not can_manage_event(current, event_id, db):
        fail(403, "Insufficient role")
    if not db.get(Event, event_id):
        fail(404, "Event not found")
    version = db.get(LogbookTemplateVersion, payload.template_version_id)
    if not version or version.status != LogbookVersionStatus.PUBLISHED:
        fail(422, "A published template version is required")
    # The frozen published version remains valid if the template is archived later.
    if version.template.status == LogbookTemplateStatus.ARCHIVED:
        fail(422, "An archived template cannot start a new recurrence")
    if payload.zone_id:
        zone = db.get(EventZone, payload.zone_id)
        if not zone or zone.event_id != event_id:
            fail(422, "Zone does not belong to event")
    active_staff = set(db.scalars(select(EventStaff.user_id).join(User).where(
        EventStaff.event_id == event_id, User.is_active.is_(True)
    )).all())
    if not set(payload.participant_ids) <= active_staff:
        fail(422, "All participants must be active event staff")
    if payload.supervisor_id:
        supervisor = db.scalar(select(User).join(EventStaff, EventStaff.user_id == User.id).where(
            EventStaff.event_id == event_id, User.id == payload.supervisor_id,
            User.role == UserRole.SUPERVISOR, User.is_active.is_(True),
        ))
        if not supervisor:
            fail(422, "Supervisor must be active event staff")
    _valid_local_datetime(payload.start_date, payload.opens_at_local, payload.timezone)
    _valid_local_datetime(payload.start_date, payload.due_at_local, payload.timezone)
    return version


def create_series(db: Session, event_id: UUID, payload, current):
    version = _validate_scope(db, event_id, payload, current)
    series = LogbookRecurrenceSeries(
        event_id=event_id, template_id=version.template_id, template_version_id=version.id,
        name=payload.name or version.template.name,
        operational_stage=version.template.operational_stage, zone_id=payload.zone_id,
        assignment_mode=payload.assignment_mode, supervisor_id=payload.supervisor_id,
        client_visibility=payload.client_visibility, frequency=payload.frequency,
        interval=payload.interval, weekdays=payload.weekdays, day_of_month=payload.day_of_month,
        start_date=payload.start_date, end_mode=payload.end_mode, end_date=payload.end_date,
        max_occurrences=payload.max_occurrences, opens_at_local=payload.opens_at_local,
        due_at_local=payload.due_at_local, timezone=payload.timezone,
        next_occurrence_date=payload.start_date, created_by=current.id,
    )
    db.add(series)
    db.flush()
    for user_id in payload.participant_ids:
        db.add(LogbookRecurrenceParticipant(
            series_id=series.id, event_id=event_id, user_id=user_id
        ))
    _audit(db, series, "LOGBOOK_RECURRENCE_CREATED", current, metadata={"frequency": payload.frequency.value, "participant_count": len(payload.participant_ids)})
    db.flush()
    generate_series_window(db, series.id, actor=current, commit=False)
    db.commit()
    return get_series(db, series.id, current)


def _series(db: Session, series_id: UUID, *, lock=False):
    query = select(LogbookRecurrenceSeries).where(LogbookRecurrenceSeries.id == series_id).options(
        selectinload(LogbookRecurrenceSeries.participants), selectinload(LogbookRecurrenceSeries.exceptions)
    )
    if lock:
        query = query.with_for_update()
    series = db.scalar(query)
    if not series:
        fail(404, "Recurrence series not found")
    return series


def _read(series, db):
    counts = dict(db.execute(select(LogbookInstance.status, func.count()).where(
        LogbookInstance.recurrence_series_id == series.id
    ).group_by(LogbookInstance.status)).all())
    return {
        **{column.name: getattr(series, column.name) for column in series.__table__.columns},
        "participant_ids": [item.user_id for item in series.participants],
        "occurrence_counts": {getattr(key, "value", str(key)): value for key, value in counts.items()},
    }


def get_series(db, series_id, current):
    series = _series(db, series_id)
    if not can_manage_event(current, series.event_id, db):
        fail(403, "Insufficient role")
    return _read(series, db)


def list_series(db, event_id, current):
    if not can_manage_event(current, event_id, db):
        fail(403, "Insufficient role")
    rows = db.scalars(select(LogbookRecurrenceSeries).where(
        LogbookRecurrenceSeries.event_id == event_id
    ).options(selectinload(LogbookRecurrenceSeries.participants)).order_by(
        LogbookRecurrenceSeries.created_at.desc()
    )).all()
    return [_read(series, db) for series in rows]


def _series_dates(series, limit=MAX_OCCURRENCES):
    return calculate_occurrence_dates(series, limit=limit)


def generate_series_window(db: Session, series_id: UUID, *, actor=None, through: date | None = None, commit=True):
    series = _series(db, series_id, lock=True)
    if series.status != LogbookRecurrenceStatus.ACTIVE:
        return {"generated": 0, "skipped": 0}
    all_dates, truncated = _series_dates(series)
    bounded = not truncated and len(all_dates) <= PREGENERATE_LIMIT
    horizon = through or (all_dates[-1] if bounded and all_dates else chile_today() + timedelta(weeks=WINDOW_WEEKS))
    existing = set(db.scalars(select(LogbookInstance.occurrence_date).where(
        LogbookInstance.recurrence_series_id == series.id
    )).all())
    exceptions = {item.original_date for item in series.exceptions}
    active_staff = set(db.scalars(select(EventStaff.user_id).join(User).where(
        EventStaff.event_id == series.event_id, User.is_active.is_(True)
    )).all())
    participant_ids = [item.user_id for item in series.participants if item.user_id in active_staff]
    generated = skipped = 0
    for occurrence_date in all_dates:
        if occurrence_date > horizon:
            series.next_occurrence_date = occurrence_date
            break
        if occurrence_date in existing or occurrence_date in exceptions:
            continue
        if not participant_ids:
            db.add(LogbookRecurrenceException(
                series_id=series.id, original_date=occurrence_date,
                exception_type=LogbookRecurrenceExceptionType.NO_VALID_PARTICIPANTS,
                reason="No active event participants at generation time",
            ))
            skipped += 1
            continue
        opens_at = _valid_local_datetime(occurrence_date, series.opens_at_local, series.timezone)
        due_at = _valid_local_datetime(occurrence_date, series.due_at_local, series.timezone)
        instance = LogbookInstance(
            event_id=series.event_id, template_id=series.template_id,
            template_version_id=series.template_version_id, name=series.name,
            operational_stage=series.operational_stage, zone_id=series.zone_id,
            assignment_mode=series.assignment_mode, opens_at=opens_at, due_at=due_at,
            supervisor_id=series.supervisor_id,
            status=LogbookInstanceStatus.SCHEDULED if opens_at > datetime.now(UTC) else LogbookInstanceStatus.OPEN,
            client_visibility=series.client_visibility, created_by=series.created_by,
            recurrence_series_id=series.id, occurrence_date=occurrence_date,
        )
        db.add(instance)
        db.flush()
        for user_id in participant_ids:
            db.add(LogbookAssignment(logbook_instance_id=instance.id, user_id=user_id))
        generated += 1
    else:
        series.next_occurrence_date = None
    series.generated_count += generated
    if generated or skipped:
        _audit(db, series, "LOGBOOK_RECURRENCE_GENERATED", actor, metadata={"generated": generated, "skipped": skipped})
    if commit:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # The database uniqueness constraint is the final concurrency guard.
            return {"generated": 0, "skipped": 0, "concurrent_retry": True}
    return {"generated": generated, "skipped": skipped}


def set_status(db, series_id, status: LogbookRecurrenceStatus, current, reason=None):
    series = _series(db, series_id, lock=True)
    if not can_manage_event(current, series.event_id, db):
        fail(403, "Insufficient role")
    allowed = {
        LogbookRecurrenceStatus.PAUSED: {LogbookRecurrenceStatus.ACTIVE},
        LogbookRecurrenceStatus.ACTIVE: {LogbookRecurrenceStatus.PAUSED},
        LogbookRecurrenceStatus.FINISHED: {LogbookRecurrenceStatus.ACTIVE, LogbookRecurrenceStatus.PAUSED},
    }
    if series.status not in allowed.get(status, set()):
        fail(409, "Series status transition is not allowed")
    old = series.status
    series.status = status
    series.revision += 1
    _audit(db, series, f"LOGBOOK_RECURRENCE_{status.value}", current, metadata={"previous_status": old.value, "reason": reason})
    db.commit()
    if status == LogbookRecurrenceStatus.ACTIVE:
        generate_series_window(db, series.id, actor=current)
    return get_series(db, series.id, current)


def update_future(db, series_id, payload, current):
    series = _series(db, series_id, lock=True)
    if not can_manage_event(current, series.event_id, db):
        fail(403, "Insufficient role")
    if series.status in {LogbookRecurrenceStatus.FINISHED, LogbookRecurrenceStatus.CANCELLED}:
        fail(409, "Finished series cannot be edited")
    if payload.revision != series.revision:
        fail(409, "Series was modified by another user")
    changes = payload.model_dump(exclude_unset=True, exclude={"revision", "participant_ids"})
    if "end_date" in changes:
        if series.end_mode != LogbookRecurrenceEndMode.END_DATE or not changes["end_date"] or changes["end_date"] < series.start_date:
            fail(422, "A valid end_date is required for this series")
    if "max_occurrences" in changes and series.end_mode != LogbookRecurrenceEndMode.COUNT:
        fail(422, "max_occurrences only applies to count-based series")
    participant_ids = payload.participant_ids
    if participant_ids is not None:
        if not participant_ids or len(participant_ids) != len(set(participant_ids)):
            fail(422, "At least one unique participant is required")
        active_staff = set(db.scalars(select(EventStaff.user_id).join(User).where(
            EventStaff.event_id == series.event_id, User.is_active.is_(True)
        )).all())
        if not set(participant_ids) <= active_staff:
            fail(422, "All participants must be active event staff")
    if payload.supervisor_id:
        valid_supervisor = db.scalar(select(User.id).join(EventStaff, EventStaff.user_id == User.id).where(
            EventStaff.event_id == series.event_id, User.id == payload.supervisor_id,
            User.role == UserRole.SUPERVISOR, User.is_active.is_(True),
        ))
        if not valid_supervisor:
            fail(422, "Supervisor must be active event staff")
    for key, value in changes.items():
        setattr(series, key, value)
    if participant_ids is not None:
        for item in list(series.participants):
            db.delete(item)
        db.flush()
        for user_id in participant_ids:
            db.add(LogbookRecurrenceParticipant(
                series_id=series.id, event_id=series.event_id, user_id=user_id
            ))
    future = db.scalars(select(LogbookInstance).where(
        LogbookInstance.recurrence_series_id == series.id,
        LogbookInstance.occurrence_date >= chile_today(),
        LogbookInstance.status.in_([LogbookInstanceStatus.SCHEDULED, LogbookInstanceStatus.OPEN]),
    ).options(selectinload(LogbookInstance.assignments))).all()
    changed_occurrences = 0
    for instance in future:
        if _has_activity(db, instance):
            continue
        if "supervisor_id" in changes:
            instance.supervisor_id = payload.supervisor_id
            instance.occurrence_modified = True
        if participant_ids is not None:
            for assignment in list(instance.assignments):
                db.delete(assignment)
            db.flush()
            for user_id in participant_ids:
                db.add(LogbookAssignment(logbook_instance_id=instance.id, user_id=user_id))
            instance.occurrence_modified = True
        changed_occurrences += 1
    series.revision += 1
    _audit(db, series, "LOGBOOK_RECURRENCE_UPDATED", current, metadata={
        "fields": sorted(changes), "participants_changed": participant_ids is not None,
        "future_occurrences_changed": changed_occurrences,
    })
    db.commit()
    generate_series_window(db, series.id, actor=current)
    return get_series(db, series.id, current)


def _has_activity(db, instance):
    return bool(
        instance.status not in {LogbookInstanceStatus.SCHEDULED, LogbookInstanceStatus.OPEN}
        or db.scalar(select(LogbookResponse.id).join(LogbookAssignment).where(LogbookAssignment.logbook_instance_id == instance.id).limit(1))
        or db.scalar(select(LogbookEvidence.id).where(LogbookEvidence.instance_id == instance.id).limit(1))
        or db.scalar(select(LogbookReviewHistory.id).join(LogbookAssignment).where(LogbookAssignment.logbook_instance_id == instance.id).limit(1))
    )


def skip_occurrence(db, series_id, payload, current):
    series = _series(db, series_id, lock=True)
    if not can_manage_event(current, series.event_id, db):
        fail(403, "Insufficient role")
    instance = db.scalar(select(LogbookInstance).where(
        LogbookInstance.recurrence_series_id == series.id,
        LogbookInstance.occurrence_date == payload.occurrence_date,
    ).with_for_update())
    if instance and _has_activity(db, instance):
        fail(409, "An occurrence with activity cannot be skipped")
    if instance:
        instance.status = LogbookInstanceStatus.CANCELLED
        instance.cancellation_reason = payload.reason or "Occurrence skipped"
        for assignment in instance.assignments:
            assignment.status = LogbookAssignmentStatus.CANCELLED
    exception = db.scalar(select(LogbookRecurrenceException).where(
        LogbookRecurrenceException.series_id == series.id,
        LogbookRecurrenceException.original_date == payload.occurrence_date,
    ))
    if not exception:
        db.add(LogbookRecurrenceException(
            series_id=series.id, original_date=payload.occurrence_date,
            exception_type=LogbookRecurrenceExceptionType.SKIPPED,
            reason=payload.reason, created_by=current.id,
        ))
    _audit(db, series, "LOGBOOK_RECURRENCE_DATE_SKIPPED", current, instance_id=instance.id if instance else None, metadata={"occurrence_date": payload.occurrence_date.isoformat(), "reason": payload.reason})
    db.commit()
    return get_series(db, series.id, current)


def reschedule_occurrence(db, series_id, payload, current):
    series = _series(db, series_id, lock=True)
    if not can_manage_event(current, series.event_id, db):
        fail(403, "Insufficient role")
    instance = db.scalar(select(LogbookInstance).where(
        LogbookInstance.recurrence_series_id == series.id,
        LogbookInstance.occurrence_date == payload.occurrence_date,
    ).with_for_update())
    if not instance or _has_activity(db, instance):
        fail(409, "Only a generated occurrence without activity can be rescheduled")
    if db.scalar(select(LogbookInstance.id).where(
        LogbookInstance.recurrence_series_id == series.id,
        LogbookInstance.occurrence_date == payload.replacement_date,
    )):
        fail(409, "The replacement date already exists")
    original = instance.occurrence_date
    instance.original_occurrence_date = original
    instance.occurrence_date = payload.replacement_date
    instance.occurrence_modified = True
    instance.opens_at = _valid_local_datetime(payload.replacement_date, series.opens_at_local, series.timezone)
    instance.due_at = _valid_local_datetime(payload.replacement_date, series.due_at_local, series.timezone)
    db.add(LogbookRecurrenceException(
        series_id=series.id, original_date=original,
        exception_type=LogbookRecurrenceExceptionType.REPROGRAMMED,
        replacement_date=payload.replacement_date, reason=payload.reason, created_by=current.id,
    ))
    _audit(db, series, "LOGBOOK_RECURRENCE_RESCHEDULED", current, instance_id=instance.id, metadata={"original_date": original.isoformat(), "replacement_date": payload.replacement_date.isoformat()})
    db.commit()
    return instance


def list_occurrences(db, series_id, current):
    series = _series(db, series_id)
    if not can_access_event(current, series.event_id, db) or current.role == UserRole.CLIENT:
        fail(403, "Insufficient role")
    return list(db.scalars(select(LogbookInstance).where(
        LogbookInstance.recurrence_series_id == series.id
    ).order_by(LogbookInstance.occurrence_date)).all())


def process_active_series(db: Session, *, actor=None, batch_size=100):
    ids = list(db.scalars(select(LogbookRecurrenceSeries.id).where(
        LogbookRecurrenceSeries.status == LogbookRecurrenceStatus.ACTIVE,
        LogbookRecurrenceSeries.next_occurrence_date <= chile_today() + timedelta(weeks=WINDOW_WEEKS),
    ).order_by(LogbookRecurrenceSeries.next_occurrence_date).limit(batch_size)).all())
    summary = {"series_inspected": len(ids), "occurrences_generated": 0, "series_failed": 0}
    for series_id in ids:
        try:
            result = generate_series_window(db, series_id, actor=actor)
            summary["occurrences_generated"] += result["generated"]
        except Exception:
            db.rollback()
            summary["series_failed"] += 1
            logger.exception("recurrence series generation failed series_id=%s", series_id)
    return summary
