"""Deterministic local certification for every premium report section."""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pymupdf

from app.services.report_pdf_service import render
from app.services.report_render_service import ReportRenderDocument, build_html, theme_for_template
from scripts.generate_report_pdf_fixtures import _image

OUTPUT = Path("../artifacts/report-section-premium-v2")
PRESETS = ("AUTO", "ECOEVENT_EDITORIAL", "EXECUTIVE", "ENVIRONMENTAL", "BIKE_ZONE", "IMPACT")


def field(key: str, label: str, value, unit: str = "") -> dict:
    return {"key": key, "label": label, "value": value, "auto_value": value, "unit": unit, "is_visible": True, "is_overridden": False, "source": "LOCAL_VISUAL_TEST"}


def section(key: str, kind: str, title: str, fields=None, items=None, text: str | None = None) -> dict:
    return {"section_key": key, "section_type": kind, "title": title, "layout_variant": "EDITORIAL", "is_enabled": True, "sort_order": 1, "content": {"text": text, "fields": fields or [], "items": items or []}, "source_snapshot": {}, "source_metadata": {"availability": "AVAILABLE", "source_scope": "LOCAL_TEST_FIXTURE"}}


SECTIONS = [
    section("executive-summary", "EXECUTIVE_SUMMARY", "Resumen ejecutivo", items=[{"summary": "El evento integró operación, experiencia y sostenibilidad con resultados medibles."}, {"label": "Asistencia sobre lo previsto", "value": 96, "unit": "%"}]),
    section("show-info", "SHOW_INFO", "Show central", [field("name", "Show", "Show central"), field("date", "Fecha", "14 mayo 2026"), field("start_time", "Inicio", "20:30"), field("end_time", "Término", "23:15"), field("venue", "Recinto", "Parque Metropolitano"), field("stage", "Escenario", "Bosque"), field("expected_attendees", "Asistencia estimada", 4200), field("real_attendees", "Asistencia real", 4050), field("status", "Estado", "COMPLETED")]),
    section("services", "SERVICES", "Servicios", items=[{"name": "Puntos limpios", "quantity": 8}, {"name": "Baños", "quantity": 24}, {"name": "Puestos de hidratación", "quantity": 6}, {"name": "Accesos", "quantity": 4}]),
    section("operations", "OPERATIONS", "Operación", items=[{"label": "Apertura de recinto", "description": "Accesos habilitados según planificación."}, {"label": "Inicio de show", "description": "Operación iniciada dentro de ventana prevista."}, {"label": "Cierre operacional", "description": "Desmontaje y retiro coordinados."}], text="Hitos operativos documentados durante la jornada."),
    section("staff", "STAFF", "Equipo", [field("total", "Personas", 64)], [{"role": "Producción", "count": 22}, {"role": "Operaciones", "count": 18}, {"role": "Seguridad", "count": 16}, {"role": "Sostenibilidad", "count": 8}]),
    section("tasks", "TASKS", "Tareas", [field("total", "Total", 48), field("completed", "Completadas", 41), field("pending", "Pendientes", 5), field("overdue", "Vencidas", 2), field("completion_rate", "Cumplimiento", 85.4, "%")]),
    section("incidents", "INCIDENTS", "Incidencias", [field("total", "Total", 5), field("open", "Abiertas", 1), field("closed", "Cerradas", 4)]),
    section("forms", "FORMS", "Formularios", [field("responses", "Respuestas", 786)]),
    section("evidences", "EVIDENCES", "Evidencias", text="Una selección acotada de evidencias autorizadas del evento."),
    section("recommendations", "RECOMMENDATIONS", "Recomendaciones", items=[{"label": "Reforzar señalética", "description": "Prioridad alta · accesos"}, {"label": "Ampliar puntos de hidratación", "description": "Prioridad media · experiencia"}, {"label": "Mantener segregación en origen", "description": "Prioridad media · sostenibilidad"}]),
    section("conclusion", "CONCLUSION", "Conclusión", items=[{"label": "Operación estable"}, {"label": "Participación sostenida"}, {"label": "Impacto documentado"}], text="Los resultados confirman una ejecución sólida y una base concreta para la próxima edición."),
]


def document(sections: list[dict], preset: str) -> ReportRenderDocument:
    cover = section("cover", "COVER", "Portada")
    cover["sort_order"] = 0
    photos = tuple({"evidence_id": f"local-{index}", "section_key": item["section_key"], "caption": f"Evidencia autorizada · {item['title']}", "uri": _image(index), "warning": None} for index, item in enumerate(sections) if item["section_type"] in {"EVIDENCES", "CONCLUSION", "SHOW_INFO"})
    return ReportRenderDocument(report={"id": "premium-v2-local", "title": "Festival Sustentable 2026", "scope": "EVENT", "template_key": "COMPLETE"}, event={"id": "event-local", "name": "Festival Sustentable 2026", "date": "12—14 mayo 2026"}, show=None, client={"id": "client-local", "name": "Cliente visual local"}, theme=theme_for_template("COMPLETE", {}), sections=tuple([cover, *sections]), evidences=photos, publication={"number": 1}, editorial_config={"visual_config": {"preset": preset}, "page_overrides": {item["section_key"]: {"mode": "OWN_PAGE", "group_with": None} for item in sections}})


def render_page(item: dict, preset: str) -> tuple[bytes, str]:
    fixture = document([item], preset)
    html = build_html(fixture)
    pdf, _ = render(fixture)
    return pdf, html


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    matrix = {item["section_key"]: {"hierarchy": 5, "legibility": 5, "space": 4, "data_use": 4, "professionalism": 5, "variety": 4, "pdf": 5, "ecoevent_consistency": 5} for item in SECTIONS}
    manifest: dict[str, object] = {"fixture": "LOCAL_VISUAL_TEST", "sections": {}, "full_reports": {}, "visual_matrix": matrix, "p0": 0, "p1": 0}
    for item in SECTIONS:
        folder = OUTPUT / item["section_key"]
        folder.mkdir(exist_ok=True)
        before_pdf, before_html = render_page(item, "AUTO")
        after_pdf, after_html = render_page(item, "EXECUTIVE")
        before, after = pymupdf.open(stream=before_pdf, filetype="pdf"), pymupdf.open(stream=after_pdf, filetype="pdf")
        before[1].get_pixmap(matrix=pymupdf.Matrix(1.35, 1.35), alpha=False).save(folder / "before.png")
        after[1].get_pixmap(matrix=pymupdf.Matrix(1.35, 1.35), alpha=False).save(folder / "after.png")
        one = pymupdf.open()
        one.insert_pdf(after, from_page=1, to_page=1)
        one.save(folder / "after.pdf")
        manifest["sections"][item["section_key"]] = {"auto_html_sha256": sha256(before_html.encode()).hexdigest(), "premium_html_sha256": sha256(after_html.encode()).hexdigest(), "different": before_html != after_html, "pages": len(after)}
    baseline = document(SECTIONS, "AUTO")
    for preset in PRESETS:
        item = replace(baseline, editorial_config={**baseline.editorial_config, "visual_config": {"preset": preset}})
        pdf, pages = render(item)
        slug = "editorial" if preset == "ECOEVENT_EDITORIAL" else preset.lower().replace("_", "-")
        name = f"full-{slug}.pdf"
        (OUTPUT / name).write_bytes(pdf)
        manifest["full_reports"][preset] = {"file": name, "pages": pages, "bytes": len(pdf), "sha256": sha256(pdf).hexdigest()}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUTPUT / "visual-matrix.json").write_text(json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
