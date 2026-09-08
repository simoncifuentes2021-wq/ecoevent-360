from app.models.enums import ReportSectionType
from app.services.ai.prompts.report_sections import SECTION_GUIDANCE, SECTION_GUIDANCE_VERSION, guidance_for


def test_every_report_section_type_has_specialized_guidance():
    assert SECTION_GUIDANCE_VERSION == "report_section_guidance_v1"
    assert {item.value for item in ReportSectionType} == set(SECTION_GUIDANCE)
    for kind in ReportSectionType:
        policy = guidance_for(kind.value, kind.value.lower())
        assert policy["policy_id"] == kind.value
        assert all(policy[key] for key in ("objective", "include_only_if_available", "must_not_include", "success_criteria"))


def test_waste_and_bike_zone_have_cross_domain_boundaries():
    waste = guidance_for("WASTE", "waste")
    bike = guidance_for("BIKE_ZONE", "bike_zone")
    assert "total gestionado o recuperado" in waste["include_only_if_available"]
    assert "tasa de valorización ya calculada" in waste["include_only_if_available"]
    assert "Bike Zone" in waste["must_not_include"]
    assert "residuos" in bike["must_not_include"]


def test_eco_equivalences_custom_section_gets_own_policy():
    policy = guidance_for("CUSTOM", "preset_eco_equivalences")
    assert policy["policy_id"] == "ECO_EQUIVALENCES"
    assert "calcular equivalencias" in policy["must_not_include"]
    assert "usa solo valores precomputados" in policy["success_criteria"]


def test_unknown_type_uses_safe_custom_policy():
    policy = guidance_for("FUTURE_MODULE", "future")
    assert policy["policy_id"] == "CUSTOM"
    assert "datos ajenos" in policy["must_not_include"]
