import asyncio
import json
import re
from copy import deepcopy

import httpx

from app.services.ai.providers.base import AIProviderError
from app.services.ai.schemas import ProviderRequest, ProviderResult


class OpenAIResponsesProvider:
    name = "openai"

    def __init__(self, api_key: str, base_url: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        payload = {
            "model": request.model,
            "instructions": request.system_prompt,
            "input": json.dumps({"context": request.context}, ensure_ascii=False),
            "max_output_tokens": request.max_output_tokens,
            "store": False,
        }
        if request.output_schema:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "strict": True,
                    "schema": self._strict_schema(request.output_schema),
                }
            }

        attempts = 0
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while attempts < 2:
                attempts += 1
                try:
                    response = await client.post(
                        f"{self.base_url}/responses",
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    if response.status_code in {400, 401, 403, 404}:
                        details = self._safe_error_details(response)
                        raise AIProviderError(
                            "invalid_configuration",
                            f"OpenAI rejected the report request ({details.get('code') or response.status_code})",
                            status_code=response.status_code,
                            provider_details=details,
                        )
                    if response.status_code == 429:
                        if attempts < 2:
                            retry_after = min(float(response.headers.get("retry-after", "1") or 1), 5.0)
                            await asyncio.sleep(retry_after)
                            continue
                        raise AIProviderError("rate_limited", "OpenAI temporary rate limit reached")
                    if response.status_code >= 500:
                        if attempts < 2:
                            await asyncio.sleep(0.5)
                            continue
                        raise AIProviderError("provider_unavailable", "OpenAI is temporarily unavailable")
                    response.raise_for_status()
                    data = response.json()
                    if data.get("status") == "incomplete":
                        reason = (data.get("incomplete_details") or {}).get("reason")
                        code = "output_truncated" if reason == "max_output_tokens" else "invalid_provider_response"
                        raise AIProviderError(code, f"OpenAI returned an incomplete response ({reason or 'unknown reason'})")
                    content = data.get("output_text") or self._output_text(data)
                    if not content:
                        raise AIProviderError("invalid_provider_response", "OpenAI returned no structured output")
                    usage = data.get("usage") or {}
                    details = usage.get("input_tokens_details") or {}
                    input_tokens = int(usage.get("input_tokens") or 0)
                    output_tokens = int(usage.get("output_tokens") or 0)
                    return ProviderResult(
                        content=content,
                        effective_model=data.get("model"),
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cached_input_tokens=int(details.get("cached_tokens") or 0),
                        total_tokens=int(usage.get("total_tokens") or input_tokens + output_tokens),
                        provider_request_id=data.get("id") or response.headers.get("x-request-id"),
                        attempt_count=attempts,
                    )
                except AIProviderError:
                    raise
                except httpx.TimeoutException as exc:
                    if attempts < 2:
                        await asyncio.sleep(0.5)
                        continue
                    raise AIProviderError("timeout", "OpenAI report generation timed out") from exc
                except httpx.HTTPError as exc:
                    if attempts < 2:
                        await asyncio.sleep(0.5)
                        continue
                    raise AIProviderError("connection_error", "Could not contact OpenAI") from exc
        raise AIProviderError("provider_unavailable", "OpenAI is temporarily unavailable")

    @staticmethod
    def _safe_error_details(response: httpx.Response) -> dict:
        """Keep actionable OpenAI metadata without persisting credentials or request data."""
        try:
            error = (response.json() or {}).get("error") or {}
        except (ValueError, TypeError):
            error = {}
        message = str(error.get("message") or "")[:500]
        message = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", message)
        return {
            "http_status": response.status_code,
            "type": error.get("type"),
            "code": error.get("code"),
            "param": error.get("param"),
            "message": message or None,
            "request_id": response.headers.get("x-request-id"),
        }

    @staticmethod
    def _output_text(data: dict) -> str:
        for item in data.get("output") or []:
            for part in item.get("content") or []:
                if part.get("type") in {"output_text", "text"} and part.get("text"):
                    return part["text"]
        return ""

    @classmethod
    def _strict_schema(cls, schema: dict) -> dict:
        """Normalize Pydantic JSON Schema to the strict Responses contract."""
        result = deepcopy(schema)

        def visit(node):
            if isinstance(node, dict):
                if node.get("type") == "object" or "properties" in node:
                    properties = node.get("properties") or {}
                    node["additionalProperties"] = False
                    node["required"] = list(properties)
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(result)
        return result
