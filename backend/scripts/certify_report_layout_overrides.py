"""Local visual smoke test for the canonical report position editor."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.services.report_render_service import (
    _apply_layout_overrides,
    _feature_html,
    _kpis,
    _photos,
    normalize_theme,
)

REPORT_ID = os.getenv("REPORT_CERT_ID", "983ac1bc-899b-4013-9b61-a47608ec3596")
API = os.getenv("REPORT_CERT_API", "http://127.0.0.1:8000/api/v1")
WEB = os.getenv("REPORT_CERT_WEB", "http://localhost:3000")


def _local_env() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (Path(__file__).parents[1] / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            result[key] = value
    return result


def _login() -> dict:
    env = _local_env()
    payload = json.dumps(
        {"email": env["FIRST_SUPER_ADMIN_EMAIL"], "password": env["FIRST_SUPER_ADMIN_PASSWORD"]}
    ).encode()
    request = Request(f"{API}/auth/login", data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed local URL
        return json.load(response)


def main() -> None:
    kpi = _kpis([{"key": "attendance", "label": "Asistencia", "value": 1200}], "event")
    image = _photos(
        [{"section_key": "evidence", "evidence_id": "photo-1", "uri": "data:image/png;base64,AA=="}],
        "photos",
    )
    chart = _feature_html(
        [{"section_key": "waste", "section_type": "WASTE", "title": "Residuos", "layout_variant": "FEATURE_CHART", "content": {"fields": [], "items": [{"label": "Vidrio", "value": 12}]}}],
        [],
        normalize_theme({}),
    )
    assert 'data-report-element-key="event.kpi.attendance"' in kpi
    assert 'data-report-element-key="evidence.image.photo-1"' in image
    assert 'data-report-element-key="waste.chart.main"' in chart
    baseline = '<div data-report-element-key="event.kpi.attendance">1200</div>'
    assert _apply_layout_overrides(baseline, tuple()) == baseline
    transformed = _apply_layout_overrides(
        baseline,
        ({"element_key": "event.kpi.attendance", "x_offset": 8, "y_offset": 4},),
    )
    assert "translate(8.0000px,4.0000px)" in transformed
    session = _login()
    output = Path(__file__).parents[2] / "artifacts" / "report-layout-override-cert"
    output.mkdir(parents=True, exist_ok=True)
    pdf_request = Request(
        f"{API}/reports/{REPORT_ID}/pdf-preview",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    with urlopen(pdf_request, timeout=90) as response:  # noqa: S310 - fixed local URL
        pdf = response.read()
    assert pdf.startswith(b"%PDF-") and len(pdf) > 1_000
    (output / "reporte-profesional.pdf").write_bytes(pdf)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1973, "height": 1248})
        page.goto(WEB)
        page.evaluate(
            "([token,user]) => { localStorage.setItem('ecoevent360.access_token', token); "
            "localStorage.setItem('ecoevent360.user', JSON.stringify(user)); }",
            [session["access_token"], session["user"]],
        )
        page.goto(f"{WEB}/reports/{REPORT_ID}/edit", wait_until="networkidle")
        page.get_by_role("button", name="Editar posiciones").click()
        page.get_by_role("button", name="Terminar edición").wait_for()
        frame = page.locator('iframe[title="Vista previa exacta y editable del reporte"]').content_frame
        editable_count = frame.locator("[data-report-element-key]").count()
        assert editable_count > 0, "The canonical HTML contains no editable elements"
        assert frame.locator(".report-resize-handle").count() == 0
        first = frame.locator("[data-report-element-key]").first
        first.evaluate("node => node.click()")
        assert frame.locator(".report-resize-handle").count() == 1
        page.screenshot(path=output / "editor-profesional.png", full_page=True)
        browser.close()
    print(
        f"visual_editor=ok editable_elements={editable_count} "
        f"pdf_bytes={len(pdf)} artifact={output}"
    )


if __name__ == "__main__":
    main()
