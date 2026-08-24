"""Stable report-AI contracts; providers never receive ORM objects or private URLs."""

from typing import Protocol
from app.services.ai.schemas import ProviderRequest, ProviderResult


class ReportAIProvider(Protocol):
    async def generate(self, request: ProviderRequest) -> ProviderResult: ...
