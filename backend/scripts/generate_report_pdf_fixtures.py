"""Generate local-only visual certification fixtures for Stage 2B."""

import base64
from hashlib import sha256
from pathlib import Path

import fitz

from app.services.report_pdf_service import render
from app.services.report_render_service import ReportRenderDocument, theme_for_template

OUTPUT = Path(".tmp/pdf-certification")
SECTION_SPECS = [
    ("event", "EVENT_INFO", "HERO_IMAGE_TEXT", "Una operación que deja huella positiva"),
    ("summary", "EXECUTIVE_SUMMARY", "KPI_GRID", "Resumen ejecutivo"),
    ("waste", "WASTE", "TWO_COLUMN", "Circularidad en acción"),
    ("materials", "SERVICES", "METRIC_LIST", "Materiales recuperados"),
    ("carbon", "CARBON", "FEATURE_CHART", "Huella de carbono"),
    ("evidence", "EVIDENCES", "PHOTO_GRID", "La experiencia, documentada"),
    ("method", "FORMS", "EDITORIAL", "Metodología y trazabilidad"),
    ("bike", "BIKE_ZONE", "TEXT_IMAGE", "Bike Zone"),
    ("conclusion", "CONCLUSION", "BIG_NUMBERS", "Una plataforma para seguir avanzando"),
]


def _image(seed: int) -> str:
    colors = [
        ("12372A", "95D5B2"),
        ("0B4F6C", "01BAEF"),
        ("4C1D95", "F59E0B"),
        ("713F12", "84CC16"),
    ]
    first, second = colors[seed % len(colors)]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800"><defs><linearGradient id="g"><stop stop-color="#{first}"/><stop offset="1" stop-color="#{second}"/></linearGradient></defs><rect width="1200" height="800" fill="url(#g)"/><circle cx="{220 + seed * 120}" cy="260" r="190" fill="#fff" opacity=".16"/><path d="M0 650 Q300 430 600 650 T1200 610 V800 H0Z" fill="#fff" opacity=".2"/></svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def document(template: str, title: str, show: str | None = None) -> ReportRenderDocument:
    sections = tuple(
        {
            "section_key": key,
            "section_type": section_type,
            "title": section_title,
            "layout_variant": variant,
            "is_enabled": True,
            "sort_order": index,
            "content": {
                "text": "EcoEvent 360 transforma datos operativos y ambientales en decisiones claras, medibles y accionables.",
                "fields": [
                    {"label": "Huella", "value": 363, "unit": "tCO2e"},
                    {"label": "Residuos", "value": 12548, "unit": "kg"},
                    {"label": "Recuperación", "value": 68, "unit": "%"},
                    {"label": "Bicicletas", "value": 238, "unit": ""},
                ],
                "items": [
                    {"label": "Botellas PET", "value": 7104, "description": "Material recuperado durante la operación ambiental."},
                    {"label": "Aluminio", "value": 3293, "description": "Indicador trazable consolidado al cierre del evento."},
                    {"label": "Vidrio", "value": 26.1, "description": "Resultado medido y validado por el equipo en terreno."},
                    {"label": "Cartón", "value": 12.6, "description": "Impacto asociado a la gestión responsable del evento."},
                ],
            },
        }
        for index, (key, section_type, variant, section_title) in enumerate(SECTION_SPECS)
    )
    evidences = tuple(
        {
            "evidence_id": f"photo-{index}",
            "section_key": key,
            "caption": caption,
            "uri": _image(index),
            "warning": None,
        }
        for index, (key, caption) in enumerate(
            [
                ("event", "Vista general del recinto"),
                ("waste", "Operación de reciclaje"),
                ("evidence", "Equipo en terreno"),
                ("bike", "Movilidad activa y Bike Zone"),
            ]
        )
    )
    return ReportRenderDocument(
        report={
            "id": template,
            "title": title,
            "scope": "SHOW" if show else "EVENT",
            "template_key": template,
        },
        event={"id": "event", "name": "Hozier · Gestión Ambiental", "date": "06—08 agosto 2026"},
        show={"id": "show", "name": show} if show else None,
        client={"id": "client", "name": "DG Medios"},
        theme=theme_for_template(template, {}),
        sections=sections,
        evidences=evidences,
        publication={"number": 1},
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fixtures = [
        ("environmental-story.pdf", document("ENVIRONMENTAL_STORY", "Gestión Ambiental")),
        ("environmental-premium.pdf", document("ENVIRONMENTAL_PREMIUM", "Gestión Ambiental")),
        ("bike-zone.pdf", document("BIKE_ZONE", "Movilidad sostenible · Bike Zone")),
        (
            "complete-show.pdf",
            document("COMPLETE", "Memoria integral del evento", "Show principal"),
        ),
    ]
    for filename, item in fixtures:
        for stale in OUTPUT.glob(f"{Path(filename).stem}-p*.png"):
            stale.unlink()
        pdf, pages = render(item)
        path = OUTPUT / filename
        path.write_bytes(pdf)
        opened = fitz.open(stream=pdf, filetype="pdf")
        for index in range(pages):
            opened[index].get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).save(
                OUTPUT / f"{path.stem}-p{index + 1}.png"
            )
        print(filename, pages, len(pdf), sha256(pdf).hexdigest())


if __name__ == "__main__":
    main()
