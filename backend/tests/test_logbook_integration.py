from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.core import Client, Event, EventStaff, User
from app.models.enums import (
    EventStatus,
    LogbookAssignmentMode,
    LogbookInstanceStatus,
    LogbookOperationalStage,
    LogbookTemplateStatus,
    LogbookVersionStatus,
    LogbookAssignmentStatus,
    UserRole,
)
from app.models.logbook import (
    LogbookAssignment,
    LogbookEvidence,
    LogbookInstance,
    LogbookTemplate,
    LogbookTemplateVersion,
    LogbookRecurrenceException,
    LogbookRecurrenceParticipant,
    LogbookRecurrenceSeries,
)
from app.schemas.logbook_schema import (
    InstanceCreate, ItemIn, RecurrenceOccurrenceOperation, RecurrenceRescheduleIn,
    RecurrenceSeriesCreate, ResponseSave, SectionIn, TemplateCreate,
)
from app.services import logbook_recurrence_service, logbook_service
from app.services.logbook_lifecycle_service import process_logbook_lifecycle


def _lifecycle_instance(ctx, *, status, opens_at=None, due_at=None):
    db = ctx["db"]
    admin = ctx["users"][0]
    template = LogbookTemplate(
        name="Lifecycle test",
        operational_stage=LogbookOperationalStage.OPERATION,
        status=LogbookTemplateStatus.ACTIVE,
        default_assignment_mode=LogbookAssignmentMode.INDIVIDUAL,
        default_client_visibility=False,
        created_by=admin.id,
    )
    db.add(template)
    db.flush()
    version = LogbookTemplateVersion(
        template_id=template.id,
        version_number=1,
        status=LogbookVersionStatus.PUBLISHED,
        created_by=admin.id,
    )
    db.add(version)
    db.flush()
    item = LogbookInstance(
        event_id=ctx["event"].id,
        template_id=template.id,
        template_version_id=version.id,
        name="Lifecycle instance",
        operational_stage=LogbookOperationalStage.OPERATION,
        assignment_mode=LogbookAssignmentMode.INDIVIDUAL,
        opens_at=opens_at,
        due_at=due_at,
        status=status,
        created_by=admin.id,
    )
    db.add(item)
    db.commit()
    ctx["template_id"] = template.id
    ctx["instance_ids"].append(item.id)
    return item


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
    super_admin = User(
        full_name="Logbook Super Admin",
        email=f"logbook-super-admin-{suffix}@example.com",
        password_hash="x",
        role=UserRole.SUPER_ADMIN,
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
    db.add_all(
        [admin, super_admin, supervisor, worker, outsider, logistics, client_user, other_client_user]
    )
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
            admin, super_admin, supervisor, worker, outsider, logistics, client_user,
            other_client_user,
        ],
        "event": event,
        "template_id": None,
        "instance_ids": [],
        "series_ids": [],
    }
    try:
        yield context
    finally:
        db.rollback()
        if context["instance_ids"]:
            db.execute(
                delete(LogbookEvidence).where(
                    LogbookEvidence.instance_id.in_(context["instance_ids"])
                )
            )
            db.execute(delete(LogbookInstance).where(LogbookInstance.id.in_(context["instance_ids"])))
        if context["series_ids"]:
            db.execute(delete(LogbookRecurrenceException).where(LogbookRecurrenceException.series_id.in_(context["series_ids"])))
            db.execute(delete(LogbookRecurrenceParticipant).where(LogbookRecurrenceParticipant.series_id.in_(context["series_ids"])))
            db.execute(delete(LogbookRecurrenceSeries).where(LogbookRecurrenceSeries.id.in_(context["series_ids"])))
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
    admin, _, supervisor, worker, outsider, logistics, client_user, other_client_user = ctx["users"]
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
    ctx["instance_ids"].append(instance.id)
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


