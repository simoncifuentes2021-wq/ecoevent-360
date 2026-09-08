from types import SimpleNamespace

from app.services import report_visual_audit_service as service


def _document(sections, evidences=()):
    return SimpleNamespace(
        sections=tuple(sections), evidences=tuple(evidences),
        report={"template_key": "COMPLETE"}, editorial_config={},
    )


def test_visual_audit_detects_dense_pages_and_autocorrects_without_hiding_content(monkeypatch):
    sections = [
        {"section_key": "operations", "section_type": "OPERATIONS", "title": "Operación", "is_enabled": True, "sort_order": 0, "content": {"text": "x", "fields": [{"key": str(i), "value": i} for i in range(12)], "items": []}},
        {"section_key": "staff", "section_type": "STAFF", "title": "Equipo", "is_enabled": True, "sort_order": 1, "content": {"text": "x", "fields": [{"key": str(i), "value": i} for i in range(12)], "items": []}},
    ]
    report = SimpleNamespace(editorial_config={}, sections=sections)
    document = _document(sections)
    monkeypatch.setattr(service.report_publication_service, "prepare_document", lambda _report: (document, {}))
    monkeypatch.setattr(service, "build_html", lambda _document: "<html></html>")
    monkeypatch.setattr(service, "_browser_findings", lambda _html: [])

    result = service.audit_correct_and_verify(report, {"operations", "staff"})

    assert result["corrections_applied"] == ["operations", "staff"]
    assert report.editorial_config["page_overrides"]["operations"]["mode"] == "OWN_PAGE"
    assert report.editorial_config["visual_config"]["visual_density"] == "COMPACT"
    assert all(section["is_enabled"] for section in sections)


def test_visual_audit_reports_chart_without_data_and_browser_failure(monkeypatch):
    sections = [{"section_key": "forms", "section_type": "FORMS", "title": "Formularios", "is_enabled": True, "sort_order": 0, "layout_variant": "FEATURE_CHART", "content": {"fields": [], "items": []}}]
    document = _document(sections)
    monkeypatch.setattr(service.report_publication_service, "prepare_document", lambda _report: (document, {}))
    monkeypatch.setattr(service, "build_html", lambda _document: "<html></html>")
    monkeypatch.setattr(service, "_browser_findings", lambda _html: (_ for _ in ()).throw(RuntimeError("browser")))
    result = service.audit(SimpleNamespace())
    codes = {item["code"] for item in result["findings"]}
    assert {"CHART_WITHOUT_DATA", "BROWSER_AUDIT_UNAVAILABLE"}.issubset(codes)
    assert result["browser_checked"] is False


def test_visual_audit_rejects_privacy_markers_and_internal_editorial_copy(monkeypatch):
    sections = [{"section_key": "impact", "section_type": "ENVIRONMENTAL_IMPACT", "title": "Impacto", "is_enabled": True, "sort_order": 0, "content": {"text": "La sección debe mostrar 31.[PHONE] kg.", "fields": [], "items": []}}]
    document = _document(sections)
    monkeypatch.setattr(service.report_publication_service, "prepare_document", lambda _report: (document, {}))
    monkeypatch.setattr(service, "build_html", lambda _document: "<html></html>")
    monkeypatch.setattr(service, "_browser_findings", lambda _html: [])

    result = service.audit(SimpleNamespace())

    codes = {item["code"] for item in result["findings"]}
    assert {"CLIENT_REDACTION_MARKER", "INTERNAL_EDITORIAL_COPY"}.issubset(codes)
    assert result["passed"] is False
