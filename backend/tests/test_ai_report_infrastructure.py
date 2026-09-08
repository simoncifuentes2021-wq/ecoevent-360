import json
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.core.config import settings
from app.services.ai.ai_router import build_provider, build_report_provider
from app.services.ai.comparison_service import compare
from app.services.ai.premium_grounding import validate_premium_proposal
from app.services.ai.pricing import PricingRegistry
from app.services.ai.usage_service import ensure_report_budget
from decimal import Decimal
from app.services.ai.privacy import sanitize
from app.services.ai.providers.base import AIProviderError
from app.services.ai.providers.openai_responses import OpenAIResponsesProvider
from app.services.ai.providers.openrouter import OpenRouterProvider
from app.services.ai.schemas import ProviderRequest, ReportAIAssistantProposal
from app.services.ai import report_assistant_service
from app.services.ai.model_policy import resolve_report_model, visual_audit_model


def test_general_and_report_provider_routing_are_independent():
    config = settings.model_copy(update={
        "ai_provider": "openrouter", "ai_api_key": "general-test-key",
        "ai_report_provider": "openai", "ai_report_api_key": "report-test-key",
    })
    assert isinstance(build_provider(config), OpenRouterProvider)
    assert isinstance(build_report_provider(config), OpenAIResponsesProvider)
    assert build_provider(config).api_key == "general-test-key"
    assert build_report_provider(config).api_key == "report-test-key"


def test_report_key_uses_documented_openai_fallback_only():
    config = settings.model_copy(update={
        "ai_report_provider": "openai", "ai_report_api_key": None,
        "openai_api_key": "fallback-test-key", "ai_api_key": "must-not-be-used",
    })
    assert build_report_provider(config).api_key == "fallback-test-key"


def test_report_model_policy_routes_fast_editorial_and_optional_audit_models():
    config = settings.model_copy(update={
        "ai_model": "fallback", "ai_report_model": "base-report",
        "ai_report_fast_model": "fast-report", "ai_report_editorial_model": "editorial-report",
        "ai_report_audit_model": "audit-report", "ai_report_max_output_tokens": 4000,
        "ai_report_fast_max_output_tokens": 1200, "ai_report_editorial_max_output_tokens": 5000,
    })
    fast = resolve_report_model(config, "reports.section_draft")
    editorial = resolve_report_model(config, "reports.premium_assistant")
    director = resolve_report_model(config, "reports.editorial_plan")
    assert (fast.model, fast.max_output_tokens, fast.tier) == ("fast-report", 1200, "FAST")
    assert (editorial.model, editorial.max_output_tokens, editorial.tier) == ("editorial-report", 5000, "EDITORIAL")
    assert director == editorial
    assert visual_audit_model(config) == "audit-report"


def test_report_model_policy_preserves_legacy_model_fallback():
    config = settings.model_copy(update={
        "ai_report_model": "legacy-report", "ai_report_fast_model": None,
        "ai_report_editorial_model": None, "ai_report_audit_model": None,
    })
    assert resolve_report_model(config, "reports.section_draft").model == "legacy-report"
    assert resolve_report_model(config, "reports.premium_assistant").model == "legacy-report"
    assert visual_audit_model(config) is None


def test_privacy_sanitizes_keys_and_free_text():
    result = sanitize({"email": "hidden@example.com", "note": "Contactar a visible@example.com o +56 9 1234 5678", "private_url": "https://private.test/x?token=secret"})
    assert "email" not in result
    assert result["note"] == "Contactar a [EMAIL] o [PHONE]"
    assert "private_url" not in result
    assert sanitize("e19d9e23-c253-4554-8280-53f010b1f6b1") == "e19d9e23-c253-4554-8280-53f010b1f6b1"


def test_privacy_does_not_confuse_decimal_measurements_with_phone_numbers():
    value = sanitize("31.68000000 kg CO2e y 36.00000000 kWh")
    assert value == "31.68000000 kg CO2e y 36.00000000 kWh"
    assert sanitize("Contacto 9876 5432") == "Contacto [PHONE]"


def test_deterministic_comparison_never_needs_model_math():
    assert compare(100, 150) == {"baseline": 100.0, "comparison": 150.0, "absolute_difference": 50.0, "percentage_difference": 50.0, "percentage_point_change": None, "trend": "UP"}


def test_pricing_is_configuration_driven():
    registry = PricingRegistry(json.dumps({"openai:test": {"input": 1, "cached_input": 0.5, "output": 2}}))
    assert registry.get("openai", "test").cost(1000, 500, 200) > 0
    assert registry.get("openai", "unknown") is None


def test_official_luna_pricing_including_cached_input():
    price = PricingRegistry().get("openai", "gpt-5.6-luna")
    assert price.cost(10_000, 2_000) == Decimal("0.0044")
    assert price.cost(10_000, 2_000, 4_000) == Decimal("0.00368")


def test_report_budget_allows_exact_limit_and_blocks_overage():
    ensure_report_budget(Decimal("9.9956"), Decimal("0.0044"), Decimal("10"))
    with pytest.raises(RuntimeError, match="REPORT_AI_BUDGET_EXCEEDED"):
        ensure_report_budget(Decimal("9.9957"), Decimal("0.0044"), Decimal("10"))