def test_response_clear_integrity_permissions_and_shared_concurrency(
    logbook_context, monkeypatch
):
    ctx = logbook_context
    db = ctx["db"]
    admin, super_admin, supervisor, worker, outsider, logistics, *_ = ctx["users"]
    template = logbook_service.create_template(
        db,
        TemplateCreate(
            name="Limpieza íntegra",
            operational_stage="OPERATION",
            default_assignment_mode="INDIVIDUAL",
            sections=[
                SectionIn(
                    title="General",
                    position=0,
                    items=[
                        ItemIn(
                            title="Control principal",
                            position=0,
                            item_type="CONFIRMATION",
                            evidence_policy="REQUIRED",
                            min_evidences=1,
                        ),
                        ItemIn(
                            title="Control secundario",
                            position=1,
                            item_type="YES_NO",
                            evidence_policy="REQUIRED_ON_FAILURE",
                            min_evidences=1,
                        ),
                    ],
                )
            ],
        ),
        admin,
    )
    ctx["template_id"] = template.id
    version = logbook_service.get_template_detail(db, template.id, admin).versions[0]
    logbook_service.publish(db, version.id, admin)
    instance = logbook_service.create_instance(
        db,
        ctx["event"].id,
        InstanceCreate(
            template_version_id=version.id,
            assignment_mode="INDIVIDUAL",
            participant_ids=[worker.id, logistics.id],
            supervisor_id=supervisor.id,
        ),
        admin,
    )
    ctx["instance_ids"].append(instance.id)
    assignments = {assignment.user_id: assignment for assignment in instance.assignments}
    first_item, second_item = version.sections[0].items
    first = logbook_service.save_response(
        db,
        assignments[worker.id].id,
        ResponseSave(
            item_id=first_item.id,
            boolean_value=True,
            result_status="COMPLETED",
            comment="contenido vigente",
        ),
        worker,
    )
    second = logbook_service.save_response(
        db,
        assignments[worker.id].id,
        ResponseSave(
            item_id=second_item.id,
            boolean_value=False,
            result_status="FAILED",
        ),
        worker,
    )
    evidence = LogbookEvidence(
        instance_id=instance.id,
        assignment_id=assignments[worker.id].id,
        item_id=first_item.id,
        response_id=first.id,
        uploaded_by=worker.id,
        mime_type="image/jpeg",
        file_size=3,
        original_filename="principal.jpg",
        storage_key="logbooks/private-principal.jpg",
        client_visible=False,
    )
    other_evidence = LogbookEvidence(
        instance_id=instance.id,
        assignment_id=assignments[worker.id].id,
        item_id=second_item.id,
        response_id=second.id,
        uploaded_by=worker.id,
        mime_type="image/jpeg",
        file_size=3,
        original_filename="secundaria.jpg",
        storage_key="logbooks/private-secondary.jpg",
        client_visible=False,
    )
    db.add_all([evidence, other_evidence])
    db.commit()

    for forbidden_actor in (logistics, admin, super_admin, supervisor, outsider):
        with pytest.raises(HTTPException) as forbidden:
            logbook_service.clear_response(
                db,
                assignments[worker.id].id,
                first_item.id,
                first.version,
                forbidden_actor,
            )
        assert forbidden.value.status_code == 403

    with pytest.raises(HTTPException) as forbidden_save:
        logbook_service.save_response(
            db,
            assignments[worker.id].id,
            ResponseSave(
                item_id=first_item.id,
                boolean_value=False,
                result_status="FAILED",
                version=first.version,
            ),
            admin,
        )
    assert forbidden_save.value.status_code == 403

    stale_version = first.version
    cleared = logbook_service.clear_response(
        db, assignments[worker.id].id, first_item.id, stale_version, worker
    )
    assert cleared.version == stale_version + 1
    assert cleared.boolean_value is None
    assert cleared.comment is None
    assert cleared.completed_by is None
    assert cleared.completed_at is None
    assert cleared.result_status.value == "PENDING"
    db.refresh(evidence)
    db.refresh(other_evidence)
    assert evidence.deleted_at is not None
    assert other_evidence.deleted_at is None
    with pytest.raises(HTTPException) as deleted_access:
        logbook_service._evidence(db, evidence.id)
    assert deleted_access.value.status_code == 404
    assert logbook_service.calculate_metrics(instance)["completed_items"] == 0

    audit_entry = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "LOGBOOK_RESPONSE_CLEARED",
            AuditLog.entity_id == first.id,
        )
    )
    assert audit_entry.user_id == worker.id
    assert audit_entry.event_id == instance.event_id
    assert audit_entry.metadata_["deleted_evidence_count"] == 1
    assert "storage_key" not in str(audit_entry.metadata_)

    with pytest.raises(HTTPException) as stale:
        logbook_service.clear_response(
            db, assignments[worker.id].id, first_item.id, stale_version, worker
        )
    assert stale.value.status_code == 409
    db.refresh(cleared)
    assert cleared.version == stale_version + 1

    restored = logbook_service.save_response(
        db,
        assignments[worker.id].id,
        ResponseSave(
            item_id=first_item.id,
            boolean_value=True,
            result_status="COMPLETED",
            version=cleared.version,
        ),
        worker,
    )
    atomic_evidence = LogbookEvidence(
        instance_id=instance.id,
        assignment_id=assignments[worker.id].id,
        item_id=first_item.id,
        response_id=restored.id,
        uploaded_by=worker.id,
        mime_type="image/jpeg",
        file_size=3,
        original_filename="atomic.jpg",
        storage_key="logbooks/private-atomic.jpg",
        client_visible=False,
    )
    db.add(atomic_evidence)
    db.commit()
    real_commit = db.commit
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("forced")))
    with pytest.raises(RuntimeError):
        logbook_service.clear_response(
            db, assignments[worker.id].id, first_item.id, restored.version, worker
        )
    db.rollback()
    monkeypatch.setattr(db, "commit", real_commit)
    db.refresh(restored)
    db.refresh(atomic_evidence)
    assert restored.boolean_value is True
    assert atomic_evidence.deleted_at is None

    assignments[worker.id].status = LogbookAssignmentStatus.SUBMITTED
    db.commit()
    with pytest.raises(HTTPException) as locked:
        logbook_service.clear_response(
            db, assignments[worker.id].id, first_item.id, restored.version, worker
        )
    assert locked.value.status_code == 409

    shared = logbook_service.create_instance(
        db,
        ctx["event"].id,
        InstanceCreate(
            template_version_id=version.id,
            assignment_mode="SHARED",
            participant_ids=[worker.id, logistics.id],
            supervisor_id=supervisor.id,
        ),
        admin,
    )
    ctx["instance_ids"].append(shared.id)
    shared_assignments = {assignment.user_id: assignment for assignment in shared.assignments}
    shared_response = logbook_service.save_response(
        db,
        shared_assignments[worker.id].id,
        ResponseSave(
            item_id=first_item.id,
            boolean_value=True,
            result_status="COMPLETED",
        ),
        worker,
    )
    shared_cleared = logbook_service.clear_response(
        db,
        shared_assignments[worker.id].id,
        first_item.id,
        shared_response.version,
        logistics,
    )
    assert shared_cleared.result_status.value == "PENDING"
    with pytest.raises(HTTPException) as shared_outsider:
        logbook_service.save_response(
            db,
            shared_assignments[worker.id].id,
            ResponseSave(
                item_id=first_item.id,
                boolean_value=True,
                result_status="COMPLETED",
                version=shared_cleared.version,
            ),
            outsider,
        )
    assert shared_outsider.value.status_code == 403


