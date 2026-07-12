from datetime import date, datetime, time, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.core import (
    Client,
    ClientPortalConfig,
    ClientPortalSection,
    ClientPortalWidget,
    Event,
    EventForm,
    EventSession,
    FormAnswer,
    FormField,
    FormResponse,
    User,
)
from app.models.enums import EventFormStatus, EventFormType, EventStatus, FormFieldType, UserRole
from app.services import event_form_service


@pytest.fixture()
def db():
    session = SessionLocal()
    created = {"clients": [], "users": [], "events": []}
    try:
        yield session, created
    finally:
        session.rollback()
        if created["events"]:
            session.execute(delete(Event).where(Event.id.in_(created["events"])))
        if created["users"]:
            session.execute(delete(User).where(User.id.in_(created["users"])))
        if created["clients"]:
            session.execute(delete(Client).where(Client.id.in_(created["clients"])))
        session.commit()
        session.close()


@pytest.fixture()
def ctx(db):
    session, created = db
    suffix = uuid4().hex[:10]
    client = Client(business_name=f"Comparison Client {suffix}", contact_email=f"comparison-{suffix}@example.com")
    session.add(client)
    session.flush()
    admin = User(full_name="Admin", email=f"comparison-admin-{suffix}@example.com", password_hash="x", role=UserRole.ADMIN)
    supervisor = User(full_name="Supervisor", email=f"comparison-supervisor-{suffix}@example.com", password_hash="x", role=UserRole.SUPERVISOR)
    client_user = User(full_name="Client", email=f"comparison-client-{suffix}@example.com", password_hash="x", role=UserRole.CLIENT, client_id=client.id)
    session.add_all([admin, supervisor, client_user])
    session.flush()
    event = Event(
        client_id=client.id,
        name=f"Comparison Event {suffix}",
        start_date=datetime.utcnow() + timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=2),
        status=EventStatus.PLANNING,
        created_by=admin.id,
    )
    session.add(event)
    session.flush()
    sessions = [
        EventSession(event_id=event.id, name="Show 1", session_date=date(2026, 7, 10), start_time=time(18, 0)),
        EventSession(event_id=event.id, name="Show 2", session_date=date(2026, 7, 11), start_time=time(18, 0)),
        EventSession(event_id=event.id, name="Show 3", session_date=date(2026, 7, 12), start_time=time(18, 0)),
    ]
    session.add_all(sessions)
    session.flush()

    form_1, fields_1 = _create_experience_form(session, event.id, sessions[0].id, suffix, "show-1")
    form_2, fields_2 = _create_experience_form(session, event.id, sessions[1].id, suffix, "show-2")
    _create_experience_form(session, event.id, sessions[2].id, suffix, "show-3")
    _add_response(session, form_1, fields_1, "Metro", 5, True, "Filas")
    _add_response(session, form_1, fields_1, "Bus", 3, False, "Banos")
    _add_response(session, form_2, fields_2, "Metro", 4, True, "Filas")
    session.commit()

    created["clients"].append(client.id)
    created["users"].extend([admin.id, supervisor.id, client_user.id])
    created["events"].append(event.id)
    return {"event": event, "admin": admin, "supervisor": supervisor, "client_user": client_user, "sessions": sessions}


def test_event_with_three_sessions_returns_comparison(db, ctx):
    session, _ = db
    result = event_form_service.session_comparison(session, ctx["event"].id, ctx["admin"])

    assert result["event_id"] == ctx["event"].id
    assert [item["session_name"] for item in result["sessions"]] == ["Show 1", "Show 2", "Show 3"]
    assert [item["total_responses"] for item in result["sessions"]] == [2, 1, 0]
    assert result["sessions"][0]["average_rating"] == 4.0
    assert result["sessions"][0]["recommendation_rate"] == 50.0
    assert result["sessions"][2]["transport_modes"] == []


