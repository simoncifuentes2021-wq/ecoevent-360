"""Local-only certification for editable professional report components v2."""

from __future__ import annotations

import json
import os
import re
import atexit
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import Page, sync_playwright

REPORT_ID = os.getenv("REPORT_CERT_ID", "983ac1bc-899b-4013-9b61-a47608ec3596")
API = os.getenv("REPORT_CERT_API", "http://127.0.0.1:8000/api/v1")
WEB = os.getenv("REPORT_CERT_WEB", "http://localhost:3000")


def local_env() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (Path(__file__).parents[1] / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            result[key] = value
    return result


def request(path: str, token: str, method: str = "GET", payload: dict | None = None) -> bytes:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    with urlopen(  # noqa: S310 - fixed local certification URL
        Request(f"{API}{path}", data=body, headers=headers, method=method), timeout=90
    ) as response:
        return response.read()


def login() -> dict:
    env = local_env()
    payload = json.dumps(
        {"email": env["FIRST_SUPER_ADMIN_EMAIL"], "password": env["FIRST_SUPER_ADMIN_PASSWORD"]}
    ).encode()
    with urlopen(  # noqa: S310 - fixed local certification URL
        Request(f"{API}/auth/login", data=payload, headers={"Content-Type": "application/json"}),
        timeout=15,
    ) as response:
        return json.load(response)


def open_editor(page: Page, session: dict) -> None:
    page.goto(WEB)
    page.evaluate(
        "([token,user]) => { localStorage.setItem('ecoevent360.access_token', token); "
        "localStorage.setItem('ecoevent360.user', JSON.stringify(user)); }",
        [session["access_token"], session["user"]],
    )
    page.goto(f"{WEB}/reports/{REPORT_ID}/edit", wait_until="networkidle")
    page.locator('iframe[title="Vista previa exacta y editable del reporte"]').wait_for()


def override(element_key: str, *, x: float = 0, y: float = 0, width: float | None = None, height: float | None = None) -> dict:
    return {
        "element_key": element_key,
        "page_key": None,
        "x_offset": x,
        "y_offset": y,
        "width_scale": 1,
        "height_scale": 1,
        "box_width": width,
        "box_height": height,
        "rotation": 0,
        "z_index": 2,
        "locked": False,
        "visible": True,
    }


def main() -> None:
    session = login()
    token = session["access_token"]
    overrides = json.loads(request(f"/reports/{REPORT_ID}/layout-overrides", token))
    fields = set(override("sample"))
    original = [{key: value for key, value in item.items() if key in fields} for item in overrides]

    def restore_original() -> None:
        request(f"/reports/{REPORT_ID}/layout-overrides", token, "DELETE")
        if original:
            request(
                f"/reports/{REPORT_ID}/layout-overrides/batch",
                token,
                "PUT",
                {"overrides": original},
            )

    atexit.register(restore_original)
    request(f"/reports/{REPORT_ID}/layout-overrides", token, "DELETE")
    baseline = request(f"/reports/{REPORT_ID}/html-preview", token).decode()
    types = Counter(re.findall(r'data-report-element-type="([^"]+)"', baseline))
    keys = re.findall(r'data-report-element-key="([^"]+)"', baseline)
    assert types["COVER_TITLE"] and types["SECTION_TITLE"] and types["TEXT_BLOCK"]
    assert len(keys) == len(set(keys)), "Rendered element keys must be unique"
    output = Path(__file__).parents[2] / "artifacts" / "report-layout-override-cert-v2"
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1973, "height": 1248})
        open_editor(page, session)
        page.screenshot(path=output / "title-before.png", full_page=True)
        page.get_by_role("button", name="Editar posiciones", exact=True).click()
        frame = page.locator('iframe[title="Vista previa exacta y editable del reporte"]').content_frame
        for element_type in (
            "COVER_TITLE",
            "SECTION_TITLE",
            "TEXT_BLOCK",
            "HIGHLIGHT",
            "BIG_NUMBERS",
            "METRIC_LIST",
        ):
            node = frame.locator(f'[data-report-element-type="{element_type}"]').first
            node.evaluate("element => element.click()")
            assert frame.locator(".report-resize-handle").count() == 1, element_type
        page.screenshot(path=output / "final-editor.png", full_page=True)
        page.get_by_role("button", name="Terminar edición", exact=True).click()
        request(
            f"/reports/{REPORT_ID}/layout-overrides",
            token,
            "PUT",
            override("cover.title", x=18, y=10, width=500, height=170),
        )
        page.reload(wait_until="networkidle")
        page.screenshot(path=output / "title-moved.png", full_page=True)
        (output / "title-pdf.pdf").write_bytes(request(f"/reports/{REPORT_ID}/pdf-preview", token))
        request(f"/reports/{REPORT_ID}/layout-overrides", token, "DELETE")
        text_key = next(key for key in keys if ".text." in key)
        request(
            f"/reports/{REPORT_ID}/layout-overrides",
            token,
            "PUT",
            override(text_key, x=14, y=8, width=430, height=135),
        )
        page.reload(wait_until="networkidle")
        page.screenshot(path=output / "text-moved.png", full_page=True)
        (output / "text-pdf.pdf").write_bytes(request(f"/reports/{REPORT_ID}/pdf-preview", token))
        request(f"/reports/{REPORT_ID}/layout-overrides", token, "DELETE")
        reset_html = request(f"/reports/{REPORT_ID}/html-preview", token).decode()
        assert reset_html == baseline, "Reset did not restore the exact canonical HTML"
        page.reload(wait_until="networkidle")
        page.screenshot(path=output / "reset.png", full_page=True)
        browser.close()
    restore_original()
    print(f"v2=ok types={dict(types)} unique_keys={len(keys)} reset_exact=true artifact={output}")


if __name__ == "__main__":
    main()
