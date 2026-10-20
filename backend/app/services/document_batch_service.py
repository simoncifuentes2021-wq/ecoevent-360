from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.permissions import can_manage_event, can_view_operational_event
from app.db.session import set_document_event_context
from app.models.core import Event, User
from app.models.documents import (
    DocumentEmployment,
    DocumentPerson,
    EppDelivery,
    EppDeliveryItem,
    ManagedDocument,
)
from app.models.enums import UserRole
from app.schemas.document_schema import (
    ExistingPeopleAssignmentCommit,
    GenerateMissingDraftsCommit,
    PersonImportCommit,
)
from app.services.document_people_service import (
    display_rut,
    normalize_person_name,
    normalize_rut,
)
from app.services.managed_documents_service import get_contract_defaults, get_event_epp_template


def _contract_input_gaps(person, employment, defaults: dict, event: Event) -> list[str]:
    gaps: list[str] = []
    checks = (
        (getattr(person, "first_name", None), "Nombre"),
        (getattr(person, "last_name", None), "Apellido"),
        (getattr(person, "rut", None), "RUT"),
        (getattr(person, "email", None), "Correo para envío"),
        (getattr(person, "address", None), "Domicilio del trabajador"),
        (getattr(person, "commune", None), "Comuna del trabajador"),
        (getattr(employment, "duties", None) or getattr(employment, "position", None), "Cargo / funciones"),
        (getattr(employment, "start_date", None), "Fecha de inicio"),
        (getattr(employment, "end_date", None), "Fecha de término"),
        (getattr(employment, "remuneration", None), "Remuneración"),
        (getattr(employment, "workplace", None) or event.location_name or event.address, "Lugar / dependencias"),
        (defaults.get("employer_name"), "Razón social del empleador"),
        (defaults.get("employer_rut"), "RUT del empleador"),
        (defaults.get("representative_name"), "Representante legal"),
        (defaults.get("representative_rut"), "RUT del representante"),
        (defaults.get("employer_address"), "Domicilio del empleador"),
    )
    gaps.extend(label for value, label in checks if value is None or not str(value).strip())
    for value, label in (
        (getattr(person, "rut", None), "RUT del trabajador"),
        (defaults.get("employer_rut"), "RUT del empleador"),
        (defaults.get("representative_rut"), "RUT del representante"),
    ):
        if value:
            try:
                normalize_rut(str(value))
            except ValueError:
                gaps.append(f"{label} inválido")
    if employment and employment.start_date and employment.end_date and employment.end_date < employment.start_date:
        gaps.append("Rango de fechas incoherente")
    if employment and employment.remuneration is not None and employment.remuneration < 0:
        gaps.append("Remuneración no puede ser negativa")
    return gaps


