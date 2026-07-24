from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.core import Client, Event, EventStaff, User
from app.models.enums import EventStatus, UserRole
from app.models.logbook import LogbookInstance, LogbookTemplate, LogbookTemplateVersion
from app.schemas.logbook_schema import InstanceCreate, ItemIn, ResponseSave, SectionIn, TemplateCreate
from app.services import logbook_service


@pytest.fixture()
def logbook_context():
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    client = Client(
        business_name=f"Logbook Client {suffix}",
        contact_email=f"logbook-client-{suffix}@example.com",
    )
    other_client = Client(
        business_name=f"Other Client {suffix}",
        contact_email=f"other-logbook-client-{suffix}@example.com",
    )
    db.add_all([client, other_client])
    db.flush()
    admin = User(
        full_name="Logbook Admin",
        email=f"logbook-admin-{suffix}@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    supervisor = User(
        full_name="Logbook Supervisor",
        email=f"logbook-supervisor-{suffix}@example.com",
        password_hash="x",
        role=UserRole.SUPERVISOR,
    )
    worker = User(
        full_name="Logbook Worker",
        email=f"logbook-worker-{suffix}@example.com",
        password_hash="x",
        role=UserRole.WORKER,
    )
    outsider = User(
        full_name="Logbook Outsider",
        email=f"logbook-outsider-{suffix}@example.com",
        password_hash="x",
        role=UserRole.WORKER,
    )
    logistics = User(
        full_name="Logbook Logistics",
        email=f"logbook-logistics-{suffix}@example.com",
        password_hash="x",
        role=UserRole.LOGISTICS_OPERATOR,
    )
    client_user = User(
        full_name="Logbook Client User",
        email=f"logbook-client-user-{suffix}@example.com",
        password_hash="x",
        role=UserRole.CLIENT,
        client_id=client.id,
    )
    other_client_user = User(
        full_name="Other Logbook Client User",
        email=f"other-logbook-client-user-{suffix}@example.com",
        password_hash="x",
        role=UserRole.CLIENT,
        client_id=other_client.id,
    )
    db.add_all([admin, supervisor, worker, outsider, logistics, client_user, other_client_user])
    db.flush()
    event = Event(
        client_id=client.id,
        name=f"Logbook Event {suffix}",
        start_date=datetime.utcnow() + timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=2),
        status=EventStatus.PLANNING,
        created_by=admin.id,
    )
    db.add(event)
    db.flush()
    db.add_all(
        [
            EventStaff(event_id=event.id, user_id=supervisor.id),
            EventStaff(event_id=event.id, user_id=worker.id),
            EventStaff(event_id=event.id, user_id=logistics.id),
        ]
    )
    db.commit()
    context = {
        "db": db,
        "clients": [client, other_client],
        "users": [
            admin, supervisor, worker, outsider, logistics, client_user, other_client_user
        ],
        "event": event,
        "template_id": None,
        "instance_id": None,
    }
    try:
        yield context
    finally:
        db.rollback()
        if context["instance_id"]:
            db.execute(delete(LogbookInstance).where(LogbookInstance.id == context["instance_id"]))
        if context["template_id"]:
            db.execute(
                delete(LogbookTemplateVersion).where(
                    LogbookTemplateVersion.template_id == context["template_id"]
                )
            )
            db.execute(delete(LogbookTemplate).where(LogbookTemplate.id == context["template_id"]))
        db.execute(delete(EventStaff).where(EventStaff.event_id == event.id))
        db.execute(delete(AuditLog).where(AuditLog.event_id == event.id))
        db.execute(delete(Event).where(Event.id == event.id))
        db.execute(delete(User).where(User.id.in_([user.id for user in context["users"]])))
        db.execute(delete(Client).where(Client.id.in_([item.id for item in context["clients"]])))
        db.commit()
        db.close()


def test_real_postgresql_permissions_archiving_and_client_isolation(logbook_context):
    ctx = logbook_context
    db = ctx["db"]
    admin, supervisor, worker, outsider, logistics, client_user, other_client_user = ctx["users"]
    template = logbook_service.create_template(
        db,
        TemplateCreate(
            name="Control operacional",
            operational_stage="OPERATION",
            default_assignment_mode="INDIVIDUAL",
            sections=[
                SectionIn(
                    title="General",
                    position=0,
                    items=[
                        ItemIn(
                            title="Confirmar área",
                            position=0,
                            item_type="CONFIRMATION",
                            evidence_policy="NONE",
                        )
                    ],
                )
            ],
        ),
        admin,
    )
    ctx["template_id"] = template.id
    detail = logbook_service.get_template_detail(db, template.id, admin)
    version = detail.versions[0]
    logbook_service.publish(db, version.id, admin)

    with pytest.raises(HTTPException) as invalid_participant:
        logbook_service.create_instance(
            db,
            ctx["event"].id,
            InstanceCreate(
                template_version_id=version.id,
                assignment_mode="INDIVIDUAL",
                participant_ids=[outsider.id],
            ),
            admin,
        )
    assert invalid_participant.value.status_code == 422

    with pytest.raises(HTTPException) as invalid_supervisor:
        logbook_service.create_instance(
            db,
            ctx["event"].id,
            InstanceCreate(
                template_version_id=version.id,
                assignment_mode="INDIVIDUAL",
                participant_ids=[worker.id],
                supervisor_id=worker.id,
            ),
            admin,
        )
    assert invalid_supervisor.value.status_code == 422

    instance = logbook_service.create_instance(
        db,
        ctx["event"].id,
        InstanceCreate(
            template_version_id=version.id,
            assignment_mode="INDIVIDUAL",
            participant_ids=[worker.id, logistics.id],
            supervisor_id=supervisor.id,
            client_visibility=True,
        ),
        admin,
    )
    ctx["instance_id"] = instance.id
    worker_detail = logbook_service.get_instance_detail(db, instance.id, worker)
    assert len(worker_detail["assignments"]) == 1
    worker_assignment = worker_detail["assignments"][0]
    item_id = worker_detail["version"]["sections"][0]["items"][0]["id"]
    saved = logbook_service.save_response(
        db,
        worker_assignment["id"],
        ResponseSave(
            item_id=item_id,
            boolean_value=False,
            result_status="FAILED",
        ),
        worker,
    )
    saved_version = saved.version
    cleared = logbook_service.clear_response(
        db,
        worker_assignment["id"],
        item_id,
        saved_version,
        worker,
    )
    assert cleared.boolean_value is None
    assert cleared.result_status.value == "PENDING"
    assert cleared.version == saved_version + 1
    with pytest.raises(HTTPException) as stale_clear:
        logbook_service.clear_response(
            db,
            worker_assignment["id"],
            item_id,
            saved_version,
            worker,
        )
    assert stale_clear.value.status_code == 409
    logistics_detail = logbook_service.get_instance_detail(db, instance.id, logistics)
    assert len(logistics_detail["assignments"]) == 1

    with pytest.raises(HTTPException) as unassigned:
        logbook_service.get_instance_detail(db, instance.id, outsider)
    assert unassigned.value.status_code == 403

    summary = logbook_service.client_summary(db, instance.id, client_user)
    assert summary["name"] == "Control operacional"
    assert "assignments" not in summary
    with pytest.raises(HTTPException) as isolated:
        logbook_service.client_summary(db, instance.id, other_client_user)
    assert isolated.value.status_code == 404

    logbook_service.archive_template(db, template.id, admin)
    assert logbook_service.get_instance_detail(db, instance.id, supervisor)["id"] == instance.id
