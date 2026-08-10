from datetime import datetime, timedelta
import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import SessionLocal
from app.models.core import (
    BikeZoneRecord,
    Client,
    Evidence,
    Event,
    EventForm,
    EventSession,
    EventSessionStaff,
    EventStaff,
    FormResponse,
    Incident,
    ReportPublication,
    Task,
    User,
)
from app.models.enums import (
    BikeZoneStatus,
    EventFormStatus,
    EventFormType,
    EventStatus,
    IncidentStatus,
    ReportLayoutVariant,
    ReportPublicationStatus,
    ReportScope,
    ReportStatus,
    TaskStatus,
    UserRole,
)
from app.schemas.report_schema import (
    CustomSectionCreate,
    CustomTextContent,
    EvidenceAdd,
    ReportSectionContent,
    ReportUpdate,
    SectionOrderUpdate,
    SectionUpdate,
)
from app.services import (
    report_autofill_service,
    report_builder_service,
    report_publication_service,
    report_revision_service,
    report_service,
)


@pytest.fixture()
def report_context():
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    client = Client(business_name=f"Report client {suffix}")
    other_client = Client(business_name=f"Other {suffix}")
    db.add_all([client, other_client])
    db.flush()
    admin = User(
        full_name="Report admin",
        email=f"report-admin-{suffix}@test.local",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    customer = User(
        full_name="Report client",
        email=f"report-client-{suffix}@test.local",
        password_hash="x",
        role=UserRole.CLIENT,
        client_id=client.id,
    )
    outsider = User(
        full_name="Other client",
        email=f"report-other-{suffix}@test.local",
        password_hash="x",
        role=UserRole.CLIENT,
        client_id=other_client.id,
    )
    db.add_all([admin, customer, outsider])
    db.flush()
    start = datetime(2026, 8, 1, 9)
    event = Event(
        client_id=client.id,
        name="Report event",
        start_date=start,
        end_date=start + timedelta(days=2),
        status=EventStatus.PLANNING,
    )
    other_event = Event(
        client_id=other_client.id,
        name="Other event",
        start_date=start,
        end_date=start + timedelta(days=2),
        status=EventStatus.PLANNING,
    )
    db.add_all([event, other_event])
    db.flush()
    show = EventSession(event_id=event.id, name="Main show", expected_attendees=100)
    other_show = EventSession(event_id=other_event.id, name="Wrong show", expected_attendees=10)
    db.add_all([show, other_show])
    db.flush()
    db.add_all(
        [
            Task(
                event_id=event.id, session_id=show.id, title="Scoped", status=TaskStatus.COMPLETED
            ),
            Task(event_id=event.id, title="Global", status=TaskStatus.PENDING),
        ]
    )
    db.commit()
    try:
        yield db, event, show, other_show, admin, customer, outsider
    finally:
        db.rollback()
        db.execute(delete(Event).where(Event.id.in_([event.id, other_event.id])))
        db.execute(delete(User).where(User.id.in_([admin.id, customer.id, outsider.id])))
        db.execute(delete(Client).where(Client.id.in_([client.id, other_client.id])))
        db.commit()
        db.close()


def test_event_and_show_drafts_are_scoped(report_context):
    db, event, show, _, admin, _, _ = report_context
    event_report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    show_report = report_builder_service.create_draft(
        db, event.id, ReportScope.SHOW, show.id, admin
    )
    assert event_report.session_id is None and show_report.session_id == show.id
    task = next(section for section in show_report.sections if section.section_key == "tasks")
    assert next(field for field in task.content["fields"] if field["key"] == "total")["value"] == 1


def test_cross_event_show_and_client_creation_are_rejected(report_context):
    db, event, _, other_show, admin, customer, _ = report_context
    with pytest.raises(HTTPException) as cross:
        report_builder_service.create_draft(db, event.id, ReportScope.SHOW, other_show.id, admin)
    assert cross.value.status_code == 409
    with pytest.raises(HTTPException) as denied:
        report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, customer)
    assert denied.value.status_code == 403