def generate_missing_draft_pairs(
    db: Session, payload: GenerateMissingDraftsCommit, user: User
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=403, detail="Rol sin permiso para generar documentos")
    if len(payload.person_ids) != len(set(payload.person_ids)):
        raise HTTPException(status_code=422, detail="La selección contiene personas repetidas")

    event = db.scalar(select(Event).where(Event.id == payload.event_id).with_for_update())
    if event is None or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Faena no encontrada o sin acceso")
    if user.role == UserRole.SUPERVISOR:
        if not can_manage_event(user, event.id, db):
            raise HTTPException(status_code=403, detail="No puedes gestionar documentos de esta faena")
        set_document_event_context(db, event.id)

    assignments = db.scalars(
        select(DocumentEmployment)
        .where(
            DocumentEmployment.event_id == event.id,
            DocumentEmployment.person_id.in_(payload.person_ids),
        )
        .order_by(DocumentEmployment.created_at.desc(), DocumentEmployment.id.desc())
    ).all()
    latest_assignment_by_person: dict[UUID, DocumentEmployment] = {}
    for assignment in assignments:
        latest_assignment_by_person.setdefault(assignment.person_id, assignment)
    if set(latest_assignment_by_person) != set(payload.person_ids):
        raise HTTPException(
            status_code=422,
            detail="La selección incluye personas que no están asignadas a esta faena",
        )

    people = {
        person.id: person
        for person in db.scalars(
            select(DocumentPerson).where(DocumentPerson.id.in_(payload.person_ids))
        ).all()
    }
    existing = db.scalars(
        select(ManagedDocument).where(
            ManagedDocument.event_id == event.id,
            ManagedDocument.person_id.in_(payload.person_ids),
            ManagedDocument.status != "CANCELLED",
        )
    ).all()
    existing_by_person: dict[UUID, set[str]] = {person_id: set() for person_id in payload.person_ids}
    for document in existing:
        existing_by_person[document.person_id].add(document.kind)

    defaults = get_contract_defaults(db, event.id)
    epp_items = get_event_epp_template(db, event.id, user)["items"]
    setup_warnings = [
        label for key, label in (
            ("employer_name", "Razón social del empleador"),
            ("employer_rut", "RUT del empleador"),
            ("representative_name", "Representante legal"),
            ("representative_rut", "RUT del representante"),
            ("employer_address", "Domicilio del empleador"),
        ) if not defaults.get(key)
    ]
    results = []
    contracts_created = epp_created = 0
    try:
        for person_id in payload.person_ids:
            person = people[person_id]
            assignment = latest_assignment_by_person[person_id]
            created: list[str] = []
            already_had: list[str] = []
            if "CONTRACT" in existing_by_person[person_id]:
                already_had.append("CONTRACT")
            else:
                db.add(ManagedDocument(
                    client_id=event.client_id,
                    person_id=person.id,
                    employment_id=assignment.id,
                    event_id=event.id,
                    created_by=user.id,
                    kind="CONTRACT",
                    title="Contrato por Obra o Faena",
                    data={
                        **defaults,
                        "contract_date": date.today().isoformat(),
                        "duties": assignment.duties or assignment.position,
                        "workplace": assignment.workplace or event.location_name or event.address or "",
                    },
                ))
                created.append("CONTRACT")
                contracts_created += 1
            if "EPP" in existing_by_person[person_id]:
                already_had.append("EPP")
            else:
                epp_doc = ManagedDocument(
                    client_id=event.client_id,
                    person_id=person.id,
                    employment_id=assignment.id,
                    event_id=event.id,
                    created_by=user.id,
                    kind="EPP",
                    title="Registro de recepción EPP / RIOHS / EIRL",
                    data={"employer_name": defaults.get("employer_name", "")},
                )
                db.add(epp_doc)
                db.flush()
                delivery = EppDelivery(
                    client_id=event.client_id,
                    document_id=epp_doc.id,
                    riohs_received=False,
                    eirl_completed=False,
                )
                db.add(delivery)
                db.flush()
                db.add_all([
                    EppDeliveryItem(
                        delivery_id=delivery.id,
                        item_code=item["item_code"],
                        label=item["label"],
                        received_conformity=False,
                    ) for item in epp_items
                ])
                created.append("EPP")
                epp_created += 1
            results.append({
                "person_id": str(person.id),
                "name": f"{person.first_name} {person.last_name}",
                "rut": person.rut,
                "created": created,
                "already_had": already_had,
            })
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "event_id": str(event.id),
        "event_name": event.name,
        "workers_processed": len(payload.person_ids),
        "contracts_created": contracts_created,
        "epp_documents_created": epp_created,
        "documents_created": contracts_created + epp_created,
        "documents_skipped": sum(len(row["already_had"]) for row in results),
        "setup_warnings": setup_warnings,
        "results": results,
    }