def proposal(report_id, *, source_key="waste.total_kg", unit_text="Se gestionaron 100 kg"):
    return ReportAIAssistantProposal.model_validate({
        "version": "1", "report_id": str(report_id), "recommended_preset": "ENVIRONMENTAL",
        "rationale": "Propuesta grounded", "estimated_pages": 5,
        "sections": [{"section_key": "waste", "visible": True, "order": 0, "premium_variant": "WASTE_CIRCULARITY", "emphasis": "HIGH", "narrative": None, "findings": [{"text": unit_text, "source_keys": [source_key]}], "selected_metric_keys": [source_key], "selected_evidence_ids": []}],
        "executive_summary": [], "key_findings": [], "recommendations": [], "conclusion": [],
        "evidence_suggestions": [], "warnings": [], "source_keys": [source_key],
    })


def grounding_context(report_id):
    return {"current": {"report_id": str(report_id)}, "allowlists": {"section_keys": ["waste"], "presets": ["AUTO", "ENVIRONMENTAL"], "premium_variants": ["AUTO", "WASTE_CIRCULARITY"], "variants_by_preset": {"ENVIRONMENTAL": {"waste": "WASTE_CIRCULARITY"}}}, "sources": {"waste.total_kg": {"value": 100, "unit": "kg", "source": "waste"}}, "evidences": []}


def test_grounding_rejects_unknown_source_and_unit_conversion():
    report_id = uuid4()
    context = grounding_context(report_id)
    validate_premium_proposal(proposal(report_id), context)
    with pytest.raises(AIProviderError, match="unknown metric"):
        validate_premium_proposal(proposal(report_id, source_key="waste.unknown"), context)
    with pytest.raises(AIProviderError, match="unit"):
        validate_premium_proposal(proposal(report_id, unit_text="Se gestionaron 100 t"), context)


def test_premium_section_grouping_is_structured_and_grounded():
    report_id = uuid4()
    payload = proposal(report_id).model_dump(mode="json")
    payload["sections"][0].update({"page_mode": "GROUP_WITH", "group_with": "missing"})
    with pytest.raises(AIProviderError, match="grouping"):
        validate_premium_proposal(ReportAIAssistantProposal.model_validate(payload), grounding_context(report_id))
    payload["sections"][0]["group_with"] = None
    with pytest.raises(ValueError, match="GROUP_WITH"):
        ReportAIAssistantProposal.model_validate(payload)


def test_section_narratives_use_specific_titles_and_remove_repeated_findings():
    waste = SimpleNamespace(
        section_key="waste", narrative="Se gestionaron 100 kg durante el evento.",
        findings=[SimpleNamespace(text="Se gestionaron 100 kg"), SimpleNamespace(text="Predominó el vidrio")],
    )
    bike = SimpleNamespace(
        section_key="bike_zone", narrative="El bicicletero registró actividad.",
        findings=[SimpleNamespace(text="Predominó el vidrio"), SimpleNamespace(text="La ocupación fue estable")],
    )
    seen = set()
    waste_text = report_assistant_service._section_narrative(waste, seen)
    bike_text = report_assistant_service._section_narrative(bike, seen)

    assert "Hallazgos clave" not in waste_text + bike_text
    assert "Resultados de circularidad" in waste_text
    assert "Uso del bicicletero" in bike_text
    assert "Se gestionaron 100 kg\n" not in waste_text
    assert "Predominó el vidrio" in waste_text and "Predominó el vidrio" not in bike_text