def test_override_refresh_reset_and_stale_version(report_context):
    db, event, show, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.SHOW, show.id, admin)
    tasks = next(section for section in report.sections if section.section_key == "tasks")
    content = ReportSectionContent.model_validate(tasks.content)
    total = next(field for field in content.fields if field.key == "total")
    total.value = 8
    report_builder_service.update_section(
        db, report, tasks.id, SectionUpdate(content=content, edit_version=report.edit_version)
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    refreshed = report_builder_service.refresh(db, report, report.edit_version, admin)
    tasks = next(section for section in refreshed.sections if section.section_key == "tasks")
    total = next(field for field in tasks.content["fields"] if field["key"] == "total")
    assert (total["value"], total["auto_value"], total["is_overridden"]) == (8, 1, True)
    stale_version = refreshed.edit_version
    report_builder_service.reset_field(db, refreshed, tasks.id, "total", stale_version, admin)
    with pytest.raises(HTTPException) as stale:
        report_builder_service.update_report(
            db, refreshed, ReportUpdate(title="stale", edit_version=stale_version)
        )
    assert stale.value.status_code == 409


def test_only_custom_sections_can_be_removed(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    automatic = report.sections[0]
    with pytest.raises(HTTPException) as protected:
        report_builder_service.remove_custom_section(db, report, automatic.id, report.edit_version)
    assert protected.value.status_code == 409

    custom = report_builder_service.add_custom_section(
        db,
        report,
        CustomSectionCreate(
            title="Temporal",
            content=CustomTextContent(kind="TEXT", text="Se puede eliminar"),
            edit_version=report.edit_version,
        ),
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    report_builder_service.remove_custom_section(db, report, custom.id, report.edit_version)
    updated = report_builder_service.get_editor(db, report.id, admin)
    assert all(section.id != custom.id for section in updated.sections)
    assert [section.sort_order for section in updated.sections] == list(
        range(len(updated.sections))
    )


def test_environmental_story_template_loads_predetermined_sections_once(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    report_builder_service.update_report(
        db,
        report,
        ReportUpdate(template_key="ENVIRONMENTAL_STORY", edit_version=report.edit_version),
    )
    configured = report_builder_service.get_editor(db, report.id, admin)
    enabled = [section.section_key for section in configured.sections if section.is_enabled]
    assert "preset_eco_equivalences" in enabled
    assert enabled.index("waste") < enabled.index("bike_zone") < enabled.index("carbon")
    equivalences = next(
        section
        for section in configured.sections
        if section.section_key == "preset_eco_equivalences"
    )
    assert [field["label"] for field in equivalences.content["fields"]] == [
        "Árboles equivalentes",
        "CO₂ evitado",
        "Residuos desviados",
        "Agua ahorrada",
    ]
    report_builder_service.update_report(
        db,
        configured,
        ReportUpdate(template_key="ENVIRONMENTAL_STORY", edit_version=configured.edit_version),
    )
    final = report_builder_service.get_editor(db, report.id, admin)
    assert sum(section.section_key == "preset_eco_equivalences" for section in final.sections) == 1


def test_revision_is_reproducible_and_restores_layout(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    section = report.sections[0]
    report_builder_service.update_section(
        db,
        report,
        section.id,
        SectionUpdate(
            layout_variant=ReportLayoutVariant.TEXT_IMAGE, edit_version=report.edit_version
        ),
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    revision = report_revision_service.create(db, report, admin, report.edit_version, "baseline")
    original = revision.snapshot.copy()
    report = report_builder_service.get_editor(db, report.id, admin)
    report_builder_service.update_report(
        db, report, ReportUpdate(title="Changed", edit_version=report.edit_version)
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    report_revision_service.restore(db, report, revision.id, report.edit_version)
    db.refresh(revision)
    restored = report_builder_service.get_editor(db, report.id, admin)
    assert restored.title == original["title"] and revision.snapshot == original
    assert restored.sections[0].layout_variant == ReportLayoutVariant.TEXT_IMAGE


def test_client_cannot_read_draft(report_context):
    db, event, _, _, admin, customer, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    with pytest.raises(HTTPException) as denied:
        report_builder_service.get_editor(db, report.id, customer)
    assert denied.value.status_code == 404


@pytest.mark.parametrize("role", [UserRole.SUPERVISOR, UserRole.WORKER])
def test_assigned_operational_roles_cannot_read_draft(report_context, role):
    db, event, _, _, admin, _, _ = report_context
    user = User(
        full_name=f"Report {role.value.lower()}",
        email=f"report-{role.value.lower()}-{uuid4().hex[:8]}@test.local",
        password_hash="x",
        role=role,
    )
    db.add(user)
    db.flush()
    db.add(EventStaff(event_id=event.id, user_id=user.id, role_in_event=role.value))
    db.commit()
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)

    with pytest.raises(HTTPException) as denied:
        report_builder_service.get_editor(db, report.id, user)

    assert denied.value.status_code == 404


def test_full_event_flow_and_bike_source_is_immutable(report_context):
    db, event, _, _, admin, _, _ = report_context
    form = EventForm(
        event_id=event.id,
        title="Bike",
        form_type=EventFormType.BIKE_ZONE_REGISTRATION,
        public_slug=f"bike-{uuid4().hex}",
        status=EventFormStatus.ACTIVE,
    )
    db.add(form)
    db.flush()
    for _ in range(5):
        response = FormResponse(
            form_id=form.id, event_id=event.id, response_code=f"bike-{uuid4().hex}"
        )
        db.add(response)
        db.flush()
        db.add(
            BikeZoneRecord(
                response_id=response.id,
                event_id=event.id,
                code=f"B-{uuid4().hex}",
                status=BikeZoneStatus.REGISTERED,
            )
        )
    evidence = Evidence(
        event_id=event.id,
        file_url="private/evidences/report.webp",
        file_type="image/webp",
        description="Report photo",
    )
    db.add(evidence)
    db.commit()
    source_ids = list(
        db.scalars(select(BikeZoneRecord.id).where(BikeZoneRecord.event_id == event.id))
    )
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    bike = next(s for s in report.sections if s.section_key == "bike_zone")
    content = ReportSectionContent.model_validate(bike.content)
    users = next(f for f in content.fields if f.key == "users")
    assert users.auto_value == 5
    users.value = 8
    report_builder_service.update_section(
        db,
        report,
        bike.id,
        SectionUpdate(
            content=content,
            layout_variant=ReportLayoutVariant.BIG_NUMBERS,
            edit_version=report.edit_version,
        ),
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    report = report_builder_service.refresh(db, report, report.edit_version, admin)
    bike = next(s for s in report.sections if s.section_key == "bike_zone")
    users = next(f for f in bike.content["fields"] if f["key"] == "users")
    assert (users["auto_value"], users["value"], users["is_overridden"]) == (5, 8, True)
    report_builder_service.reset_field(db, report, bike.id, "users", report.edit_version, admin)
    report = report_builder_service.get_editor(db, report.id, admin)
    bike = next(s for s in report.sections if s.section_key == "bike_zone")
    assert next(f for f in bike.content["fields"] if f["key"] == "users")["value"] == 5
    ids = [s.id for s in report.sections]
    report_builder_service.reorder(
        db,
        report,
        SectionOrderUpdate(section_ids=list(reversed(ids)), edit_version=report.edit_version),
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    first = report.sections[0]
    report_builder_service.update_section(
        db, report, first.id, SectionUpdate(is_enabled=False, edit_version=report.edit_version)
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    report_builder_service.update_section(
        db, report, first.id, SectionUpdate(is_enabled=True, edit_version=report.edit_version)
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    report_builder_service.add_custom_section(
        db,
        report,
        CustomSectionCreate(
            title="Editorial",
            content=CustomTextContent(kind="TEXT", text="Resultado destacado"),
            edit_version=report.edit_version,
        ),
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    report_builder_service.add_evidence(
        db, report, EvidenceAdd(evidence_id=evidence.id, edit_version=report.edit_version)
    )
    report = report_builder_service.get_editor(db, report.id, admin)
    revision = report_revision_service.create(db, report, admin, report.edit_version, "E2E")
    report = report_builder_service.get_editor(db, report.id, admin)
    report_revision_service.restore(db, report, revision.id, report.edit_version)
    preview = report_builder_service.get_editor(db, report.id, admin)
    assert preview.evidences and any(s.is_custom for s in preview.sections)
    assert (
        list(db.scalars(select(BikeZoneRecord.id).where(BikeZoneRecord.event_id == event.id)))
        == source_ids
    )


def test_show_flow_filters_tasks_and_evidence(report_context):
    db, event, show, _, admin, _, _ = report_context
    second = EventSession(event_id=event.id, name="Second show", expected_attendees=10)
    db.add(second)
    db.flush()
    staff = EventStaff(event_id=event.id, user_id=admin.id, role_in_event="Coordinación")
    db.add(staff)
    db.flush()
    db.add(
        EventSessionStaff(
            event_id=event.id,
            session_id=show.id,
            event_staff_id=staff.id,
            operational_role="Coordinación",
        )
    )
    db.add_all(
        [
            Incident(
                event_id=event.id,
                session_id=show.id,
                title="Own incident",
                status=IncidentStatus.RESOLVED,
            ),
            Incident(
                event_id=event.id,
                session_id=second.id,
                title="Other incident",
                status=IncidentStatus.REPORTED,
            ),
        ]
    )
    own = Evidence(
        event_id=event.id, session_id=show.id, file_url="private/own.webp", file_type="image/webp"
    )
    other = Evidence(
        event_id=event.id,
        session_id=second.id,
        file_url="private/other.webp",
        file_type="image/webp",
    )
    db.add_all([own, other])
    db.commit()
    report = report_builder_service.create_draft(db, event.id, ReportScope.SHOW, show.id, admin)
    assert {item["id"] for item in report_builder_service.available_evidences(db, report)} == {
        own.id
    }
    tasks = next(s for s in report.sections if s.section_key == "tasks")
    assert next(f for f in tasks.content["fields"] if f["key"] == "total")["value"] == 1
    staff_section = next(s for s in report.sections if s.section_key == "staff")
    incidents = next(s for s in report.sections if s.section_key == "incidents")
    assert next(f for f in staff_section.content["fields"] if f["key"] == "total")["value"] == 1
    assert next(f for f in incidents.content["fields"] if f["key"] == "total")["value"] == 1
    with pytest.raises(HTTPException) as error:
        report_builder_service.add_evidence(
            db, report, EvidenceAdd(evidence_id=other.id, edit_version=report.edit_version)
        )
    assert error.value.status_code == 409


def _rls(engine, user, sql, params=None):
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(
            text("select set_config('app.current_user_id',:v,true)"), {"v": str(user.id)}
        )
        connection.execute(
            text("select set_config('app.current_role',:v,true)"), {"v": user.role.value}
        )
        connection.execute(
            text("select set_config('app.current_client_id',:v,true)"),
            {"v": str(user.client_id or "")},
        )
        try:
            result = connection.execute(text(sql), params or {})
            rows = result.fetchall() if result.returns_rows else []
            transaction.rollback()
            return rows, None
        except DBAPIError as error:
            transaction.rollback()
            return [], error


def test_report_rls_real_runtime_role(report_context):
    db, event, _, _, admin, customer, outsider = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    revision = report_revision_service.create(db, report, admin, report.edit_version, "RLS")
    report = report_builder_service.get_editor(db, report.id, admin)
    publication = ReportPublication(
        report_id=report.id,
        publication_number=1,
        status=ReportPublicationStatus.GENERATED,
        storage_key=f"private/reports/{report.id}/publications/v1/report.pdf",
        sha256="a" * 64,
        file_size=200,
        page_count=1,
        snapshot={},
        theme_snapshot={},
        generated_by=admin.id,
        idempotency_key="rls-publication-v1",
    )
    db.add(publication)
    db.commit()
    engine = create_engine(os.environ["RLS_DATABASE_URL"])
    try:
        client_rows, _ = _rls(
            engine, customer, "select id from reports where id=:id", {"id": report.id}
        )
        admin_rows, _ = _rls(
            engine, admin, "select id from reports where id=:id", {"id": report.id}
        )
        foreign_rows, _ = _rls(
            engine, outsider, "select id from reports where id=:id", {"id": report.id}
        )
        revision_rows, _ = _rls(
            engine, customer, "select id from report_revisions where id=:id", {"id": revision.id}
        )
        hidden_publication, _ = _rls(
            engine,
            customer,
            "select id from report_publications where id=:id",
            {"id": publication.id},
        )
        _, client_write = _rls(
            engine,
            customer,
            "insert into report_sections(report_id,section_key,section_type,title,sort_order) values (:id,'blocked','CUSTOM','Blocked',99)",
            {"id": report.id},
        )
        assert (
            client_rows == []
            and len(admin_rows) == 1
            and foreign_rows == []
            and revision_rows == []
            and hidden_publication == []
            and client_write is not None
        )
        report.status = ReportStatus.GENERATED
        publication.status = ReportPublicationStatus.DELIVERED
        db.commit()
        published, _ = _rls(
            engine, customer, "select id from reports where id=:id", {"id": report.id}
        )
        section_rows, _ = _rls(
            engine,
            customer,
            "select id from report_sections where report_id=:id",
            {"id": report.id},
        )
        delivered_publication, _ = _rls(
            engine,
            customer,
            "select id from report_publications where id=:id",
            {"id": publication.id},
        )
        foreign_publication, _ = _rls(
            engine,
            outsider,
            "select id from report_publications where id=:id",
            {"id": publication.id},
        )
        assert (
            len(published) == 1
            and section_rows
            and len(delivered_publication) == 1
            and foreign_publication == []
        )
    finally:
        engine.dispose()


def test_postgresql_scope_and_composite_constraints(report_context):
    db, event, show, other_show, _, _, _ = report_context
    engine = db.get_bind()
    invalid = [
        (
            "insert into reports(event_id,title,scope) values (:event,'bad','SHOW')",
            {"event": event.id},
        ),
        (
            "insert into reports(event_id,title,scope,session_id) values (:event,'bad','EVENT',:show)",
            {"event": event.id, "show": show.id},
        ),
        (
            "insert into reports(event_id,title,scope,session_id) values (:event,'bad','SHOW',:show)",
            {"event": event.id, "show": other_show.id},
        ),
    ]
    for sql, params in invalid:
        with engine.connect() as connection:
            with pytest.raises(DBAPIError):
                connection.execute(text(sql), params)
                connection.commit()


def test_legacy_report_flow_remains_available(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_service.create_final_report(db, event_id=event.id, current_user=admin)
    assert report.status == ReportStatus.GENERATED
    assert report_service.build_report_pdf(report).read(4) == b"%PDF"
    items, total = report_service.list_event_reports(
        db, event_id=event.id, current_user=admin, page=1, limit=20
    )
    assert total == 1 and items[0].id == report.id
    assert (
        report_service.mark_report_delivered(db, report_id=report.id, current_user=admin).status
        == ReportStatus.DELIVERED
    )
    assert (
        report_service.archive_report(db, report_id=report.id, current_user=admin).status
        == ReportStatus.ARCHIVED
    )


def test_premium_publications_are_immutable_idempotent_and_deliverable(report_context, monkeypatch):
    db, event, _, _, admin, customer, outsider = report_context
    stored = {}

    def render(document):
        marker = str(document.sections[0]["content"]).encode()
        return b"%PDF-1.7\n" + marker + b"\n%%EOF" + b"x" * 200, 2

    monkeypatch.setattr(report_publication_service.report_pdf_service, "render", render)
    monkeypatch.setattr(
        report_publication_service.file_storage_service,
        "save_private_object",
        lambda key, content, **_: stored.setdefault(key, content) and key,
    )
    monkeypatch.setattr(
        report_publication_service.file_storage_service,
        "delete_stored_file",
        lambda key: stored.pop(key, None),
    )
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    v1 = report_publication_service.generate(db, report.id, admin, "request-v1-fixed")
    same = report_publication_service.generate(db, report.id, admin, "request-v1-fixed")
    assert same.id == v1.id
    assert v1.sha256 == __import__("hashlib").sha256(stored[v1.storage_key]).hexdigest()
    assert report_publication_service.list_publications(db, report.id, customer) == []
    report = report_builder_service.get_editor(db, report.id, admin)
    section = report.sections[0]
    content = ReportSectionContent.model_validate(section.content)
    content.text = "Published later"
    report_builder_service.update_section(
        db, report, section.id, SectionUpdate(content=content, edit_version=report.edit_version)
    )
    v2 = report_publication_service.generate(db, report.id, admin, "request-v2-fixed")
    assert v2.publication_number == 2 and v1.sha256 != v2.sha256 and v1.snapshot != v2.snapshot
    report_publication_service.deliver(db, v1.id, admin)
    assert [
        item.id for item in report_publication_service.list_publications(db, report.id, customer)
    ] == [v1.id]
    with pytest.raises(HTTPException):
        report_publication_service.get_publication(db, v1.id, outsider)


def test_premium_renderer_opens_and_renders_all_layouts():
    from app.services.report_pdf_service import render
    from app.services.report_render_service import ReportRenderDocument, build_html, normalize_theme

    sections = tuple(
        {
            "section_key": str(index),
            "section_type": "CUSTOM",
            "title": f"Sección editorial {index + 1}",
            "layout_variant": variant.value,
            "is_enabled": True,
            "sort_order": index,
            "content": {
                "text": "Contenido editorial seguro",
                "fields": [{"label": "Bicicletas", "value": 238, "unit": "unidades"}],
                "items": [{"label": "PET", "value": 7104}],
            },
        }
        for index, variant in enumerate(ReportLayoutVariant)
    )
    document = ReportRenderDocument(
        report={
            "id": "r",
            "title": "Gestión Ambiental",
            "scope": "EVENT",
            "template_key": "COMPLETE",
        },
        event={"id": "e", "name": "Evento certificado", "date": "06.08.2026"},
        show=None,
        client={"id": "c", "name": "Cliente"},
        theme=normalize_theme({}),
        sections=sections,
        evidences=tuple(),
        publication={"number": None},
    )
    html = build_html(document)
    assert all(
        label not in html
        for label in ("HERO IMAGE TEXT", "KPI GRID", "BIG NUMBERS", "FEATURE CHART", "PHOTO GRID")
    )
    pdf, pages = render(document)
    assert pdf.startswith(b"%PDF-") and len(pdf) > 20_000 and 4 <= pages <= 7


def test_environmental_story_template_preserves_key_content():
    from app.services.report_render_service import (
        ReportRenderDocument,
        build_html,
        theme_for_template,
    )

    def section(key, kind, fields=None, items=None, text_value=None):
        return {
            "section_key": key,
            "section_type": kind,
            "title": key,
            "layout_variant": "METRIC_LIST",
            "is_enabled": True,
            "sort_order": 1,
            "content": {"text": text_value, "fields": fields or [], "items": items or []},
        }

    sections = (
        section("waste", "WASTE", items=[{"label": "Botellas PET", "value": 7104}]),
        section("bike", "BIKE_ZONE", fields=[{"label": "Bicicletas", "value": 6}]),
        section(
            "carbon",
            "CARBON",
            fields=[{"label": "Emisión total", "value": 363, "unit": "t CO2-e"}],
            items=[
                {
                    "label": "Transporte público",
                    "value": 209,
                    "unit": "t CO2-e",
                    "description": "Principal agente emisor del evento",
                }
            ],
        ),
        section(
            "eco",
            "CUSTOM",
            fields=[{"label": "Árboles", "value": 2}],
            text_value="Agua y residuos evitados",
        ),
    )
    document = ReportRenderDocument(
        report={
            "id": "story",
            "title": "Gestión Ambiental",
            "scope": "EVENT",
            "template_key": "ENVIRONMENTAL_STORY",
        },
        event={"id": "event", "name": "Evento", "date": "08.08.2026"},
        show=None,
        client={"id": "client", "name": "Cliente"},
        theme=theme_for_template("ENVIRONMENTAL_STORY", None),
        sections=sections,
        evidences=tuple(),
        publication={"number": None},
    )
    html = build_html(document)
    for value in (
        "environmental-story",
        "carbon-story",
        "Botellas PET",
        "7104",
        "Bicicletas",
        "363",
        "Transporte público",
        "209 t CO2-e",
        "Principal agente emisor del evento",
        "Árboles",
        "Agua y residuos evitados",
    ):
        assert value in html


def test_refresh_preserves_manual_items_and_visibility():
    old = {
        "text": "Narrativa",
        "fields": [{"key": "total", "value": 10, "is_visible": False}],
        "items": [
            {
                "label": "PET",
                "value": 10,
                "unit": "kg",
                "description": "Recuperado",
                "_is_visible": False,
            },
            {"label": "Textiles", "value": 4, "unit": "kg", "_manual": True},
        ],
    }
    fresh = {
        "text": None,
        "fields": [{"key": "total", "value": 12}],
        "items": [{"label": "PET", "value": 12, "unit": "kg"}],
    }
    merged = report_autofill_service.merge_preserving_overrides(old, fresh)
    assert merged["fields"][0]["is_visible"] is False
    assert merged["items"][0]["_is_visible"] is False
    assert merged["items"][0]["description"] == "Recuperado"
    assert merged["items"][1]["label"] == "Textiles"


@pytest.mark.parametrize("section_type", ["CUSTOM", "WASTE", "EVIDENCES"])
@pytest.mark.parametrize("variant", list(ReportLayoutVariant))
def test_every_layout_preserves_information_in_regular_and_feature_recipes(section_type, variant):
    from app.services.report_render_service import (
        ReportRenderDocument,
        build_html,
        normalize_theme,
    )

    section = {
        "section_key": f"matrix-{section_type.lower()}-{variant.value.lower()}",
        "section_type": section_type,
        "title": f"Título matriz {section_type} {variant.value}",
        "layout_variant": variant.value,
        "is_enabled": True,
        "sort_order": 1,
        "content": {
            "text": "Narrativa premium conservada",
            "fields": [
                {"key": "sentinel", "label": "Indicador preservado", "value": 7341, "unit": "kg"},
                {
                    "key": "hidden",
                    "label": "Indicador oculto",
                    "value": 9999,
                    "unit": "kg",
                    "is_visible": False,
                },
            ],
            "items": [
                {"label": "Categoría preservada", "value": 219},
                {"label": "Categoría oculta", "value": 999, "_is_visible": False},
            ],
        },
    }
    document = ReportRenderDocument(
        report={
            "id": "matrix",
            "title": "Matriz visual",
            "scope": "EVENT",
            "template_key": "COMPLETE",
        },
        event={"id": "event", "name": "Evento", "date": "08.08.2026"},
        show=None,
        client={"id": "client", "name": "Cliente"},
        theme=normalize_theme({}),
        sections=(section,),
        evidences=tuple(),
        publication={"number": None},
    )
    html = build_html(document)
    for value in (
        section["title"],
        "Narrativa premium conservada",
        "Indicador preservado",
        "7341",
        "kg",
        "Categoría preservada",
        "219",
    ):
        assert value in html
    assert f"layout-{variant.value.lower().replace('_', '-')}" in html
    assert "Indicador oculto" not in html
    assert "Categoría oculta" not in html