def preview_missing_draft_pairs(
    db: Session, payload: GenerateMissingDraftsCommit, user: User
) -> dict:
    if len(payload.person_ids) != len(set(payload.person_ids)):
        raise HTTPException(status_code=422, detail="La selección contiene personas repetidas")
    event = db.get(Event, payload.event_id)
    if event is None or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Faena no encontrada o sin acceso")
    if user.role == UserRole.SUPERVISOR:
        if not can_manage_event(user, event.id, db):
            raise HTTPException(status_code=403, detail="No puedes gestionar documentos de esta faena")
        set_document_event_context(db, event.id)

    assignments = db.scalars(
        select(DocumentEmployment)
        .where(
            DocumentEmployment.event_id == event.id,
            DocumentEmployment.person_id.in_(payload.person_ids),
        )
        .order_by(DocumentEmployment.created_at.desc(), DocumentEmployment.id.desc())
    ).all()
    assignment_by_person: dict[UUID, DocumentEmployment] = {}
    for assignment in assignments:
        assignment_by_person.setdefault(assignment.person_id, assignment)
    if set(assignment_by_person) != set(payload.person_ids):
        raise HTTPException(status_code=422, detail="La selección incluye personas que no están asignadas a esta faena")
    people = {
        person.id: person
        for person in db.scalars(select(DocumentPerson).where(DocumentPerson.id.in_(payload.person_ids))).all()
    }
    existing = db.scalars(
        select(ManagedDocument).where(
            ManagedDocument.event_id == event.id,
            ManagedDocument.person_id.in_(payload.person_ids),
            ManagedDocument.status != "CANCELLED",
        )
    ).all()
    existing_by_person: dict[UUID, set[str]] = {person_id: set() for person_id in payload.person_ids}
    for document in existing:
        existing_by_person[document.person_id].add(document.kind)
    defaults = get_contract_defaults(db, event.id)
    warnings = [
        label for key, label in (
            ("employer_name", "Razón social del empleador"),
            ("employer_rut", "RUT del empleador"),
            ("representative_name", "Representante legal"),
            ("representative_rut", "RUT del representante"),
            ("employer_address", "Domicilio del empleador"),
        ) if not defaults.get(key)
    ]
    results = []
    for person_id in payload.person_ids:
        person = people[person_id]
        had = sorted(existing_by_person[person_id])
        create = [kind for kind in ("CONTRACT", "EPP") if kind not in had]
        assignment = assignment_by_person[person_id]
        missing_data = _contract_input_gaps(person, assignment, defaults, event) if "CONTRACT" in create else []
        results.append({
            "person_id": str(person_id),
            "name": f"{person.first_name} {person.last_name}",
            "rut": person.rut,
            "create": create,
            "already_had": had,
            "employment_id": str(assignment_by_person[person_id].id),
            "missing_data": missing_data,
        })
    return {
        "event_id": str(event.id), "event_name": event.name,
        "workers_processed": len(results),
        "contracts_to_create": sum("CONTRACT" in row["create"] for row in results),
        "epp_to_create": sum("EPP" in row["create"] for row in results),
        "documents_to_create": sum(len(row["create"]) for row in results),
        "documents_existing": sum(len(row["already_had"]) for row in results),
        "setup_warnings": warnings, "results": results,
    }


