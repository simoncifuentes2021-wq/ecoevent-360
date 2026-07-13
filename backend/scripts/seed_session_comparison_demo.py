from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import settings
from app.models.core import (
    BikeZoneRecord,
    Client,
    ClientPortalConfig,
    ClientPortalSection,
    ClientPortalWidget,
    Event,
    EventForm,
    EventSession,
    FormAnswer,
    FormField,
    FormFieldOption,
    FormResponse,
    User,
)
from app.models.enums import BikeZoneStatus, EventFormStatus, EventFormType, EventStatus, FormFieldType, UserRole
from app.services.event_form_service import CHILE_REGION_OPTIONS, COUNTRY_OPTIONS

DEMO_PREFIX = "[DEMO COMPARATIVO]"
LANGUAGES = ["es", "en", "pt", "ko"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea o elimina datos demo para probar el comparativo por show.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Crear evento, shows, formularios y respuestas demo.")
    seed_parser.add_argument("--client-id", help="Cliente existente para asociar el evento.")
    seed_parser.add_argument("--admin-email", help="Email de admin existente para created_by.")
    seed_parser.add_argument("--yes", action="store_true", help="Confirma la creacion de datos demo.")
    seed_parser.add_argument("--allow-production", action="store_true", help="Permite ejecutar contra APP_ENV=production.")

    cleanup_parser = subparsers.add_parser("cleanup", help="Eliminar eventos demo creados por este script.")
    cleanup_parser.add_argument("--yes", action="store_true", help="Confirma el borrado de datos demo.")
    cleanup_parser.add_argument("--allow-production", action="store_true", help="Permite ejecutar contra APP_ENV=production.")

    args = parser.parse_args()
    if settings.app_env.lower() == "production" and not args.allow_production:
        print("Entorno production detectado. No se ejecuta sin --allow-production.")
        return 3
    with SessionLocal() as db:
        if args.command == "seed":
            if not args.yes:
                print("No se creo nada. Ejecuta con --yes para confirmar.")
                return 2
            return seed(db, client_id=args.client_id, admin_email=args.admin_email)
        if args.command == "cleanup":
            if not args.yes:
                print("No se borro nada. Ejecuta con --yes para confirmar.")
                return 2
            return cleanup(db)
    return 0


def seed(db: Session, *, client_id: str | None, admin_email: str | None) -> int:
    suffix = uuid4().hex[:8]
    admin = _find_admin(db, admin_email)
    client = _find_or_create_client(db, client_id, suffix)
    event = Event(
        client_id=client.id,
        name=f"{DEMO_PREFIX} Festival pruebas {suffix}",
        event_type="Demo",
        description="Datos temporales para probar el dashboard comparativo por show/sesion.",
        location_name="Recinto Demo",
        city="Santiago",
        region="Metropolitana",
        country="Chile",
        start_date=datetime.combine(date.today() + timedelta(days=7), time(18, 0)),
        end_date=datetime.combine(date.today() + timedelta(days=9), time(23, 0)),
        estimated_attendees=1200,
        status=EventStatus.PLANNING,
        created_by=admin.id if admin else None,
    )
    db.add(event)
    db.flush()

    sessions = _create_sessions(db, event)
    forms = []
    for index, session in enumerate(sessions):
        forms.append(_create_transport_form(db, event, session, suffix, index))
        forms.append(_create_experience_form(db, event, session, suffix, index))
    bike_form = _create_bike_form(db, event, sessions[0], suffix)
    forms.append(bike_form)
    _create_client_portal_config(db, event, admin)

    transport_payloads = [
        [("Metro", "Chile"), ("Metro", "Chile"), ("Auto", "Argentina")],
        [("Bus", "Chile"), ("Auto", "Brasil")],
        [("Bicicleta", "Chile")],
    ]
    experience_payloads = [
        [(6, True, "Filas"), (7, True, "Sin problemas"), (6, False, "Banos")],
        [(5, True, "Filas"), (6, False, "Senaletica")],
        [(7, True, "Sin problemas")],
    ]
    for index, session in enumerate(sessions):
        transport_form = forms[index * 2]
        experience_form = forms[index * 2 + 1]
        for mode, country in transport_payloads[index]:
            _add_transport_response(db, transport_form, mode, country)
        for rating, recommend, problem in experience_payloads[index]:
            _add_experience_response(db, experience_form, rating, recommend, problem)
    bike_response = _add_bike_response(db, bike_form)
    db.add(
        BikeZoneRecord(
            response_id=bike_response.id,
            event_id=event.id,
            session_id=sessions[0].id,
            code=f"DEMO-BIKE-{suffix.upper()}",
            status=BikeZoneStatus.CHECKED_IN,
            check_in_at=datetime.utcnow(),
            checked_in_by=admin.id if admin else None,
        )
    )
    db.commit()

    print("Datos demo creados.")
    print(f"event_id: {event.id}")
    print(f"event_name: {event.name}")
    print("shows:")
    for session in sessions:
        print(f"- {session.name}: {session.id}")
    print("formularios publicos:")
    for form in forms:
        print(f"- {form.title}: /f/{form.public_slug} ({form.form_type.value}, session_id={form.session_id})")
    print("")
    print("Para borrar estos datos:")
    print("python scripts/seed_session_comparison_demo.py cleanup --yes")
    return 0


def cleanup(db: Session) -> int:
    events = list(db.scalars(select(Event).where(Event.name.startswith(DEMO_PREFIX))).all())
    if not events:
        print("No hay eventos demo para borrar.")
        return 0
    event_ids = [event.id for event in events]
    client_ids = {event.client_id for event in events}
    db.execute(delete(ClientPortalConfig).where(ClientPortalConfig.event_id.in_(event_ids)))
    db.flush()
    db.execute(delete(Event).where(Event.id.in_(event_ids)))
    db.flush()
    for client_id in client_ids:
        remaining = db.scalar(select(Event.id).where(Event.client_id == client_id).limit(1))
        client = db.get(Client, client_id)
        if client and client.business_name.startswith(DEMO_PREFIX) and remaining is None:
            db.delete(client)
    db.commit()
    print(f"Eventos demo borrados: {len(event_ids)}")
    for event_id in event_ids:
        print(f"- {event_id}")
    return 0


def _find_admin(db: Session, admin_email: str | None) -> User | None:
    if admin_email:
        return db.scalar(select(User).where(User.email == admin_email, User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])))
    return db.scalar(select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])).order_by(User.created_at.asc()))


