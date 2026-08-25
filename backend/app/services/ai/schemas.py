from typing import Any, Literal
from uuid import UUID

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
    output_schema: dict[str, Any] | None = None
    schema_name: str = "ecoevent_response"


class ProviderResult(BaseModel):
    content: str
    effective_model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    total_tokens: int = 0
    provider_request_id: str | None = None
    attempt_count: int = 1


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
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    actual_cost_usd: float | None = None


class ReportAISectionPlan(BaseModel):
    section_key: str = Field(pattern=r"^[a-z0-9_-]{1,100}$")
    title_suggestion: str | None = Field(default=None, max_length=180)
    layout_variant: Literal["HERO_IMAGE_TEXT", "KPI_GRID", "TWO_COLUMN", "METRIC_LIST", "FEATURE_CHART", "PHOTO_GRID", "EDITORIAL", "TEXT_IMAGE", "BIG_NUMBERS"]
    page_mode: Literal["AUTO", "KEEP_WITH_NEXT", "OWN_PAGE", "GROUP_WITH", "NEW_PAGE"] = "AUTO"
    group_with: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,100}$")
    generated_text: str | None = Field(default=None, max_length=10000)
    rationale: str = Field(min_length=1, max_length=1000)


class ReportAIEditorialPlan(BaseModel):
    report_title_suggestion: str | None = Field(default=None, max_length=180)
    cover_style: Literal["FULL_PHOTO", "SIDE_PHOTO", "EDITORIAL", "MINIMAL_PREMIUM"]
    section_order: list[str] = Field(min_length=1, max_length=50)
    sections: list[ReportAISectionPlan] = Field(min_length=1, max_length=50)
    overall_rationale: str = Field(min_length=1, max_length=3000)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    used_data_keys: list[str] = Field(default_factory=list, max_length=200)


class ReportAIEditorialPlanResponse(ReportAIEditorialPlan):
    generation_id: str
    provider: str
    model: str
    effective_model: str | None = None
    prompt_version: str
    cached: bool
    generated_at: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    actual_cost_usd: float | None = None


class ReportAIEditorialRequest(BaseModel):
    style: Literal["EXECUTIVE", "TECHNICAL", "COMMERCIAL", "BRIEF"] = "EXECUTIVE"
    include_text_rewrites: bool = True
    force_refresh: bool = False


class ReportAIEditorialApplyRequest(BaseModel):
    generation_id: UUID
    edit_version: int = Field(ge=1)


class ReportAIClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    source_keys: list[str] = Field(min_length=1, max_length=20)


class ReportAIRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=2000)
    priority: Literal["LOW", "MEDIUM", "HIGH"]
    source_keys: list[str] = Field(min_length=1, max_length=20)
    origin: Literal["AI_GENERATED_RECOMMENDATION"] = "AI_GENERATED_RECOMMENDATION"


class ReportAIEvidenceSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: UUID
    section_key: str
    rationale: str = Field(min_length=1, max_length=500)


class ReportAISectionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_key: str
    visible: bool
    order: int = Field(ge=0, le=100)
    premium_variant: str
    emphasis: Literal["LOW", "NORMAL", "HIGH"] = "NORMAL"
    narrative: str | None = Field(default=None, max_length=10000)
    findings: list[ReportAIClaim] = Field(default_factory=list, max_length=10)
    selected_metric_keys: list[str] = Field(default_factory=list, max_length=30)
    selected_evidence_ids: list[UUID] = Field(default_factory=list, max_length=20)


class ReportAIAssistantProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["1"] = "1"
    report_id: UUID
    recommended_preset: str
    rationale: str = Field(min_length=1, max_length=3000)
    estimated_pages: int = Field(ge=1, le=50)
    sections: list[ReportAISectionProposal] = Field(min_length=1, max_length=50)
    executive_summary: list[ReportAIClaim] = Field(default_factory=list, max_length=10)
    key_findings: list[ReportAIClaim] = Field(default_factory=list, max_length=20)
    recommendations: list[ReportAIRecommendation] = Field(default_factory=list, max_length=12)
    conclusion: list[ReportAIClaim] = Field(default_factory=list, max_length=10)
    evidence_suggestions: list[ReportAIEvidenceSuggestion] = Field(default_factory=list, max_length=30)
    warnings: list[str] = Field(default_factory=list, max_length=12)
    source_keys: list[str] = Field(default_factory=list, max_length=300)


class ReportAIAssistantRequest(BaseModel):
    instructions: str = Field(min_length=10, max_length=4000)
    force_refresh: bool = False


class ReportAIAssistantResponse(ReportAIAssistantProposal):
    generation_id: UUID
    provider: str
    model: str
    effective_model: str | None = None
    prompt_version: str
    cached: bool
    generated_at: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    actual_cost_usd: float | None = None
    diff: list[dict[str, Any]] = Field(default_factory=list)


class ReportAIAssistantApplyRequest(BaseModel):
    generation_id: UUID
    edit_version: int = Field(ge=1)
    accepted_section_keys: list[str] | None = None
    apply_preset: bool = True


class ReportAIGenerationHistoryItem(BaseModel):
    id: UUID
    created_at: str
    capability: str
    provider: str
    model: str
    effective_model: str | None = None
    status: str
    cached: bool = False
    applied: bool
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    actual_cost_usd: float | None = None
