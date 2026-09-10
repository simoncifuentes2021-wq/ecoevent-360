"""Normalize legacy Bike Zone region selectors.

Revision ID: 20260910_0063
Revises: 20260910_0062
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260910_0063"
down_revision: str | None = "20260910_0062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REGIONS = [
    "Arica y Parinacota",
    "Tarapacá",
    "Antofagasta",
    "Atacama",
    "Coquimbo",
    "Valparaíso",
    "Metropolitana de Santiago",
    "O'Higgins",
    "Maule",
    "Ñuble",
    "Biobío",
    "La Araucanía",
    "Los Ríos",
    "Los Lagos",
    "Aysén",
    "Magallanes",
]


def _sql_value(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    # The earliest Bike Zone template stored region as TEXT. Normalize every
    # legacy form so the UI can offer the controlled Chilean region list.
    op.execute(
        "update form_fields fields set field_type = 'SELECT' "
        "from event_forms forms "
        "where fields.form_id = forms.id "
        "and forms.form_type = 'BIKE_ZONE_REGISTRATION' "
        "and fields.field_key = 'residence_region'"
    )

    # Migration 0062 placed the new field at position 9 for compatibility with
    # the current template. Older templates used shorter ordering, so move it
    # directly below their region and keep intervening fields in the same order.
    op.execute(
        "with positions as ("
        "select forms.id as form_id, region.sort_order as region_order, "
        "commune.id as commune_id, commune.sort_order as commune_order "
        "from event_forms forms "
        "join form_fields region on region.form_id = forms.id "
        "and region.field_key = 'residence_region' "
        "join form_fields commune on commune.form_id = forms.id "
        "and commune.field_key = 'residence_commune' "
        "where forms.form_type = 'BIKE_ZONE_REGISTRATION'"
        ") update form_fields fields set sort_order = fields.sort_order + 1 "
        "from positions "
        "where fields.form_id = positions.form_id "
        "and fields.id <> positions.commune_id "
        "and positions.commune_order > positions.region_order + 1 "
        "and fields.sort_order > positions.region_order "
        "and fields.sort_order < positions.commune_order"
    )
    op.execute(
        "update form_fields commune set sort_order = region.sort_order + 1 "
        "from event_forms forms, form_fields region "
        "where commune.form_id = forms.id "
        "and region.form_id = forms.id "
        "and forms.form_type = 'BIKE_ZONE_REGISTRATION' "
        "and commune.field_key = 'residence_commune' "
        "and region.field_key = 'residence_region' "
        "and commune.sort_order > region.sort_order"
    )

    # Replace the mojibake values inserted by an older data migration. Form
    # answers store their own text and are not deleted by replacing options.
    op.execute(
        "delete from form_field_options options using form_fields fields, event_forms forms "
        "where options.field_id = fields.id "
        "and fields.form_id = forms.id "
        "and forms.form_type = 'BIKE_ZONE_REGISTRATION' "
        "and fields.field_key = 'residence_region'"
    )
    rows = ", ".join(f"({_sql_value(value)}, {index})" for index, value in enumerate(REGIONS))
    op.execute(
        "insert into form_field_options (field_id, label, value, sort_order) "
        "select fields.id, choices.value, choices.value, choices.sort_order "
        "from form_fields fields "
        "join event_forms forms on forms.id = fields.form_id "
        f"cross join (values {rows}) as choices(value, sort_order) "
        "where forms.form_type = 'BIKE_ZONE_REGISTRATION' "
        "and fields.field_key = 'residence_region'"
    )


def downgrade() -> None:
    # Keep corrected configurable data and previously submitted answers intact.
    pass