def _find_or_create_client(db: Session, client_id: str | None, suffix: str) -> Client:
    if client_id:
        client = db.get(Client, UUID(client_id))
        if not client:
            raise SystemExit(f"No existe client_id={client_id}")
        return client
    client = Client(
        business_name=f"{DEMO_PREFIX} Cliente {suffix}",
        contact_email=f"demo-comparativo-{suffix}@example.com",
        contact_phone="+56 9 0000 0000",
    )
    db.add(client)
    db.flush()
    return client


def _create_sessions(db: Session, event: Event) -> list[EventSession]:
    base_day = date.today() + timedelta(days=7)
    sessions = [
        EventSession(event_id=event.id, name="Show Viernes", session_date=base_day, start_time=time(20, 0), venue_name="Escenario Principal", expected_attendees=500),
        EventSession(event_id=event.id, name="Show Sabado", session_date=base_day + timedelta(days=1), start_time=time(20, 0), venue_name="Escenario Principal", expected_attendees=450),
        EventSession(event_id=event.id, name="Show Domingo", session_date=base_day + timedelta(days=2), start_time=time(18, 0), venue_name="Escenario Principal", expected_attendees=250),
    ]
    db.add_all(sessions)
    db.flush()
    return sessions


def _create_transport_form(db: Session, event: Event, session: EventSession, suffix: str, index: int) -> EventForm:
    form = _create_form(db, event, session, f"Encuesta Transporte Personal {session.name}", EventFormType.STAFF_TRANSPORT_SURVEY, f"demo-transporte-personal-{index + 1}-{suffix}")
    fields = [
        FormField(form_id=form.id, label="Nombre del evento", field_key="event_name", field_type=FormFieldType.TEXT, is_required=False, sort_order=1, placeholder=event.name),
        FormField(form_id=form.id, label="Nombre del venue / recinto", field_key="venue_name", field_type=FormFieldType.TEXT, is_required=False, sort_order=2, placeholder=session.venue_name or event.location_name),
        FormField(form_id=form.id, label="Nombre completo", field_key="full_name", field_type=FormFieldType.TEXT, is_required=True, sort_order=3),
        FormField(form_id=form.id, label="Empresa", field_key="company", field_type=FormFieldType.TEXT, is_required=False, sort_order=4),
        FormField(form_id=form.id, label="Pais de origen", field_key="country_origin", field_type=FormFieldType.SELECT, analytics_key="country_origin", is_required=True, sort_order=5),
        FormField(form_id=form.id, label="Tipo de transporte utilizado para llegar", field_key="transport_mode", field_type=FormFieldType.SELECT, analytics_key="transport_mode", is_required=True, sort_order=6),
    ]
    db.add_all(fields)
    db.flush()
    _add_options(db, fields[4], COUNTRY_OPTIONS)
    _add_options(db, fields[5], ["Metro", "Bus", "Auto", "Bicicleta"])
    return form


