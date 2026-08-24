"""Local E2E certification for the professional report layout editor v3."""

from __future__ import annotations

import atexit
import json
import os
import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from certify_report_layout_overrides_v2 import WEB, login, override, request

REPORT_ID = os.getenv("REPORT_CERT_ID", "c7f23208-331d-4b89-9eaa-7513a6f8480b")
OUTPUT = Path(__file__).parents[2] / "artifacts" / "report-layout-override-cert-v3"


def open_editor(page: Page, session: dict) -> None:
    page.goto(WEB)
    page.evaluate(
        "([token,user]) => { localStorage.setItem('ecoevent360.access_token', token); "
        "localStorage.setItem('ecoevent360.user', JSON.stringify(user)); }",
        [session["access_token"], session["user"]],
    )
    page.goto(f"{WEB}/reports/{REPORT_ID}/edit", wait_until="networkidle")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    session = login()
    token = session["access_token"]
    fields = set(override("sample"))
    previous = json.loads(request(f"/reports/{REPORT_ID}/layout-overrides", token))
    original = [{key: value for key, value in item.items() if key in fields} for item in previous]

    def restore() -> None:
        request(f"/reports/{REPORT_ID}/layout-overrides", token, "DELETE")
        if original:
            request(f"/reports/{REPORT_ID}/layout-overrides/batch", token, "PUT", {"overrides": original})

    atexit.register(restore)
    request(f"/reports/{REPORT_ID}/layout-overrides", token, "DELETE")
    baseline = request(f"/reports/{REPORT_ID}/html-preview", token).decode()
    types = re.findall(r'data-report-element-type="([^"]+)"', baseline)
    assert "CHART" in types and "IMAGE" in types and "PHOTO_GRID" in types
    assert re.search(r'data-report-element-type="CHART" data-report-resize-mode="box"', baseline)
    assert re.search(r'data-report-element-type="IMAGE" data-report-resize-mode="box"', baseline)
    assert "data:image/" in baseline and "private/" not in baseline
    (OUTPUT / "chart-pdf.pdf").write_bytes(request(f"/reports/{REPORT_ID}/pdf-preview", token))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1973, "height": 1248})
        open_editor(page, session)
        page.screenshot(path=OUTPUT / "fixture-baseline.png", full_page=True)
        page.get_by_role("button", name="Editar posiciones", exact=True).click()
        frame = page.locator('iframe[title="Vista previa exacta y editable del reporte"]').content_frame
        editable_count = frame.locator("[data-report-element-key]").count()
        assert 20 <= editable_count <= 80

        chart = frame.locator('[data-report-element-type="CHART"]').first
        chart.evaluate("node => { node.scrollIntoView({block:'center'}); node.click(); }")
        page.keyboard.press("Shift+ArrowRight")
        page.wait_for_timeout(400)
        page.screenshot(path=OUTPUT / "chart-moved.png", full_page=True)

        image = frame.locator('[data-report-element-type="IMAGE"]').first
        image.evaluate("node => { node.scrollIntoView({block:'center'}); node.click(); }")
        handle = frame.locator(".report-resize-handle")
        box = handle.bounding_box()
        assert box
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + 35, box["y"] + 24)
        page.mouse.up()
        page.wait_for_timeout(400)
        page.screenshot(path=OUTPUT / "image-resized.png", full_page=True)
        pdf = request(f"/reports/{REPORT_ID}/pdf-preview", token)
        (OUTPUT / "image-pdf.pdf").write_bytes(pdf)

        gallery = frame.locator('[data-report-element-type="PHOTO_GRID"]').first
        gallery.evaluate("node => { node.scrollIntoView({block:'center'}); node.click(); }")
        page.keyboard.press("ArrowDown")
        page.screenshot(path=OUTPUT / "gallery-moved.png", full_page=True)
        (OUTPUT / "gallery-pdf.pdf").write_bytes(request(f"/reports/{REPORT_ID}/pdf-preview", token))

        choices = [
            frame.locator('[data-report-element-type="KPI"]').first,
            frame.locator('[data-report-element-type="SECTION_TITLE"]').first,
            frame.locator('[data-report-element-type="TEXT_BLOCK"]').first,
        ]
        choices[0].evaluate("node => node.click()")
        for choice in choices[1:]:
            choice.evaluate("node => node.dispatchEvent(new MouseEvent('click',{bubbles:true,ctrlKey:true}))")
        page.get_by_text("3 elementos seleccionados", exact=True).wait_for()
        page.screenshot(path=OUTPUT / "multiselect.png", full_page=True)
        page.keyboard.press("Shift+ArrowDown")
        page.keyboard.press("Control+z")
        page.keyboard.press("Control+y")
        page.get_by_role("button", name="Alinear izquierda").click()
        page.get_by_role("button", name="Distribuir horizontalmente").click()
        page.wait_for_timeout(400)
        page.screenshot(path=OUTPUT / "aligned.png", full_page=True)

        first_box = choices[0].bounding_box()
        assert first_box
        page.mouse.move(first_box["x"] + first_box["width"] / 2, first_box["y"] + first_box["height"] / 2)
        page.mouse.down()
        page.mouse.move(397, first_box["y"] + first_box["height"] / 2)
        page.wait_for_timeout(100)
        page.screenshot(path=OUTPUT / "guides.png", full_page=True)
        page.mouse.up()
        page.wait_for_timeout(500)
        page.screenshot(path=OUTPUT / "final-editor.png", full_page=True)

        saved = json.loads(request(f"/reports/{REPORT_ID}/layout-overrides", token))
        assert len(saved) >= 5
        page.reload(wait_until="networkidle")
        reloaded = json.loads(request(f"/reports/{REPORT_ID}/layout-overrides", token))
        assert {(x["element_key"], x["x_offset"], x["y_offset"]) for x in saved} == {
            (x["element_key"], x["x_offset"], x["y_offset"]) for x in reloaded
        }
        final_pdf = request(f"/reports/{REPORT_ID}/pdf-preview", token)
        assert final_pdf.startswith(b"%PDF-") and len(final_pdf) > 10_000
        (OUTPUT / "final-pdf.pdf").write_bytes(final_pdf)
        page.get_by_role("button", name="Editar posiciones", exact=True).click()
        frame = page.locator('iframe[title="Vista previa exacta y editable del reporte"]').content_frame
        reset_choices = [
            frame.locator('[data-report-element-type="KPI"]').first,
            frame.locator('[data-report-element-type="SECTION_TITLE"]').first,
            frame.locator('[data-report-element-type="TEXT_BLOCK"]').first,
        ]
        reset_choices[0].evaluate("node => node.click()")
        for choice in reset_choices[1:]:
            choice.evaluate("node => node.dispatchEvent(new MouseEvent('click',{bubbles:true,ctrlKey:true}))")
        page.get_by_role("button", name="Restablecer seleccionados", exact=True).click()
        page.wait_for_timeout(500)
        after_selected_reset = json.loads(request(f"/reports/{REPORT_ID}/layout-overrides", token))
        assert len(after_selected_reset) < len(reloaded)
        page.get_by_role("button", name="Restablecer todo", exact=True).click()
        page.wait_for_timeout(500)
        reset_html = request(f"/reports/{REPORT_ID}/html-preview", token).decode()
        assert reset_html == baseline
        page.reload(wait_until="networkidle")
        page.screenshot(path=OUTPUT / "reset-baseline.png", full_page=True)
        browser.close()
    restore()
    print(f"v3=ok editable={editable_count} chart=true image=true gallery=true persistence=true reset_exact=true pdf_bytes={len(final_pdf)}")


if __name__ == "__main__":
    main()
