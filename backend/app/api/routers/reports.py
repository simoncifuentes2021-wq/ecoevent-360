from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.core.config import settings
from app.core.rate_limit import enforce
from app.models.core import User
from app.schemas.report_schema import (
    AvailableEvidence,
    CustomSectionCreate,
    EvidenceAdd,
    EvidenceUpdate,
    ReportEditor,
    ReportAIEditorialApplyResponse,
    ReportEvidenceRead,
    ReportPublicationRead,
    ReportPagePlanRead,
    ReportPageCreate,
    ReportPageUpdate,
    ReportPageRead,
    ReportElementCreate,
    ReportElementUpdate,
    ReportElementBatchUpdate,
    ReportElementRead,
    ReportLayoutOverrideBatch,
    ReportLayoutOverrideRead,
    ReportLayoutOverrideUpsert,
    ReportTemplateLayoutCreate,
    ReportTemplateLayoutRead,
    ReportRead,
    ReportRevisionRead,
    ReportSectionRead,
    ReportUpdate,
    PublicationGenerate,
    RestoreRevision,
    RevisionCreate,
    SectionOrderUpdate,
    SectionUpdate,
)
from app.services import report_service
from app.services.ai.ai_service import AIService, AIServiceError
from app.services.ai.schemas import (
    ReportAIAssistantApplyRequest,
    ReportAIAssistantRequest,
    ReportAIAssistantResponse,
    ReportAIGenerationHistoryItem,
    ReportAIDraftResponse,
    ReportAIEditorialApplyRequest,
    ReportAIEditorialPlanResponse,
    ReportAIEditorialRequest,
    ReportAIRequest,
)
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/{report_id}/ai-assistant/proposals", response_model=ReportAIAssistantResponse)
async def generate_report_ai_assistant_proposal(
    report_id: UUID, payload: ReportAIAssistantRequest, request: Request,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user),
):
    enforce(request, "ai_report_assistant", str(current_user.id), settings.rate_limit_ai_reports)
    try:
        return await AIService().generate_report_assistant_proposal(db, report_id, current_user, payload)
    except AIServiceError as exc:
        status_code = 429 if exc.code == "rate_limited" else 402 if exc.code == "REPORT_AI_BUDGET_EXCEEDED" else 503
        raise HTTPException(status_code, str(exc)) from exc


@router.post("/{report_id}/ai-assistant/proposals/apply", response_model=ReportAIEditorialApplyResponse)
def apply_report_ai_assistant_proposal(
    report_id: UUID, payload: ReportAIAssistantApplyRequest, request: Request,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service
    from app.services.ai import report_assistant_service
    report = report_builder_service.get_editor(db, report_id, current_user)
    revision, updated = report_assistant_service.apply_proposal(
        db, report, payload.generation_id, payload.edit_version, current_user,
        payload.accepted_section_keys, payload.apply_preset,
    )
    create_audit_log(db, user=current_user, action="REPORT_AI_ASSISTANT_PROPOSAL_APPLIED", module="reports", entity_type="Report", entity_id=report.id, event_id=report.event_id, metadata={"generation_id": str(payload.generation_id), "rollback_revision_id": str(revision.id)}, request=request)
    return {"revision_id": revision.id, "report": updated}


@router.get("/{report_id}/ai-generations", response_model=list[ReportAIGenerationHistoryItem])
def list_report_ai_generations(
    report_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user),
):
    from sqlalchemy import select
    from app.models.ai import AIGeneration
    from app.services import report_builder_service
    report_builder_service.get_editor(db, report_id, current_user)
    from app.models.core import ReportSection
    section_ids = list(db.scalars(select(ReportSection.id).where(ReportSection.report_id == report_id)).all())
    rows = db.scalars(select(AIGeneration).where(
        AIGeneration.subject_id.in_([report_id, *section_ids]), AIGeneration.capability.like("reports.%")
    ).order_by(AIGeneration.created_at.desc()).limit(50)).all()
    return [ReportAIGenerationHistoryItem(
        id=row.id, created_at=row.created_at.isoformat(), capability=row.capability,
        provider=row.provider, model=row.model, effective_model=row.effective_model,
        status=row.status, applied=row.applied, input_tokens=row.input_tokens,
        output_tokens=row.output_tokens, cached_input_tokens=row.cached_input_tokens,
        actual_cost_usd=float(row.actual_cost_usd) if row.actual_cost_usd is not None else None,
    ) for row in rows]


def _element_read(item):
    return ReportElementRead.from_model(item)


