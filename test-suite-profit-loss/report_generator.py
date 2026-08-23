"""Generate HTML test reports matching the Dividend_Report1.html format."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).with_name("report_template.html")
DEFAULT_OUTPUT = Path(__file__).with_name("Marcom_SEO_Report.html")


def _format_range(records: list[dict[str, Any]]) -> str:
    starts = sorted(r.get("start", "") for r in records if r.get("start"))
    if not starts:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"{starts[0]} → {starts[-1]}"


def generate_report(
    records: list[dict[str, Any]],
    *,
    output_path: str | Path = DEFAULT_OUTPUT,
    title: str = "Test Execution Report — Profit & Loss Pages",
    eyebrow: str = "Automated Test Suite · Marcom SEO Pages Frontend",
    subtitle: str | None = None,
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
    return output
