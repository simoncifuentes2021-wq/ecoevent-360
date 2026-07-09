from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.core.config import settings
from app.models.core import Client, Event, EventForm, EventSession, EventStaff, FormField, FormFieldOption, User
from app.models.enums import EventFormStatus, EventFormType, EventStatus, FormFieldType, UserRole
from app.schemas.event_form_schema import EventFormCreate, FormQRCodeCreate, FormResponseCreate
from app.services import event_form_service, form_qr_service


@pytest.fixture()
def local_qr_storage():
    original = {
        "cloudflare_r2_bucket": settings.cloudflare_r2_bucket,
        "cloudflare_r2_account_id": settings.cloudflare_r2_account_id,
        "cloudflare_r2_access_key_id": settings.cloudflare_r2_access_key_id,
        "cloudflare_r2_secret_access_key": settings.cloudflare_r2_secret_access_key,
        "cloudflare_r2_public_base_url": settings.cloudflare_r2_public_base_url,
    }
    settings.cloudflare_r2_bucket = None
    settings.cloudflare_r2_account_id = None
    settings.cloudflare_r2_access_key_id = None
    settings.cloudflare_r2_secret_access_key = None
    settings.cloudflare_r2_public_base_url = None
    try:
        yield
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


@pytest.fixture()
def db(local_qr_storage):
    session = SessionLocal()
    created = {"clients": [], "users": [], "events": []}
    session.info["created"] = created
    try:
        yield session
    finally:
        session.rollback()
        session.expunge_all()
        if created["events"]:
            session.execute(delete(Event).where(Event.id.in_(created["events"])))
        if created["users"]:
            session.execute(delete(User).where(User.id.in_(created["users"])))
        if created["clients"]:
            session.execute(delete(Client).where(Client.id.in_(created["clients"])))
        session.commit()
        for path in (Path("uploads") / "qrcodes").glob("functional-form-*.png"):
            path.unlink(missing_ok=True)
        session.close()


@pytest.fixture()
def ctx(db):
    suffix = uuid4().hex[:10]
    client = Client(business_name=f"Test Client {suffix}", contact_email=f"client-{suffix}@example.com")
    db.add(client)
    db.flush()
    admin = User(
        full_name="Admin Test",
        email=f"admin-{suffix}@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    client_user = User(
        full_name="Client Test",
        email=f"client-user-{suffix}@example.com",
        password_hash="x",
        role=UserRole.CLIENT,
        client_id=client.id,
    )
    supervisor = User(
        full_name="Supervisor Test",
        email=f"supervisor-{suffix}@example.com",
        password_hash="x",
        role=UserRole.SUPERVISOR,
    )
    other_supervisor = User(
        full_name="Other Supervisor Test",
        email=f"other-supervisor-{suffix}@example.com",
        password_hash="x",
        role=UserRole.SUPERVISOR,
    )
    db.add_all([admin, client_user, supervisor, other_supervisor])
    db.flush()
    now = datetime.utcnow()
    event = Event(
        client_id=client.id,
        name=f"Public Forms Event {suffix}",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        status=EventStatus.PLANNING,
        created_by=admin.id,
    )
    other_event = Event(
        client_id=client.id,
        name=f"Other Event {suffix}",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        status=EventStatus.PLANNING,
        created_by=admin.id,
    )
    db.add_all([event, other_event])
    db.flush()
    db.add(EventStaff(event_id=event.id, user_id=supervisor.id, role_in_event="Supervisor"))
    db.flush()
    db.commit()
    db.info["created"]["clients"].append(client.id)
    db.info["created"]["users"].extend([admin.id, client_user.id, supervisor.id, other_supervisor.id])
    db.info["created"]["events"].extend([event.id, other_event.id])
    return {
        "suffix": suffix,
        "client": client,
        "admin": admin,
        "client_user": client_user,
        "supervisor": supervisor,
        "other_supervisor": other_supervisor,
        "event": event,
        "other_event": other_event,
    }


def make_form(db, event, suffix: str, *, status=EventFormStatus.ACTIVE) -> EventForm:
    form = EventForm(
        event_id=event.id,
        title=f"Functional Form {suffix}",
        form_type=EventFormType.CUSTOM,
        public_slug=f"functional-form-{suffix}-{uuid4().hex[:6]}",
        status=status,
        default_language="es",
        available_languages=["es", "en"],
    )
    db.add(form)
    db.flush()
    email = FormField(form_id=form.id, label="Email", field_key="email", field_type=FormFieldType.EMAIL, is_required=True, sort_order=0)
    transport = FormField(form_id=form.id, label="Transport", field_key="transport", field_type=FormFieldType.SELECT, is_required=True, sort_order=1)
    rating = FormField(form_id=form.id, label="Rating", field_key="rating", field_type=FormFieldType.RATING_1_5, is_required=False, sort_order=2)
    db.add_all([email, transport, rating])
    db.flush()
    db.add_all(
        [
            FormFieldOption(field_id=transport.id, label="Bus", value="bus", sort_order=0),
            FormFieldOption(field_id=transport.id, label="Metro", value="metro", sort_order=1),
        ]
    )
    db.commit()
    return event_form_service.get_form_or_404(db, form.id)


