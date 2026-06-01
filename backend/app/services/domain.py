from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import (
    CarbonFactor,
    CarbonRecord,
    Client,
    Event,
    EventService,
    EventZone,
    Evidence,
    Incident,
    Service,
    SurveyImport,
    Task,
    WasteRecord,
)
from app.services.crud import CRUDService

clients = CRUDService(Client)
events = CRUDService(Event)
services = CRUDService(Service)
event_services = CRUDService(EventService)
event_zones = CRUDService(EventZone)
tasks = CRUDService(Task)
incidents = CRUDService(Incident)
evidences = CRUDService(Evidence)
waste_records = CRUDService(WasteRecord)
carbon_factors = CRUDService(CarbonFactor)
survey_imports = CRUDService(SurveyImport)


def create_carbon_record(
    db: Session,
    *,
    event_id: UUID,
    factor_id: UUID,
    category: str,
    activity_value: float,
    activity_unit: str,
    emissions_kgco2e: float,
    description: str | None = None,
    recorded_by: UUID | None = None,
) -> CarbonRecord:
    item = CarbonRecord(
        event_id=event_id,
        factor_id=factor_id,
        category=category,
        description=description,
        activity_value=activity_value,
        activity_unit=activity_unit,
        emissions_kgco2e=emissions_kgco2e,
        recorded_by=recorded_by,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def event_dashboard(db: Session, event_id: UUID) -> dict[str, float | int | UUID]:
    tasks_total = db.scalar(
        select(func.count()).select_from(Task).where(Task.event_id == event_id)
    )
    incidents_open = db.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.event_id == event_id, Incident.status.not_in(["RESOLVED", "CLOSED"]))
    )
    waste_kg = db.scalar(
        select(func.coalesce(func.sum(WasteRecord.weight_kg), 0)).where(
            WasteRecord.event_id == event_id
        )
    )
    total_kg_co2e = db.scalar(
        select(func.coalesce(func.sum(CarbonRecord.emissions_kgco2e), 0)).where(
            CarbonRecord.event_id == event_id
        )
    )
    return {
        "event_id": event_id,
        "tasks_total": tasks_total or 0,
        "incidents_open": incidents_open or 0,
        "waste_kg": float(waste_kg or 0),
        "total_kg_co2e": float(total_kg_co2e or 0),
    }