def test_participant_removal_and_cancellation_preserve_operational_history(logbook_context):
    ctx = logbook_context
    db = ctx["db"]
    admin, _, supervisor, worker, outsider, logistics, *_ = ctx["users"]
    template = logbook_service.create_template(
        db,
        TemplateCreate(
            name="Ciclo de participantes",
            operational_stage="OPERATION",
            default_assignment_mode="SHARED",
            sections=[
                SectionIn(
                    title="General",
                    position=0,
                    items=[
                        ItemIn(
                            title="Confirmar",
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
    version = logbook_service.get_template_detail(db, template.id, admin).versions[0]
    logbook_service.publish(db, version.id, admin)
    instance = logbook_service.create_instance(
        db,
        ctx["event"].id,
        InstanceCreate(
            template_version_id=version.id,
            assignment_mode="SHARED",
            participant_ids=[worker.id, logistics.id],
            supervisor_id=supervisor.id,
            client_visibility=True,
        ),
        admin,
    )
    ctx["instance_ids"].append(instance.id)
    assignments = {assignment.user_id: assignment for assignment in instance.assignments}
    item = version.sections[0].items[0]

    with pytest.raises(HTTPException) as duplicate:
        logbook_service.add_participants(db, instance.id, [worker.id], admin)
    assert duplicate.value.status_code == 409
    with pytest.raises(HTTPException) as alien:
        logbook_service.add_participants(db, instance.id, [outsider.id], admin)
    assert alien.value.status_code == 422

    added = logbook_service.add_participants(db, instance.id, [supervisor.id], admin)
    temporary = next(assignment for assignment in added if assignment.user_id == supervisor.id)
    temporary_id = temporary.id
    logbook_service.remove_participant(db, instance.id, temporary_id, admin)
    assert db.get(type(temporary), temporary_id) is None

    response = logbook_service.save_response(
        db,
        assignments[worker.id].id,
        ResponseSave(item_id=item.id, boolean_value=True, result_status="COMPLETED"),
        worker,
    )
    logbook_service.remove_participant(db, instance.id, assignments[worker.id].id, admin)
    db.refresh(assignments[worker.id])
    assert assignments[worker.id].status == LogbookAssignmentStatus.CANCELLED
    assert db.get(type(response), response.id) is not None
    with pytest.raises(HTTPException) as removed_edit:
        logbook_service.save_response(
            db,
            assignments[worker.id].id,
            ResponseSave(
                item_id=item.id,
                boolean_value=False,
                result_status="FAILED",
                version=response.version,
            ),
            worker,
        )
    assert removed_edit.value.status_code == 409

    shared_detail = logbook_service.get_instance_detail(db, instance.id, logistics)
    reflected = shared_detail["assignments"][0]["responses"][0]
    assert reflected["id"] == response.id
    updated = logbook_service.save_response(
        db,
        assignments[logistics.id].id,
        ResponseSave(
            item_id=item.id,
            boolean_value=False,
            result_status="FAILED",
            version=response.version,
        ),
        logistics,
    )
    assert updated.id == response.id

    cancelled = logbook_service.cancel_instance(db, instance.id, "Evento cancelado", admin)
    assert cancelled.status.value == "CANCELLED"
    assert cancelled.cancellation_reason == "Evento cancelado"
    assert db.get(type(response), response.id) is not None
    for assignment in cancelled.assignments:
        assert assignment.status == LogbookAssignmentStatus.CANCELLED
    with pytest.raises(HTTPException) as cancelled_edit:
        logbook_service.save_response(
            db,
            assignments[logistics.id].id,
            ResponseSave(
                item_id=item.id,
                boolean_value=True,
                result_status="COMPLETED",
                version=updated.version,
            ),
            logistics,
        )
    assert cancelled_edit.value.status_code == 409
    with pytest.raises(HTTPException) as cancelled_submit:
        logbook_service.submit(db, assignments[logistics.id].id, logistics)
    assert cancelled_submit.value.status_code == 409
    with pytest.raises(HTTPException) as cancelled_review:
        logbook_service.review(
            db, assignments[logistics.id].id, supervisor, True, "No permitido"
        )
    assert cancelled_review.value.status_code == 409
    assert logbook_service.get_instance_detail(db, instance.id, supervisor)["id"] == instance.id
    cancel_audit = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "LOGBOOK_INSTANCE_CANCELLED",
            AuditLog.entity_id == instance.id,
        )
    )
    assert cancel_audit.metadata_["reason"] == "Evento cancelado"


def test_lifecycle_is_idempotent_and_audited_once_on_real_postgresql(logbook_context):
    now = datetime(2026, 7, 25, 15, 0, tzinfo=UTC)
    item = _lifecycle_instance(
        logbook_context,
        status=LogbookInstanceStatus.SCHEDULED,
        opens_at=now - timedelta(hours=2),
        due_at=now - timedelta(hours=1),
    )
    first = process_logbook_lifecycle(logbook_context["db"], now=now, batch_size=10)
    second = process_logbook_lifecycle(logbook_context["db"], now=now, batch_size=10)
    logbook_context["db"].refresh(item)
    assert item.status == LogbookInstanceStatus.OVERDUE
    assert (first.opened_count, first.overdue_count) == (1, 1)
    assert (second.opened_count, second.overdue_count) == (0, 0)
    actions = list(
        logbook_context["db"].scalars(
            select(AuditLog.action).where(
                AuditLog.entity_id == item.id,
                AuditLog.action.in_(
                    ["LOGBOOK_LIFECYCLE_OPENED", "LOGBOOK_LIFECYCLE_OVERDUE"]
                ),
            )
        )
    )
    assert sorted(actions) == ["LOGBOOK_LIFECYCLE_OPENED", "LOGBOOK_LIFECYCLE_OVERDUE"]


def test_two_workers_do_not_duplicate_lifecycle_transition(logbook_context):
    now = datetime(2026, 7, 25, 15, 0, tzinfo=UTC)
    item = _lifecycle_instance(
        logbook_context,
        status=LogbookInstanceStatus.OPEN,
        due_at=now - timedelta(seconds=1),
    )

    def run_worker():
        with SessionLocal() as worker_db:
            return process_logbook_lifecycle(worker_db, now=now, batch_size=1)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run_worker(), range(2)))

    logbook_context["db"].expire_all()
    assert logbook_context["db"].get(LogbookInstance, item.id).status == LogbookInstanceStatus.OVERDUE
    assert sum(result.overdue_count for result in results) == 1
    assert (
        logbook_context["db"].scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.entity_id == item.id,
                AuditLog.action == "LOGBOOK_LIFECYCLE_OVERDUE",
            )
        )
        == 1
    )


