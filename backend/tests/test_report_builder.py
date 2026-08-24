from datetime import datetime, timedelta
import asyncio
import json
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
import httpx
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
from app.models.ai import AIGeneration
from app.models.enums import (
    BikeZoneStatus,
    EventFormStatus,
    EventFormType,
    EventStatus,
    IncidentStatus,
    ReportLayoutVariant,
    ReportElementType,
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
    ReportElementBatchItem,
    ReportElementBatchUpdate,
    ReportElementCreate,
    ReportElementUpdate,
    ReportPageCreate,
    SectionOrderUpdate,
    SectionUpdate,
)
from app.services import (
    report_autofill_service,
    report_builder_service,
    report_publication_service,
    report_layout_service,
    report_revision_service,
    report_service,
)
from app.services.ai.ai_service import AIService, AIServiceError
from app.services.ai.ai_service import _parse_editorial_output
from app.services.ai.contexts.reports import build_report_section_context
from app.services.ai.contexts.reports import build_report_editorial_context
from app.services.ai.schemas import ProviderResult, ReportAIEditorialRequest, ReportAIRequest
from app.services.ai import report_editorial_service
from app.services.ai.providers.openrouter import OpenRouterProvider
from app.services.ai.schemas import ProviderRequest


def test_freeform_page_element_batch_persists_exact_geometry(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    page = report_layout_service.create_page(db, report.id, ReportPageCreate(), admin)
    text_element = report_layout_service.create_element(
        db,
        report.id,
        page.id,
        ReportElementCreate(type=ReportElementType.TEXT, x=10, y=20, width=300, height=80),
        admin,
    )
    kpi = report_layout_service.create_element(
        db,
        report.id,
        page.id,
        ReportElementCreate(type=ReportElementType.KPI, x=50, y=150, width=250, height=160),
        admin,
    )
    report_layout_service.batch_update(
        db,
        report.id,
        page.id,
        ReportElementBatchUpdate(
            elements=[
                ReportElementBatchItem(
                    id=text_element.id, x=123.25, y=45.5, width=333.75, height=90.125
                ),
                ReportElementBatchItem(id=kpi.id, x=600.5, y=900.25, width=250.5, height=180.75),
            ]
        ),
        admin,
    )
    db.expire_all()
    loaded = report_layout_service.list_pages(db, report.id, admin)[0]
    geometry = {item.type: (item.x, item.y, item.width, item.height) for item in loaded.elements}
    assert geometry[ReportElementType.TEXT] == (123.25, 45.5, 333.75, 90.125)
    assert geometry[ReportElementType.KPI] == (600.5, 900.25, 250.5, 180.75)


def test_freeform_layout_permissions_bounds_lock_layers_and_delete(report_context):
    db, event, _, _, admin, client, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    page = report_layout_service.create_page(db, report.id, ReportPageCreate(), admin)
    with pytest.raises(HTTPException) as forbidden:
        report_layout_service.create_page(db, report.id, ReportPageCreate(), client)
    assert forbidden.value.status_code == 403
    with pytest.raises(HTTPException) as invalid:
        report_layout_service.create_element(
            db,
            report.id,
            page.id,
            ReportElementCreate(type=ReportElementType.TEXT, x=950, y=0, width=100, height=40),
            admin,
        )
    assert invalid.value.status_code == 422
    element = report_layout_service.create_element(
        db,
        report.id,
        page.id,
        ReportElementCreate(type=ReportElementType.SHAPE, x=20, y=20, width=100, height=100),
        admin,
    )
    updated = report_layout_service.update_element(
        db, report.id, element.id, ReportElementUpdate(locked=True, z_index=7), admin
    )
    assert updated.locked is True and updated.z_index == 7
    report_layout_service.delete_element(db, report.id, element.id, admin)
    assert report_layout_service.list_pages(db, report.id, admin)[0].elements == []


class ReportFakeAIProvider:
    def __init__(self, content: str | None = None):
        self.content = (
            content
            or '{"title_suggestion":"Balance","generated_text":"Se registraron tareas completadas.","key_points":["Tareas registradas"],"warnings":[],"used_data_keys":["effective_content.fields"]}'
        )
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return ProviderResult(content=self.content, effective_model="test-model")


class EditorialFakeAIProvider:
    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        visible = [item for item in request.context["sections"] if item["is_enabled"]]
        output = {
            "report_title_suggestion": "Informe editorial optimizado",
            "cover_style": "EDITORIAL",
            "section_order": [item["section_key"] for item in reversed(visible)],
            "sections": [
                {
                    "section_key": item["section_key"],
                    "title_suggestion": item["title"],
                    "layout_variant": "EDITORIAL",
                    "page_mode": "AUTO",
                    "group_with": None,
                    "generated_text": None,
                    "rationale": "Mejora la lectura",
                }
                for item in visible
            ],
            "overall_rationale": "Orden editorial coherente",
            "warnings": [],
            "used_data_keys": ["sections"],
        }
        return ProviderResult(content=json.dumps(output), effective_model="editorial-test-model")


def report_ai_settings(**changes):
    values = dict(
        ai_enabled=True,
        ai_reports_enabled=True,
        ai_provider="openrouter",
        ai_model="test",
        ai_api_key="key",
        ai_base_url=None,
        ai_timeout_seconds=5,
        ai_max_output_tokens=500,
        ai_temperature=0.1,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def test_openrouter_free_falls_back_when_optional_parameters_return_400(monkeypatch):
    payloads = []

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, headers, json):
            payloads.append(json.copy())
            request = httpx.Request("POST", url)
            if len(payloads) == 1:
                return httpx.Response(400, request=request, json={"error": "unsupported parameter"})
            return httpx.Response(
                200,
                request=request,
                json={
                    "model": "free-model",
                    "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    provider = OpenRouterProvider("key", "https://example.test", 5)
    result = asyncio.run(
        provider.generate(
            ProviderRequest(
                system_prompt="Return JSON",
                context={},
                model="openrouter/free",
                temperature=0.1,
                max_output_tokens=100,
            )
        )
    )
    assert result.effective_model == "free-model"
    assert "response_format" in payloads[0] and "reasoning" in payloads[0]
    assert "response_format" not in payloads[1] and "reasoning" not in payloads[1]


def test_editorial_ai_normalizes_invalid_group_with_token():
    raw = {
        "cover_style": "HERO_IMAGE_TEXT",
        "section_order": ["event_info"],
        "sections": [
            {
                "section_key": "event_info",
                "title_suggestion": None,
                "layout_variant": "EDITORIAL",
                "page_mode": "GROUP_WITH",
                "group_with": "GROUP_WITH",
                "generated_text": None,
                "rationale": "Lectura clara",
            }
        ],
        "overall_rationale": "Plan seguro",
        "warnings": [],
        "used_data_keys": [],
    }
    plan = _parse_editorial_output(json.dumps(raw))
    assert plan.cover_style == "FULL_PHOTO"
    assert plan.sections[0].page_mode == "AUTO" and plan.sections[0].group_with is None


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


def test_report_ai_context_scope_manual_priority_and_no_pii(report_context):
    db, event, show, _, admin, _, outsider = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.SHOW, show.id, admin)
    tasks = next(section for section in report.sections if section.section_key == "tasks")
    tasks.content = {**tasks.content, "text": "Correccion manual aprobada"}
    tasks.source_snapshot = {**tasks.source_snapshot, "email": "private@example.com"}
    db.commit()
    _, context = build_report_section_context(
        db, report.id, tasks.id, admin, ReportAIRequest(operation="IMPROVE")
    )
    assert context["scope"] == {"type": "SHOW", "event_id": str(event.id), "show_id": str(show.id)}
    assert context["effective_content"]["text"] == "Correccion manual aprobada"
    assert "private@example.com" not in str(context)
    summary = next(
        section for section in report.sections if section.section_key == "executive_summary"
    )
    tasks.is_enabled = False
    db.commit()
    _, summary_context = build_report_section_context(
        db, report.id, summary.id, admin, ReportAIRequest()
    )
    assert "tasks" not in {item["key"] for item in summary_context["included_sections"]}
    assert summary_context["source_data"] == {}
    with pytest.raises(HTTPException):
        build_report_section_context(db, report.id, tasks.id, outsider, ReportAIRequest())


def test_report_ai_candidate_cache_regenerate_and_persistence(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    tasks = next(section for section in report.sections if section.section_key == "tasks")
    provider = ReportFakeAIProvider()
    ai = AIService(report_ai_settings(), provider)
    options = ReportAIRequest(style="TECHNICAL", length="SHORT")
    first = asyncio.run(ai.generate_report_section_draft(db, report.id, tasks.id, admin, options))
    cached = asyncio.run(ai.generate_report_section_draft(db, report.id, tasks.id, admin, options))
    regenerated = asyncio.run(
        ai.generate_report_section_draft(
            db,
            report.id,
            tasks.id,
            admin,
            ReportAIRequest(operation="REGENERATE", style="TECHNICAL", length="SHORT"),
        )
    )
    assert first.cached is False and cached.cached is True
    assert cached.generation_id == first.generation_id
    assert regenerated.generation_id != first.generation_id and len(provider.requests) == 2
    stored = db.get(AIGeneration, first.generation_id)
    assert stored.capability == "reports.section_draft" and stored.subject_id == tasks.id
    assert tasks.content.get("text") is None


def test_report_ai_disabled_and_rejects_invented_figures(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    tasks = next(section for section in report.sections if section.section_key == "tasks")
    with pytest.raises(AIServiceError, match="deshabilitada"):
        asyncio.run(
            AIService(report_ai_settings(ai_reports_enabled=False)).generate_report_section_draft(
                db, report.id, tasks.id, admin, ReportAIRequest()
            )
        )
    provider = ReportFakeAIProvider(
        '{"generated_text":"Se completaron 999 tareas.","key_points":[],"warnings":[],"used_data_keys":[]}'
    )
    with pytest.raises(AIServiceError) as exc:
        asyncio.run(
            AIService(report_ai_settings(), provider).generate_report_section_draft(
                db, report.id, tasks.id, admin, ReportAIRequest()
            )
        )
    assert exc.value.code == "unsupported_numeric_claim"


def test_report_ai_normalizes_provider_lists_to_contract(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    tasks = next(section for section in report.sections if section.section_key == "tasks")
    points = ",".join(f'"Punto {letter}"' for letter in "ABCDEFGHIJ")
    provider = ReportFakeAIProvider(
        '{"generated_text":"Texto seguro","key_points":['
        + points
        + '],"warnings":[],"used_data_keys":[]}'
    )
    result = asyncio.run(
        AIService(report_ai_settings(), provider).generate_report_section_draft(
            db, report.id, tasks.id, admin, ReportAIRequest()
        )
    )
    assert len(result.key_points) == 8


def test_report_ai_allows_numeric_indexes_only_in_traceability_keys(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    tasks = next(section for section in report.sections if section.section_key == "tasks")
    provider = ReportFakeAIProvider(
        '{"generated_text":"Texto seguro","key_points":[],"warnings":[],"used_data_keys":["effective_content.items.99"]}'
    )
    result = asyncio.run(
        AIService(report_ai_settings(), provider).generate_report_section_draft(
            db, report.id, tasks.id, admin, ReportAIRequest()
        )
    )
    assert result.used_data_keys == ["effective_content.items.99"]


def test_editorial_ai_plan_applies_with_automatic_rollback_revision(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    original_title = report.title
    original_order = [section.section_key for section in report.sections]
    provider = EditorialFakeAIProvider()
    proposal = asyncio.run(
        AIService(report_ai_settings(), provider).generate_report_editorial_plan(
            db, report.id, admin, ReportAIEditorialRequest()
        )
    )
    revision, updated = report_editorial_service.apply_plan(
        db, report, proposal.generation_id, report.edit_version, admin
    )
    assert updated.title == "Informe editorial optimizado"
    assert updated.editorial_config["cover_style"] == "EDITORIAL"
    assert [section.section_key for section in updated.sections if section.is_enabled] == list(
        reversed(
            [
                key
                for key in original_order
                if next(item for item in report.sections if item.section_key == key).is_enabled
            ]
        )
    )
    assert revision.note == "Antes de aplicar optimizacion editorial con IA"
    report_revision_service.restore(db, updated, revision.id, updated.edit_version)
    restored = report_builder_service.get_editor(db, report.id, admin)
    assert restored.title == original_title
    assert [section.section_key for section in restored.sections] == original_order


def test_editorial_ai_context_is_scoped_and_sanitized(report_context):
    db, event, show, _, admin, _, outsider = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.SHOW, show.id, admin)
    report.sections[0].content = {
        **report.sections[0].content,
        "contact_email": "private@test.local",
    }
    db.commit()
    _, context = build_report_editorial_context(db, report.id, admin, "EXECUTIVE", True)
    assert context["scope"]["show_id"] == str(show.id)
    assert "private@test.local" not in str(context)
    with pytest.raises(HTTPException):
        build_report_editorial_context(db, report.id, outsider, "EXECUTIVE", True)


def test_editorial_ai_uses_safe_fallback_for_invalid_provider_output(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    provider = ReportFakeAIProvider("respuesta sin JSON")
    proposal = asyncio.run(
        AIService(report_ai_settings(), provider).generate_report_editorial_plan(
            db, report.id, admin, ReportAIEditorialRequest(force_refresh=True)
        )
    )
    assert proposal.section_order
    assert all(section.generated_text is None for section in proposal.sections)
    assert any("planificador seguro" in warning for warning in proposal.warnings)


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


def test_environmental_visibility_preferences_persist_after_section_reload(report_context):
    db, event, _, _, admin, _, _ = report_context
    report = report_builder_service.create_draft(db, event.id, ReportScope.EVENT, None, admin)
    section = next(item for item in report.sections if item.section_key == "environmental_impact")
    content = ReportSectionContent.model_validate(section.content)
    content.show_traceability = False
    content.items = [{"label": "Gasolina", "value": "8.94", "unit": "L", "_is_visible": False}]

    report_builder_service.update_section(
        db,
        report,
        section.id,
        SectionUpdate(content=content, edit_version=report.edit_version),
    )
    reloaded = report_builder_service.get_editor(db, report.id, admin)
    stored = next(item for item in reloaded.sections if item.id == section.id).content

    assert stored["show_traceability"] is False
    assert stored["items"][0]["_is_visible"] is False


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
    assert "preset_eco_equivalences" not in enabled
    assert enabled.index("waste") < enabled.index("bike_zone") < enabled.index("carbon")
    equivalences = next(
        section
        for section in configured.sections
        if section.section_key == "preset_eco_equivalences"
    )
    assert equivalences.content["fields"] == []
    assert equivalences.source_metadata["availability"] == "NO_DATA"
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


def test_environmental_impact_renderer_uses_human_readable_precision_and_details():
    from app.services.report_render_service import _environmental_impact_html

    html = _environmental_impact_html(
        [
            {
                "content": {
                    "fields": [
                        {
                            "key": "energy_kwh",
                            "label": "Energía utilizada",
                            "value": "30.00000000",
                            "unit": "kWh",
                        },
                        {
                            "key": "co2e_baseline_kg",
                            "label": "CO2e línea base",
                            "value": "27.10000000",
                            "unit": "kg",
                        },
                        {
                            "key": "pm25_avoided_kg",
                            "label": "PM2.5 evitado",
                            "value": "0.04023000",
                            "unit": "kg",
                        },
                    ]
                },
                "source_snapshot": {
                    "official_data": {
                        "actions": [
                            {
                                "name": "Torre eléctrica",
                                "session_name": "Show 1",
                                "methodology": "Energía medida",
                                "metrics": {"CO2E_AVOIDED_KG": "21.037"},
                            }
                        ],
                        "breakdown": [
                            {
                                "session_name": "Show 1",
                                "metrics": {"co2e_avoided_kg": "21.037"},
                            }
                        ],
                        "methodologies": [{"name": "Torre diésel vs torre eléctrica"}],
                        "sources": [
                            {"source": "US EPA AP-42", "year": 1998},
                            {"source": "US EPA AP-42", "year": 1998},
                        ],
                        "equivalences": [
                            {"label": "Gasolina no consumida", "value": "8.944", "unit": "L"}
                        ],
                        "disclaimer": "Referencia comunicacional.",
                    }
                },
            }
        ]
    )

    assert "30.00000000" not in html
    assert "30<small>kWh</small>" in html
    assert "27,10<small>kg</small>" in html
    assert "0,04023<small>kg</small>" in html
    assert "Resultados por alcance" in html and "Show 1: 21,04 kg CO2e" in html
    assert "Metodologías y equivalencias" in html
    assert html.count("US EPA AP-42") == 1


def test_environmental_impact_renderer_respects_item_and_traceability_visibility():
    from app.services.report_render_service import _environmental_impact_html

    html = _environmental_impact_html(
        [
            {
                "content": {
                    "show_traceability": False,
                    "fields": [],
                    "items": [
                        {"label": "Gasolina", "_is_visible": False},
                        {"label": "Bosque", "_is_visible": True},
                    ],
                },
                "source_snapshot": {
                    "official_data": {
                        "actions": [],
                        "breakdown": [
                            {
                                "session_name": "Show 1",
                                "metrics": {"CO2E_AVOIDED_KG": "21.037"},
                            }
                        ],
                        "methodologies": [],
                        "sources": [],
                        "equivalences": [
                            {"name": "Gasolina", "value": "8.94", "unit": "L/kgCO2e"},
                            {"name": "Bosque", "value": "0.02104", "unit": "acre-año/kgCO2e"},
                        ],
                    }
                },
            }
        ]
    )

    assert "Trazabilidad aprobada" not in html
    assert "no-trace" in html
    assert "Gasolina" not in html
    assert "Bosque: 0,02 acre-año" in html
    assert "Show 1: 21,04 kg CO2e" not in html


def test_full_html_pipeline_keeps_environmental_hidden_item_configuration():
    from app.services.report_render_service import ReportRenderDocument, build_html, normalize_theme

    section = {
        "section_key": "environmental_impact",
        "section_type": "ENVIRONMENTAL_IMPACT",
        "title": "Impacto ambiental evitado",
        "layout_variant": "KPI_GRID",
        "is_enabled": True,
        "sort_order": 1,
        "content": {
            "show_traceability": False,
            "fields": [],
            "items": [
                {"label": "Torre", "_is_visible": False},
                {"label": "Gasolina", "_is_visible": False},
            ],
        },
        "source_snapshot": {
            "official_data": {
                "actions": [
                    {
                        "name": "Torre",
                        "session_name": "Evento completo",
                        "methodology": "Método oculto",
                        "metrics": {"CO2E_AVOIDED_KG": "21.04"},
                    }
                ],
                "breakdown": [],
                "methodologies": [{"name": "Método oculto"}],
                "sources": [],
                "equivalences": [{"name": "Gasolina", "value": "8.94", "unit": "L"}],
            }
        },
    }
    document = ReportRenderDocument(
        report={"id": "r", "title": "Reporte", "scope": "EVENT", "template_key": "COMPLETE"},
        event={"id": "e", "name": "Evento", "date": "19.08.2026"},
        show=None,
        client={"id": "c", "name": "Cliente"},
        theme=normalize_theme({}),
        sections=(section,),
        evidences=tuple(),
        publication={"number": None},
    )

    html = build_html(document)

    assert "Trazabilidad aprobada" not in html
    assert "Resultados por alcance" not in html
    assert "Método oculto" not in html
    assert "Gasolina: 8,94 L" not in html


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


def test_freeform_renderer_preserves_exact_logical_geometry_and_escapes_content():
    from app.services.report_render_service import ReportRenderDocument, build_html, normalize_theme

    document = ReportRenderDocument(
        report={
            "id": "report",
            "title": "Libre",
            "scope": "EVENT",
            "template_key": "EXECUTIVE",
            "composition_mode": "FREEFORM",
        },
        event={"id": "event", "name": "Evento", "date": "24.08.2026"},
        show=None,
        client={"id": "client", "name": "Cliente"},
        theme=normalize_theme({}),
        sections=tuple(),
        evidences=tuple(),
        publication={"number": None},
        freeform_pages=(
            {
                "page_number": 1,
                "width": 1000,
                "height": 1414,
                "background": "#FFFFFF",
                "is_enabled": True,
                "elements": [
                    {
                        "id": "text-1",
                        "type": "TEXT",
                        "x": 125,
                        "y": 141.4,
                        "width": 500,
                        "height": 282.8,
                        "rotation": 0,
                        "z_index": 3,
                        "visible": True,
                        "content": {"text": "<script>unsafe</script>"},
                        "style": {"fontSize": 20},
                    }
                ],
            },
        ),
    )
    html = build_html(document)
    assert "left:12.50000000%" in html and "top:10.00000000%" in html
    assert "width:50.00000000%" in html and "height:20.00000000%" in html
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in html
    assert "<script>unsafe</script>" not in html


def test_report_binding_registry_is_allowlisted_and_returns_no_data():
    from app.services.report_data_binding_registry import canonical_key, resolve

    report = SimpleNamespace(
        event=SimpleNamespace(
            name="Evento",
            client=SimpleNamespace(business_name="Cliente"),
            start_date=datetime(2026, 8, 1),
            end_date=datetime(2026, 8, 2),
        ),
        session=None,
        sections=[],
    )
    assert resolve(report, {"key": "event.name"})["value"] == "Evento"
    missing = resolve(report, {"source": "waste", "metric": "total_kg"})
    assert missing["availability"] == "NO_DATA" and missing["value"] is None
    with pytest.raises(ValueError):
        canonical_key({"key": "sql.select_all"})


def test_freeform_chart_dataset_is_normalized_in_backend():
    from app.services.report_visual_data_service import chart_dataset

    report = SimpleNamespace(
        sections=[
            SimpleNamespace(
                section_key="waste",
                title="Residuos",
                content={
                    "items": [
                        {"label": "Reciclaje", "weight_kg": 42},
                        {"label": "Compost", "weight_kg": 18},
                    ]
                },
            )
        ]
    )
    dataset = chart_dataset(report, "waste", "DONUT")
    assert dataset == {
        "chart_type": "DONUT",
        "labels": ["Reciclaje", "Compost"],
        "series": [{"name": "Residuos", "data": [42, 18]}],
        "points": [{"label": "Reciclaje", "value": 42}, {"label": "Compost", "value": 18}],
        "availability": "AVAILABLE",
        "source": "waste",
    }
    assert (
        chart_dataset(SimpleNamespace(sections=[]), "carbon", "LINE")["availability"] == "NO_DATA"
    )


def test_freeform_template_keeps_bindings_but_drops_private_evidence_values():
    from app.services.report_template_layout_service import _snapshot_pages

    common = dict(rotation=0, locked=False, visible=True, style={}, metadata_={})
    image = SimpleNamespace(
        type=SimpleNamespace(value="IMAGE"),
        x=1,
        y=2,
        width=3,
        height=4,
        z_index=1,
        content={"evidence_id": "private-id", "uri": "private-url", "caption": "Foto"},
        data_binding=None,
        **common,
    )
    kpi = SimpleNamespace(
        type=SimpleNamespace(value="KPI"),
        x=5,
        y=6,
        width=7,
        height=8,
        z_index=2,
        content={"text": "4850"},
        data_binding={"key": "waste.total_kg"},
        **common,
    )
    report = SimpleNamespace(
        pages=[
            SimpleNamespace(
                page_number=1,
                name="A4",
                width=1000,
                height=1414,
                background="#FFFFFF",
                background_image=None,
                is_enabled=True,
                elements=[image, kpi],
            )
        ]
    )
    pages = _snapshot_pages(report)
    assert pages[0]["elements"][0]["content"] == {"caption": "Foto"}
    assert pages[0]["elements"][1]["data_binding"] == {"key": "waste.total_kg"}


def test_ai_page_layout_validator_rejects_bounds_bindings_fonts_and_overlaps():
    from app.services.ai.report_layout_service import LayoutValidator

    valid = {
        "elements": [
            {
                "type": "KPI",
                "x": 50,
                "y": 100,
                "width": 300,
                "height": 180,
                "data_binding": {"key": "waste.total_kg"},
                "style": {"fontFamily": "Inter"},
            }
        ]
    }
    assert LayoutValidator.validate(valid).elements[0].type == "KPI"
    for invalid in [
        {"elements": [{"type": "TEXT", "x": 950, "y": 0, "width": 100, "height": 40}]},
        {
            "elements": [
                {
                    "type": "KPI",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 40,
                    "data_binding": {"key": "secret.sql"},
                }
            ]
        },
        {
            "elements": [
                {
                    "type": "TEXT",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 40,
                    "style": {"fontFamily": "RemoteFont"},
                }
            ]
        },
    ]:
        with pytest.raises(ValueError):
            LayoutValidator.validate(invalid)


def test_full_report_ai_validator_enforces_grounding_and_privacy():
    from app.services.ai.report_orchestration_service import ReportAIValidator

    raw = {
        "title": "Ambiental",
        "pages": [{"elements": [{"type": "TEXT", "x": 10, "y": 10, "width": 400, "height": 100}]}],
        "claims": [{"text": "Se recuperaron 42 kg", "sources": ["waste.total_kg"]}],
    }
    assert ReportAIValidator.validate(raw, {"waste.total_kg": 42}).title == "Ambiental"
    raw["claims"][0]["text"] = "Se recuperaron 99 kg"
    with pytest.raises(ValueError):
        ReportAIValidator.validate(raw, {"waste.total_kg": 42})
