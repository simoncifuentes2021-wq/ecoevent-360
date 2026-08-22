import httpx

from app.services.ai.providers.base import AIProviderError
from app.services.ai.schemas import ProviderRequest, ProviderResult


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, api_key: str, base_url: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.model_dump_json(include={"context"})},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AIProviderError("timeout", "AI provider timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise AIProviderError("http_error", f"AI provider returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("connection_error", "AI provider is unavailable") from exc

        try:
            data = response.json()
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                effective_model=data.get("model"),
                metadata={"request_id": response.headers.get("x-request-id")},
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError("invalid_provider_response", "AI provider response was incomplete") from exc