def preview_import_draft_pairs(
    db: Session, payload: PersonImportCommit, user: User
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=403, detail="Rol sin permiso para generar documentos")
    if not payload.event_id:
        raise HTTPException(status_code=422, detail="Selecciona la faena antes de generar los documentos")
    event = db.get(Event, payload.event_id)
    if event is None or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Evento no encontrado o sin acceso")
    if payload.client_id and payload.client_id != event.client_id:
        raise HTTPException(status_code=422, detail="El evento no pertenece al cliente seleccionado")
    if user.role == UserRole.SUPERVISOR:
        if not can_manage_event(user, event.id, db):
            raise HTTPException(status_code=403, detail="No puedes generar documentos para esta faena")
        set_document_event_context(db, event.id)

    defaults = get_contract_defaults(db, event.id)
    setup_warnings = [
        label for key, label in (
            ("employer_name", "Razón social del empleador"),
            ("employer_rut", "RUT del empleador"),
            ("representative_name", "Representante legal"),
            ("representative_rut", "RUT del representante"),
            ("employer_address", "Domicilio del empleador"),
        ) if not defaults.get(key)
    ]
    seen: set[str] = set()
    results = []
    for row in payload.rows:
        try:
            normalized = normalize_rut(row.rut)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"RUT inválido: {row.rut}") from exc
        if normalized in seen:
            raise HTTPException(status_code=409, detail=f"RUT duplicado en el archivo: {row.rut}")
        seen.add(normalized)
        if row.start_date and row.end_date and row.end_date < row.start_date:
            raise HTTPException(status_code=422, detail=f"Fechas inválidas para el RUT {row.rut}")

        person = db.scalar(select(DocumentPerson).where(DocumentPerson.rut_normalized == normalized))
        existing_kinds: set[str] = set()
        existing_assignment = None
        if person:
            assignment_query = select(DocumentEmployment).where(
                DocumentEmployment.client_id == event.client_id,
                DocumentEmployment.person_id == person.id,
                DocumentEmployment.event_id == event.id,
                DocumentEmployment.position == row.position.strip(),
            )
            if row.start_date is not None:
                assignment_query = assignment_query.where(DocumentEmployment.start_date == row.start_date)
            existing_assignment = db.scalar(assignment_query.order_by(DocumentEmployment.created_at.desc()).limit(1))
            existing_kinds = set(db.scalars(select(ManagedDocument.kind).where(
                ManagedDocument.person_id == person.id,
                ManagedDocument.event_id == event.id,
                ManagedDocument.status != "CANCELLED",
            )).all())
        create = [kind for kind in ("CONTRACT", "EPP") if kind not in existing_kinds]
        missing_data = []
        if "CONTRACT" in create:
            row_person = SimpleNamespace(
                first_name=row.first_name, last_name=row.last_name, rut=row.rut,
                email=row.email or (person.email if person else None),
                address=row.address or (person.address if person else None),
                commune=row.commune or (person.commune if person else None),
            )
            row_employment = SimpleNamespace(
                position=row.position,
                duties=(row.duties or (existing_assignment.duties if existing_assignment else None)),
                start_date=row.start_date or (existing_assignment.start_date if existing_assignment else None),
                end_date=row.end_date or (existing_assignment.end_date if existing_assignment else None),
                remuneration=row.remuneration if row.remuneration is not None else (existing_assignment.remuneration if existing_assignment else None),
                workplace=row.workplace or (existing_assignment.workplace if existing_assignment else None),
            )
            missing_data = _contract_input_gaps(row_person, row_employment, defaults, event)
        results.append({
            "rut": row.rut,
            "name": f"{normalize_person_name(row.first_name)} {normalize_person_name(row.last_name)}",
            "person_action": "Actualizar ficha" if person else "Crear ficha",
            "assignment_action": "Actualizar asignación" if existing_assignment else "Crear asignación",
            "create": create,
            "already_had": sorted(existing_kinds),
            "missing_data": missing_data,
        })
    return {
        "event_id": str(event.id), "event_name": event.name,
        "workers_processed": len(results),
        "contracts_to_create": sum("CONTRACT" in row["create"] for row in results),
        "epp_to_create": sum("EPP" in row["create"] for row in results),
        "documents_to_create": sum(len(row["create"]) for row in results),
        "documents_existing": sum(len(row["already_had"]) for row in results),
        "setup_warnings": setup_warnings, "results": results,
    }


