"""Seed disposable PostgreSQL for the real-browser recurrence certification."""

from datetime import UTC, date, datetime, time, timedelta
import json
import secrets
from uuid import uuid4

from sqlalchemy import select

from app.core.database_safety import require_disposable_database
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.core import Client, Event, EventStaff, User
from app.models.enums import EventStatus, UserRole
from app.models.logbook import LogbookAssignment, LogbookInstance
from app.schemas.logbook_schema import ItemIn, RecurrenceSeriesCreate, SectionIn, TemplateCreate
from app.services import logbook_recurrence_service, logbook_service


def main() -> None:
    require_disposable_database()
    suffix = uuid4().hex[:8]
    password = f"E2e-{secrets.token_urlsafe(24)}"
    db = SessionLocal()
    try:
        client = Client(
            business_name=f"Cliente E2E {suffix}", contact_email=f"client-{suffix}@example.test"
        )
        other_client = Client(
            business_name=f"Cliente externo E2E {suffix}",
            contact_email=f"other-client-{suffix}@example.test",
        )
        db.add_all([client, other_client])
        db.flush()

        def user(label: str, role: UserRole, client_id=None) -> User:
            row = User(
                full_name=label,
                email=f"{label.lower().replace(' ', '.')}-{suffix}@example.test",
                password_hash=hash_password(password),
                role=role,
                client_id=client_id,
            )
            db.add(row)
            db.flush()
            return row

        admin = user("Admin E2E", UserRole.ADMIN)
        worker = user("Worker Participante", UserRole.WORKER)
        outsider = user("Worker Externo", UserRole.WORKER)
        supervisor = user("Supervisor Participante", UserRole.SUPERVISOR)
        other_supervisor = user("Supervisor Externo", UserRole.SUPERVISOR)
        own_client = user("Client Propio", UserRole.CLIENT, client.id)
        foreign_client = user("Client Externo", UserRole.CLIENT, other_client.id)

        now = datetime.now(UTC)
        event = Event(
            client_id=client.id,
            name=f"Evento recurrencia E2E {suffix}",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=10),
            status=EventStatus.IN_PROGRESS,
            created_by=admin.id,
        )
        other_event = Event(
            client_id=other_client.id,
            name=f"Evento externo E2E {suffix}",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=10),
            status=EventStatus.IN_PROGRESS,
            created_by=admin.id,
        )
        db.add_all([event, other_event])
        db.flush()
        db.add_all(
            [
                EventStaff(event_id=event.id, user_id=worker.id),
                EventStaff(event_id=event.id, user_id=supervisor.id),
                EventStaff(event_id=other_event.id, user_id=other_supervisor.id),
            ]
        )
        db.commit()

        template = logbook_service.create_template(
            db,
            TemplateCreate(
                name="Control fotográfico E2E",
                operational_stage="OPERATION",
                default_assignment_mode="INDIVIDUAL",
                sections=[
                    SectionIn(
                        title="Control",
                        position=0,
                        items=[
                            ItemIn(
                                title="Confirmar tarea",
                                position=0,
                                item_type="CONFIRMATION",
                                evidence_policy="NONE",
                            ),
                            ItemIn(
                                title="Fotografía del resultado",
                                position=1,
                                item_type="PHOTO",
                                evidence_policy="REQUIRED",
                                min_evidences=1,
                                max_evidences=2,
                            ),
                        ],
                    )
                ],
            ),
            admin,
        )
        version = logbook_service.get_template_detail(db, template.id, admin).versions[0]
        logbook_service.publish(db, version.id, admin)
        series = logbook_recurrence_service.create_series(
            db,
            event.id,
            RecurrenceSeriesCreate(
                template_version_id=version.id,
                name="Serie E2E real",
                assignment_mode="INDIVIDUAL",
                participant_ids=[worker.id],
                supervisor_id=supervisor.id,
                client_visibility=True,
                frequency="DAILY",
                interval=1,
                start_date=date.today(),
                end_mode="COUNT",
                max_occurrences=3,
                opens_at_local=time(0, 1),
                due_at_local=time(23, 59),
                timezone="America/Santiago",
            ),
            admin,
        )
        instances = list(
            db.scalars(
                select(LogbookInstance)
                .where(LogbookInstance.recurrence_series_id == series["id"])
                .order_by(LogbookInstance.occurrence_date)
            )
        )
        assignments = {
            str(row.logbook_instance_id): str(row.id)
            for row in db.scalars(
                select(LogbookAssignment).where(
                    LogbookAssignment.logbook_instance_id.in_([item.id for item in instances])
                )
            )
        }
        payload = {
            "password": password,
            "event_id": str(event.id),
            "other_event_id": str(other_event.id),
            "series_id": str(series["id"]),
            "template_id": str(template.id),
            "version_id": str(version.id),
            "users": {
                name: {"id": str(row.id), "email": row.email, "role": row.role.value}
                for name, row in {
                    "admin": admin,
                    "worker": worker,
                    "outsider": outsider,
                    "supervisor": supervisor,
                    "other_supervisor": other_supervisor,
                    "own_client": own_client,
                    "foreign_client": foreign_client,
                }.items()
            },
            "instances": [
                {
                    "id": str(item.id),
                    "date": str(item.occurrence_date),
                    "status": item.status.value,
                    "assignment_id": assignments[str(item.id)],
                }
                for item in instances
            ],
        }
        print(json.dumps(payload))
    finally:
        db.close()


if __name__ == "__main__":
    main()
