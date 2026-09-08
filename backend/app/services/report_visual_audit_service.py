"""Post-render visual audit and bounded, non-destructive corrections for AI reports."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, dataclass

from app.services import report_publication_service
from app.services.report_page_planner import EditorialDensity, plan_pages
from app.services.report_render_service import build_html

CLIENT_REDACTION_MARKER = ("[PHONE]", "[EMAIL]", "[DOCUMENT_ID]", "[PRIVATE_URL]", "[SECRET]")
INTERNAL_COPY_MARKERS = (
    "esta sección debe", "la sección debe", "la lectura debe", "debe limitarse",
    "deben rotularse", "no se debe inferir", "requiere conservarse",
    "los datos suministrados", "información disponible permite comunicar",
)


@dataclass(frozen=True)
class VisualAuditFinding:
    code: str
    severity: str
    message: str
    page: int | None = None
    section_keys: tuple[str, ...] = ()
    auto_fixed: bool = False

    def as_dict(self) -> dict:
        value = asdict(self)
        value["section_keys"] = list(self.section_keys)
        return value


def _has_numeric_data(section: dict) -> bool:
    content = section.get("content") or {}
    values = [item.get("value") for item in [*(content.get("fields") or []), *(content.get("items") or [])]]
    return any(isinstance(value, (int, float)) for value in values)


def _structural_findings(document) -> list[VisualAuditFinding]:
    enabled = [item for item in document.sections if item.get("is_enabled") and item.get("section_type") != "COVER"]
    by_key = {item.get("section_key"): item for item in enabled}
    plans = plan_pages(list(document.sections), document.report["template_key"], document.editorial_config)
    findings: list[VisualAuditFinding] = []
    rendered_keys = {key for page in plans for key in page.section_keys}
    missing = tuple(sorted(set(by_key).difference(rendered_keys)))
    if missing:
        findings.append(VisualAuditFinding("SECTION_NOT_RENDERED", "ERROR", "Hay secciones visibles fuera del plan de páginas.", section_keys=missing))
    for page in plans:
        sections = [by_key[key] for key in page.section_keys if key in by_key]
        if not sections:
            findings.append(VisualAuditFinding("EMPTY_PAGE", "ERROR", "La página no contiene una sección visible.", page=page.number))
            continue
        if page.density == EditorialDensity.HIGH and len(sections) > 1:
            findings.append(VisualAuditFinding("DENSE_PAGE", "WARNING", "La página combina demasiada información.", page=page.number, section_keys=page.section_keys))
        for section in sections:
            content = section.get("content") or {}
            narrative = str(content.get("text") or "")
            if any(marker in narrative for marker in CLIENT_REDACTION_MARKER):
                findings.append(VisualAuditFinding("CLIENT_REDACTION_MARKER", "ERROR", "El texto contiene un marcador interno de privacidad.", page=page.number, section_keys=(section["section_key"],)))
            if any(marker in narrative.lower() for marker in INTERNAL_COPY_MARKERS):
                findings.append(VisualAuditFinding("INTERNAL_EDITORIAL_COPY", "ERROR", "El texto contiene instrucciones internas no aptas para clientes.", page=page.number, section_keys=(section["section_key"],)))
            score = len(content.get("fields") or []) + len(content.get("items") or [])
            if score > 18 or len(str(content.get("text") or "")) > 3500:
                findings.append(VisualAuditFinding("SECTION_OVERFLOW_RISK", "WARNING", "La sección excede la capacidad editorial recomendada.", page=page.number, section_keys=(section["section_key"],)))
            if str(section.get("layout_variant")) == "FEATURE_CHART" and not _has_numeric_data(section):
                findings.append(VisualAuditFinding("CHART_WITHOUT_DATA", "WARNING", "La composición de gráfico no tiene datos numéricos.", page=page.number, section_keys=(section["section_key"],)))
    assigned_photos = [item for item in document.evidences if item.get("section_key")]
    counts: dict[str, int] = {}
    for photo in assigned_photos:
        counts[photo["section_key"]] = counts.get(photo["section_key"], 0) + 1
    for key, count in counts.items():
        if count > 6:
            findings.append(VisualAuditFinding("PHOTO_DENSITY", "WARNING", "Demasiadas fotografías compiten en una sección.", section_keys=(key,)))
    return findings


def _browser_findings(html: str) -> list[VisualAuditFinding]:
    from playwright.sync_api import sync_playwright

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 794, "height": 1123}, java_script_enabled=False)
            page.route("**/*", lambda route: route.abort())
            page.set_content(html, wait_until="domcontentloaded", timeout=15_000)
            page.emulate_media(media="print")
            rows = page.locator(".page").evaluate_all("""pages => pages.map((page, index) => ({
              page: index + 1,
              sections: (page.dataset.reportSections || '').split(',').filter(Boolean),
              overflow: page.scrollHeight > page.clientHeight + 2 || [...page.querySelectorAll('img,svg,table')].some(el => el.getBoundingClientRect().right > page.getBoundingClientRect().right + 2 || el.getBoundingClientRect().bottom > page.getBoundingClientRect().bottom + 2),
              empty: !(page.innerText || '').trim() && !page.querySelector('img,svg')
            }))""")
        finally:
            browser.close()
    findings = []
    for row in rows:
        if row["overflow"]:
            findings.append(VisualAuditFinding("DOM_OVERFLOW", "ERROR", "El render detectó contenido cortado o fuera de página.", row["page"], tuple(row["sections"])))
        if row["empty"]:
            findings.append(VisualAuditFinding("EMPTY_RENDERED_PAGE", "ERROR", "El render produjo una página vacía.", row["page"], tuple(row["sections"])))
    return findings


def audit(report, *, include_browser: bool = True) -> dict:
    document, _ = report_publication_service.prepare_document(report)
    html = build_html(document)
    findings = _structural_findings(document)
    browser_checked = False
    if include_browser:
        try:
            findings.extend(_browser_findings(html))
            browser_checked = True
        except Exception:
            findings.append(VisualAuditFinding("BROWSER_AUDIT_UNAVAILABLE", "WARNING", "No se pudo ejecutar la medición visual del navegador."))
    return {"passed": not any(item.severity == "ERROR" for item in findings), "browser_checked": browser_checked, "findings": [item.as_dict() for item in findings]}


def autocorrect(report, audit_result: dict, accepted: set[str]) -> list[str]:
    config = dict(report.editorial_config or {})
    overrides = dict(config.get("page_overrides") or {})
    visual = dict(config.get("visual_config") or {})
    corrected: list[str] = []
    correctable = {"DENSE_PAGE", "SECTION_OVERFLOW_RISK", "DOM_OVERFLOW", "PHOTO_DENSITY"}
    for finding in audit_result.get("findings") or []:
        if finding.get("code") not in correctable:
            continue
        for key in finding.get("section_keys") or []:
            if key in accepted:
                overrides[key] = {"mode": "OWN_PAGE", "group_with": None}
                corrected.append(key)
    if corrected:
        visual["visual_density"] = "COMPACT"
        config.update({"mode": "CUSTOM", "page_overrides": overrides, "visual_config": visual})
        report.editorial_config = config
    return sorted(set(corrected))


def audit_correct_and_verify(report, accepted: set[str]) -> dict:
    initial = audit(report)
    corrected = autocorrect(report, initial, accepted)
    final = audit(report) if corrected else initial
    return {"initial": initial, "corrections_applied": corrected, "final": final}
