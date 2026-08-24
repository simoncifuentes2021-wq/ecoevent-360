"""Local visual fixture for the five premium section renderer variants."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from app.services.report_pdf_service import render
from app.services.report_render_service import ReportRenderDocument, theme_for_template
from scripts.generate_report_pdf_fixtures import _image

OUTPUT = Path("../artifacts/report-section-premium-v1")


def field(key: str, label: str, value, unit: str = "") -> dict:
    return {"key": key, "label": label, "value": value, "auto_value": value, "unit": unit, "is_visible": True, "is_overridden": False, "source": "VISUAL_TEST_FIXTURE"}


def section(key: str, kind: str, title: str, fields: list[dict], items: list[dict], text: str) -> dict:
    return {"section_key": key, "section_type": kind, "title": title, "layout_variant": "EDITORIAL", "is_enabled": True, "sort_order": len(SECTIONS), "content": {"text": text, "fields": fields, "items": items}, "source_snapshot": {}, "source_metadata": {"availability": "AVAILABLE", "source_scope": "TEST_FIXTURE"}}


SECTIONS: list[dict] = []
SECTIONS.append(section("event-info", "EVENT_INFO", "Datos del evento", [field("name", "Nombre", "Festival Sustentable de Santiago 2026"), field("type", "Tipo", "Festival cultural"), field("location", "Ubicación", "Parque Metropolitano"), field("city", "Ciudad", "Santiago"), field("start_date", "Inicio", "12 mayo 2026"), field("end_date", "Término", "14 mayo 2026"), field("estimated_attendees", "Asistencia estimada", 12500, "attendees"), field("real_attendees", "Asistencia real", 11840, "attendees")], [], "Tres jornadas que integraron cultura, movilidad activa y gestión ambiental medible."))
SECTIONS.append(section("bike-zone", "BIKE_ZONE", "Bike Zone", [field("users", "Usuarios registrados", 486), field("checked_in", "Ingresos confirmados", 451), field("participation_rate", "Participación", 92.8, "%")], [{"label": "Show apertura", "value": 128}, {"label": "Show central", "value": 214}, {"label": "Show cierre", "value": 144}], "La operación facilitó una alternativa de movilidad activa para asistentes y equipos."))
SECTIONS.append(section("waste", "WASTE", "Gestión de residuos", [field("total", "Residuos totales", 4280.75, "kg"), field("recovery_rate", "Tasa de valorización", 76.4, "%")], [{"label": "Vidrio", "value": 1480.5, "unit": "kg"}, {"label": "Cartón", "value": 1125.25, "unit": "kg"}, {"label": "PET", "value": 940, "unit": "kg"}, {"label": "Aluminio", "value": 520.75, "unit": "kg"}], "La segregación en origen permitió priorizar los materiales con mayor potencial de recuperación."))
SECTIONS.append(section("carbon", "CARBON", "Huella de carbono", [field("total", "Emisiones totales", 363.2235937004225, "kgCO2e"), field("intensity", "Intensidad por asistente", 0.030677, "kgCO2e")], [{"label": "Transporte", "value": 184.82, "unit": "kgCO2e"}, {"label": "Energía", "value": 96.4, "unit": "kgCO2e"}, {"label": "Residuos", "value": 52.75, "unit": "kgCO2e"}, {"label": "Operación", "value": 29.2535937, "unit": "kgCO2e"}], "Cálculo consolidado desde las categorías registradas en el inventario del evento."))
SECTIONS.append(section("environmental-impact", "ENVIRONMENTAL_IMPACT", "Impacto ambiental evitado", [field("energy_kwh", "Energía generada", 0.75000000, "kWh"), field("fuel_avoided_l", "Diésel evitado", 0.2235937004225, "L"), field("co2e_baseline_kg", "CO₂e línea base", 0.68, "kg"), field("co2e_actual_kg", "CO₂e escenario real", 0.15, "kg"), field("co2e_avoided_kg", "CO₂e evitado", 0.53, "kg"), field("pm25_avoided_kg", "PM2.5 evitado", 0.000525925, "kg"), field("pm10_avoided_kg", "PM10 evitado", 0.00142, "kg")], [{"label": "Acción solar aprobada"}, {"label": "Sustitución de diésel aprobada"}], "Resultados provenientes exclusivamente de acciones ambientales aprobadas y factores documentados."))


def fixture(preset: str) -> ReportRenderDocument:
    cover = {"section_key": "cover", "section_type": "COVER", "title": "Portada", "layout_variant": "HERO_IMAGE_TEXT", "is_enabled": True, "sort_order": -1, "content": {"text": "Memoria de sostenibilidad", "fields": []}}
    evidences = tuple({"evidence_id": f"local-{index}", "section_key": key, "caption": caption, "uri": _image(index), "warning": None} for index, (key, caption) in enumerate((("event-info", "Vista general del festival"), ("bike-zone", "Operación de movilidad activa"), ("waste", "Punto limpio del evento"))))
    return ReportRenderDocument(report={"id": "section-premium-v1", "title": "Festival Sustentable 2026", "scope": "EVENT", "template_key": "COMPLETE"}, event={"id": "event", "name": "Festival Sustentable 2026", "date": "12—14 mayo 2026"}, show=None, client={"id": "client", "name": "Cliente de prueba visual"}, theme=theme_for_template("COMPLETE", {}), sections=tuple([cover, *SECTIONS]), evidences=evidences, publication={"number": 1}, editorial_config={"visual_config": {"preset": preset}})


def write_pdf(name: str, preset: str) -> bytes:
    pdf, _ = render(fixture(preset))
    (OUTPUT / name).write_bytes(pdf)
    return pdf


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    auto = write_pdf("full-report-auto.pdf", "AUTO")
    environmental = write_pdf("full-report-environmental.pdf", "ENVIRONMENTAL")
    write_pdf("full-report-executive.pdf", "EXECUTIVE")
    before, after = pymupdf.open(stream=auto, filetype="pdf"), pymupdf.open(stream=environmental, filetype="pdf")
    page_map = {"event-info": 1, "environmental-impact": 2, "waste": 3, "carbon": 4, "bike-zone": 5}
    for name, index in page_map.items():
        folder = OUTPUT / name
        folder.mkdir(exist_ok=True)
        before[index].get_pixmap(matrix=pymupdf.Matrix(1.35, 1.35), alpha=False).save(folder / "before.png")
        after[index].get_pixmap(matrix=pymupdf.Matrix(1.35, 1.35), alpha=False).save(folder / "after.png")
        single = pymupdf.open()
        single.insert_pdf(after, from_page=index, to_page=index)
        single.save(folder / "after.pdf")
    print(f"Generated {len(page_map)} before/after section comparisons in {OUTPUT}")


if __name__ == "__main__":
    main()
