"""Seed documented environmental factors and comparison methodologies.

Revision ID: 20260818_0050
Revises: 20260818_0049
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260818_0050"
down_revision = "20260818_0049"
branch_labels = None
depends_on = None

HUELLA_URL = (
    "https://huellachile.mma.gob.cl/wp-content/uploads/2026/02/"
    "RDC-Proyectos-Reduccion-HuellaChile-V02.pdf"
)
EPA_EQ_URL = (
    "https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references"
)
EPA_HUB_URL = "https://www.epa.gov/climateleadership/ghg-emission-factors-hub"
AP42_URL = (
    "https://www.epa.gov/air-emissions-factors-and-quantification/"
    "ap-42-fifth-edition-volume-i-chapter-3-stationary-0"
)

# Stable IDs let methodology JSON refer to factors without database-specific lookups.
IDS = {
    "grid": "51000000-0000-4000-8000-000000000001",
    "solar": "51000000-0000-4000-8000-000000000002",
    "generator": "51000000-0000-4000-8000-000000000003",
    "generator_fuel": "51000000-0000-4000-8000-000000000004",
    "diesel_vehicle": "51000000-0000-4000-8000-000000000005",
    "electric_vehicle": "51000000-0000-4000-8000-000000000006",
    "gasoline_car": "51000000-0000-4000-8000-000000000007",
    "bike": "51000000-0000-4000-8000-000000000008",
    "public_bus": "51000000-0000-4000-8000-000000000009",
    "electric_proxy": "51000000-0000-4000-8000-000000000010",
    "motorcycle": "51000000-0000-4000-8000-000000000011",
    "generator_pm25": "51000000-0000-4000-8000-000000000012",
    "generator_pm10": "51000000-0000-4000-8000-000000000013",
    "generator_nox": "51000000-0000-4000-8000-000000000014",
    "zero_pm25": "51000000-0000-4000-8000-000000000015",
    "zero_pm10": "51000000-0000-4000-8000-000000000016",
    "zero_nox": "51000000-0000-4000-8000-000000000017",
}


def _factor(
    key: str,
    impact: str,
    technology: str,
    basis: str,
    value: str,
    unit: str,
    source: str,
    url: str,
    year: int,
    methodology: str,
    pollutant: str | None = None,
) -> dict:
    return {
        "id": IDS[key],
        "impact_type": impact,
        "technology": technology,
        "pollutant": pollutant,
        "unit_basis": basis,
        "factor_value": value,
        "factor_unit": unit,
        "source": source,
        "source_url": url,
        "year": year,
        "country": "Chile" if "HuellaChile" in source else "International proxy",
        "methodology": methodology,
        "is_active": True,
    }


def upgrade() -> None:
    factor_table = sa.table(
        "environmental_factors",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("impact_type", sa.String()),
        sa.column("technology", sa.String()),
        sa.column("pollutant", sa.String()),
        sa.column("unit_basis", sa.String()),
        sa.column("factor_value", sa.Numeric()),
        sa.column("factor_unit", sa.String()),
        sa.column("source", sa.Text()),
        sa.column("source_url", sa.Text()),
        sa.column("year", sa.Integer()),
        sa.column("country", sa.String()),
        sa.column("methodology", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    huella = "HuellaChile, Reglas de contabilidad para proyectos de reducción V02"
    op.bulk_insert(
        factor_table,
        [
            _factor(
                "grid",
                "CO2E",
                "Electricidad SEN Chile 2024",
                "ENERGY_KWH",
                "0.2021",
                "kgCO2e/kWh",
                huella,
                HUELLA_URL,
                2024,
                "Factor oficial de electricidad importada, tablas 21, 23, 27 y 31.",
            ),
            _factor(
                "solar",
                "CO2E",
                "Generación solar fotovoltaica operacional",
                "ENERGY_KWH",
                "0",
                "kgCO2e/kWh",
                huella,
                HUELLA_URL,
                2025,
                "Emisiones operacionales del escenario proyecto, tabla 7; no representa ciclo de vida.",
            ),
            _factor(
                "generator",
                "CO2E",
                "Grupo electrógeno diésel, 3 kWh/L",
                "ENERGY_KWH",
                "0.9033333333",
                "kgCO2e/kWh",
                huella,
                HUELLA_URL,
                2024,
                "Derivado de 2,71 kgCO2e/L y rendimiento 3 kWh/L del caso Electromovilidad III.",
            ),
            _factor(
                "generator_fuel",
                "FUEL",
                "Consumo grupo electrógeno diésel, 3 kWh/L",
                "ENERGY_KWH",
                "0.3333333333",
                "L/kWh",
                huella,
                HUELLA_URL,
                2024,
                "Inverso del rendimiento documentado de 3 kWh/L.",
            ),
            _factor(
                "diesel_vehicle",
                "CO2E",
                "Vehículo diésel, 13,8 km/L",
                "DISTANCE_KM",
                "0.1985507246",
                "kgCO2e/km",
                huella,
                HUELLA_URL,
                2024,
                "Derivado de 2,74 kgCO2e/L dividido por 13,8 km/L, caso Electromovilidad I.",
            ),
            _factor(
                "electric_vehicle",
                "CO2E",
                "Vehículo eléctrico con SEN Chile",
                "DISTANCE_KM",
                "0.050525",
                "kgCO2e/km",
                huella,
                HUELLA_URL,
                2024,
                "Derivado del caso Electromovilidad I: 3.000 kWh / 12.000 km por 0,2021 kgCO2e/kWh.",
            ),
            _factor(
                "gasoline_car",
                "CO2E",
                "Automóvil promedio a gasolina",
                "UNIT_DISTANCE",
                "0.244198",
                "kgCO2e/pasajero-km",
                "US EPA Greenhouse Gas Equivalencies Calculator",
                EPA_EQ_URL,
                2024,
                "Conversión de 3,93e-4 tCO2e/milla a kgCO2e/km; proxy internacional, sustituible por dato de flota.",
            ),
            _factor(
                "bike",
                "CO2E",
                "Bicicleta, emisiones operacionales",
                "UNIT_DISTANCE",
                "0",
                "kgCO2e/pasajero-km",
                "GHG Protocol project accounting boundary",
                EPA_EQ_URL,
                2024,
                "Cero emisiones operacionales directas; excluye fabricación, alimentación e infraestructura.",
            ),
            _factor(
                "public_bus",
                "CO2E",
                "Bus promedio por pasajero",
                "UNIT_DISTANCE",
                "0.044117",
                "kgCO2e/pasajero-km",
                "US EPA 2024 GHG Emission Factors Hub",
                EPA_HUB_URL,
                2024,
                "Conversión del factor 0,071 kgCO2/pasajero-milla; proxy internacional dependiente de ocupación.",
            ),
            _factor(
                "electric_proxy",
                "CO2E",
                "Movilidad eléctrica, proxy 3,6 km/kWh con SEN Chile",
                "UNIT_DISTANCE",
                "0.0561388889",
                "kgCO2e/km",
                "US DOE efficiency proxy + HuellaChile SEN 2024",
                EPA_EQ_URL,
                2024,
                "0,2021 kgCO2e/kWh dividido por 3,6 km/kWh. Usar solo si no existe consumo medido del equipo.",
            ),
            _factor(
                "motorcycle",
                "CO2E",
                "Motocicleta convencional promedio",
                "UNIT_DISTANCE",
                "0.238356",
                "kgCO2e/km",
                "US EPA 2024 GHG Emission Factors Hub",
                EPA_HUB_URL,
                2024,
                "CO2, CH4 y N2O por vehículo-milla convertidos a CO2e y a kilómetro; proxy internacional.",
            ),
            _factor(
                "generator_pm25",
                "PM25",
                "Grupo electrógeno diésel <600 hp",
                "ENERGY_KWH",
                "0.001341",
                "kgPM2.5/kWh",
                "US EPA AP-42 sección 3.3",
                AP42_URL,
                1996,
                "Proxy conservador: PM total 1 g/hp-h, tratado como PM2.5 y convertido a kg/kWh.",
                "PM2.5",
            ),
            _factor(
                "generator_pm10",
                "PM10",
                "Grupo electrógeno diésel <600 hp",
                "ENERGY_KWH",
                "0.001341",
                "kgPM10/kWh",
                "US EPA AP-42 sección 3.3",
                AP42_URL,
                1996,
                "Proxy conservador: PM total 1 g/hp-h, tratado como PM10 y convertido a kg/kWh.",
                "PM10",
            ),
            _factor(
                "generator_nox",
                "NOX",
                "Grupo electrógeno diésel <600 hp",
                "ENERGY_KWH",
                "0.018908",
                "kgNOx/kWh",
                "US EPA AP-42 sección 3.3",
                AP42_URL,
                1996,
                "14,1 gNOx/hp-h convertidos a kg/kWh; factor agregado con calificación C.",
                "NOx",
            ),
            _factor(
                "zero_pm25",
                "PM25",
                "Solución eléctrica/solar sin combustión local",
                "ENERGY_KWH",
                "0",
                "kgPM2.5/kWh",
                "Operational boundary (sin combustión in situ)",
                HUELLA_URL,
                2025,
                "Cero emisiones locales operacionales; no representa impactos aguas arriba de la red.",
                "PM2.5",
            ),
            _factor(
                "zero_pm10",
                "PM10",
                "Solución eléctrica/solar sin combustión local",
                "ENERGY_KWH",
                "0",
                "kgPM10/kWh",
                "Operational boundary (sin combustión in situ)",
                HUELLA_URL,
                2025,
                "Cero emisiones locales operacionales; no representa impactos aguas arriba de la red.",
                "PM10",
            ),
            _factor(
                "zero_nox",
                "NOX",
                "Solución eléctrica/solar sin combustión local",
                "ENERGY_KWH",
                "0",
                "kgNOx/kWh",
                "Operational boundary (sin combustión in situ)",
                HUELLA_URL,
                2025,
                "Cero emisiones locales operacionales; no representa impactos aguas arriba de la red.",
                "NOx",
            ),
        ],
    )

    methodology_table = sa.table(
        "environmental_methodologies",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("name", sa.String()),
        sa.column("action_type", sa.String()),
        sa.column("baseline_technology", sa.String()),
        sa.column("actual_technology", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("parameters", sa.JSON()),
        sa.column("is_active", sa.Boolean()),
    )

    def metrics(baseline: str, actual: str, basis: str, impacts=("CO2E",)) -> dict:
        return {
            impact: {
                "baseline_factor_id": IDS[
                    baseline if impact == "CO2E" else f"generator_{impact.lower()}"
                ],
                "actual_factor_id": IDS[actual if impact == "CO2E" else f"zero_{impact.lower()}"],
                "baseline_basis": basis,
                "actual_basis": basis,
            }
            for impact in impacts
        }

    methods = [
        (
            "01",
            "ELECTRIC_LIGHTING_TOWER",
            "Torre diésel vs torre eléctrica (energía medida)",
            "Grupo electrógeno diésel",
            "Torre conectada al SEN",
            "Compara igual energía útil. Incluye CO2e y emisiones locales AP-42; requiere kWh medidos.",
            metrics("generator", "grid", "ENERGY_KWH", ("CO2E", "PM25", "PM10", "NOX")),
            {"factor_id": IDS["generator_fuel"], "basis": "ENERGY_KWH"},
        ),
        (
            "02",
            "SOLAR_ENERGY",
            "Electricidad SEN vs generación solar",
            "Electricidad SEN Chile",
            "Paneles fotovoltaicos",
            "Caso oficial HuellaChile: energía solar generada desplaza electricidad de red; límite operacional.",
            metrics("grid", "solar", "ENERGY_KWH"),
            None,
        ),
        (
            "03",
            "ELECTRIC_VEHICLE",
            "Vehículo diésel vs vehículo eléctrico",
            "Vehículo diésel 13,8 km/L",
            "Vehículo eléctrico",
            "Caso oficial HuellaChile Electromovilidad I por distancia recorrida.",
            metrics("diesel_vehicle", "electric_vehicle", "DISTANCE_KM"),
            None,
        ),
        (
            "04",
            "ELECTRIC_CART",
            "Vehículo convencional vs carrito eléctrico (proxy)",
            "Automóvil promedio a gasolina",
            "Movilidad eléctrica",
            "Proxy internacional para prueba; reemplazar por rendimiento específico del carrito cuando esté disponible.",
            metrics("gasoline_car", "electric_proxy", "UNIT_DISTANCE"),
            None,
        ),
        (
            "05",
            "ELECTRIC_MOTORCYCLE",
            "Motocicleta convencional vs moto eléctrica (proxy)",
            "Motocicleta convencional promedio",
            "Movilidad eléctrica",
            "Proxy internacional para prueba; reemplazar por consumo certificado del modelo.",
            metrics("motorcycle", "electric_proxy", "UNIT_DISTANCE"),
            None,
        ),
        (
            "06",
            "BIKE_MOBILITY",
            "Automóvil individual vs bicicleta",
            "Automóvil promedio a gasolina",
            "Bicicleta",
            "Compara pasajero-km y considera únicamente emisiones operacionales.",
            metrics("gasoline_car", "bike", "UNIT_DISTANCE"),
            None,
        ),
        (
            "07",
            "PUBLIC_TRANSPORT",
            "Automóvil individual vs bus público",
            "Automóvil promedio a gasolina",
            "Bus promedio por pasajero",
            "Compara pasajero-km; factores EPA usados como proxy internacional por ocupación.",
            metrics("gasoline_car", "public_bus", "UNIT_DISTANCE"),
            None,
        ),
    ]
    op.bulk_insert(
        methodology_table,
        [
            {
                "id": f"52000000-0000-4000-8000-0000000000{suffix}",
                "name": name,
                "action_type": action_type,
                "baseline_technology": baseline,
                "actual_technology": actual,
                "description": description,
                "parameters": {
                    "metrics": metric_config,
                    **({"fuel_avoided": fuel} if fuel else {}),
                },
                "is_active": True,
            }
            for suffix, action_type, name, baseline, actual, description, metric_config, fuel in methods
        ],
    )

    equivalence_table = sa.table(
        "eco_equivalence_factors",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("metric_source", sa.String()),
        sa.column("factor", sa.Numeric()),
        sa.column("unit", sa.String()),
        sa.column("source", sa.Text()),
        sa.column("year", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        equivalence_table,
        [
            {
                "id": "53000000-0000-4000-8000-000000000001",
                "key": "GASOLINE_LITERS",
                "name": "Litros de gasolina no consumidos",
                "metric_source": "CO2E_AVOIDED_KG",
                "factor": "0.4251437",
                "unit": "L/kgCO2e",
                "source": "US EPA: 8.887 kgCO2 por galón de gasolina; convertido a litros",
                "year": 2024,
                "is_active": True,
            },
            {
                "id": "53000000-0000-4000-8000-000000000002",
                "key": "FOREST_ACRE_YEAR",
                "name": "Acres de bosque estadounidense capturando CO2 durante un año",
                "metric_source": "CO2E_AVOIDED_KG",
                "factor": "0.001",
                "unit": "acre-año/kgCO2e",
                "source": "US EPA: 1,00 tonelada CO2 por acre-año; equivalencia contextual, no compensación",
                "year": 2024,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute("delete from eco_equivalence_factors where id::text like '53000000-%'")
    op.execute("delete from environmental_methodologies where id::text like '52000000-%'")
    op.execute("delete from environmental_factors where id::text like '51000000-%'")
