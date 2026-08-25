import json
import asyncio
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


def test_privacy_sanitizes_keys_and_free_text():
    result = sanitize({"email": "hidden@example.com", "note": "Contactar a visible@example.com o +56 9 1234 5678", "private_url": "https://private.test/x?token=secret"})
    assert "email" not in result
    assert result["note"] == "Contactar a [EMAIL] o [PHONE]"
    assert "private_url" not in result
    assert sanitize("e19d9e23-c253-4554-8280-53f010b1f6b1") == "e19d9e23-c253-4554-8280-53f010b1f6b1"


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