def _generate_one_import_row(db, row, rut_normalized, event, user, defaults, epp_items):
    if user.role == UserRole.SUPERVISOR:
        db.connection().execute(
            text("select set_config('app.document_person_lookup_rut', :rut, true)"),
            {"rut": rut_normalized},
        )
    person = db.scalar(
        select(DocumentPerson).where(DocumentPerson.rut_normalized == rut_normalized).with_for_update()
    )
    person_action = "updated"
    if person is None:
        person = DocumentPerson(
            first_name=normalize_person_name(row.first_name),
            last_name=normalize_person_name(row.last_name),
            rut=display_rut(rut_normalized),
            rut_normalized=rut_normalized,
            email=str(row.email).lower() if row.email else None,
            phone=row.phone.strip() if row.phone else None,
            address=row.address.strip() if row.address else None,
            commune=row.commune.strip() if row.commune else None,
        )
        db.add(person)
        db.flush()
        person_action = "created"
    else:
        person.first_name = normalize_person_name(row.first_name)
        person.last_name = normalize_person_name(row.last_name)
        person.rut = display_rut(rut_normalized)
        person.email = str(row.email).lower() if row.email else person.email
        person.phone = row.phone.strip() if row.phone else person.phone
        person.address = row.address.strip() if row.address else person.address
        person.commune = row.commune.strip() if row.commune else person.commune
        person.updated_at = datetime.utcnow()

    assignment_query = select(DocumentEmployment).where(
        DocumentEmployment.client_id == event.client_id,
        DocumentEmployment.person_id == person.id,
        DocumentEmployment.event_id == event.id,
        DocumentEmployment.position == row.position.strip(),
    )
    if row.start_date is not None:
        assignment_query = assignment_query.where(DocumentEmployment.start_date == row.start_date)
    assignment = db.scalar(
        assignment_query.order_by(DocumentEmployment.created_at.desc()).limit(1).with_for_update()
    )
    assignment_action = "updated"
    if assignment is None:
        assignment = DocumentEmployment(
            client_id=event.client_id,
            person_id=person.id,
            event_id=event.id,
            position=row.position.strip(),
            area=row.area.strip() if row.area else None,
            workplace=row.workplace.strip() if row.workplace else None,
            duties=row.duties.strip() if row.duties else None,
            start_date=row.start_date,
            end_date=row.end_date,
            remuneration=row.remuneration,
        )
        db.add(assignment)
        db.flush()
        assignment_action = "created"
    else:
        assignment.area = row.area.strip() if row.area else None
        assignment.workplace = row.workplace.strip() if row.workplace else assignment.workplace
        assignment.duties = row.duties.strip() if row.duties and row.duties.strip() else assignment.duties
        assignment.end_date = row.end_date or assignment.end_date
        if row.remuneration is not None:
            assignment.remuneration = row.remuneration
        assignment.updated_at = datetime.utcnow()

    existing_kinds = set(db.scalars(select(ManagedDocument.kind).where(
        ManagedDocument.person_id == person.id,
        ManagedDocument.event_id == event.id,
        ManagedDocument.status != "CANCELLED",
    )).all())
    contract_data = {
        **defaults,
        "contract_date": date.today().isoformat(),
        "duties": row.duties.strip() if row.duties and row.duties.strip() else row.position.strip(),
        "workplace": row.workplace.strip() if row.workplace else event.location_name or event.address or "",
    }
    created: list[str] = []
    already_had: list[str] = []
    if "CONTRACT" not in existing_kinds:
        db.add(ManagedDocument(
            client_id=event.client_id,
            person_id=person.id,
            employment_id=assignment.id,
            event_id=event.id,
            created_by=user.id,
            kind="CONTRACT",
            title="Contrato por Obra o Faena",
            data=contract_data,
        ))
        created.append("CONTRACT")
    else:
        already_had.append("CONTRACT")

    if "EPP" not in existing_kinds:
        epp_doc = ManagedDocument(
            client_id=event.client_id,
            person_id=person.id,
            employment_id=assignment.id,
            event_id=event.id,
            created_by=user.id,
            kind="EPP",
            title="Registro de recepción EPP / RIOHS / EIRL",
            data={"employer_name": defaults.get("employer_name", "")},
        )
        db.add(epp_doc)
        db.flush()
        delivery = EppDelivery(
            client_id=event.client_id,
            document_id=epp_doc.id,
            riohs_received=False,
            eirl_completed=False,
        )
        db.add(delivery)
        db.flush()
        db.add_all([
            EppDeliveryItem(
                delivery_id=delivery.id,
                item_code=item["item_code"],
                label=item["label"],
                received_conformity=False,
            ) for item in epp_items
        ])
        created.append("EPP")
    else:
        already_had.append("EPP")
    db.flush()
    return {
        "person_id": str(person.id),
        "rut": display_rut(rut_normalized),
        "name": f"{person.first_name} {person.last_name}",
        "person_action": person_action,
        "assignment_action": assignment_action,
        "created": created,
        "already_had": already_had,
        "status": "SUCCESS",
        "error": None,
    }
