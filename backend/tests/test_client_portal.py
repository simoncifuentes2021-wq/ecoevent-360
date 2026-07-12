from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.core import Client, Event, User
from app.models.enums import EventStatus, UserRole
from app.schemas.client_portal_schema import ClientPortalConfigUpdate, ClientPortalSectionUpdate, ClientPortalWidgetUpdate
from app.services import client_portal_service


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
    client = Client(business_name=f"Portal Client {suffix}", contact_email=f"portal-{suffix}@example.com")
    session.add(client)
    session.flush()
    admin = User(full_name="Admin", email=f"portal-admin-{suffix}@example.com", password_hash="x", role=UserRole.ADMIN)
    supervisor = User(full_name="Supervisor", email=f"portal-supervisor-{suffix}@example.com", password_hash="x", role=UserRole.SUPERVISOR)
    client_user = User(full_name="Client", email=f"portal-client-{suffix}@example.com", password_hash="x", role=UserRole.CLIENT, client_id=client.id)
    session.add_all([admin, supervisor, client_user])
    session.flush()
    event = Event(
        client_id=client.id,
        name=f"Portal Event {suffix}",
        start_date=datetime.utcnow() + timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=2),
        status=EventStatus.PLANNING,
        created_by=admin.id,
    )
    session.add(event)
    session.commit()
    created["clients"].append(client.id)
    created["users"].extend([admin.id, supervisor.id, client_user.id])
    created["events"].append(event.id)
    return {"event": event, "admin": admin, "supervisor": supervisor, "client_user": client_user}


def test_admin_configures_client_portal_and_client_sees_only_enabled_sections(db, ctx):
    session, _ = db
    config = client_portal_service.update_config(
        session,
        ctx["event"].id,
        ClientPortalConfigUpdate(
            sections=[
                ClientPortalSectionUpdate(section_key="summary", label="Resumen", is_enabled=True, sort_order=1),
                ClientPortalSectionUpdate(section_key="forms", label="Formularios", is_enabled=False, sort_order=2),
            ],
            widgets=[
                ClientPortalWidgetUpdate(widget_key="event_status", section_key="summary", label="Estado", is_enabled=True, sort_order=1),
                ClientPortalWidgetUpdate(widget_key="forms_total_responses", section_key="forms", label="Respuestas", is_enabled=True, sort_order=2),
            ],
        ),
        ctx["admin"],
    )
    assert config.sections[0].section_key == "summary"

    portal = client_portal_service.client_portal(session, ctx["event"].id, ctx["client_user"])
    assert [section["section_key"] for section in portal["sections"]] == ["summary"]
    assert [widget["widget_key"] for widget in portal["widgets"]] == ["event_status"]
    assert "raw_data" not in str(portal)


def test_supervisor_cannot_configure_client_portal(db, ctx):
    session, _ = db
    with pytest.raises(HTTPException) as exc:
        client_portal_service.get_config(session, ctx["event"].id, ctx["supervisor"])
    assert exc.value.status_code == 403
