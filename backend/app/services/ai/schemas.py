from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIInterpretation(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    impact_explanation: str | None = Field(default=None, max_length=4000)
    key_points: list[str] = Field(default_factory=list, max_length=8)
    recommendations: list[str] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=8)


class ProviderRequest(BaseModel):
    system_prompt: str
    context: dict[str, Any]
    model: str
    temperature: float
    max_output_tokens: int


class ProviderResult(BaseModel):
    content: str
    effective_model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIInterpretationResponse(AIInterpretation):
    model_config = ConfigDict(from_attributes=True)

    generation_id: str
    provider: str
    model: str
    effective_model: str | None = None
    prompt_version: str
    cached: bool
    generated_at: str