def _page_read(item):
    return ReportPageRead.from_model(item)


@router.get("/{report_id}/layout-overrides", response_model=list[ReportLayoutOverrideRead])
def list_report_layout_overrides(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_override_service

    return report_layout_override_service.list_all(db, report_id, current_user)


@router.put("/{report_id}/layout-overrides", response_model=ReportLayoutOverrideRead)
def upsert_report_layout_override(
    report_id: UUID,
    payload: ReportLayoutOverrideUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_override_service

    return report_layout_override_service.upsert(db, report_id, payload, current_user)


@router.put("/{report_id}/layout-overrides/batch", response_model=list[ReportLayoutOverrideRead])
def batch_report_layout_overrides(
    report_id: UUID,
    payload: ReportLayoutOverrideBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_override_service

    return report_layout_override_service.batch_upsert(db, report_id, payload, current_user)


@router.delete("/{report_id}/layout-overrides", status_code=204)
def reset_report_layout_overrides(
    report_id: UUID,
    element_key: str | None = Query(default=None, min_length=3, max_length=220),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_override_service

    if element_key:
        report_layout_override_service.reset_element(db, report_id, element_key, current_user)
    else:
        report_layout_override_service.reset_all(db, report_id, current_user)
    return Response(status_code=204)


@router.get("/{report_id}/pages", response_model=list[ReportPageRead])
def list_report_pages(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    return [
        _page_read(item) for item in report_layout_service.list_pages(db, report_id, current_user)
    ]


@router.post("/{report_id}/pages/materialize-auto", response_model=list[ReportPageRead])
def materialize_auto_report_pages(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    return [
        _page_read(item)
        for item in report_layout_service.materialize_auto_layout(db, report_id, current_user)
    ]


@router.post("/{report_id}/pages", response_model=ReportPageRead, status_code=201)
def create_report_page(
    report_id: UUID,
    payload: ReportPageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    return _page_read(report_layout_service.create_page(db, report_id, payload, current_user))


@router.patch("/{report_id}/pages/{page_id}", response_model=ReportPageRead)
def update_report_page(
    report_id: UUID,
    page_id: UUID,
    payload: ReportPageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    return _page_read(
        report_layout_service.update_page(db, report_id, page_id, payload, current_user)
    )


@router.delete("/{report_id}/pages/{page_id}", status_code=204)
def delete_report_page(
    report_id: UUID,
    page_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    report_layout_service.delete_page(db, report_id, page_id, current_user)
    return Response(status_code=204)


@router.post(
    "/{report_id}/pages/{page_id}/elements", response_model=ReportElementRead, status_code=201
)
def create_report_element(
    report_id: UUID,
    page_id: UUID,
    payload: ReportElementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    return _element_read(
        report_layout_service.create_element(db, report_id, page_id, payload, current_user)
    )


@router.patch("/{report_id}/elements/{element_id}", response_model=ReportElementRead)
def update_report_element(
    report_id: UUID,
    element_id: UUID,
    payload: ReportElementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    return _element_read(
        report_layout_service.update_element(db, report_id, element_id, payload, current_user)
    )


@router.delete("/{report_id}/elements/{element_id}", status_code=204)
def delete_report_element(
    report_id: UUID,
    element_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    report_layout_service.delete_element(db, report_id, element_id, current_user)
    return Response(status_code=204)


@router.put("/{report_id}/pages/{page_id}/elements/batch", response_model=list[ReportElementRead])
def batch_update_report_elements(
    report_id: UUID,
    page_id: UUID,
    payload: ReportElementBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_layout_service

    return [
        _element_read(item)
        for item in report_layout_service.batch_update(
            db, report_id, page_id, payload, current_user
        )
    ]


@router.get("/{report_id}/bindings")
def list_report_bindings(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service
    from app.services.report_data_binding_registry import catalog

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    return catalog(report)


@router.get("/{report_id}/chart-data/{section_key}")
def get_report_chart_data(
    report_id: UUID,
    section_key: str,
    chart_type: str = "BAR",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service
    from app.services.report_visual_data_service import chart_dataset

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    return chart_dataset(report, section_key, chart_type)


@router.get("/layout-templates", response_model=list[ReportTemplateLayoutRead])
def list_report_layout_templates(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    from app.services import report_template_layout_service

    return report_template_layout_service.list_templates(db, current_user)


@router.post(
    "/{report_id}/layout-templates", response_model=ReportTemplateLayoutRead, status_code=201
)
def save_report_layout_template(
    report_id: UUID,
    payload: ReportTemplateLayoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_template_layout_service

    return report_template_layout_service.save(db, report_id, payload, current_user)


@router.post(
    "/{report_id}/layout-templates/{template_id}/apply", response_model=list[ReportPageRead]
)
def apply_report_layout_template(
    report_id: UUID,
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_template_layout_service

    return [
        _page_read(item)
        for item in report_template_layout_service.apply(db, report_id, template_id, current_user)
    ]


@router.get("/{report_id}/html-preview", response_class=HTMLResponse)
def preview_report_html(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fast preview rendered from the exact document and CSS used by Chromium."""
    from app.services import report_publication_service
    from app.services.report_render_service import build_html

    report_service._ensure_admin(current_user)
    report = report_publication_service._report(db, report_id, current_user)
    document, _ = report_publication_service.prepare_document(report)
    return HTMLResponse(
        build_html(document),
        headers={
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": "default-src 'none'; img-src data:; style-src 'unsafe-inline'",
        },
    )


@router.get("/{report_id}/page-plan", response_model=ReportPagePlanRead)
def get_report_page_plan(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service
    from app.services.report_page_planner import plan_pages

    report = report_builder_service.get_editor(db, report_id, current_user)
    pages = plan_pages(
        [
            {
                "section_key": section.section_key,
                "section_type": section.section_type.value,
                "title": section.title,
                "is_enabled": section.is_enabled,
                "sort_order": section.sort_order,
                "content": section.content,
            }
            for section in report.sections
        ],
        report.template_key.value,
        report.editorial_config,
    )
    return {
        "mode": (report.editorial_config or {}).get("mode", "AUTO"),
        "pages": [page.as_dict() for page in pages],
    }


@router.get("/{report_id}/pdf-preview")
def preview_report_pdf(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_publication_service

    pdf, pages, report = report_publication_service.preview(db, report_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_PDF_PREVIEWED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        metadata={"page_count": pages},
        request=request,
    )
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="report-preview.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{report_id}/publications", response_model=ReportPublicationRead, status_code=201)
def generate_report_publication(
    report_id: UUID,
    payload: PublicationGenerate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_publication_service

    item = report_publication_service.generate(db, report_id, current_user, payload.idempotency_key)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_PUBLICATION_CREATED",
        module="reports",
        entity_type="ReportPublication",
        entity_id=item.id,
        event_id=item.report.event_id,
        metadata={
            "publication_number": item.publication_number,
            "sha256": item.sha256,
            "file_size": item.file_size,
            "page_count": item.page_count,
        },
        request=request,
    )
    return item


@router.get("/{report_id}/publications", response_model=list[ReportPublicationRead])
def list_report_publications(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_publication_service

    return report_publication_service.list_publications(db, report_id, current_user)


@router.get("/publications/{publication_id}/download")
def download_publication(
    publication_id: UUID,
    request: Request,
    inline: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import file_storage_service, report_publication_service

    item = report_publication_service.get_publication(db, publication_id, current_user)
    content, _ = file_storage_service.read_stored_file(item.storage_key)
    client = current_user.role.value == "CLIENT"
    action = (
        "REPORT_CLIENT_VIEWED"
        if client and inline
        else "REPORT_CLIENT_DOWNLOADED"
        if client
        else "REPORT_PUBLICATION_DOWNLOADED"
    )
    create_audit_log(
        db,
        user=current_user,
        action=action,
        module="reports",
        entity_type="ReportPublication",
        entity_id=item.id,
        event_id=item.report.event_id,
        request=request,
    )
    disposition = "inline" if inline else "attachment"
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="report-v{item.publication_number}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/publications/{publication_id}/deliver", response_model=ReportPublicationRead)
def deliver_publication(
    publication_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_publication_service

    item = report_publication_service.deliver(db, publication_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_DELIVERED",
        module="reports",
        entity_type="ReportPublication",
        entity_id=item.id,
        event_id=item.report.event_id,
        request=request,
    )
    return item


@router.post("/publications/{publication_id}/archive", response_model=ReportPublicationRead)
def archive_publication(
    publication_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_publication_service

    item = report_publication_service.archive(db, publication_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_PUBLICATION_ARCHIVED",
        module="reports",
        entity_type="ReportPublication",
        entity_id=item.id,
        event_id=item.report.event_id,
        request=request,
    )
    return item


@router.get("/{report_id}/editor", response_model=ReportEditor)
def get_report_editor(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    return report_builder_service.get_editor(db, report_id, current_user)


@router.patch("/{report_id}", response_model=ReportRead)
def update_report(
    report_id: UUID,
    payload: ReportUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_builder_service.update_report(db, report, payload)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_UPDATED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.patch("/{report_id}/sections/{section_id}", response_model=ReportSectionRead)
def update_section(
    report_id: UUID,
    section_id: UUID,
    payload: SectionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_builder_service.update_section(db, report, section_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_SECTION_UPDATED",
        module="reports",
        entity_type="ReportSection",
        entity_id=section_id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.post("/{report_id}/sections/{section_id}/ai-draft", response_model=ReportAIDraftResponse)
async def generate_section_ai_draft(
    report_id: UUID,
    section_id: UUID,
    payload: ReportAIRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    enforce(request, "ai_report_section", str(current_user.id), settings.rate_limit_ai_reports)
    try:
        result = await AIService().generate_report_section_draft(
            db, report_id, section_id, current_user, payload
        )
    except AIServiceError as exc:
        code = status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.code == "not_found":
            code = status.HTTP_404_NOT_FOUND
        elif exc.code == "timeout":
            code = status.HTTP_504_GATEWAY_TIMEOUT
        raise HTTPException(
            status_code=code, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_AI_DRAFT_REQUESTED",
        module="reports",
        entity_type="ReportSection",
        entity_id=section_id,
        event_id=report.event_id,
        metadata={
            "generation_id": result.generation_id,
            "operation": payload.operation,
            "style": payload.style,
            "length": payload.length,
            "cached": result.cached,
        },
        request=request,
    )
    return result


@router.post("/{report_id}/ai-editorial-plan", response_model=ReportAIEditorialPlanResponse)
async def generate_report_ai_editorial_plan(
    report_id: UUID,
    payload: ReportAIEditorialRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    enforce(request, "ai_report_editorial", str(current_user.id), settings.rate_limit_ai_reports)
    try:
        result = await AIService().generate_report_editorial_plan(
            db, report_id, current_user, payload
        )
    except AIServiceError as exc:
        code = (
            status.HTTP_504_GATEWAY_TIMEOUT
            if exc.code == "timeout"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(
            status_code=code, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_AI_EDITORIAL_PLAN_REQUESTED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        metadata={
            "generation_id": result.generation_id,
            "style": payload.style,
            "cached": result.cached,
        },
        request=request,
    )
    return result


@router.post("/{report_id}/ai-editorial-plan/apply", response_model=ReportAIEditorialApplyResponse)
def apply_report_ai_editorial_plan(
    report_id: UUID,
    payload: ReportAIEditorialApplyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service
    from app.services.ai import report_editorial_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    revision, updated = report_editorial_service.apply_plan(
        db, report, payload.generation_id, payload.edit_version, current_user
    )
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_AI_EDITORIAL_PLAN_APPLIED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        metadata={
            "generation_id": str(payload.generation_id),
            "rollback_revision_id": str(revision.id),
        },
        request=request,
    )
    return {"revision_id": revision.id, "report": updated}


@router.post("/{report_id}/sections", response_model=ReportSectionRead, status_code=201)
def add_custom_section(
    report_id: UUID,
    payload: CustomSectionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_builder_service.add_custom_section(db, report, payload)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_SECTION_UPDATED",
        module="reports",
        entity_type="ReportSection",
        entity_id=result.id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.put("/{report_id}/sections/order", response_model=ReportEditor)
def reorder_sections(
    report_id: UUID,
    payload: SectionOrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    report_builder_service.reorder(db, report, payload)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_SECTIONS_REORDERED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        request=request,
    )
    return report_builder_service.get_editor(db, report.id, current_user)


@router.delete("/{report_id}/sections/{section_id}", status_code=204)
def remove_custom_section(
    report_id: UUID,
    section_id: UUID,
    edit_version: int = Query(ge=1),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    report_builder_service.remove_custom_section(db, report, section_id, edit_version)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_CUSTOM_SECTION_REMOVED",
        module="reports",
        entity_type="ReportSection",
        entity_id=section_id,
        event_id=report.event_id,
        request=request,
    )
    return Response(status_code=204)


@router.post("/{report_id}/refresh", response_model=ReportEditor)
def refresh_report(
    report_id: UUID,
    edit_version: int = Query(ge=1),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_builder_service.refresh(db, report, edit_version, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_AUTOFILL_REFRESHED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.post(
    "/{report_id}/sections/{section_id}/fields/{field_key}/reset", response_model=ReportSectionRead
)
def reset_field(
    report_id: UUID,
    section_id: UUID,
    field_key: str,
    edit_version: int = Query(ge=1),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_builder_service.reset_field(
        db, report, section_id, field_key, edit_version, current_user
    )
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_FIELD_RESET_TO_AUTO",
        module="reports",
        entity_type="ReportSection",
        entity_id=section_id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.get("/{report_id}/available-evidences", response_model=list[AvailableEvidence])
def get_available_evidences(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    return report_builder_service.available_evidences(db, report)


@router.post("/{report_id}/evidences", response_model=ReportEvidenceRead, status_code=201)
def add_report_evidence(
    report_id: UUID,
    payload: EvidenceAdd,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_builder_service.add_evidence(db, report, payload)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_EVIDENCE_ADDED",
        module="reports",
        entity_type="ReportEvidence",
        entity_id=result.id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.delete("/{report_id}/evidences/{item_id}", status_code=204)
def remove_report_evidence(
    report_id: UUID,
    item_id: UUID,
    edit_version: int = Query(ge=1),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    report_builder_service.remove_evidence(db, report, item_id, edit_version)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_EVIDENCE_REMOVED",
        module="reports",
        entity_type="ReportEvidence",
        entity_id=item_id,
        event_id=report.event_id,
        request=request,
    )
    return Response(status_code=204)


@router.patch("/{report_id}/evidences/{item_id}", response_model=ReportEvidenceRead)
def update_report_evidence(
    report_id: UUID,
    item_id: UUID,
    payload: EvidenceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_builder_service.update_evidence(db, report, item_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_EVIDENCE_UPDATED",
        module="reports",
        entity_type="ReportEvidence",
        entity_id=item_id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.post("/{report_id}/revisions", response_model=ReportRevisionRead, status_code=201)
def create_revision(
    report_id: UUID,
    payload: RevisionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service, report_revision_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    result = report_revision_service.create(
        db, report, current_user, payload.edit_version, payload.note
    )
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_REVISION_CREATED",
        module="reports",
        entity_type="ReportRevision",
        entity_id=result.id,
        event_id=report.event_id,
        request=request,
    )
    return result


@router.get("/{report_id}/revisions", response_model=list[ReportRevisionRead])
def list_revisions(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service, report_revision_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    return report_revision_service.list_all(db, report)


@router.post("/{report_id}/revisions/{revision_id}/restore", response_model=ReportEditor)
def restore_revision(
    report_id: UUID,
    revision_id: UUID,
    payload: RestoreRevision,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service, report_revision_service

    report = report_builder_service.get_editor(db, report_id, current_user)
    report_service._ensure_admin(current_user)
    report_revision_service.restore(db, report, revision_id, payload.edit_version)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_REVISION_RESTORED",
        module="reports",
        entity_type="ReportRevision",
        entity_id=revision_id,
        event_id=report.event_id,
        request=request,
    )
    return report_builder_service.get_editor(db, report.id, current_user)


@router.get("/{report_id}/preview", response_model=ReportEditor)
def preview_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_builder_service

    return report_builder_service.get_editor(db, report_id, current_user)


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return report_service.ensure_can_access_report(db, current_user, report_id)


@router.get("/{report_id}/download")
def download_report(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import file_storage_service, report_publication_service

    report = report_service.ensure_can_access_report(db, current_user, report_id)
    publication = report_publication_service.latest_publication(db, report_id, current_user)
    if publication:
        content, _ = file_storage_service.read_stored_file(publication.storage_key)
    else:
        content, _, report = report_publication_service.preview(db, report_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_DOWNLOADED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        status="SUCCESS",
        metadata={
            "filename": f"report-{report.id}.pdf",
            "publication_id": str(publication.id) if publication else None,
            "premium": True,
        },
        request=request,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.pdf"'},
    )


@router.patch("/{report_id}/deliver", response_model=ReportRead)
def mark_report_delivered(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.services import report_publication_service

    before = report_service.ensure_can_access_report(db, current_user, report_id)
    old_data = serialize_model_for_audit(before)
    publication = report_publication_service.deliver_latest(
        db, report_id=report_id, user=current_user
    )
    report = publication.report
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_DELIVERED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(report),
        metadata={"publication_id": str(publication.id)},
        request=request,
    )
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = report_service.ensure_can_access_report(db, current_user, report_id)
    report = report_service.archive_report(db, report_id=report_id, current_user=current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_ARCHIVED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        old_data=serialize_model_for_audit(before),
        new_data=serialize_model_for_audit(report),
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
