"""Read-only certification of every report section/layout combination."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parents[1]))

from playwright.sync_api import sync_playwright
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.core import User
from app.models.enums import UserRole
from app.services import report_builder_service, report_publication_service
from app.services.report_render_service import build_html
from scripts.generate_report_pdf_fixtures import _image

REPORT_ID = UUID("6a68bbbb-793a-420b-a12c-1149ffff5d2e")
LAYOUTS = (
    "HERO_IMAGE_TEXT", "KPI_GRID", "TWO_COLUMN", "METRIC_LIST", "FEATURE_CHART",
    "PHOTO_GRID", "EDITORIAL", "TEXT_IMAGE", "BIG_NUMBERS",
)
IMAGE_LAYOUTS = {"HERO_IMAGE_TEXT", "PHOTO_GRID", "TEXT_IMAGE"}
COVER_STYLES = ("FULL_PHOTO", "SIDE_PHOTO", "EDITORIAL", "MINIMAL_PREMIUM")
OUTPUT = Path("../artifacts/report-composition-certification.json")


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.role == UserRole.SUPER_ADMIN))
        report = report_builder_service.get_editor(db, REPORT_ID, user)
        base, _ = report_publication_service.prepare_document(report)

    source_sections = [
        section for section in base.sections if section.get("section_type") != "COVER"
    ]
    results: list[dict] = []
    cover_results: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 794, "height": 1123}, java_script_enabled=False)
        page.route("**/*", lambda route: route.abort())
        try:
            for layout in LAYOUTS:
                sections = []
                photos = []
                for index, original in enumerate(source_sections):
                    section = {**original, "layout_variant": layout, "is_enabled": True}
                    sections.append(section)
                    photos.append({
                        "evidence_id": f"cert-{layout.lower()}-{index}",
                        "section_key": section["section_key"],
                        "caption": None,
                        "uri": _image(index),
                        "warning": None,
                    })
                cover = next(
                    (item for item in base.sections if item.get("section_type") == "COVER"),
                    None,
                )
                config = {
                    **base.editorial_config,
                    "visual_config": {"preset": "AUTO"},
                    "section_visuals": {},
                    "page_overrides": {
                        section["section_key"]: {"mode": "OWN_PAGE", "group_with": None}
                        for section in sections
                    },
                    "cover_show_photo": False,
                }
                document = replace(
                    base,
                    sections=tuple(([cover] if cover else []) + sections),
                    evidences=tuple(photos),
                    editorial_config=config,
                )
                page.set_content(build_html(document), wait_until="domcontentloaded", timeout=30_000)
                page.emulate_media(media="print")
                rows = page.locator(".page").evaluate_all(
                    """nodes => nodes.map((node, pageIndex) => ({
                      page: pageIndex + 1,
                      keys: (node.dataset.reportSections || '').split(',').filter(Boolean),
                      images: node.querySelectorAll('img').length,
                      textLength: (node.innerText || '').trim().length,
                      clientHeight: node.clientHeight,
                      scrollHeight: node.scrollHeight,
                      clientWidth: node.clientWidth,
                      scrollWidth: node.scrollWidth,
                      overflow: node.scrollHeight > node.clientHeight + 2 ||
                        [...node.querySelectorAll('img,svg,table')].some(el =>
                          el.getBoundingClientRect().right > node.getBoundingClientRect().right + 2 ||
                          el.getBoundingClientRect().bottom > node.getBoundingClientRect().bottom + 2)
                    }))"""
                )
                by_key = {key: row for row in rows for key in row["keys"]}
                for section in sections:
                    key = section["section_key"]
                    row = by_key.get(key)
                    results.append({
                        "section_key": key,
                        "section_type": section["section_type"],
                        "layout": layout,
                        "rendered": row is not None,
                        "image_required": layout in IMAGE_LAYOUTS,
                        "image_rendered": bool(row and row["images"]),
                        "content_rendered": bool(row and row["textLength"] > 20),
                        "overflow": bool(row and row["overflow"]),
                        "bounds": ({key: row[key] for key in ("clientHeight", "scrollHeight", "clientWidth", "scrollWidth")} if row else None),
                        "page": row["page"] if row else None,
                    })
            cover = next(
                item for item in base.sections if item.get("section_type") == "COVER"
            )
            cover_photo = {
                "evidence_id": "cert-cover",
                "section_key": None,
                "caption": None,
                "uri": _image(99),
                "warning": None,
            }
            for style in COVER_STYLES:
                document = replace(
                    base,
                    sections=({**cover, "is_enabled": True},),
                    evidences=(cover_photo,),
                    editorial_config={
                        **base.editorial_config,
                        "cover_style": style,
                        "cover_show_photo": True,
                        "cover_evidence_id": "cert-cover",
                    },
                )
                page.set_content(build_html(document), wait_until="domcontentloaded", timeout=30_000)
                row = page.locator(".cover").evaluate(
                    """node => ({
                      rendered: Boolean(node),
                      textLength: (node.innerText || '').trim().length,
                      hasPhoto: node.getAttribute('style')?.includes('background-image') || false,
                      overflow: node.scrollHeight > node.clientHeight + 2
                    })"""
                )
                cover_results.append({
                    "section_key": "cover",
                    "section_type": "COVER",
                    "layout": style,
                    "rendered": row["rendered"],
                    "image_required": style != "MINIMAL_PREMIUM",
                    "image_rendered": row["hasPhoto"],
                    "content_rendered": row["textLength"] > 20,
                    "overflow": row["overflow"],
                })
        finally:
            browser.close()

    failures = [
        item for item in [*results, *cover_results]
        if not item["rendered"] or not item["content_rendered"] or item["overflow"]
        or (item["image_required"] and not item["image_rendered"])
    ]
    payload = {
        "report_id": str(REPORT_ID),
        "sections": len(source_sections) + 1,
        "layouts": len(LAYOUTS),
        "combinations": len(results) + len(cover_results),
        "passed": not failures,
        "failures": failures,
        "results": results,
        "cover_results": cover_results,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
