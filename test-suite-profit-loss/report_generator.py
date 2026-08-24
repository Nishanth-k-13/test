"""Generate HTML and PDF test reports matching the Dividend_Report1.html format."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).with_name("report_template.html")
DEFAULT_OUTPUT = Path(__file__).with_name("Marcom_SEO_Report.html")
DEFAULT_PDF_OUTPUT = Path(__file__).with_name("Marcom_SEO_Report.pdf")

# Cap PDF table rows so huge runs stay printable; prefer failures when over limit.
PDF_MAX_ROWS = 2_000


def _format_range(records: list[dict[str, Any]]) -> str:
    starts = sorted(r.get("start", "") for r in records if r.get("start"))
    if not starts:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"{starts[0]} → {starts[-1]}"


def html_to_pdf(html_path: Path, pdf_path: Path | None = None) -> Path:
    """Render the HTML report in Chromium and export a PDF."""
    from playwright.sync_api import sync_playwright

    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path or html_path.with_suffix(".pdf")).resolve()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle", timeout=120_000)
        page.wait_for_selector("#summaryGrid .card", timeout=60_000)

        page.add_style_tag(
            content="""
            .filters, .pagination, .page-size-control { display: none !important; }
            .col-text { max-width: none !important; white-space: normal !important;
                        overflow: visible !important; text-overflow: unset !important; }
            body { background: #fff !important; }
            """
        )
        page.evaluate(
            """(maxRows) => {
              const tableChip = document.getElementById('tableChip');
              const totalMatch = (tableChip?.textContent || '').match(/([\\d,]+)/);
              const total = totalMatch ? Number(totalMatch[1].replace(/,/g, '')) : 0;

              if (total > maxRows) {
                const statusFilter = document.getElementById('statusFilter');
                if (statusFilter && [...statusFilter.options].some(o => o.value === 'failed')) {
                  statusFilter.value = 'failed';
                  statusFilter.dispatchEvent(new Event('change'));
                }
              }

              const resultCount = document.getElementById('resultCount');
              const shownMatch = (resultCount?.textContent || '').match(/^([\\d,]+)/);
              const shown = shownMatch
                ? Number(shownMatch[1].replace(/,/g, ''))
                : Math.max(total, 1);

              const pageSizeSelect = document.getElementById('pageSizeSelect');
              if (pageSizeSelect) {
                const value = String(Math.max(shown, 1));
                if (![...pageSizeSelect.options].some(o => o.value === value)) {
                  const opt = document.createElement('option');
                  opt.value = value;
                  opt.textContent = value;
                  pageSizeSelect.appendChild(opt);
                }
                pageSizeSelect.value = value;
                pageSizeSelect.dispatchEvent(new Event('change'));
              }
            }""",
            PDF_MAX_ROWS,
        )
        page.wait_for_timeout(500)

        page.pdf(
            path=str(pdf_path),
            format="A4",
            landscape=True,
            print_background=True,
            margin={"top": "12mm", "right": "10mm", "bottom": "12mm", "left": "10mm"},
        )
        browser.close()

    return pdf_path


def generate_report(
    records: list[dict[str, Any]],
    *,
    output_path: str | Path = DEFAULT_OUTPUT,
    pdf_path: str | Path | None = DEFAULT_PDF_OUTPUT,
    title: str = "Test Execution Report — Profit & Loss Pages",
    eyebrow: str = "Automated Test Suite · Marcom SEO Pages Frontend",
    subtitle: str | None = None,
    also_pdf: bool = True,
) -> Path:
    if not records:
        raise ValueError("No test records to render")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    unique_urls = len({r.get("url", "") for r in records if r.get("url")})
    unique_classes = len({r.get("cls", "") for r in records if r.get("cls")})

    if subtitle is None:
        subtitle = (
            f"Execution Range: <span id=\"hdrRange\">{_format_range(records)}</span> "
            f"&middot; <span>{unique_classes} test classes</span> "
            f"&middot; {unique_urls} target URLs"
        )

    raw_json = json.dumps(records, ensure_ascii=False)
    html = (
        template.replace("__REPORT_TITLE__", title)
        .replace("__REPORT_EYEBROW__", eyebrow)
        .replace("__REPORT_SUBTITLE__", subtitle)
        .replace("__RAW_JSON__", raw_json)
    )

    output = Path(output_path)
    output.write_text(html, encoding="utf-8")

    if also_pdf:
        target_pdf = Path(pdf_path) if pdf_path else output.with_suffix(".pdf")
        try:
            html_to_pdf(output, target_pdf)
        except Exception as exc:
            print(f"PDF report generation failed: {exc}")

    return output