def test_apply_premium_proposal_persists_every_output_without_losing_source_data(monkeypatch):
    report_id, generation_id, user_id = uuid4(), uuid4(), uuid4()
    def section(key, order, content=None):
        return SimpleNamespace(
            id=uuid4(), section_key=key, sort_order=order, is_enabled=True,
            content=content or {"fields": [], "items": []}, updated_at=None,
        )
    summary = section("executive_summary", 0)
    waste = section("waste", 1, {"text": "Texto automático", "fields": [{"key": "total", "value": 100}], "items": []})
    recommendations = section("recommendations", 2, {"fields": [], "items": [{"label": "Manual"}]})
    conclusion = section("conclusion", 3)
    evidence_id = uuid4()
    evidence = SimpleNamespace(evidence_id=evidence_id, section_id=None, is_enabled=False, sort_order=9)
    report = SimpleNamespace(id=report_id, edit_version=4, editorial_config={}, sections=[summary, waste, recommendations, conclusion], evidences=[evidence], updated_at=None)
    output = {
        "version": "1", "report_id": str(report_id), "recommended_preset": "ENVIRONMENTAL", "rationale": "Completo", "estimated_pages": 7,
        "sections": [
            {"section_key": "executive_summary", "visible": True, "order": 0, "premium_variant": "EXECUTIVE_OVERVIEW", "page_mode": "OWN_PAGE"},
            {"section_key": "waste", "visible": True, "order": 1, "premium_variant": "WASTE_CIRCULARITY", "emphasis": "HIGH", "narrative": "Narrativa IA", "findings": [{"text": "Se gestionaron 100 kg", "source_keys": ["waste.total"]}], "selected_metric_keys": ["waste.total"], "selected_evidence_ids": [str(evidence_id)]},
            {"section_key": "recommendations", "visible": True, "order": 2, "premium_variant": "ACTION_ROADMAP"},
            {"section_key": "conclusion", "visible": True, "order": 3, "premium_variant": "EDITORIAL_CLOSE"},
        ],
        "executive_summary": [{"text": "Resumen verificado", "source_keys": ["waste.total"]}],
        "key_findings": [{"text": "Hallazgo verificado", "source_keys": ["waste.total"]}],
        "recommendations": [{"title": "Separar", "description": "Mejorar segregación", "priority": "HIGH", "source_keys": ["waste.total"], "origin": "AI_GENERATED_RECOMMENDATION"}],
        "conclusion": [{"text": "Conclusión verificada", "source_keys": ["waste.total"]}],
        "evidence_suggestions": [], "warnings": [], "source_keys": ["waste.total"],
    }
    generation = SimpleNamespace(id=generation_id, output=output, applied=False)
    db = SimpleNamespace(scalar=lambda _query: generation, commit=lambda: None)
    user = SimpleNamespace(id=user_id)
    monkeypatch.setattr(report_assistant_service.report_builder_service, "_assert_editable", lambda *_: None)
    monkeypatch.setattr(report_assistant_service.report_revision_service, "create", lambda *_: "revision")
    monkeypatch.setattr(report_assistant_service.report_builder_service, "get_editor", lambda *_: "editor")
    monkeypatch.setattr(report_assistant_service.report_visual_audit_service, "audit_correct_and_verify", lambda *_: {"initial": {"passed": True}, "corrections_applied": [], "final": {"passed": True}})

    revision, editor, visual_audit = report_assistant_service.apply_proposal(db, report, generation_id, 4, user)

    assert (revision, editor, report.edit_version, generation.applied) == ("revision", "editor", 5, True)
    assert visual_audit["final"]["passed"] is True
    assert report.editorial_config["target_page_count"] == 7
    assert report.editorial_config["page_overrides"]["executive_summary"]["mode"] == "OWN_PAGE"
    assert report.editorial_config["section_visuals"]["waste"]["selected_metric_keys"] == ["waste.total"]
    assert waste.content["fields"] == [{"key": "total", "value": 100}]
    assert "Narrativa IA" in waste.content["text"] and "Se gestionaron 100 kg" in waste.content["text"]
    assert "Resumen verificado" in summary.content["text"] and "Hallazgo verificado" in summary.content["text"]
    assert recommendations.content["items"][0]["label"] == "Manual"
    assert recommendations.content["items"][1]["origin"] == "AI_GENERATED_RECOMMENDATION"
    assert "Conclusión verificada" in conclusion.content["text"]
    assert evidence.section_id == waste.id and evidence.is_enabled is True


def test_openai_responses_uses_strict_schema_and_normalizes_usage(monkeypatch):
    captured = {}
    response = httpx.Response(200, json={"id": "resp_test", "model": "test-model", "output_text": "{\"ok\":true}", "usage": {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15, "input_tokens_details": {"cached_tokens": 2}}}, request=httpx.Request("POST", "https://api.openai.test/v1/responses"))
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return response
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    result = asyncio.run(OpenAIResponsesProvider("secret-test-key", "https://api.openai.test/v1", 3).generate(ProviderRequest(system_prompt="system", context={"safe": 1}, model="test-model", temperature=0.2, max_output_tokens=100, output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False})))
    assert captured["url"].endswith("/responses")
    assert captured["json"]["text"]["format"]["strict"] is True
    assert captured["json"]["text"]["format"]["schema"]["required"] == ["ok"]
    assert captured["json"]["text"]["format"]["schema"]["additionalProperties"] is False
    assert captured["json"]["store"] is False
    assert "temperature" not in captured["json"]
    assert "secret-test-key" not in json.dumps(captured["json"])
    assert (result.input_tokens, result.output_tokens, result.cached_input_tokens, result.attempt_count) == (12, 3, 2, 1)


def test_openai_400_preserves_only_sanitized_diagnostic_metadata(monkeypatch):
    response = httpx.Response(400, json={"error": {"type": "invalid_request_error", "code": "unsupported_parameter", "param": "temperature", "message": "key sk-secret cannot be used"}}, headers={"x-request-id": "req_test"}, request=httpx.Request("POST", "https://api.openai.test/v1/responses"))
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs): return response
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(AIProviderError) as caught:
        asyncio.run(OpenAIResponsesProvider("sk-secret", "https://api.openai.test/v1", 3).generate(ProviderRequest(system_prompt="system", context={}, model="gpt-5.6-luna", temperature=0.2, max_output_tokens=100)))
    assert caught.value.status_code == 400
    assert caught.value.provider_details["param"] == "temperature"
    assert caught.value.provider_details["request_id"] == "req_test"
    assert "sk-secret" not in json.dumps(caught.value.provider_details)