def field_errors(exc: HTTPException) -> dict[str, str]:
    assert isinstance(exc.detail, list)
    return {item["field_key"]: item["message"] for item in exc.detail}


def test_public_active_form_opens(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    payload = event_form_service.public_form_payload(event_form_service.get_public_form_or_404(db, form.public_slug), "es")
    assert payload["title"] == form.title
    assert len(payload["fields"]) == 3


def test_public_draft_and_closed_forms_do_not_open(db, ctx):
    draft = make_form(db, ctx["event"], f"{ctx['suffix']}-draft", status=EventFormStatus.DRAFT)
    closed = make_form(db, ctx["event"], f"{ctx['suffix']}-closed", status=EventFormStatus.CLOSED)
    for form in (draft, closed):
        with pytest.raises(HTTPException) as exc:
            event_form_service.public_form_payload(event_form_service.get_public_form_or_404(db, form.public_slug), "es")
        assert exc.value.status_code == 400


def test_submit_required_empty_fails(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    with pytest.raises(HTTPException) as exc:
        event_form_service.submit_public_form(db, form.public_slug, FormResponseCreate(language="es", answers={}))
    assert field_errors(exc.value)["email"] == "Este campo es obligatorio"


def test_submit_invalid_email_fails(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    with pytest.raises(HTTPException) as exc:
        event_form_service.submit_public_form(
            db,
            form.public_slug,
            FormResponseCreate(language="es", answers={"email": "bad-email", "transport": "bus"}),
        )
    assert field_errors(exc.value)["email"] == "Correo inválido"


def test_submit_invalid_select_option_fails(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    with pytest.raises(HTTPException) as exc:
        event_form_service.submit_public_form(
            db,
            form.public_slug,
            FormResponseCreate(language="es", answers={"email": "ok@example.com", "transport": "plane"}),
        )
    assert field_errors(exc.value)["transport"] == "Debe seleccionar una opción válida"


def test_submit_rating_out_of_range_fails(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    with pytest.raises(HTTPException) as exc:
        event_form_service.submit_public_form(
            db,
            form.public_slug,
            FormResponseCreate(language="es", answers={"email": "ok@example.com", "transport": "bus", "rating": 9}),
        )
    assert field_errors(exc.value)["rating"] == "La calificación debe estar entre 1 y 5"


def test_client_cannot_list_full_responses_but_can_see_anonymous_summary(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    event_form_service.submit_public_form(
        db,
        form.public_slug,
        FormResponseCreate(language="es", answers={"email": "ok@example.com", "transport": "bus", "rating": 5}),
    )
    with pytest.raises(HTTPException) as exc:
        event_form_service.list_responses(db, form.id, ctx["client_user"])
    assert exc.value.status_code == 403
    summary = event_form_service.summary(db, form.id, ctx["client_user"])
    assert summary["total_responses"] == 1
    assert summary["comments_sample"] == []


def test_unassigned_supervisor_cannot_manage_form(db, ctx):
    with pytest.raises(HTTPException) as exc:
        event_form_service.create_form(
            db,
            ctx["event"].id,
            EventFormCreate(title="Denied", form_type=EventFormType.CUSTOM, generate_template=False),
            ctx["other_supervisor"],
        )
    assert exc.value.status_code == 403


def test_session_id_from_other_event_is_rejected(db, ctx):
    session = EventSession(event_id=ctx["other_event"].id, name="Other Session")
    db.add(session)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        event_form_service.create_form(
            db,
            ctx["event"].id,
            EventFormCreate(title="Wrong Session", session_id=session.id, form_type=EventFormType.CUSTOM, generate_template=False),
            ctx["admin"],
        )
    assert exc.value.status_code == 400


def test_admin_generates_form_qr(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    qr = form_qr_service.create_form_qr(
        db,
        form.id,
        FormQRCodeCreate(label="QR General", qr_type="FORM"),
        ctx["admin"],
    )
    assert qr.target_url.endswith(f"/f/{form.public_slug}")
    assert qr.file_path


def test_admin_generates_language_qr(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    qr = form_qr_service.create_form_qr(
        db,
        form.id,
        FormQRCodeCreate(label="QR English", qr_type="FORM_LANGUAGE", language="en"),
        ctx["admin"],
    )
    assert qr.target_url.endswith(f"/f/{form.public_slug}?lang=en")
    assert qr.language == "en"


def test_assigned_supervisor_generates_qr(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    qr = form_qr_service.create_form_qr(
        db,
        form.id,
        FormQRCodeCreate(label="QR Supervisor", qr_type="FORM"),
        ctx["supervisor"],
    )
    assert qr.id


def test_unassigned_supervisor_cannot_generate_qr(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    with pytest.raises(HTTPException) as exc:
        form_qr_service.create_form_qr(
            db,
            form.id,
            FormQRCodeCreate(label="QR Denied", qr_type="FORM"),
            ctx["other_supervisor"],
        )
    assert exc.value.status_code == 403


def test_client_can_list_and_download_but_not_create_qr(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    qr = form_qr_service.create_form_qr(
        db,
        form.id,
        FormQRCodeCreate(label="QR Client", qr_type="FORM"),
        ctx["admin"],
    )
    assert form_qr_service.list_form_qr_codes(db, form.id, ctx["client_user"])
    path = form_qr_service.get_download_path(db, qr.id, ctx["client_user"])
    assert path.read_bytes().startswith(b"\x89PNG")
    content, content_type, filename = form_qr_service.get_download_content(db, qr.id, ctx["client_user"])
    assert content.startswith(b"\x89PNG")
    assert content_type == "image/png"
    assert filename.endswith(".png")
    with pytest.raises(HTTPException) as exc:
        form_qr_service.create_form_qr(
            db,
            form.id,
            FormQRCodeCreate(label="QR Client Denied", qr_type="FORM"),
            ctx["client_user"],
        )
    assert exc.value.status_code == 403


def test_qr_invalid_language_fails(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    with pytest.raises(HTTPException) as exc:
        form_qr_service.create_form_qr(
            db,
            form.id,
            FormQRCodeCreate(label="QR Invalid", qr_type="FORM_LANGUAGE", language="fr"),
            ctx["admin"],
        )
    assert exc.value.status_code == 400


def test_qr_duplicate_without_force_does_not_duplicate(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    first = form_qr_service.create_form_qr(db, form.id, FormQRCodeCreate(label="QR One", qr_type="FORM"), ctx["admin"])
    second = form_qr_service.create_form_qr(db, form.id, FormQRCodeCreate(label="QR Two", qr_type="FORM"), ctx["admin"])
    assert second.id == first.id
    assert len(form_qr_service.list_form_qr_codes(db, form.id, ctx["admin"])) == 1


def test_qr_force_updates_existing(db, ctx):
    form = make_form(db, ctx["event"], ctx["suffix"])
    first = form_qr_service.create_form_qr(db, form.id, FormQRCodeCreate(label="QR One", qr_type="FORM"), ctx["admin"])
    second = form_qr_service.create_form_qr(db, form.id, FormQRCodeCreate(label="QR Forced", qr_type="FORM", force=True), ctx["admin"])
    assert second.id == first.id
    assert second.label == "QR Forced"


def test_qr_list_refreshes_stale_public_url(db, ctx, monkeypatch):
    form = make_form(db, ctx["event"], ctx["suffix"])
    qr = form_qr_service.create_form_qr(db, form.id, FormQRCodeCreate(label="QR One", qr_type="FORM"), ctx["admin"])
    qr.target_url = f"http://localhost:3000/f/{form.public_slug}"
    db.commit()

    monkeypatch.setattr(form_qr_service.settings, "public_app_url", "https://ecoevent-360.vercel.app")

    refreshed = form_qr_service.list_form_qr_codes(db, form.id, ctx["admin"])[0]
    assert refreshed.target_url == f"https://ecoevent-360.vercel.app/f/{form.public_slug}"
    assert refreshed.file_path


def test_qr_uses_request_public_base_url_when_env_is_missing(db, ctx, monkeypatch):
    form = make_form(db, ctx["event"], ctx["suffix"])
    monkeypatch.setattr(form_qr_service.settings, "public_app_url", None)

    qr = form_qr_service.create_form_qr(
        db,
        form.id,
        FormQRCodeCreate(label="QR One", qr_type="FORM"),
        ctx["admin"],
        public_base_url="https://ecoevent-360.vercel.app",
    )

    assert qr.target_url == f"https://ecoevent-360.vercel.app/f/{form.public_slug}"
