"""Add conditional commune field to existing Bike Zone forms.

Revision ID: 20260910_0062
Revises: 20260909_0061
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260910_0062"
down_revision: str | None = "20260909_0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


COMMUNES = [
    "Alhué", "Buin", "Calera de Tango", "Cerrillos", "Cerro Navia", "Colina",
    "Conchalí", "Curacaví", "El Bosque", "El Monte", "Estación Central",
    "Huechuraba", "Independencia", "Isla de Maipo", "La Cisterna", "La Florida",
    "La Granja", "La Pintana", "La Reina", "Lampa", "Las Condes", "Lo Barnechea",
    "Lo Espejo", "Lo Prado", "Macul", "Maipú", "María Pinto", "Melipilla",
    "Ñuñoa", "Padre Hurtado", "Paine", "Pedro Aguirre Cerda", "Peñaflor",
    "Peñalolén", "Pirque", "Providencia", "Pudahuel", "Puente Alto", "Quilicura",
    "Quinta Normal", "Recoleta", "Renca", "San Bernardo", "San Joaquín",
    "San José de Maipo", "San Miguel", "San Pedro", "San Ramón", "Santiago",
    "Talagante", "Tiltil", "Vitacura",
]


def _sql_value(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    # Preserve the field order of customized forms while placing comuna directly
    # after región in standard Bike Zone forms.
    op.execute(
        "update form_fields existing set sort_order = existing.sort_order + 1 "
        "from event_forms forms "
        "where existing.form_id = forms.id "
        "and forms.form_type = 'BIKE_ZONE_REGISTRATION' "
        "and existing.sort_order >= 9 "
        "and not exists (select 1 from form_fields commune "
        "where commune.form_id = forms.id and commune.field_key = 'residence_commune')"
    )
    op.execute(
        "insert into form_fields "
        "(form_id, label, field_key, field_type, is_required, sort_order, analytics_key) "
        "select forms.id, 'Comuna de residencia', 'residence_commune', "
        "'SELECT', false, 9, 'residence_commune' "
        "from event_forms forms "
        "where forms.form_type = 'BIKE_ZONE_REGISTRATION' "
        "and not exists (select 1 from form_fields existing "
        "where existing.form_id = forms.id and existing.field_key = 'residence_commune')"
    )

    rows = ", ".join(f"({_sql_value(value)}, {index})" for index, value in enumerate(COMMUNES))
    op.execute(
        "insert into form_field_options (field_id, label, value, sort_order) "
        "select fields.id, choices.value, choices.value, choices.sort_order "
        "from form_fields fields "
        "join event_forms forms on forms.id = fields.form_id "
        f"cross join (values {rows}) as choices(value, sort_order) "
        "where forms.form_type = 'BIKE_ZONE_REGISTRATION' "
        "and fields.field_key = 'residence_commune' "
        "and not exists (select 1 from form_field_options current "
        "where current.field_id = fields.id and current.value = choices.value)"
    )


def downgrade() -> None:
    # Preserve submitted answers and any later administrator customization.
    pass
