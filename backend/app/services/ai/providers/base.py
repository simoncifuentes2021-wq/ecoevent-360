from typing import Protocol

from app.services.ai.schemas import ProviderRequest, ProviderResult


class AIProvider(Protocol):
    name: str

    async def generate(self, request: ProviderRequest) -> ProviderResult: ...


class AIProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int | None = None, provider_details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.provider_details = provider_details or {}