def test_recurrence_generates_independent_idempotent_occurrences_and_blocks_scheduled(
    logbook_context,
):
    ctx = logbook_context
    db = ctx["db"]
    admin, _, supervisor, worker, *_ = ctx["users"]
    template = logbook_service.create_template(
        db,
        TemplateCreate(
            name="Control recurrente",
            operational_stage="OPERATION",
            default_assignment_mode="INDIVIDUAL",
            sections=[SectionIn(
                title="General", position=0,
                items=[ItemIn(
                    title="Confirmación recurrente", position=0,
                    item_type="CONFIRMATION", evidence_policy="NONE",
                )],
            )],
        ),
        admin,
    )
    ctx["template_id"] = template.id
    version = logbook_service.get_template_detail(db, template.id, admin).versions[0]
    logbook_service.publish(db, version.id, admin)
    start = (datetime.now(UTC) + timedelta(days=3)).date()
    created = logbook_recurrence_service.create_series(
        db,
        ctx["event"].id,
        RecurrenceSeriesCreate(
            template_version_id=version.id,
            assignment_mode="INDIVIDUAL",
            participant_ids=[worker.id],
            supervisor_id=supervisor.id,
            frequency="DAILY",
            interval=1,
            start_date=start,
            end_mode="COUNT",
            max_occurrences=3,
            opens_at_local="09:00",
            due_at_local="18:00",
            timezone="America/Santiago",
        ),
        admin,
    )
    ctx["series_ids"].append(created["id"])
    occurrences = logbook_recurrence_service.list_occurrences(db, created["id"], admin)
    ctx["instance_ids"].extend(item.id for item in occurrences)
    assert [item.occurrence_date for item in occurrences] == [
        start, start + timedelta(days=1), start + timedelta(days=2)
    ]
    assert len({item.id for item in occurrences}) == 3
    assert all(item.status == LogbookInstanceStatus.SCHEDULED for item in occurrences)
    assert all(len(item.assignments) == 1 for item in occurrences)

    repeated = logbook_recurrence_service.generate_series_window(db, created["id"], actor=admin)
    assert repeated["generated"] == 0
    assert db.scalar(select(func.count(LogbookInstance.id)).where(
        LogbookInstance.recurrence_series_id == created["id"]
    )) == 3

    item_id = version.sections[0].items[0].id
    with pytest.raises(HTTPException) as early_response:
        logbook_service.save_response(
            db, occurrences[0].assignments[0].id,
            ResponseSave(item_id=item_id, boolean_value=True, result_status="COMPLETED"),
            worker,
        )
    assert early_response.value.status_code == 409
    with pytest.raises(HTTPException) as early_evidence:
        logbook_service.upload_evidence(
            db, occurrences[0].assignments[0].id, uuid4(),
            UploadFile(filename="evidence.png", file=BytesIO(b"not-read")), None, worker,
        )
    assert early_evidence.value.status_code == 409

    rescheduled = logbook_recurrence_service.reschedule_occurrence(
        db, created["id"],
        RecurrenceRescheduleIn(
            occurrence_date=start + timedelta(days=2),
            replacement_date=start + timedelta(days=5), reason="Cambio operativo",
        ),
        admin,
    )
    assert rescheduled.original_occurrence_date == start + timedelta(days=2)
    assert rescheduled.occurrence_modified
    logbook_recurrence_service.skip_occurrence(
        db, created["id"],
        RecurrenceOccurrenceOperation(occurrence_date=start + timedelta(days=1), reason="Feriado"),
        admin,
    )
    db.refresh(occurrences[1])
    assert occurrences[1].status == LogbookInstanceStatus.CANCELLED
    assert db.scalar(select(func.count(LogbookRecurrenceException.id)).where(
        LogbookRecurrenceException.series_id == created["id"]
    )) == 2


