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
