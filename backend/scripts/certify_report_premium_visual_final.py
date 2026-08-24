"""Generate the same deterministic report with AUTO and every premium preset."""

from __future__ import annotations

import json
import time
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pymupdf

from app.services.report_pdf_service import render
from app.services.report_render_service import build_html
from scripts.generate_report_pdf_fixtures import document

OUTPUT = Path("../artifacts/report-premium-visual-cert-final")
PRESETS = (
    "AUTO",
    "ECOEVENT_EDITORIAL",
    "EXECUTIVE",
    "ENVIRONMENTAL",
    "BIKE_ZONE",
    "IMPACT",
)


def main() -> None:
    baseline = document("COMPLETE", "Memoria integral EcoEvent 360", "Show principal")
    manifest: dict[str, object] = {"fixture": "same-data-complete-report", "presets": {}}
    for preset in PRESETS:
        folder = OUTPUT / preset.lower().replace("_", "-")
        folder.mkdir(parents=True, exist_ok=True)
        item = replace(
            baseline,
            editorial_config={
                "mode": "AUTO",
                "visual_config": {
                    "preset": preset,
                    "icon_density": "MEDIUM",
                    "visual_density": "BALANCED",
                    "show_icons": True,
                    "show_trends": True,
                    "show_equivalences": True,
                },
                "section_visuals": {},
            },
        )
        started = time.perf_counter()
        html = build_html(item)
        html_ms = (time.perf_counter() - started) * 1000
        (folder / "preview.html").write_text(html, encoding="utf-8")
        started = time.perf_counter()
        pdf, pages = render(item)
        pdf_ms = (time.perf_counter() - started) * 1000
        (folder / "report.pdf").write_bytes(pdf)
        opened = pymupdf.open(stream=pdf, filetype="pdf")
        for index, page in enumerate(opened):
            page.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25), alpha=False).save(
                folder / f"page-{index + 1:02d}.png"
            )
        (folder / "preview-screenshot.png").write_bytes((folder / "page-01.png").read_bytes())
        manifest["presets"][preset] = {
            "html_bytes": len(html.encode("utf-8")),
            "html_sha256": sha256(html.encode("utf-8")).hexdigest(),
            "pdf_bytes": len(pdf),
            "pdf_sha256": sha256(pdf).hexdigest(),
            "pages": pages,
            "html_render_ms": round(html_ms, 2),
            "pdf_render_ms": round(pdf_ms, 2),
            "premium_elements": html.count('<aside class="premium-insight'),
        }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