def test_two_real_generators_are_idempotent_and_leave_no_partial_data(logbook_context):
    ctx = logbook_context
    db = ctx["db"]
    admin, _, supervisor, worker, *_ = ctx["users"]
    template = logbook_service.create_template(
        db,
        TemplateCreate(
            name="Concurrencia recurrente",
            operational_stage="OPERATION",
            default_assignment_mode="INDIVIDUAL",
            sections=[SectionIn(
                title="General", position=0,
                items=[ItemIn(
                    title="Control", position=0, item_type="CONFIRMATION",
                    evidence_policy="NONE",
                )],
            )],
        ),
        admin,
    )
    ctx["template_id"] = template.id
    version = logbook_service.get_template_detail(db, template.id, admin).versions[0]
    logbook_service.publish(db, version.id, admin)
    start = (datetime.now(UTC) + timedelta(days=10)).date()
    series = LogbookRecurrenceSeries(
        event_id=ctx["event"].id, template_id=template.id,
        template_version_id=version.id, name="Concurrencia recurrente",
        operational_stage="OPERATION", assignment_mode="INDIVIDUAL",
        supervisor_id=supervisor.id, client_visibility=False,
        frequency="DAILY", interval=1, start_date=start, end_mode="COUNT",
        max_occurrences=4, opens_at_local=time(9), due_at_local=time(18),
        timezone="America/Santiago", status="ACTIVE",
        next_occurrence_date=start, created_by=admin.id,
    )
    db.add(series)
    db.flush()
    db.add(LogbookRecurrenceParticipant(
        series_id=series.id, event_id=ctx["event"].id, user_id=worker.id
    ))
    db.commit()
    ctx["series_ids"].append(series.id)

    def generate():
        with SessionLocal() as independent_db:
            return logbook_recurrence_service.generate_series_window(
                independent_db, series.id, actor=admin
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: generate(), range(2)))

    db.expire_all()
    occurrences = list(db.scalars(select(LogbookInstance).where(
        LogbookInstance.recurrence_series_id == series.id
    ).order_by(LogbookInstance.occurrence_date)).all())
    ctx["instance_ids"].extend(item.id for item in occurrences)
    assert sum(result["generated"] for result in results) == 4
    assert len(occurrences) == 4
    assert len({item.occurrence_date for item in occurrences}) == 4
    assert db.scalar(select(func.count(LogbookAssignment.id)).where(
        LogbookAssignment.logbook_instance_id.in_([item.id for item in occurrences])
    )) == 4
    assert db.scalar(select(func.count(AuditLog.id)).where(
        AuditLog.event_id == ctx["event"].id,
        AuditLog.action == "LOGBOOK_RECURRENCE_GENERATED",
        AuditLog.entity_id == series.id,
    )) == 1
    db.refresh(series)
    assert series.generated_count == 4
    assert series.next_occurrence_date is None

    for _ in range(3):
        assert generate()["generated"] == 0
    with SessionLocal() as duplicate_db:
        duplicate_db.add(LogbookInstance(
            event_id=ctx["event"].id, template_id=template.id,
            template_version_id=version.id, name="Duplicada",
            operational_stage="OPERATION", assignment_mode="INDIVIDUAL",
            opens_at=occurrences[0].opens_at, due_at=occurrences[0].due_at,
            status="SCHEDULED", recurrence_series_id=series.id,
            occurrence_date=occurrences[0].occurrence_date,
        ))
        with pytest.raises(IntegrityError) as duplicate:
            duplicate_db.commit()
        duplicate_db.rollback()
    assert "uq_logbook_instance_recurrence_date" in str(duplicate.value)
    with SessionLocal() as healthy_db:
        assert healthy_db.scalar(select(func.count(LogbookInstance.id)).where(
            LogbookInstance.recurrence_series_id == series.id
        )) == 4
