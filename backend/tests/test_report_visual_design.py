from app.schemas.report_schema import ReportEditorialConfig
from app.services.report_render_service import _editable_attr
from app.services.report_visual_design_service import icon_svg, normalized, section_enrichment


def test_visual_config_is_controlled_and_defaults_to_original_design():
    config = ReportEditorialConfig()
    assert config.visual_config.preset == "AUTO"
    assert config.section_visuals == {}
    assert normalized(None)["preset"] == "AUTO"


def test_internal_icon_allowlist_never_renders_input_as_markup():
    rendered = icon_svg('<script>alert("x")</script>')
    assert "script" not in rendered
    assert rendered.startswith('<svg aria-hidden="true"')


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