def test_session_comparison_filters_by_form_type(db, ctx):
    session, _ = db
    result = event_form_service.session_comparison(session, ctx["event"].id, ctx["admin"], form_type=EventFormType.TRANSPORT_SURVEY)

    assert len(result["sessions"]) == 3
    assert all(item["total_forms"] == 0 for item in result["sessions"])
    assert all(item["total_responses"] == 0 for item in result["sessions"])


def test_client_without_widget_cannot_receive_comparison(db, ctx):
    session, _ = db
    _configure_client_portal(session, ctx["event"].id, ctx["event"].client_id, comparison_enabled=False)

    with pytest.raises(HTTPException) as exc:
        event_form_service.session_comparison(session, ctx["event"].id, ctx["client_user"])

    assert exc.value.status_code == 403


def test_client_with_widget_receives_only_aggregates(db, ctx):
    session, _ = db
    _configure_client_portal(session, ctx["event"].id, ctx["event"].client_id, comparison_enabled=True)

    result = event_form_service.session_comparison(session, ctx["event"].id, ctx["client_user"])

    assert result["sessions"][0]["total_responses"] == 2
    assert "respondent_email" not in str(result)
    assert "raw_data" not in str(result)


def test_unassigned_supervisor_cannot_receive_comparison(db, ctx):
    session, _ = db

    with pytest.raises(HTTPException) as exc:
        event_form_service.session_comparison(session, ctx["event"].id, ctx["supervisor"])

    assert exc.value.status_code == 403


def _create_experience_form(session, event_id, session_id, suffix: str, slug_suffix: str):
    form = EventForm(
        event_id=event_id,
        session_id=session_id,
        title=f"Experience {slug_suffix}",
        form_type=EventFormType.EXPERIENCE_SURVEY,
        public_slug=f"comparison-{suffix}-{slug_suffix}",
        status=EventFormStatus.ACTIVE,
        available_languages=["es"],
        default_language="es",
    )
    session.add(form)
    session.flush()
    fields = {
        "transport": FormField(form_id=form.id, label="Transport", field_key="transport_mode", field_type=FormFieldType.TEXT, analytics_key="transport_mode"),
        "rating": FormField(form_id=form.id, label="Rating", field_key="rating", field_type=FormFieldType.RATING_1_5, analytics_key="general_rating"),
        "recommend": FormField(form_id=form.id, label="Recommend", field_key="recommend", field_type=FormFieldType.YES_NO, analytics_key="would_recommend"),
        "problem": FormField(form_id=form.id, label="Problem", field_key="main_problem", field_type=FormFieldType.TEXT, analytics_key="main_problem"),
    }
    session.add_all(fields.values())
    session.flush()
    return form, fields


def _add_response(session, form: EventForm, fields: dict[str, FormField], transport: str, rating: int, recommend: bool, problem: str) -> None:
    response = FormResponse(
        form_id=form.id,
        event_id=form.event_id,
        session_id=form.session_id,
        language="es",
        raw_data={"transport_mode": transport, "rating": rating, "recommend": recommend, "main_problem": problem},
    )
    session.add(response)
    session.flush()
    session.add_all([
        FormAnswer(response_id=response.id, field_id=fields["transport"].id, value_text=transport),
        FormAnswer(response_id=response.id, field_id=fields["rating"].id, value_number=rating),
        FormAnswer(response_id=response.id, field_id=fields["recommend"].id, value_boolean=recommend),
        FormAnswer(response_id=response.id, field_id=fields["problem"].id, value_text=problem),
    ])


def _configure_client_portal(session, event_id, client_id, comparison_enabled: bool) -> None:
    config = ClientPortalConfig(client_id=client_id, event_id=event_id, scope="EVENT", is_active=True)
    session.add(config)
    session.flush()
    session.add(ClientPortalSection(config_id=config.id, section_key="forms", label="Formularios", is_enabled=True, sort_order=1))
    session.add(
        ClientPortalWidget(
            config_id=config.id,
            widget_key="forms_session_comparison",
            section_key="forms",
            label="Comparativo por show",
            is_enabled=comparison_enabled,
            sort_order=1,
            visibility_config={},
        )
    )
    session.commit()
