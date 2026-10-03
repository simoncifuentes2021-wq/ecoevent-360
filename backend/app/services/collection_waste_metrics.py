from decimal import Decimal
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import WasteCollectionRecord, WasteType
from app.models.enums import WasteDestination


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def collection_waste_by_destination(db: Session, *filters) -> dict[WasteDestination, Decimal]:
    """Classify Acopios weights using the configured stream type and its route.

    Greenway's Acopios streams go to recycling or composting. General non-
    recyclable waste goes to landfill, and hazardous waste to special disposal.
    """
    rows = db.execute(
        select(
            WasteType.name,
            WasteType.is_recyclable,
            func.coalesce(func.sum(WasteCollectionRecord.weight_kg), Decimal("0")),
        )
        .select_from(WasteCollectionRecord)
        .join(WasteType, WasteType.id == WasteCollectionRecord.waste_type_id)
        .where(*filters)
        .group_by(WasteType.name, WasteType.is_recyclable)
    ).all()

    totals: dict[WasteDestination, Decimal] = {}
    for name, is_recyclable, weight in rows:
        normalized_name = _normalized(name)
        if "organ" in normalized_name or "compost" in normalized_name:
            destination = WasteDestination.COMPOSTING
        elif "pelig" in normalized_name:
            destination = WasteDestination.SPECIAL_DISPOSAL
        elif is_recyclable:
            destination = WasteDestination.RECYCLING
        else:
            destination = WasteDestination.LANDFILL
        totals[destination] = totals.get(destination, Decimal("0")) + Decimal(weight or 0)
    return totals
