"""Bounded WeasyPrint PDF renderer and validation."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from io import BytesIO
from threading import BoundedSemaphore

from pypdf import PdfReader
from app.services.report_render_service import ReportRenderDocument, build_html

_slots = BoundedSemaphore(2)
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="report-pdf")


def render(document: ReportRenderDocument, *, timeout_seconds: int = 45) -> tuple[bytes, int]:
    if not _slots.acquire(blocking=False):
        raise RuntimeError("PDF renderer is busy")
    try:
        future = _pool.submit(_chromium_pdf, build_html(document))
        try:
            pdf = future.result(timeout=timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            raise RuntimeError("PDF rendering timed out") from exc
    finally:
        _slots.release()
    if not pdf.startswith(b"%PDF-") or len(pdf) < 1000 or len(pdf) > 50 * 1024 * 1024:
        raise RuntimeError("Invalid PDF output")
    reader = PdfReader(BytesIO(pdf))
    if not reader.pages:
        raise RuntimeError("PDF has no pages")
    return pdf, len(reader.pages)


def _chromium_pdf(html: str) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(java_script_enabled=False, offline=True)
            page = context.new_page()
            page.route("**/*", lambda route: route.abort())
            page.set_content(html, wait_until="domcontentloaded", timeout=15_000)
            return page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=False,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
        finally:
            browser.close()