def assign_existing_people(
    db: Session, payload: ExistingPeopleAssignmentCommit, user: User
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Solo admin puede reasignar personal entre faenas")
    if payload.source_event_id == payload.target_event_id:
        raise HTTPException(status_code=422, detail="Elige una faena de destino distinta a la de origen")

    source_event = db.scalar(select(Event).where(Event.id == payload.source_event_id))
    target_event = db.scalar(
        select(Event).where(Event.id == payload.target_event_id).with_for_update()
    )
    if source_event is None or target_event is None:
        raise HTTPException(status_code=404, detail="No se encontró la faena de origen o destino")
    if not can_view_operational_event(user, source_event, db) or not can_view_operational_event(
        user, target_event, db
    ):
        raise HTTPException(status_code=403, detail="No tienes acceso a una de las faenas seleccionadas")

    person_ids = [row.person_id for row in payload.assignments]
    if len(person_ids) != len(set(person_ids)):
        raise HTTPException(status_code=422, detail="La selección contiene personas repetidas")

    people = {
        person.id: person
        for person in db.scalars(select(DocumentPerson).where(DocumentPerson.id.in_(person_ids))).all()
    }
    if len(people) != len(person_ids):
        raise HTTPException(status_code=404, detail="Una persona seleccionada ya no está disponible")

    source_ids = set(
        db.scalars(
            select(DocumentEmployment.person_id).where(
                DocumentEmployment.event_id == source_event.id,
                DocumentEmployment.person_id.in_(person_ids),
            )
        ).all()
    )
    if source_ids != set(person_ids):
        raise HTTPException(status_code=422, detail="Todas las personas deben pertenecer a la faena de origen")

    already_assigned_ids = set(
        db.scalars(
            select(DocumentEmployment.person_id).where(
                DocumentEmployment.event_id == target_event.id,
                DocumentEmployment.person_id.in_(person_ids),
            )
        ).all()
    )
    already_assigned = [
        {
            "person_id": str(person_id),
            "name": f"{people[person_id].first_name} {people[person_id].last_name}",
            "rut": people[person_id].rut,
        }
        for person_id in person_ids
        if person_id in already_assigned_ids
    ]
    defaults = get_contract_defaults(db, target_event.id) if payload.generate_documents else {}
    epp_items = get_event_epp_template(db, target_event.id, user)["items"] if payload.generate_documents else []
    setup_warnings = [
        label
        for key, label in (
            ("employer_name", "Razón social del empleador"),
            ("employer_rut", "RUT del empleador"),
            ("representative_name", "Representante legal"),
            ("representative_rut", "RUT del representante"),
            ("employer_address", "Domicilio del empleador"),
        )
        if payload.generate_documents and not defaults.get(key)
    ]

    assigned = []
    contracts_created = epp_created = documents_skipped = 0
    try:
        for row in payload.assignments:
            person = people[row.person_id]
            if row.person_id in already_assigned_ids:
                continue
            if row.start_date and row.end_date and row.end_date < row.start_date:
                raise HTTPException(
                    status_code=422,
                    detail=f"Las fechas de asignación son inválidas para {person.first_name} {person.last_name}",
                )

            assignment = DocumentEmployment(
                client_id=target_event.client_id,
                person_id=person.id,
                event_id=target_event.id,
                position=row.position.strip(),
                area=row.area.strip() if row.area else None,
                workplace=row.workplace.strip() if row.workplace else None,
                start_date=row.start_date,
                end_date=row.end_date,
                remuneration=row.remuneration,
                duties=row.duties.strip() if row.duties else None,
            )
            db.add(assignment)
            db.flush()
            assigned.append({
                "person_id": str(person.id),
                "name": f"{person.first_name} {person.last_name}",
                "rut": person.rut,
                "employment_id": str(assignment.id),
            })

            if not payload.generate_documents:
                continue

            existing_kinds = set(
                db.scalars(
                    select(ManagedDocument.kind).where(
                        ManagedDocument.person_id == person.id,
                        ManagedDocument.event_id == target_event.id,
                        ManagedDocument.status != "CANCELLED",
                    )
                ).all()
            )
            if "CONTRACT" not in existing_kinds:
                db.add(ManagedDocument(
                    client_id=target_event.client_id,
                    person_id=person.id,
                    employment_id=assignment.id,
                    event_id=target_event.id,
                    created_by=user.id,
                    kind="CONTRACT",
                    title="Contrato por Obra o Faena",
                    data={
                        **defaults,
                        "contract_date": date.today().isoformat(),
                        "duties": row.duties.strip() if row.duties and row.duties.strip() else row.position.strip(),
                        "workplace": row.workplace.strip() if row.workplace else (
                            target_event.location_name or target_event.address or ""
                        ),
                    },
                ))
                contracts_created += 1
            else:
                documents_skipped += 1

            if "EPP" not in existing_kinds:
                epp_doc = ManagedDocument(
                    client_id=target_event.client_id,
                    person_id=person.id,
                    employment_id=assignment.id,
                    event_id=target_event.id,
                    created_by=user.id,
                    kind="EPP",
                    title="Registro de recepción EPP / RIOHS / EIRL",
                    data={"employer_name": defaults.get("employer_name", "")},
                )
                db.add(epp_doc)
                db.flush()
                delivery = EppDelivery(
                    client_id=target_event.client_id,
                    document_id=epp_doc.id,
                    riohs_received=False,
                    eirl_completed=False,
                )
                db.add(delivery)
                db.flush()
                db.add_all([
                    EppDeliveryItem(
                        delivery_id=delivery.id,
                        item_code=code,
                        label=label,
                        received_conformity=False,
                    )
                    for code, label in ((item["item_code"], item["label"]) for item in epp_items)
                ])
                epp_created += 1
            else:
                documents_skipped += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "source_event_id": str(source_event.id),
        "target_event_id": str(target_event.id),
        "target_event_name": target_event.name,
        "assigned": assigned,
        "already_assigned": already_assigned,
        "contracts_created": contracts_created,
        "epp_documents_created": epp_created,
        "documents_created": contracts_created + epp_created,
        "documents_skipped": documents_skipped,
        "setup_warnings": setup_warnings,
    }


