import hashlib
import json
import re
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.ai import AIGeneration
from app.models.core import User
from app.services.ai.ai_router import build_provider, build_report_provider
from app.services.ai.contexts.environmental import CAPABILITY, build_environmental_context
from app.services.ai.contexts.reports import ASSISTANT_CAPABILITY, CAPABILITY as REPORT_CAPABILITY, EDITORIAL_CAPABILITY, build_report_assistant_context, build_report_editorial_context, build_report_section_context
from app.services.ai.prompts.environmental import PROMPT_VERSION, SYSTEM_PROMPT
from app.services.ai.prompts.reports import PROMPT_VERSION as REPORT_PROMPT_VERSION, SYSTEM_PROMPT as REPORT_SYSTEM_PROMPT
from app.services.ai.prompts.report_editorial import PROMPT_VERSION as EDITORIAL_PROMPT_VERSION, SYSTEM_PROMPT as EDITORIAL_SYSTEM_PROMPT
from app.services.ai.providers.base import AIProvider, AIProviderError
from app.services.ai.schemas import AIInterpretation, AIInterpretationResponse, ProviderRequest, ReportAIDraft, ReportAIDraftResponse, ReportAIEditorialPlan, ReportAIEditorialPlanResponse, ReportAIEditorialRequest, ReportAIRequest
from app.services.ai.usage_service import actual_report_cost, enforce_report_budget, mark_stale_pending
from app.services.ai.prompts.report_assistant import PROMPT_VERSION as ASSISTANT_PROMPT_VERSION, SYSTEM_PROMPT as ASSISTANT_SYSTEM_PROMPT
from app.services.ai.premium_grounding import validate_premium_proposal
from app.services.ai.report_assistant_service import proposal_diff
from app.services.ai.schemas import ReportAIAssistantProposal, ReportAIAssistantRequest, ReportAIAssistantResponse


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
    if not candidate.startswith("{") or not candidate.endswith("}"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    try:
        return AIInterpretation.model_validate_json(candidate)
    except (ValidationError, ValueError) as exc:
        raise AIProviderError("invalid_output", "AI provider returned invalid structured output") from exc


def _parse_report_output(content: str) -> ReportAIDraft:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    if not candidate.startswith("{") or not candidate.endswith("}"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    try:
        payload = json.loads(candidate)
        if isinstance(payload, dict):
            for key, limit in (("key_points", 8), ("warnings", 8), ("used_data_keys", 100)):
                if isinstance(payload.get(key), list):
                    payload[key] = payload[key][:limit]
        return ReportAIDraft.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
        raise AIProviderError("invalid_output", "AI provider returned invalid structured output") from exc


def _parse_editorial_output(content: str) -> ReportAIEditorialPlan:
    candidate = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    if not candidate.startswith("{") or not candidate.endswith("}"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    try:
        payload = json.loads(candidate)
        if isinstance(payload, dict):
            cover_aliases = {
                "HERO_IMAGE_TEXT": "FULL_PHOTO",
                "TEXT_IMAGE": "SIDE_PHOTO",
                "MINIMAL": "MINIMAL_PREMIUM",
            }
            payload["cover_style"] = cover_aliases.get(
                payload.get("cover_style"), payload.get("cover_style")
            )
            payload["warnings"] = (payload.get("warnings") or [])[:8]
            payload["used_data_keys"] = (payload.get("used_data_keys") or [])[:200]
            payload["sections"] = (payload.get("sections") or [])[:50]
            for section in payload["sections"]:
                if not isinstance(section, dict):
                    continue
                group_with = section.get("group_with")
                if not isinstance(group_with, str) or not re.fullmatch(r"[a-z0-9_-]{1,100}", group_with):
                    section["group_with"] = None
                if section.get("page_mode") == "GROUP_WITH" and not section.get("group_with"):
                    section["page_mode"] = "AUTO"
        return ReportAIEditorialPlan.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
        raise AIProviderError(
            "invalid_output", f"AI provider returned invalid editorial plan: {str(exc)[:500]}"
        ) from exc


def _fallback_editorial_plan(context: dict, reason: str) -> ReportAIEditorialPlan:
    rank = {
        "COVER": 0, "EXECUTIVE_SUMMARY": 1, "EVENT_INFO": 2, "SHOW_INFO": 2,
        "OPERATIONS": 3, "STAFF": 4, "TASKS": 5, "INCIDENTS": 6, "FORMS": 7,
        "ENVIRONMENTAL_IMPACT": 8, "BIKE_ZONE": 9, "WASTE": 10, "CARBON": 11,
        "EVIDENCES": 12, "RECOMMENDATIONS": 13, "CONCLUSION": 14,
    }
    visible = [item for item in context["sections"] if item["is_enabled"]]
    visible.sort(key=lambda item: (rank.get(item["section_type"], 12), item["sort_order"]))
    sections = []
    for item in visible:
        content = item.get("effective_content") or {}
        field_count = len([field for field in content.get("fields") or [] if field.get("is_visible", True)])
        item_count = len([row for row in content.get("items") or [] if row.get("_is_visible", True)])
        kind = item["section_type"]
        if kind == "COVER":
            layout, page_mode = "HERO_IMAGE_TEXT", "OWN_PAGE"
        elif kind == "EVIDENCES":
            layout, page_mode = "PHOTO_GRID", "OWN_PAGE"
        elif kind in {"ENVIRONMENTAL_IMPACT", "CARBON"}:
            layout, page_mode = "FEATURE_CHART", "OWN_PAGE"
        elif field_count >= 4:
            layout, page_mode = "KPI_GRID", "AUTO"
        elif item_count >= 4:
            layout, page_mode = "METRIC_LIST", "OWN_PAGE"
        elif item.get("evidence_count"):
            layout, page_mode = "TEXT_IMAGE", "AUTO"
        else:
            layout, page_mode = "EDITORIAL", "AUTO"
        sections.append({
            "section_key": item["section_key"], "title_suggestion": item["title"],
            "layout_variant": layout, "page_mode": page_mode, "group_with": None,
            "generated_text": None,
            "rationale": "Composicion segura basada en el tipo y densidad del contenido.",
        })
    cover_style = (context.get("report", {}).get("editorial_config") or {}).get("cover_style", "FULL_PHOTO")
    if cover_style not in {"FULL_PHOTO", "SIDE_PHOTO", "EDITORIAL", "MINIMAL_PREMIUM"}:
        cover_style = "FULL_PHOTO"
    return ReportAIEditorialPlan(
        report_title_suggestion=context["report"]["title"], cover_style=cover_style,
        section_order=[item["section_key"] for item in visible], sections=sections,
        overall_rationale="EcoEvent preparo una composicion editorial estable segun contenido, densidad y evidencias.",
        warnings=[f"Se uso el planificador seguro porque el modelo no entrego un plan aplicable: {reason[:180]}"],
        used_data_keys=["sections", "report.editorial_config"],
    )


def _validate_numbers(output: AIInterpretation, context: dict) -> None:
    def collect(value):
        if isinstance(value, dict):
            return [item for child in value.values() for item in collect(child)]
        if isinstance(value, list):
            return [item for child in value for item in collect(child)]
        if isinstance(value, (int, float)):
            return [str(value)]
        if isinstance(value, str):
            return re.findall(r"(?<![A-Za-z0-9.])-?\d+(?:[.,]\d+)?", value)
        return []

    allowed: set[Decimal] = set()
    for value in collect(context):
        try:
            number = Decimal(value.replace(",", "."))
        except InvalidOperation:
            continue
        allowed.add(number)
        for digits in range(7):
            quantum = Decimal(1).scaleb(-digits)
            allowed.add(number.quantize(quantum, rounding=ROUND_HALF_UP))
    rendered_output = output.model_dump()
    # Data-path indexes are traceability metadata, not claims shown to users.
    rendered_output.pop("used_data_keys", None)
    rendered = json.dumps(rendered_output, ensure_ascii=False)
    mentioned = re.findall(r"(?<![A-Za-z0-9.])-?\d+(?:[.,]\d+)?", rendered)
    invented = []
    for value in mentioned:
        try:
            if Decimal(value.replace(",", ".")) not in allowed:
                invented.append(value)
        except InvalidOperation:
            invented.append(value)
    if invented:
        values = ", ".join(dict.fromkeys(invented[:10]))
        raise AIProviderError(
            "unsupported_numeric_claim", f"AI output introduced unsupported numbers: {values}"
        )


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
            request = ProviderRequest(
                system_prompt=SYSTEM_PROMPT,
                context=context,
                model=self.config.ai_model,
                temperature=self.config.ai_temperature,
                max_output_tokens=self.config.ai_max_output_tokens,
            )
            for output_attempt in range(2):
                result = await provider.generate(request)
                try:
                    output = _parse_output(result.content)
                    _validate_numbers(output, context)
                    break
                except AIProviderError as exc:
                    if output_attempt == 0 and exc.code in {
                        "invalid_output",
                        "unsupported_numeric_claim",
                    }:
                        continue
                    raise
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

    async def generate_report_section_draft(
        self, db: Session, report_id: UUID, section_id: UUID, user: User, options: ReportAIRequest
    ) -> ReportAIDraftResponse:
        if not self.config.ai_enabled or not self.config.ai_reports_enabled:
            raise AIServiceError("disabled", "La asistencia de IA para reportes esta deshabilitada")
        try:
            section, context = build_report_section_context(db, report_id, section_id, user, options)
        except ValueError as exc:
            raise AIServiceError("not_found", str(exc)) from exc
        input_hash = _hash(context)
        provider_name = getattr(self.config, "ai_report_provider", self.config.ai_provider).strip().lower()
        report_model = getattr(self.config, "ai_report_model", None) or self.config.ai_model
        cached = None
        if options.operation != "REGENERATE":
            cached = db.scalar(
                select(AIGeneration).where(
                    AIGeneration.capability == REPORT_CAPABILITY,
                    AIGeneration.subject_id == section_id,
                    AIGeneration.input_hash == input_hash,
                    AIGeneration.prompt_version == REPORT_PROMPT_VERSION,
                    AIGeneration.provider == provider_name,
                    AIGeneration.model == report_model,
                    AIGeneration.status == "SUCCEEDED",
                ).order_by(AIGeneration.created_at.desc())
            )
        if cached and cached.output:
            return self._report_response(cached, cached=True)
        generation = AIGeneration(
            capability=REPORT_CAPABILITY,
            subject_type="ReportSection",
            subject_id=section_id,
            event_id=section.report.event_id,
            requested_by=user.id,
            provider=provider_name,
            model=report_model,
            prompt_version=REPORT_PROMPT_VERSION,
            input_hash=input_hash,
            input_snapshot=context,
            status="PENDING",
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)
        started = time.perf_counter()
        try:
            mark_stale_pending(db, self.config)
            try:
                generation.estimated_cost_usd = enforce_report_budget(db, self.config)
            except RuntimeError as exc:
                generation.status = "FAILED"
                generation.error_code = "REPORT_AI_BUDGET_EXCEEDED"
                generation.error_message = "Report AI monthly budget reached"
                generation.completed_at = _utcnow()
                db.commit()
                raise AIServiceError("REPORT_AI_BUDGET_EXCEEDED", "Se alcanzo el presupuesto mensual configurado") from exc
            provider = self._provider or build_report_provider(self.config)
            request = ProviderRequest(
                system_prompt=REPORT_SYSTEM_PROMPT,
                context=context,
                model=report_model,
                temperature=getattr(self.config, "ai_report_temperature", self.config.ai_temperature),
                max_output_tokens=getattr(self.config, "ai_report_max_output_tokens", self.config.ai_max_output_tokens),
                output_schema=ReportAIDraft.model_json_schema(),
                schema_name="report_section_draft",
            )
            result = await provider.generate(request)
            output = _parse_report_output(result.content)
            _validate_numbers(output, context)
            generation.output = output.model_dump()
            generation.effective_model = result.effective_model
            self._record_usage(generation, result)
            generation.status = "SUCCEEDED"
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            db.refresh(generation)
            return self._report_response(generation, cached=False)
        except AIProviderError as exc:
            generation.status = "FAILED"
            generation.error_code = exc.code
            generation.error_message = str(exc)[:2000]
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            raise AIServiceError(exc.code, "No fue posible generar el borrador en este momento") from exc

    async def generate_report_editorial_plan(
        self, db: Session, report_id: UUID, user: User, options: ReportAIEditorialRequest
    ) -> ReportAIEditorialPlanResponse:
        if not self.config.ai_enabled or not self.config.ai_reports_enabled:
            raise AIServiceError("disabled", "La asistencia de IA para reportes esta deshabilitada")
        report, context = build_report_editorial_context(
            db, report_id, user, options.style, options.include_text_rewrites
        )
        input_hash = _hash(context)
        provider_name = getattr(self.config, "ai_report_provider", self.config.ai_provider).strip().lower()
        report_model = getattr(self.config, "ai_report_model", None) or self.config.ai_model
        cached = None
        if not options.force_refresh:
            cached = db.scalar(select(AIGeneration).where(
                AIGeneration.capability == EDITORIAL_CAPABILITY,
                AIGeneration.subject_id == report_id,
                AIGeneration.input_hash == input_hash,
                AIGeneration.prompt_version == EDITORIAL_PROMPT_VERSION,
                AIGeneration.provider == provider_name,
                AIGeneration.model == report_model,
                AIGeneration.status == "SUCCEEDED",
            ).order_by(AIGeneration.created_at.desc()))
        if cached and cached.output:
            return self._editorial_response(cached, True)
        generation = AIGeneration(
            capability=EDITORIAL_CAPABILITY, subject_type="Report", subject_id=report_id,
            event_id=report.event_id, requested_by=user.id, provider=provider_name,
            model=report_model, prompt_version=EDITORIAL_PROMPT_VERSION,
            input_hash=input_hash, input_snapshot=context, status="PENDING",
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)
        started = time.perf_counter()
        try:
            mark_stale_pending(db, self.config)
            try:
                generation.estimated_cost_usd = enforce_report_budget(db, self.config)
            except RuntimeError as exc:
                generation.status = "FAILED"
                generation.error_code = "REPORT_AI_BUDGET_EXCEEDED"
                generation.error_message = "Report AI monthly budget reached"
                generation.completed_at = _utcnow()
                db.commit()
                raise AIServiceError("REPORT_AI_BUDGET_EXCEEDED", "Se alcanzo el presupuesto mensual configurado") from exc
            provider = self._provider or build_report_provider(self.config)
            request = ProviderRequest(system_prompt=EDITORIAL_SYSTEM_PROMPT, context=context,
                model=report_model, temperature=getattr(self.config, "ai_report_temperature", self.config.ai_temperature),
                max_output_tokens=max(getattr(self.config, "ai_report_max_output_tokens", self.config.ai_max_output_tokens), 3200),
                output_schema=ReportAIEditorialPlan.model_json_schema(), schema_name="report_editorial_plan")
            allowed_keys = [item["section_key"] for item in context["sections"] if item["is_enabled"]]
            result = None
            try:
                result = await provider.generate(request)
                output = _parse_editorial_output(result.content)
                normalized_order = []
                for key in [*output.section_order, *allowed_keys]:
                    if key in allowed_keys and key not in normalized_order:
                        normalized_order.append(key)
                output.section_order = normalized_order
                planned_keys = {item.section_key for item in output.sections}
                if not planned_keys.issubset(set(allowed_keys)):
                    raise AIProviderError("invalid_output", "Editorial plan referenced an unknown section")
                _validate_numbers(output, context)
            except AIProviderError as exc:
                if exc.code not in {"invalid_output", "unsupported_numeric_claim", "invalid_provider_response"}:
                    raise
                output = _fallback_editorial_plan(context, str(exc))
            generation.output = output.model_dump()
            generation.effective_model = result.effective_model if result else None
            if result:
                self._record_usage(generation, result)
            generation.status = "SUCCEEDED"
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            db.refresh(generation)
            return self._editorial_response(generation, False)
        except AIProviderError as exc:
            generation.status = "FAILED"
            generation.error_code = exc.code
            generation.error_message = str(exc)[:2000]
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            raise AIServiceError(exc.code, "No fue posible optimizar el informe en este momento") from exc

    async def generate_report_assistant_proposal(
        self, db: Session, report_id: UUID, user: User, options: ReportAIAssistantRequest
    ) -> ReportAIAssistantResponse:
        if not self.config.ai_enabled or not self.config.ai_reports_enabled:
            raise AIServiceError("disabled", "La asistencia de IA para reportes esta deshabilitada")
        report, context = build_report_assistant_context(db, report_id, user, options.instructions)
        input_hash = _hash(context)
        provider_name = getattr(self.config, "ai_report_provider", self.config.ai_provider).strip().lower()
        model = getattr(self.config, "ai_report_model", None) or self.config.ai_model
        cached = None if options.force_refresh else db.scalar(select(AIGeneration).where(
            AIGeneration.capability == ASSISTANT_CAPABILITY,
            AIGeneration.subject_id == report_id,
            AIGeneration.input_hash == input_hash,
            AIGeneration.prompt_version == ASSISTANT_PROMPT_VERSION,
            AIGeneration.provider == provider_name,
            AIGeneration.model == model,
            AIGeneration.status == "SUCCEEDED",
        ).order_by(AIGeneration.created_at.desc()))
        if cached and cached.output:
            return self._assistant_response(report, cached, True)
        generation = AIGeneration(
            capability=ASSISTANT_CAPABILITY, subject_type="Report", subject_id=report.id,
            event_id=report.event_id, requested_by=user.id, provider=provider_name, model=model,
            prompt_version=ASSISTANT_PROMPT_VERSION, input_hash=input_hash,
            input_snapshot=context, status="PENDING",
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)
        started = time.perf_counter()
        try:
            mark_stale_pending(db, self.config)
            try:
                generation.estimated_cost_usd = enforce_report_budget(db, self.config)
            except RuntimeError as exc:
                raise AIProviderError("REPORT_AI_BUDGET_EXCEEDED", "Report AI monthly budget reached") from exc
            provider = self._provider or build_report_provider(self.config)
            result = await provider.generate(ProviderRequest(
                system_prompt=ASSISTANT_SYSTEM_PROMPT, context=context, model=model,
                temperature=getattr(self.config, "ai_report_temperature", self.config.ai_temperature),
                max_output_tokens=getattr(self.config, "ai_report_max_output_tokens", self.config.ai_max_output_tokens),
                output_schema=ReportAIAssistantProposal.model_json_schema(),
                schema_name="report_premium_assistant_proposal",
            ))
            try:
                output = ReportAIAssistantProposal.model_validate_json(result.content)
            except ValidationError as exc:
                raise AIProviderError("invalid_output", "OpenAI returned an invalid report proposal") from exc
            validate_premium_proposal(output, context)
            generation.output = output.model_dump(mode="json")
            generation.effective_model = result.effective_model
            self._record_usage(generation, result)
            generation.status = "SUCCEEDED"
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            db.refresh(generation)
            return self._assistant_response(report, generation, False)
        except AIProviderError as exc:
            generation.status = "FAILED"
            generation.error_code = exc.code
            generation.error_message = str(exc)[:2000]
            generation.completed_at = _utcnow()
            generation.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()
            messages = {
                "invalid_configuration": "Configuracion de IA invalida.",
                "rate_limited": "Limite temporal del proveedor.",
                "timeout": "No fue posible completar la generacion.",
                "REPORT_AI_BUDGET_EXCEEDED": "Se alcanzo el presupuesto mensual configurado.",
                "invalid_output": "Respuesta IA invalida y no fue aplicada.",
            }
            raise AIServiceError(exc.code, messages.get(exc.code, "No fue posible generar la propuesta.")) from exc

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

    @staticmethod
    def _report_response(generation: AIGeneration, cached: bool) -> ReportAIDraftResponse:
        return ReportAIDraftResponse(
            **(generation.output or {}),
            generation_id=str(generation.id),
            provider=generation.provider,
            model=generation.model,
            effective_model=generation.effective_model,
            prompt_version=generation.prompt_version,
            cached=cached,
            generated_at=(generation.completed_at or generation.created_at).isoformat(),
            input_tokens=generation.input_tokens, output_tokens=generation.output_tokens,
            cached_input_tokens=generation.cached_input_tokens,
            actual_cost_usd=float(generation.actual_cost_usd) if generation.actual_cost_usd is not None else None,
        )

    @staticmethod
    def _editorial_response(generation: AIGeneration, cached: bool) -> ReportAIEditorialPlanResponse:
        return ReportAIEditorialPlanResponse(
            **(generation.output or {}), generation_id=str(generation.id), provider=generation.provider,
            model=generation.model, effective_model=generation.effective_model,
            prompt_version=generation.prompt_version, cached=cached,
            generated_at=(generation.completed_at or generation.created_at).isoformat(),
            input_tokens=generation.input_tokens, output_tokens=generation.output_tokens,
            cached_input_tokens=generation.cached_input_tokens,
            actual_cost_usd=float(generation.actual_cost_usd) if generation.actual_cost_usd is not None else None,
        )

    def _record_usage(self, generation: AIGeneration, result) -> None:
        generation.input_tokens = result.input_tokens
        generation.output_tokens = result.output_tokens
        generation.cached_input_tokens = result.cached_input_tokens
        generation.total_tokens = result.total_tokens
        generation.provider_request_id = result.provider_request_id
        generation.attempt_count = result.attempt_count
        generation.actual_cost_usd = actual_report_cost(self.config, result)

    @staticmethod
    def _assistant_response(report, generation: AIGeneration, cached: bool) -> ReportAIAssistantResponse:
        proposal = ReportAIAssistantProposal.model_validate(generation.output or {})
        return ReportAIAssistantResponse(
            **proposal.model_dump(), generation_id=generation.id, provider=generation.provider,
            model=generation.model, effective_model=generation.effective_model,
            prompt_version=generation.prompt_version, cached=cached,
            generated_at=(generation.completed_at or generation.created_at).isoformat(),
            input_tokens=generation.input_tokens, output_tokens=generation.output_tokens,
            cached_input_tokens=generation.cached_input_tokens,
            actual_cost_usd=float(generation.actual_cost_usd) if generation.actual_cost_usd is not None else None,
            diff=proposal_diff(report, proposal),
        )
