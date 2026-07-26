import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.core import User
from app.models.enums import LogbookInstanceStatus
from app.models.logbook import LogbookInstance

logger = logging.getLogger(__name__)
MAX_BATCH_SIZE = 500
LIFECYCLE_ACTIONS = {
    LogbookInstanceStatus.OPEN: "LOGBOOK_LIFECYCLE_OPENED",
    LogbookInstanceStatus.OVERDUE: "LOGBOOK_LIFECYCLE_OVERDUE",
}


@dataclass
class LifecycleSummary:
    run_id: UUID
    started_at: datetime
    finished_at: datetime
    inspected_count: int = 0
    opened_count: int = 0
    overdue_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    batch_count: int = 0

    def model_dump(self) -> dict:
        return asdict(self)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        # Compatibility while migration 0036 converts historical UTC-naive values.
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def lifecycle_transitions(instance: LogbookInstance, now: datetime) -> list[tuple[LogbookInstanceStatus, datetime]]:
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    now = now.astimezone(UTC)
    opens_at = _aware(instance.opens_at)
    due_at = _aware(instance.due_at)
    transitions: list[tuple[LogbookInstanceStatus, datetime]] = []
    status = instance.status
    if status == LogbookInstanceStatus.SCHEDULED and opens_at and opens_at <= now:
        transitions.append((LogbookInstanceStatus.OPEN, opens_at))
        status = LogbookInstanceStatus.OPEN
    if status == LogbookInstanceStatus.OPEN and due_at and due_at <= now:
        transitions.append((LogbookInstanceStatus.OVERDUE, due_at))
    return transitions


def _audit_transition(
    db: Session,
    instance: LogbookInstance,
    old_status: LogbookInstanceStatus,
    new_status: LogbookInstanceStatus,
    scheduled_at: datetime,
    *,
    processed_at: datetime,
    origin: str,
    run_id: UUID,
    actor: User | None,
) -> None:
    db.add(
        AuditLog(
            user_id=actor.id if actor else None,
            event_id=instance.event_id,
            action=LIFECYCLE_ACTIONS[new_status],
            module="logbooks",
            entity_type="LogbookInstance",
            entity_id=instance.id,
            old_data={"status": old_status.value},
            new_data={"status": new_status.value},
            metadata_={
                "scheduled_at": scheduled_at.isoformat(),
                "processed_at": processed_at.isoformat(),
                "origin": origin,
                "run_id": str(run_id),
            },
            description=(
                f"Bitácora cambió automáticamente de {old_status.value} a {new_status.value}."
                if origin == "AUTOMATIC"
                else f"Administrador procesó bitácora de {old_status.value} a {new_status.value}."
            ),
        )
    )


def process_logbook_lifecycle(
    db: Session,
    *,
    now: datetime | None = None,
    batch_size: int = 100,
    dry_run: bool = False,
    actor: User | None = None,
    origin: str = "AUTOMATIC",
) -> LifecycleSummary:
    if not 1 <= batch_size <= MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")
    if origin not in {"AUTOMATIC", "MANUAL_ADMIN"}:
        raise ValueError("invalid lifecycle origin")
    reference = now or utc_now()
    if reference.tzinfo is None:
        raise ValueError("now must include a timezone")
    reference = reference.astimezone(UTC)
    summary = LifecycleSummary(run_id=uuid4(), started_at=utc_now(), finished_at=utc_now())
    logger.info("logbook lifecycle started run_id=%s", summary.run_id)

    while True:
        query = (
            select(LogbookInstance)
            .where(
                or_(
                    (LogbookInstance.status == LogbookInstanceStatus.SCHEDULED)
                    & (LogbookInstance.opens_at.is_not(None))
                    & (LogbookInstance.opens_at <= reference),
                    (LogbookInstance.status == LogbookInstanceStatus.OPEN)
                    & (LogbookInstance.due_at.is_not(None))
                    & (LogbookInstance.due_at <= reference),
                )
            )
            .order_by(LogbookInstance.opens_at.asc().nullslast(), LogbookInstance.due_at.asc().nullslast())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        instances = list(db.scalars(query).all())
        if not instances:
            db.rollback()
            break
        summary.batch_count += 1
        summary.inspected_count += len(instances)
        try:
            for instance in instances:
                transitions = lifecycle_transitions(instance, reference)
                if not transitions:
                    summary.skipped_count += 1
                    continue
                for new_status, scheduled_at in transitions:
                    old_status = instance.status
                    if not dry_run:
                        instance.status = new_status
                        _audit_transition(
                            db, instance, old_status, new_status, scheduled_at,
                            processed_at=reference, origin=origin, run_id=summary.run_id, actor=actor,
                        )
                    if new_status == LogbookInstanceStatus.OPEN:
                        summary.opened_count += 1
                    else:
                        summary.overdue_count += 1
            if dry_run:
                db.rollback()
                break
            db.commit()
        except Exception:
            db.rollback()
            summary.failed_count += len(instances)
            summary.finished_at = utc_now()
            logger.exception("logbook lifecycle batch failed run_id=%s", summary.run_id)
            raise
    summary.finished_at = utc_now()
    logger.info(
        "logbook lifecycle finished run_id=%s inspected=%s opened=%s overdue=%s failed=%s",
        summary.run_id, summary.inspected_count, summary.opened_count,
        summary.overdue_count, summary.failed_count,
    )
    return summary