def _create_experience_form(db: Session, event: Event, session: EventSession, suffix: str, index: int) -> EventForm:
    form = _create_form(db, event, session, f"Encuesta Experiencia {session.name}", EventFormType.EXPERIENCE_SURVEY, f"demo-experiencia-{index + 1}-{suffix}")
    fields = [
        FormField(form_id=form.id, label="Nota general", field_key="general_rating", field_type=FormFieldType.RATING_1_7, analytics_key="general_rating", is_required=True, sort_order=1),
        FormField(form_id=form.id, label="Recomendarias el evento", field_key="would_recommend", field_type=FormFieldType.YES_NO, analytics_key="would_recommend", is_required=True, sort_order=2),
        FormField(form_id=form.id, label="Problema principal", field_key="main_problem", field_type=FormFieldType.SELECT, analytics_key="main_problem", is_required=True, sort_order=3),
    ]
    db.add_all(fields)
    db.flush()
    _add_options(db, fields[2], ["Filas", "Banos", "Senaletica", "Sin problemas"])
    return form


def _create_bike_form(db: Session, event: Event, session: EventSession, suffix: str) -> EventForm:
    form = _create_form(db, event, session, "Registro Bike Zone Demo", EventFormType.BIKE_ZONE_REGISTRATION, f"demo-bike-zone-{suffix}")
    fields = [
        FormField(form_id=form.id, label="Nombre del evento", field_key="event_name", field_type=FormFieldType.TEXT, is_required=False, sort_order=1, placeholder=event.name),
        FormField(form_id=form.id, label="Nombre del venue / recinto", field_key="venue_name", field_type=FormFieldType.TEXT, is_required=False, sort_order=2, placeholder=session.venue_name or event.location_name),
        FormField(form_id=form.id, label="Nombre completo", field_key="full_name", field_type=FormFieldType.TEXT, is_required=True, sort_order=3),
        FormField(form_id=form.id, label="Email", field_key="email", field_type=FormFieldType.EMAIL, is_required=True, sort_order=4),
        FormField(form_id=form.id, label="Telefono", field_key="phone", field_type=FormFieldType.PHONE, is_required=True, sort_order=5),
        FormField(form_id=form.id, label="Marca de bicicleta", field_key="bike_brand", field_type=FormFieldType.TEXT, is_required=True, sort_order=6),
        FormField(form_id=form.id, label="Modelo de bicicleta", field_key="bike_model", field_type=FormFieldType.TEXT, is_required=True, sort_order=7),
        FormField(form_id=form.id, label="Color de bicicleta", field_key="bike_color", field_type=FormFieldType.TEXT, is_required=True, sort_order=8),
        FormField(form_id=form.id, label="Region", field_key="residence_region", field_type=FormFieldType.SELECT, analytics_key="residence_region", is_required=True, sort_order=9),
        FormField(form_id=form.id, label="Numero de ticket del evento", field_key="event_ticket_number", field_type=FormFieldType.TEXT, is_required=True, sort_order=10),
    ]
    db.add_all(fields)
    db.flush()
    _add_options(db, fields[8], CHILE_REGION_OPTIONS)
    return form


def _create_form(db: Session, event: Event, session: EventSession, title: str, form_type: EventFormType, slug: str) -> EventForm:
    form = EventForm(
        event_id=event.id,
        session_id=session.id,
        title=title,
        description="Formulario demo creado automaticamente para probar el comparativo por show.",
        form_type=form_type,
        public_slug=slug,
        status=EventFormStatus.ACTIVE,
        primary_color="#16b86a",
        show_event_name=True,
        show_session_name=True,
        collect_personal_data=form_type == EventFormType.BIKE_ZONE_REGISTRATION,
        default_language="es",
        available_languages=LANGUAGES,
        requires_language_selection=False,
    )
    db.add(form)
    db.flush()
    return form


def _add_options(db: Session, field: FormField, labels: list[str]) -> None:
    for index, label in enumerate(labels):
        db.add(FormFieldOption(field_id=field.id, label=label, value=label, sort_order=index))


def _add_transport_response(db: Session, form: EventForm, mode: str, country: str) -> None:
    fields = {field.field_key: field for field in form.fields}
    event_name = form.event.name if form.event else ""
    venue_name = form.session.venue_name if form.session and form.session.venue_name else (form.event.location_name if form.event else "")
    response = FormResponse(
        form_id=form.id,
        event_id=form.event_id,
        session_id=form.session_id,
        language="es",
        raw_data={"event_name": event_name, "venue_name": venue_name, "full_name": "Demo Personal", "company": "ACME Touring", "country_origin": country, "transport_mode": mode},
    )
    db.add(response)
    db.flush()
    db.add_all([
        FormAnswer(response_id=response.id, field_id=fields["event_name"].id, value_text=event_name),
        FormAnswer(response_id=response.id, field_id=fields["venue_name"].id, value_text=venue_name),
        FormAnswer(response_id=response.id, field_id=fields["full_name"].id, value_text="Demo Personal"),
        FormAnswer(response_id=response.id, field_id=fields["company"].id, value_text="ACME Touring"),
        FormAnswer(response_id=response.id, field_id=fields["country_origin"].id, value_text=country),
        FormAnswer(response_id=response.id, field_id=fields["transport_mode"].id, value_text=mode),
    ])


