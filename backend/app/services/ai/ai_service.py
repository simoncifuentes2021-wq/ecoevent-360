import hashlib
import json
import re
import time
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.ai import AIGeneration
from app.models.core import User
from app.services.ai.ai_router import build_provider
from app.services.ai.contexts.environmental import CAPABILITY, build_environmental_context
from app.services.ai.prompts.environmental import PROMPT_VERSION, SYSTEM_PROMPT
from app.services.ai.providers.base import AIProvider, AIProviderError
from app.services.ai.schemas import AIInterpretation, AIInterpretationResponse, ProviderRequest


class AIServiceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash(context: dict) -> str:
    payload = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_output(content: str) -> AIInterpretation:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return AIInterpretation.model_validate_json(candidate)
    except (ValidationError, ValueError) as exc:
        raise AIProviderError("invalid_output", "AI provider returned invalid structured output") from exc


def _validate_numbers(output: AIInterpretation, context: dict) -> None:
    def collect(value):
        if isinstance(value, dict):
            return [item for child in value.values() for item in collect(child)]
        if isinstance(value, list):
            return [item for child in value for item in collect(child)]
        if isinstance(value, (int, float)) or (isinstance(value, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", value)):
            return [str(value)]
        return []

    allowed = {value.replace(",", ".").lstrip("+") for value in collect(context)}
    allowed_normalized = {str(float(value)) for value in allowed}
    rendered = json.dumps(output.model_dump(), ensure_ascii=False)
    mentioned = re.findall(r"(?<![A-Za-z0-9.])-?\d+(?:[.,]\d+)?", rendered)
    invented = [value for value in mentioned if str(float(value.replace(",", "."))) not in allowed_normalized]
    if invented:
        raise AIProviderError("unsupported_numeric_claim", "AI output introduced unsupported numbers")


class AIService:
    def __init__(self, config: Settings = settings, provider: AIProvider | None = None) -> None:
        self.config = config
        self._provider = provider

    async def interpret_environmental_action(
        self, db: Session, event_id: UUID, action_id: UUID, user: User
    ) -> AIInterpretationResponse:
        if not self.config.ai_enabled:
            raise AIServiceError("disabled", "AI interpretation is disabled")

        action, context = build_environmental_context(db, event_id, action_id, user)
        if not action.metrics:
            raise AIServiceError("not_calculated", "Environmental action must be calculated first")
        input_hash = _hash(context)
        provider_name = self.config.ai_provider.strip().lower()
        cached = db.scalar(
            select(AIGeneration)
            .where(
                AIGeneration.capability == CAPABILITY,
                AIGeneration.subject_id == action_id,
                AIGeneration.input_hash == input_hash,
                AIGeneration.prompt_version == PROMPT_VERSION,
                AIGeneration.provider == provider_name,
                AIGeneration.model == self.config.ai_model,
                AIGeneration.status == "SUCCEEDED",
            )
            .order_by(AIGeneration.created_at.desc())
        )
        if cached and cached.output:
            return self._response(cached, cached=True)

        generation = AIGeneration(
            capability=CAPABILITY,
            subject_type="EnvironmentalAction",
            subject_id=action_id,
            event_id=event_id,
            requested_by=user.id,
            provider=provider_name,
            model=self.config.ai_model,
            prompt_version=PROMPT_VERSION,
            input_hash=input_hash,
            input_snapshot=context,
            status="PENDING",
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)
        started = time.perf_counter()
        try:
            provider = self._provider or build_provider(self.config)
            result = await provider.generate(
                ProviderRequest(
                    system_prompt=SYSTEM_PROMPT,
                    context=context,
                    model=self.config.ai_model,
                    temperature=self.config.ai_temperature,
                    max_output_tokens=self.config.ai_max_output_tokens,
                )
            )
            output = _parse_output(result.content)
            _validate_numbers(output, context)
            generation.output = output.model_dump()
            generation.effective_model = result.effective_model
            generation.status = "SUCCEEDED"
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            db.refresh(generation)
            return self._response(generation, cached=False)
        except AIProviderError as exc:
            generation.status = "FAILED"
            generation.error_code = exc.code
            generation.error_message = str(exc)[:2000]
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            raise AIServiceError(exc.code, "No fue posible generar la interpretación en este momento") from exc

    @staticmethod
    def _response(generation: AIGeneration, cached: bool) -> AIInterpretationResponse:
        return AIInterpretationResponse(
            **(generation.output or {}),
            generation_id=str(generation.id),
            provider=generation.provider,
            model=generation.model,
            effective_model=generation.effective_model,
            prompt_version=generation.prompt_version,
            cached=cached,
            generated_at=generation.completed_at.isoformat() if generation.completed_at else generation.created_at.isoformat(),
        )