def generate_draft_pairs(
    db: Session, payload: PersonImportCommit, user: User
) -> dict:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=403, detail="Rol sin permiso para generar documentos")
    if not payload.event_id:
        raise HTTPException(status_code=422, detail="Selecciona la faena antes de generar los documentos")

    event = db.scalar(
        select(Event).where(Event.id == payload.event_id).with_for_update()
    )
    if event is None or not can_view_operational_event(user, event, db):
        raise HTTPException(status_code=404, detail="Evento no encontrado o sin acceso")
    if payload.client_id and payload.client_id != event.client_id:
        raise HTTPException(status_code=422, detail="El evento no pertenece al cliente seleccionado")
    if user.role == UserRole.SUPERVISOR and not can_manage_event(user, event.id, db):
        raise HTTPException(status_code=403, detail="No puedes generar documentos para esta faena")
    if user.role == UserRole.SUPERVISOR:
        set_document_event_context(db, event.id)

    rows: list[tuple[object, str]] = []
    seen: set[str] = set()
    for row in payload.rows:
        try:
            rut_normalized = normalize_rut(row.rut)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Uno de los RUT no es válido") from exc
        if rut_normalized in seen:
            raise HTTPException(status_code=409, detail="La planilla contiene RUT duplicados")
        seen.add(rut_normalized)
        if row.start_date and row.end_date and row.end_date < row.start_date:
            raise HTTPException(status_code=422, detail=f"Fechas inválidas para el RUT {row.rut}")
        rows.append((row, rut_normalized))

    defaults = get_contract_defaults(db, event.id)
    epp_items = get_event_epp_template(db, event.id, user)["items"]
    setup_warnings = [
        label
        for key, label in (
            ("employer_name", "Razón social del empleador"),
            ("employer_rut", "RUT del empleador"),
            ("representative_name", "Representante legal"),
            ("representative_rut", "RUT del representante"),
            ("employer_address", "Domicilio del empleador"),
        )
        if not defaults.get(key)
    ]

    people_created = people_updated = assignments_created = 0
    contracts_created = epp_created = documents_skipped = 0
    row_results = []
    try:
        for row, rut_normalized in rows:
            try:
                with db.begin_nested():
                    outcome = _generate_one_import_row(
                        db, row, rut_normalized, event, user, defaults, epp_items
                    )
                row_results.append(outcome)
                people_created += outcome["person_action"] == "created"
                people_updated += outcome["person_action"] == "updated"
                assignments_created += outcome["assignment_action"] == "created"
                contracts_created += "CONTRACT" in outcome["created"]
                epp_created += "EPP" in outcome["created"]
                documents_skipped += len(outcome["already_had"])
            except Exception:
                row_results.append({
                    "rut": display_rut(rut_normalized),
                    "name": f"{normalize_person_name(row.first_name)} {normalize_person_name(row.last_name)}",
                    "person_action": "unchanged",
                    "assignment_action": "unchanged",
                    "created": [],
                    "already_had": [],
                    "status": "ERROR",
                    "error": "No se pudo procesar esta fila. Puedes reintentarla individualmente.",
                })
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "event_id": event.id,
        "event_name": event.name,
        "people_created": people_created,
        "people_updated": people_updated,
        "assignments_created": assignments_created,
        "contracts_created": contracts_created,
        "epp_documents_created": epp_created,
        "documents_created": contracts_created + epp_created,
        "documents_skipped": documents_skipped,
        "workers_processed": len(rows),
        "setup_warnings": setup_warnings,
        "results": row_results,
        "workers_failed": sum(result["status"] == "ERROR" for result in row_results),
    }
