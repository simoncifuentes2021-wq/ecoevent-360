from typing import Protocol

from app.services.ai.schemas import ProviderRequest, ProviderResult


class AIProvider(Protocol):
    name: str

    async def generate(self, request: ProviderRequest) -> ProviderResult: ...


class AIProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
