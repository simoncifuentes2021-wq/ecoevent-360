"""Add dependent Chile residence fields to transport surveys.

Revision ID: 20260814_0045
Revises: 20260807_0044
"""
from alembic import op


revision = "20260814_0045"
down_revision = "20260807_0044"
branch_labels = None
depends_on = None


REGIONS = [
    "Arica y Parinacota", "TarapacÃƒÂ¡", "Antofagasta", "Atacama", "Coquimbo",
    "ValparaÃƒÂ­so", "Metropolitana de Santiago", "O'Higgins", "Maule", "Ãƒâ€˜uble",
    "BiobÃƒÂ­o", "La AraucanÃƒÂ­a", "Los RÃƒÂ­os", "Los Lagos", "AysÃƒÂ©n", "Magallanes",
]
COMMUNES = [
    "AlhuÃƒÂ©", "Buin", "Calera de Tango", "Cerrillos", "Cerro Navia", "Colina",
    "ConchalÃƒÂ­", "CuracavÃƒÂ­", "El Bosque", "El Monte", "EstaciÃƒÂ³n Central",
    "Huechuraba", "Independencia", "Isla de Maipo", "La Cisterna", "La Florida",
    "La Granja", "La Pintana", "La Reina", "Lampa", "Las Condes", "Lo Barnechea",
    "Lo Espejo", "Lo Prado", "Macul", "MaipÃƒÂº", "MarÃƒÂ­a Pinto", "Melipilla",
    "Ãƒâ€˜uÃƒÂ±oa", "Padre Hurtado", "Paine", "Pedro Aguirre Cerda", "PeÃƒÂ±aflor",
    "PeÃƒÂ±alolÃƒÂ©n", "Pirque", "Providencia", "Pudahuel", "Puente Alto", "Quilicura",
    "Quinta Normal", "Recoleta", "Renca", "San Bernardo", "San JoaquÃƒÂ­n",
    "San JosÃƒÂ© de Maipo", "San Miguel", "San Pedro", "San RamÃƒÂ³n", "Santiago",
    "Talagante", "Tiltil", "Vitacura",
]


def _sql_value(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _add_options(field_key: str, values: list[str]) -> None:
    rows = ", ".join(f"({_sql_value(value)}, {index})" for index, value in enumerate(values))
    op.execute(
        "insert into form_field_options (field_id, label, value, sort_order) "
        "select ff.id, choices.value, choices.value, choices.sort_order "
        "from form_fields ff "
        f"cross join (values {rows}) as choices(value, sort_order) "
        f"where ff.field_key = '{field_key}' "
        "and not exists (select 1 from form_field_options current "
        "where current.field_id = ff.id and current.value = choices.value)"
    )


def upgrade() -> None:
    op.execute(
        "insert into form_fields (form_id, label, field_key, field_type, is_required, sort_order, analytics_key) "
        "select id, 'RegiÃƒÂ³n de residencia', 'residence_region', 'SELECT', false, 6, 'residence_region' "
        "from event_forms where form_type in ('TRANSPORT_SURVEY', 'STAFF_TRANSPORT_SURVEY') "
        "and not exists (select 1 from form_fields where form_id = event_forms.id and field_key = 'residence_region')"
    )
    op.execute(
        "insert into form_fields (form_id, label, field_key, field_type, is_required, sort_order, analytics_key) "
        "select id, 'Comuna de residencia', 'residence_commune', 'SELECT', false, 7, 'residence_commune' "
        "from event_forms where form_type in ('TRANSPORT_SURVEY', 'STAFF_TRANSPORT_SURVEY') "
        "and not exists (select 1 from form_fields where form_id = event_forms.id and field_key = 'residence_commune')"
    )
    _add_options("residence_region", REGIONS)
    _add_options("residence_commune", COMMUNES)


def downgrade() -> None:
    # This migration backfills configurable form data. Removing it automatically
    # could destroy fields or answers subsequently customized by an administrator.
    # A rollback therefore preserves the data; the application remains compatible
    # with these optional fields.
    pass