def _add_experience_response(db: Session, form: EventForm, rating: int, recommend: bool, problem: str) -> None:
    fields = {field.field_key: field for field in form.fields}
    response = FormResponse(
        form_id=form.id,
        event_id=form.event_id,
        session_id=form.session_id,
        language="es",
        raw_data={"general_rating": rating, "would_recommend": recommend, "main_problem": problem},
    )
    db.add(response)
    db.flush()
    db.add_all([
        FormAnswer(response_id=response.id, field_id=fields["general_rating"].id, value_number=rating),
        FormAnswer(response_id=response.id, field_id=fields["would_recommend"].id, value_boolean=recommend),
        FormAnswer(response_id=response.id, field_id=fields["main_problem"].id, value_text=problem),
    ])


def _add_bike_response(db: Session, form: EventForm) -> FormResponse:
    fields = {field.field_key: field for field in form.fields}
    event_name = form.event.name if form.event else ""
    venue_name = form.session.venue_name if form.session and form.session.venue_name else (form.event.location_name if form.event else "")
    response = FormResponse(
        form_id=form.id,
        event_id=form.event_id,
        session_id=form.session_id,
        response_code=f"DEMO-{uuid4().hex[:8].upper()}",
        respondent_name="Demo Bike",
        respondent_email="demo-bike@example.com",
        respondent_phone="+56 9 1111 1111",
        language="es",
        raw_data={
            "event_name": event_name,
            "venue_name": venue_name,
            "full_name": "Demo Bike",
            "email": "demo-bike@example.com",
            "phone": "+56 9 1111 1111",
            "bike_brand": "Trek",
            "bike_model": "Urban",
            "bike_color": "Azul",
            "residence_region": "Metropolitana de Santiago",
            "event_ticket_number": "123456",
        },
    )
    db.add(response)
    db.flush()
    db.add_all([
        FormAnswer(response_id=response.id, field_id=fields["event_name"].id, value_text=event_name),
        FormAnswer(response_id=response.id, field_id=fields["venue_name"].id, value_text=venue_name),
        FormAnswer(response_id=response.id, field_id=fields["full_name"].id, value_text="Demo Bike"),
        FormAnswer(response_id=response.id, field_id=fields["email"].id, value_text="demo-bike@example.com"),
        FormAnswer(response_id=response.id, field_id=fields["phone"].id, value_text="+56 9 1111 1111"),
        FormAnswer(response_id=response.id, field_id=fields["bike_brand"].id, value_text="Trek"),
        FormAnswer(response_id=response.id, field_id=fields["bike_model"].id, value_text="Urban"),
        FormAnswer(response_id=response.id, field_id=fields["bike_color"].id, value_text="Azul"),
        FormAnswer(response_id=response.id, field_id=fields["residence_region"].id, value_text="Metropolitana de Santiago"),
        FormAnswer(response_id=response.id, field_id=fields["event_ticket_number"].id, value_text="123456"),
    ])
    return response


def _create_client_portal_config(db: Session, event: Event, admin: User | None) -> None:
    config = ClientPortalConfig(client_id=event.client_id, event_id=event.id, scope="EVENT", is_active=True, created_by=admin.id if admin else None)
    db.add(config)
    db.flush()
    for order, section_key in enumerate(["summary", "forms", "bike_zone", "reports"], start=1):
        db.add(ClientPortalSection(config_id=config.id, section_key=section_key, label=_section_label(section_key), is_enabled=True, sort_order=order * 10))
    widgets = [
        ("event_status", "summary", "Estado del evento"),
        ("forms_total_responses", "forms", "Respuestas de formularios"),
        ("forms_transport_modes", "forms", "Modos de transporte"),
        ("forms_average_rating", "forms", "Rating promedio"),
        ("forms_session_comparison", "forms", "Comparativo por show"),
        ("bike_zone_total_registrations", "bike_zone", "Registros Bike Zone"),
        ("reports_download", "reports", "Descarga de reportes"),
    ]
    for order, (widget_key, section_key, label) in enumerate(widgets, start=1):
        db.add(ClientPortalWidget(config_id=config.id, widget_key=widget_key, section_key=section_key, label=label, is_enabled=True, sort_order=order * 10, visibility_config={}))


def _section_label(section_key: str) -> str:
    return {
        "summary": "Resumen",
        "forms": "Formularios",
        "bike_zone": "Bike Zone",
        "reports": "Reportes",
    }.get(section_key, section_key)


if __name__ == "__main__":
    raise SystemExit(main())
