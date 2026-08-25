from app.schemas.report_schema import ReportEditorialConfig
from app.services.report_render_service import _editable_attr
from app.services.report_render_service import _premium_page_html
from app.services.report_visual_design_service import (
    SECTION_ICONS,
    format_metric,
    icon_svg,
    normalized,
    section_enrichment,
    section_variant,
)


def test_visual_config_is_controlled_and_defaults_to_original_design():
    config = ReportEditorialConfig()
    assert config.visual_config.preset == "AUTO"
    assert config.section_visuals == {}
    assert normalized(None)["preset"] == "AUTO"


def test_internal_icon_allowlist_never_renders_input_as_markup():
    rendered = icon_svg('<script>alert("x")</script>')
    assert "script" not in rendered
    assert rendered.startswith('<svg aria-hidden="true"')
    assert SECTION_ICONS["INCIDENTS"] == "ALERT"
    assert SECTION_ICONS["TASKS"] == "CHECK"
    assert SECTION_ICONS["FORMS"] == "CHART"


def test_auto_is_byte_neutral_and_preset_uses_official_visible_data():
    section = {
        "section_key": "environmental-impact",
        "section_type": "ENVIRONMENTAL_IMPACT",
        "title": "Impacto ambiental",
        "content": {
            "fields": [
                {"key": "energy", "label": "Energía evitada", "value": "125", "unit": "kWh"},
                {"key": "hidden", "label": "Oculto", "value": "999", "is_visible": False},
            ],
            "items": [{"label": "Resultado aprobado"}],
        },
    }
    assert section_enrichment(section, normalized(None), None, _editable_attr) == ""
    html = section_enrichment(section, normalized({"preset": "IMPACT"}), None, _editable_attr)
    assert "125" in html and "Energía evitada" in html
    assert "999" not in html and "Oculto" not in html
    assert 'data-report-element-key="section.environmental-impact.insight.main"' in html


def test_preset_selects_internal_section_variants_without_changing_auto():
    assert section_variant("AUTO", "WASTE") is None
    assert section_variant("ENVIRONMENTAL", "WASTE") == "WASTE_CIRCULARITY"
    assert section_variant("ENVIRONMENTAL", "CARBON") == "CARBON_FOOTPRINT"
    assert section_variant("BIKE_ZONE", "WASTE") is None
    assert section_variant("BIKE_ZONE", "BIKE_ZONE") == "BIKE_ZONE_MOBILITY"


def test_metric_formatting_is_human_readable_and_keeps_small_precision():
    assert format_metric("0.75000000", "kWh") == "0,75"
    assert format_metric("0.223593700422500000", "L") == "0,22"
    assert format_metric("100.0", "kgCO2e") == "100"
    assert format_metric("0.000525925") == "0,00053"


def test_premium_page_replaces_content_with_editable_internal_section_blocks():
    waste = {
        "section_key": "waste", "section_type": "WASTE", "title": "Residuos",
        "content": {"fields": [{"key": "total", "label": "Total", "value": "20.5000", "unit": "kg"}], "items": [{"label": "Vidrio", "value": "12.25", "unit": "kg"}]},
    }
    html = _premium_page_html([waste], [], {"accent_color": "#95D5B2"}, normalized({"preset": "ENVIRONMENTAL"}))
    assert "premium-waste" in html
    assert "premium-insight" not in html
    assert 'data-report-element-key="section.waste.hero"' in html
    assert 'data-report-element-key="section.waste.recovery"' in html


def test_bike_zone_zero_uses_professional_empty_state():
    bike = {"section_key": "bike-zone", "section_type": "BIKE_ZONE", "title": "Bike Zone", "content": {"fields": [{"key": "users", "label": "Usuarios", "value": 0}], "items": []}}
    html = _premium_page_html([bike], [], {"accent_color": "#95D5B2"}, normalized({"preset": "BIKE_ZONE"}))
    assert "No se registraron usuarios" in html
    assert "premium-empty-state" in html


def test_premium_renderer_keeps_and_enriches_siblings_on_grouped_pages():
    bike = {"section_key": "bike-zone", "section_type": "BIKE_ZONE", "title": "Bike Zone", "content": {"fields": [{"key": "users", "label": "Usuarios", "value": 12}], "items": []}}
    evidences = {"section_key": "evidences", "section_type": "EVIDENCES", "title": "Evidencias", "content": {"text": "Galería del evento", "fields": [], "items": []}}

    html = _premium_page_html(
        [bike, evidences],
        [{"uri": "data:image/png;base64,audit", "caption": "Evidencia"}],
        {"accent_color": "#95D5B2"},
        normalized({"preset": "BIKE_ZONE"}),
    )

    assert "premium-page-sections" in html
    assert "BIKE ZONE" in html.upper()
    assert "Historia visual" in html
    assert 'src="data:image/png;base64,audit"' in html


