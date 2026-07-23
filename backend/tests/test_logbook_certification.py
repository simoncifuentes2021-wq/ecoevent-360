from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy import delete, select
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.core import Client, Event, EventStaff, Incident, Task, User
from app.models.enums import EventStatus, UserRole
from app.models.logbook import (
    LogbookCorrectiveEvidenceLink,
    LogbookEvidence,
    LogbookIncidentLink,
    LogbookInstance,
    LogbookTaskLink,
    LogbookTemplate,
    LogbookTemplateVersion,
)
from app.schemas.logbook_schema import (
    CorrectiveIncidentIn,
    CorrectiveTaskIn,
    InstanceCreate,
    ItemIn,
    OptionIn,
    ResponseSave,
    SectionIn,
    TemplateCreate,
    TemplateUpdate,
)
from app.services import logbook_service


def expect_http(status: int, call):
    with pytest.raises(HTTPException) as exc:
        call()
    assert exc.value.status_code == status
    return exc.value


def image_bytes(fmt: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (3, 3), "green").save(output, format=fmt)
    return output.getvalue()


def upload(name: str, content: bytes, mime: str) -> UploadFile:
    return UploadFile(
        filename=name,
        file=BytesIO(content),
        headers=Headers({"content-type": mime}),
    )


@pytest.fixture()
def pg():
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    original_storage = {
        key: getattr(settings, key)
        for key in (
            "cloudflare_r2_bucket",
            "cloudflare_r2_account_id",
            "cloudflare_r2_access_key_id",
            "cloudflare_r2_secret_access_key",
            "cloudflare_r2_public_base_url",
        )
    }
    for key in original_storage:
        setattr(settings, key, None)

    owner = Client(
        business_name=f"Certification Owner {suffix}",
        contact_email=f"cert-owner-{suffix}@example.com",
    )
    other_client = Client(
        business_name=f"Certification Other {suffix}",
        contact_email=f"cert-other-{suffix}@example.com",
    )
    db.add_all([owner, other_client])
    db.flush()

    def user(label, role, *, client_id=None, active=True):
        value = User(
            full_name=f"Cert {label}",
            email=f"cert-{label.lower()}-{suffix}@example.com",
            password_hash="x",
            role=role,
            client_id=client_id,
            is_active=active,
        )
        db.add(value)
        db.flush()
        return value

    users = {
        "admin": user("Admin", UserRole.ADMIN),
        "super_admin": user("SuperAdmin", UserRole.SUPER_ADMIN),
        "supervisor": user("Supervisor", UserRole.SUPERVISOR),
        "other_supervisor": user("OtherSupervisor", UserRole.SUPERVISOR),
        "worker1": user("Worker1", UserRole.WORKER),
        "worker2": user("Worker2", UserRole.WORKER),
        "outsider": user("Outsider", UserRole.WORKER),
        "logistics": user("Logistics", UserRole.LOGISTICS_OPERATOR),
        "other_logistics": user("OtherLogistics", UserRole.LOGISTICS_OPERATOR),
        "inactive": user("Inactive", UserRole.WORKER, active=False),
        "client": user("Client", UserRole.CLIENT, client_id=owner.id),
        "other_client": user("OtherClient", UserRole.CLIENT, client_id=other_client.id),
    }
    now = datetime.utcnow()
    event = Event(
        client_id=owner.id,
        name=f"Certification Event {suffix}",
        start_date=now + timedelta(days=1),
        end_date=now + timedelta(days=2),
        status=EventStatus.PLANNING,
        created_by=users["admin"].id,
    )
    other_event = Event(
        client_id=other_client.id,
        name=f"Other Certification Event {suffix}",
        start_date=now + timedelta(days=1),
        end_date=now + timedelta(days=2),
        status=EventStatus.PLANNING,
        created_by=users["admin"].id,
    )
    db.add_all([event, other_event])
    db.flush()
    for name in ("supervisor", "worker1", "worker2", "logistics", "inactive"):
        db.add(EventStaff(event_id=event.id, user_id=users[name].id))
    db.add(EventStaff(event_id=other_event.id, user_id=users["other_supervisor"].id))
    db.commit()

    context = {
        "db": db,
        "suffix": suffix,
        "clients": [owner, other_client],
        "users": users,
        "events": [event, other_event],
    }
    try:
        yield context
    finally:
        db.rollback()
        event_ids = [item.id for item in context["events"]]
        instance_ids = list(
            db.scalars(select(LogbookInstance.id).where(LogbookInstance.event_id.in_(event_ids)))
        )
        storage_paths = list(
            db.scalars(
                select(LogbookEvidence.storage_key).where(
                    LogbookEvidence.instance_id.in_(instance_ids)
                )
            )
        ) if instance_ids else []
        if instance_ids:
            incident_link_ids = list(
                db.scalars(
                    select(LogbookIncidentLink.id).where(
                        LogbookIncidentLink.instance_id.in_(instance_ids)
                    )
                )
            )
            task_link_ids = list(
                db.scalars(
                    select(LogbookTaskLink.id).where(LogbookTaskLink.instance_id.in_(instance_ids))
                )
            )
            db.execute(
                delete(LogbookCorrectiveEvidenceLink).where(
                    (LogbookCorrectiveEvidenceLink.incident_link_id.in_(incident_link_ids))
                    | (LogbookCorrectiveEvidenceLink.task_link_id.in_(task_link_ids))
                )
            )
            db.execute(
                delete(LogbookIncidentLink).where(
                    LogbookIncidentLink.instance_id.in_(instance_ids)
                )
            )
            db.execute(
                delete(LogbookTaskLink).where(LogbookTaskLink.instance_id.in_(instance_ids))
            )
            db.execute(
                delete(LogbookEvidence).where(LogbookEvidence.instance_id.in_(instance_ids))
            )
            db.execute(delete(LogbookInstance).where(LogbookInstance.id.in_(instance_ids)))
        template_ids = list(
            db.scalars(
                select(LogbookTemplate.id).where(
                    LogbookTemplate.created_by.in_(
                        [users["admin"].id, users["super_admin"].id]
                    )
                )
            )
        )
        if template_ids:
            db.execute(
                delete(LogbookTemplateVersion).where(
                    LogbookTemplateVersion.template_id.in_(template_ids)
                )
            )
            db.execute(delete(LogbookTemplate).where(LogbookTemplate.id.in_(template_ids)))
        db.execute(delete(Task).where(Task.event_id.in_(event_ids)))
        db.execute(delete(Incident).where(Incident.event_id.in_(event_ids)))
        db.execute(delete(EventStaff).where(EventStaff.event_id.in_(event_ids)))
        db.execute(delete(AuditLog).where(AuditLog.event_id.in_(event_ids)))
        db.execute(delete(Event).where(Event.id.in_(event_ids)))
        user_ids = [item.id for item in users.values()]
        db.execute(delete(AuditLog).where(AuditLog.user_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.execute(delete(Client).where(Client.id.in_([owner.id, other_client.id])))
        db.commit()
        db.close()
        for value in storage_paths:
            path = Path(value)
            if path.is_file():
                path.unlink()
        for key, value in original_storage.items():
            setattr(settings, key, value)


def make_template(db, actor, *, all_types=False, shared=False):
    if all_types:
        items = [
            ItemIn(title="Casilla", position=0, item_type="CHECKBOX"),
            ItemIn(title="Sí o no", position=1, item_type="YES_NO"),
            ItemIn(
                title="Estado",
                position=2,
                item_type="STATUS_SELECT",
                options=[
                    OptionIn(label="Correcto", value="OK", position=0, is_success_value=True),
                    OptionIn(label="Falla", value="FAIL", position=1, is_failure_value=True),
                ],
            ),
            ItemIn(title="Número", position=3, item_type="NUMBER"),
            ItemIn(title="Texto corto", position=4, item_type="SHORT_TEXT"),
            ItemIn(title="Texto largo", position=5, item_type="LONG_TEXT"),
            ItemIn(
                title="Fotografía",
                position=6,
                item_type="PHOTO",
                evidence_policy="REQUIRED",
                min_evidences=1,
                max_evidences=2,
                client_visible_by_default=True,
            ),
            ItemIn(
                title="Confirmación",
                position=7,
                item_type="CONFIRMATION",
                require_comment_on_failure=True,
            ),
            ItemIn(
                title="No aplica",
                position=8,
                item_type="SHORT_TEXT",
                allow_not_applicable=True,
            ),
        ]
    else:
        items = [
            ItemIn(title="Control compartido", position=0, item_type="CHECKBOX"),
            ItemIn(title="Observación compartida", position=1, item_type="SHORT_TEXT"),
        ]
    return logbook_service.create_template(
        db,
        TemplateCreate(
            name=f"{'Shared' if shared else 'Individual'} certification {uuid4().hex[:6]}",
            operational_stage="OPERATION",
            default_assignment_mode="SHARED" if shared else "INDIVIDUAL",
            default_client_visibility=True,
            sections=[SectionIn(title="General", position=0, items=items)],
        ),
        actor,
    )


def published_version(db, template, actor):
    detail = logbook_service.get_template_detail(db, template.id, actor)
    version = detail.versions[0]
    logbook_service.publish(db, version.id, actor)
    return logbook_service.get_version_detail(db, version.id, actor)


def save(db, assignment, item, actor, **values):
    return logbook_service.save_response(
        db,
        assignment.id,
        ResponseSave(item_id=item.id, result_status="PENDING", **values),
        actor,
    )


def test_certification_roles_templates_versions_and_audit(pg):
    db, users, (event, other_event) = pg["db"], pg["users"], pg["events"]
    template = make_template(db, users["admin"])
    draft = logbook_service.get_template_detail(db, template.id, users["admin"]).versions[0]
    sections = [
        SectionIn(
            title="Segunda",
            position=0,
            items=[ItemIn(title="Movido", position=0, item_type="SHORT_TEXT")],
        ),
        SectionIn(
            title="Primera",
            position=1,
            items=[ItemIn(title="Reordenado", position=0, item_type="CHECKBOX")],
        ),
    ]
    updated = logbook_service.update_template(
        db,
        template.id,
        TemplateUpdate(
            name="Plantilla certificada",
            description="Metadatos editados",
            default_client_visibility=False,
            sections=sections,
        ),
        users["admin"],
    )
    assert updated.name == "Plantilla certificada"
    detail = logbook_service.get_version_detail(db, draft.id, users["admin"])
    assert [section.title for section in detail.sections] == ["Segunda", "Primera"]
    assert detail.sections[0].items[0].title == "Movido"
    logbook_service.publish(db, draft.id, users["super_admin"])
    expect_http(
        409,
        lambda: logbook_service.update_template(
            db, template.id, TemplateUpdate(description="No permitido"), users["admin"]
        ),
    )
    clone = logbook_service.new_version(db, template.id, users["admin"], draft.id)
    assert clone.version_number == 2
    assert logbook_service.get_version_detail(db, clone.id, users["admin"]).sections
    expect_http(
        403,
        lambda: logbook_service.create_instance(
            db,
            event.id,
            InstanceCreate(
                template_version_id=draft.id,
                assignment_mode="INDIVIDUAL",
                participant_ids=[users["worker1"].id],
            ),
            users["other_supervisor"],
        ),
    )
    expect_http(
        422,
        lambda: logbook_service.create_instance(
            db,
            event.id,
            InstanceCreate(
                template_version_id=draft.id,
                assignment_mode="INDIVIDUAL",
                participant_ids=[users["outsider"].id],
            ),
            users["admin"],
        ),
    )
    expect_http(
        422,
        lambda: logbook_service.create_instance(
            db,
            event.id,
            InstanceCreate(
                template_version_id=draft.id,
                assignment_mode="INDIVIDUAL",
                participant_ids=[users["inactive"].id],
            ),
            users["admin"],
        ),
    )
    expect_http(
        403,
        lambda: logbook_service.list_event_instances(
            db, other_event.id, users["supervisor"], 1, 20
        ),
    )
    actions = set(
        db.scalars(
            select(AuditLog.action).where(
                AuditLog.user_id.in_([users["admin"].id, users["super_admin"].id]),
                AuditLog.module == "logbooks",
            )
        )
    )
    assert {
        "LOGBOOK_TEMPLATE_CREATED",
        "LOGBOOK_TEMPLATE_UPDATED",
        "LOGBOOK_VERSION_UPDATED",
        "LOGBOOK_STRUCTURE_REORDERED",
        "LOGBOOK_CLIENT_VISIBILITY_CHANGED",
        "LOGBOOK_VERSION_PUBLISHED",
        "LOGBOOK_VERSION_CREATED",
    } <= actions


def test_certification_individual_all_types_evidence_review_and_client(pg):
    db, users, event = pg["db"], pg["users"], pg["events"][0]
    template = make_template(db, users["admin"], all_types=True)
    version = published_version(db, template, users["admin"])
    instance = logbook_service.create_instance(
        db,
        event.id,
        InstanceCreate(
            template_version_id=version.id,
            assignment_mode="INDIVIDUAL",
            participant_ids=[users["worker1"].id],
            supervisor_id=users["supervisor"].id,
            client_visibility=True,
        ),
        users["admin"],
    )
    assignment = instance.assignments[0]
    items = {item.title: item for item in version.sections[0].items}
    option = items["Estado"].options[0]
    save(db, assignment, items["Casilla"], users["worker1"], boolean_value=True)
    save(db, assignment, items["Sí o no"], users["worker1"], boolean_value=True)
    save(db, assignment, items["Estado"], users["worker1"], selected_option_id=option.id)
    save(db, assignment, items["Número"], users["worker1"], numeric_value=12)
    save(db, assignment, items["Texto corto"], users["worker1"], text_value="corto")
    save(db, assignment, items["Texto largo"], users["worker1"], text_value="texto largo")
    photo_response = save(db, assignment, items["Fotografía"], users["worker1"])
    failed = save(
        db, assignment, items["Confirmación"], users["worker1"], boolean_value=False
    )
    save(db, assignment, items["No aplica"], users["worker1"], is_not_applicable=True)
    expect_http(422, lambda: logbook_service.submit(db, assignment.id, users["worker1"]))
    failed = save(
        db,
        assignment,
        items["Confirmación"],
        users["worker1"],
        boolean_value=False,
        comment="Falla documentada",
        version=failed.version,
    )
    expect_http(422, lambda: logbook_service.submit(db, assignment.id, users["worker1"]))

    expect_http(
        422,
        lambda: logbook_service.upload_evidence(
            db,
            assignment.id,
            photo_response.id,
            upload("fake.jpg", image_bytes("PNG"), "image/jpeg"),
            None,
            users["worker1"],
        ),
    )
    expect_http(
        413,
        lambda: logbook_service.upload_evidence(
            db,
            assignment.id,
            photo_response.id,
            upload(
                "too-large.jpg",
                b"x" * (settings.max_upload_size_bytes + 1),
                "image/jpeg",
            ),
            None,
            users["worker1"],
        ),
    )
    evidence = logbook_service.upload_evidence(
        db,
        assignment.id,
        photo_response.id,
        upload("real.png", image_bytes("PNG"), "image/png"),
        "foto pública",
        users["worker1"],
    )
    second = logbook_service.upload_evidence(
        db,
        assignment.id,
        photo_response.id,
        upload("real.webp", image_bytes("WEBP"), "image/webp"),
        None,
        users["worker1"],
    )
    expect_http(
        422,
        lambda: logbook_service.upload_evidence(
            db,
            assignment.id,
            photo_response.id,
            upload("extra.jpg", image_bytes("JPEG"), "image/jpeg"),
            None,
            users["worker1"],
        ),
    )
    logbook_service.delete_evidence(db, second.id, users["worker1"])
    assert db.get(LogbookEvidence, second.id).deleted_at is not None

    access = logbook_service.evidence_access(db, evidence.id, users["worker1"])
    token = parse_qs(urlparse(access["url"]).query)["token"][0]
    content, _, filename = logbook_service.evidence_content(db, evidence.id, token)
    assert content == image_bytes("PNG")
    assert filename == "real.png"
    expired = create_access_token(
        {"scope": "logbook_evidence", "evidence_id": str(evidence.id)},
        expires_delta=timedelta(seconds=-1),
    )
    expect_http(
        401, lambda: logbook_service.evidence_content(db, evidence.id, expired)
    )
    wrong = create_access_token(
        {"scope": "logbook_evidence", "evidence_id": str(uuid4())},
        expires_delta=timedelta(minutes=1),
    )
    expect_http(403, lambda: logbook_service.evidence_content(db, evidence.id, wrong))
    expect_http(
        403, lambda: logbook_service.evidence_access(db, evidence.id, users["worker2"])
    )

    submitted = logbook_service.submit(db, assignment.id, users["worker1"])
    assert submitted.attempt_number == 1
    expect_http(
        409,
        lambda: save(
            db, assignment, items["Texto corto"], users["worker1"], text_value="bloqueado"
        ),
    )
    expect_http(
        422,
        lambda: logbook_service.review(
            db, assignment.id, users["supervisor"], False, None
        ),
    )
    changes = logbook_service.review(
        db, assignment.id, users["supervisor"], False, "Corregir confirmación"
    )
    assert changes.status.value == "CHANGES_REQUESTED"
    corrected = save(
        db,
        assignment,
        items["Confirmación"],
        users["worker1"],
        boolean_value=True,
        version=failed.version,
    )
    assert corrected.result_status.value == "COMPLETED"
    resubmitted = logbook_service.submit(db, assignment.id, users["worker1"])
    assert resubmitted.attempt_number == 2
    approved = logbook_service.review(
        db, assignment.id, users["supervisor"], True, "Aprobado"
    )
    assert approved.status.value == "APPROVED"
    detail = logbook_service.get_instance_detail(db, instance.id, users["supervisor"])
    assert detail["metrics"]["completion_percentage"] > 0
    assert detail["metrics"]["participation_percentage"] == 100
    assert detail["metrics"]["approval_percentage"] == 100
    assert len(detail["assignments"][0]["history"]) == 4
    expect_http(
        403,
        lambda: logbook_service.get_instance_detail(
            db, instance.id, users["other_logistics"]
        ),
    )

    summary = logbook_service.client_summary(db, instance.id, users["client"])
    serialized = str(summary).lower()
    assert "storage_key" not in serialized
    assert users["worker1"].email not in serialized
    assert summary["public_evidences"][0].id == evidence.id
    expect_http(
        404,
        lambda: logbook_service.client_summary(db, instance.id, users["other_client"]),
    )


def test_certification_shared_concurrency_collaboration_and_review(pg):
    db, users, event = pg["db"], pg["users"], pg["events"][0]
    template = make_template(db, users["super_admin"], shared=True)
    version = published_version(db, template, users["super_admin"])
    instance = logbook_service.create_instance(
        db,
        event.id,
        InstanceCreate(
            template_version_id=version.id,
            assignment_mode="SHARED",
            participant_ids=[
                users["worker1"].id,
                users["worker2"].id,
                users["logistics"].id,
            ],
            supervisor_id=users["supervisor"].id,
        ),
        users["super_admin"],
    )
    assignments = {item.user_id: item for item in instance.assignments}
    first_item, second_item = version.sections[0].items
    first = save(
        db,
        assignments[users["worker1"].id],
        first_item,
        users["worker1"],
        boolean_value=True,
    )
    second_phone_db = SessionLocal()
    try:
        worker_two_detail = logbook_service.get_instance_detail(
            second_phone_db,
            instance.id,
            second_phone_db.get(User, users["worker2"].id),
        )
        assert len(worker_two_detail["assignments"]) == 1
        assert worker_two_detail["assignments"][0]["user_id"] == users["worker2"].id
        reflected = next(
            response
            for response in worker_two_detail["assignments"][0]["responses"]
            if response["logbook_item_id"] == first_item.id
        )
        assert reflected["boolean_value"] is True
        assert reflected["completed_by_name"] == users["worker1"].full_name
    finally:
        second_phone_db.close()
    stale_version = first.version
    updated = save(
        db,
        assignments[users["worker2"].id],
        first_item,
        users["worker2"],
        boolean_value=False,
        version=stale_version,
    )
    assert updated.completed_by == users["worker2"].id
    expect_http(
        409,
        lambda: save(
            db,
            assignments[users["worker1"].id],
            first_item,
            users["worker1"],
            boolean_value=True,
            version=stale_version,
        ),
    )
    save(
        db,
        assignments[users["logistics"].id],
        second_item,
        users["logistics"],
        text_value="colaboración logística",
    )
    expect_http(
        403,
        lambda: logbook_service.save_response(
            db,
            assignments[users["worker1"].id].id,
            ResponseSave(
                item_id=second_item.id,
                result_status="COMPLETED",
                text_value="intrusión",
            ),
            users["outsider"],
        ),
    )
    prior_version = updated.version
    latest = save(
        db,
        assignments[users["worker2"].id],
        first_item,
        users["worker2"],
        boolean_value=True,
        version=prior_version,
    )
    assert latest.version > prior_version
    submitted = logbook_service.submit(
        db, assignments[users["worker1"].id].id, users["worker1"]
    )
    assert submitted.attempt_number == 1
    changed = logbook_service.review(
        db,
        assignments[users["worker1"].id].id,
        users["supervisor"],
        False,
        "Ajustar observación",
    )
    assert changed.status.value == "CHANGES_REQUESTED"
    for assignment in instance.assignments:
        db.refresh(assignment)
        assert assignment.status.value == "CHANGES_REQUESTED"
    corrected = save(
        db,
        assignments[users["worker2"].id],
        second_item,
        users["worker2"],
        text_value="observación corregida",
    )
    assert corrected.completed_by == users["worker2"].id
    resubmitted = logbook_service.submit(
        db, assignments[users["worker2"].id].id, users["worker2"]
    )
    assert resubmitted.attempt_number == 2
    logbook_service.review(
        db,
        assignments[users["worker2"].id].id,
        users["supervisor"],
        True,
        "Aprobación compartida",
    )
    detail = logbook_service.get_instance_detail(db, instance.id, users["supervisor"])
    assert detail["metrics"]["collaborating_participants"] >= 2
    assert detail["metrics"]["completion_percentage"] == 100
    assert detail["metrics"]["approval_percentage"] == 100
    assert any(
        response["completed_by_name"] == users["worker2"].full_name
        for assignment in detail["assignments"]
        for response in assignment["responses"]
    )


def test_certification_correctives_selected_evidence_and_secure_audit(pg):
    db, users, event = pg["db"], pg["users"], pg["events"][0]
    template = make_template(db, users["admin"])
    version = published_version(db, template, users["admin"])
    instance = logbook_service.create_instance(
        db,
        event.id,
        InstanceCreate(
            template_version_id=version.id,
            assignment_mode="INDIVIDUAL",
            participant_ids=[users["worker1"].id],
            supervisor_id=users["supervisor"].id,
        ),
        users["admin"],
    )
    assignment = instance.assignments[0]
    response = save(
        db,
        assignment,
        version.sections[0].items[0],
        users["worker1"],
        boolean_value=False,
    )
    evidence = logbook_service.upload_evidence(
        db,
        assignment.id,
        response.id,
        upload("corrective.jpg", image_bytes("JPEG"), "image/jpeg"),
        None,
        users["worker1"],
    )
    alien_id = uuid4()
    expect_http(
        422,
        lambda: logbook_service.create_corrective_incident(
            db,
            response.id,
            CorrectiveIncidentIn(
                title="Incidencia inválida",
                evidence_ids=[alien_id],
            ),
            users["supervisor"],
        ),
    )
    incident = logbook_service.create_corrective_incident(
        db,
        response.id,
        CorrectiveIncidentIn(
            title="Incidencia certificada",
            assigned_to=users["worker1"].id,
            priority="HIGH",
            evidence_ids=[evidence.id],
        ),
        users["supervisor"],
    )
    assert incident.priority.value == "HIGH"
    expect_http(
        409,
        lambda: logbook_service.create_corrective_incident(
            db,
            response.id,
            CorrectiveIncidentIn(title="Duplicada"),
            users["supervisor"],
        ),
    )
    expect_http(
        422,
        lambda: logbook_service.create_corrective_task(
            db,
            response.id,
            CorrectiveTaskIn(
                title="Responsable inválido",
                assigned_to=users["outsider"].id,
            ),
            users["supervisor"],
        ),
    )
    due = datetime.utcnow() + timedelta(days=1)
    task = logbook_service.create_corrective_task(
        db,
        response.id,
        CorrectiveTaskIn(
            title="Tarea certificada",
            assigned_to=users["worker1"].id,
            scheduled_at=due,
            priority="CRITICAL",
            evidence_ids=[evidence.id],
        ),
        users["supervisor"],
    )
    assert task.priority.value == "CRITICAL"
    assert task.scheduled_at == due
    expect_http(
        409,
        lambda: logbook_service.create_corrective_task(
            db,
            response.id,
            CorrectiveTaskIn(
                title="Duplicada",
                assigned_to=users["worker1"].id,
            ),
            users["supervisor"],
        ),
    )
    assert db.get(LogbookEvidence, evidence.id).deleted_at is None
    logs = list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.event_id == event.id,
                AuditLog.action.in_(
                    ["LOGBOOK_INCIDENT_CREATED", "LOGBOOK_CORRECTIVE_TASK_CREATED"]
                ),
            )
        )
    )
    assert len(logs) == 2
    assert {entry.user_id for entry in logs} == {users["supervisor"].id}
    serialized = " ".join(
        str((entry.old_data, entry.new_data, entry.metadata_)).lower() for entry in logs
    )
    for forbidden in ("jwt", "storage_key", "password", "signed_url", "access_token"):
        assert forbidden not in serialized
