from typing import Any, Literal

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


class ReportAIDraft(BaseModel):
    title_suggestion: str | None = Field(default=None, max_length=180)
    generated_text: str = Field(min_length=1, max_length=10000)
    key_points: list[str] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    used_data_keys: list[str] = Field(default_factory=list, max_length=100)


class ReportAIRequest(BaseModel):
    operation: Literal["GENERATE", "IMPROVE", "REGENERATE"] = "GENERATE"
    style: Literal["EXECUTIVE", "TECHNICAL", "COMMERCIAL", "BRIEF"] = "EXECUTIVE"
    length: Literal["SHORT", "MEDIUM", "LONG"] = "MEDIUM"
    current_text: str | None = Field(default=None, max_length=10000)


class ReportAIDraftResponse(ReportAIDraft):
    generation_id: str
    provider: str
    model: str
    effective_model: str | None = None
    prompt_version: str
    cached: bool
    generated_at: str