def test_all_remaining_sections_have_controlled_premium_variants():
    expected = {
        "EXECUTIVE_SUMMARY": "EXECUTIVE_SUMMARY_PREMIUM",
        "SHOW_INFO": "SHOW_INFO_EDITORIAL",
        "SERVICES": "SERVICES_OVERVIEW",
        "OPERATIONS": "OPERATIONS_STORY",
        "STAFF": "STAFF_OVERVIEW",
        "TASKS": "TASKS_PERFORMANCE",
        "INCIDENTS": "INCIDENTS_OVERVIEW",
        "FORMS": "FORMS_INSIGHTS",
        "EVIDENCES": "EVIDENCE_STORY",
        "RECOMMENDATIONS": "RECOMMENDATIONS_ACTION_PLAN",
        "CONCLUSION": "CONCLUSION_EDITORIAL",
    }
    for preset in ("ECOEVENT_EDITORIAL", "EXECUTIVE", "ENVIRONMENTAL", "BIKE_ZONE", "IMPACT"):
        for section_type, variant in expected.items():
            assert section_variant(preset, section_type) == variant
    for section_type in expected:
        assert section_variant("AUTO", section_type) is None


def test_premium_presets_have_distinct_controlled_tone_classes():
    section = {"section_key": "services", "section_type": "SERVICES", "title": "Servicios", "content": {"fields": [], "items": [{"name": "Accesos", "quantity": 4}]}}
    rendered = {
        preset: _premium_page_html([section], [], {"accent_color": "#95D5B2"}, normalized({"preset": preset}))
        for preset in ("ECOEVENT_EDITORIAL", "EXECUTIVE", "ENVIRONMENTAL", "BIKE_ZONE", "IMPACT")
    }
    assert len(set(rendered.values())) == 5
    for preset, html in rendered.items():
        assert f"premium-tone-{preset.lower()}" in html


def test_staff_premium_uses_only_aggregate_fields():
    staff = {
        "section_key": "staff", "section_type": "STAFF", "title": "Equipo",
        "content": {"fields": [{"key": "total", "label": "Personas", "value": 8}, {"key": "email", "label": "Email", "value": "private@example.test"}], "items": [{"role": "Producción", "count": 8}, {"name": "Persona privada", "phone": "+56 9 0000 0000"}]},
    }
    html = _premium_page_html([staff], [], {"accent_color": "#95D5B2"}, normalized({"preset": "EXECUTIVE"}))
    assert "8" in html and "Producción" in html
    assert "email" not in html.lower() and "phone" not in html.lower()
    assert "private@example.test" not in html and "Persona privada" not in html


def test_forms_premium_never_renders_individual_answers():
    forms = {"section_key": "forms", "section_type": "FORMS", "title": "Formularios", "content": {"fields": [{"key": "responses", "label": "Respuestas", "value": 12}], "items": [{"name": "Persona privada", "answer": "Respuesta privada"}]}}
    html = _premium_page_html([forms], [], {"accent_color": "#95D5B2"}, normalized({"preset": "EXECUTIVE"}))
    assert "12" in html
    assert "Persona privada" not in html and "Respuesta privada" not in html


def test_zero_operational_sections_use_truthful_empty_states():
    for section_type, expected in (("TASKS", "No hay tareas registradas"), ("INCIDENTS", "No se registraron incidencias"), ("FORMS", "No existen respuestas registradas")):
        key = section_type.lower()
        field_key = "responses" if section_type == "FORMS" else "total"
        section = {"section_key": key, "section_type": section_type, "title": key, "content": {"fields": [{"key": field_key, "label": "Total", "value": 0}], "items": []}}
        html = _premium_page_html([section], [], {"accent_color": "#95D5B2"}, normalized({"preset": "EXECUTIVE"}))
        assert expected in html


def test_carbon_premium_renders_assigned_evidence():
    carbon = {
        "section_key": "carbon",
        "section_type": "CARBON",
        "title": "Huella de carbono",
        "content": {
            "fields": [{"key": "total", "label": "Emisiones totales", "value": 120, "unit": "kgCO2e"}],
            "items": [{"label": "Transporte", "value": 80, "unit": "kgCO2e"}],
        },
    }

    html = _premium_page_html(
        [carbon],
        [{"uri": "data:image/png;base64,audit", "caption": "Medición"}],
        {"accent_color": "#95D5B2"},
        normalized({"preset": "ENVIRONMENTAL"}),
    )

    assert 'class="premium-carbon-photo"' in html
    assert 'src="data:image/png;base64,audit"' in html
