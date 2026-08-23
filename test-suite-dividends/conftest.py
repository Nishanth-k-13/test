"""Pytest hooks — collect results and emit Dividend-style HTML report."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

import pytest

from report_generator import _format_range, generate_report

SUITE_NAME = "Marcom SEO Pages — Dividends"
TEST_CLASS = "tests.MarcomSeoPagesTest"

SECTION_META: dict[str, dict[str, str]] = {
    "test_Section_1_Header_and_Meta": {
        "suite": "Header and Meta",
        "desc": "Confirms page title, meta description, and H1 tag",
        "steps": "Load page → Validate title/meta/H1 → Capture screenshot",
        "objective": "Header and Meta validation for dividend leaf pages",
    },
    "test_Section_2_Analytics_Tags": {
        "suite": "Analytics Tags",
        "desc": "Confirms GA/GTM analytics tags are present",
        "steps": "Inspect page HTML → Assert GTM/GA scripts exist",
        "objective": "Analytics Tags audit for dividend leaf pages",
    },
    "test_Section_3_Graph_and_Chart": {
        "suite": "Graph and Chart",
        "desc": "Confirms price chart and time toggles render",
        "steps": "Locate chart canvas/SVG → Validate 1D/1M/1Y toggles",
        "objective": "Graph and Chart section validation",
    },
    "test_Section_4_Content_Tabs": {
        "suite": "Content Tabs",
        "desc": "Confirms Overview/Dividends and FAQ tabs are present",
        "steps": "Find tab labels → Click Overview → Validate FAQ tab",
        "objective": "Content Tabs navigation validation",
    },
    "test_Section_5_Live_Stats_and_Market_Cap": {
        "suite": "Live Stats and Market Cap",
        "desc": "Confirms live stats grid with market cap and ratios",
        "steps": "Locate Market Cap → Validate P/E or P/B metrics",
        "objective": "Live Stats and Market Cap section validation",
    },
    "test_Section_6_Dividend_Metrics": {
        "suite": "Dividend Metrics",
        "desc": "Confirms dividend yield and related metrics render",
        "steps": "Locate Div. Yield / Dividend Per Share blocks",
        "objective": "Dividend Metrics section validation",
    },
    "test_Section_7_History_Table": {
        "suite": "History Table",
        "desc": "Confirms corporate actions history table columns",
        "steps": "Validate Corporate Actions heading → Check Ex-Date columns",
        "objective": "History Table validation",
    },
    "test_Section_8_FAQs": {
        "suite": "FAQs",
        "desc": "Confirms FAQ accordion and JSON-LD structured data",
        "steps": "Validate FAQ text → Parse FAQPage schema → Check placeholders",
        "objective": "FAQs section and structured data validation",
    },
    "test_Section_9_Footer_Components": {
        "suite": "Footer Components",
        "desc": "Confirms peer stocks and calculators in the footer",
        "steps": "Validate peer toggles → Count calculators",
        "objective": "Footer Components validation",
    },
}

_collected_records: list[dict[str, Any]] = []
_record_counter = 0
_session_start = 0.0


def pytest_sessionstart(session: pytest.Session) -> None:
    global _session_start
    _session_start = time.time()


def _extract_url(nodeid: str) -> str:
    match = re.search(r"\[(https?://[^\]]+)\]", nodeid)
    return match.group(1) if match else ""


def _build_detail(meta: dict[str, str], status: str, error: str) -> str:
    lines = [
        f"Objective: {meta.get('objective', meta.get('desc', ''))}",
        "",
        "What This Test Verifies:",
        f"- {meta.get('desc', '')}",
        "",
        "Steps (as executed):",
        meta.get("steps", "(no steps recorded)"),
        "",
        f"Result: {status.upper()}",
    ]
    if error:
        lines.extend(["", "Failure Details:", error])
    return "\n".join(lines)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    # Strip parametrize suffix so SECTION_META keys match under -n workers
    method = getattr(item, "originalname", None) or item.name.split("[")[0]
    meta = SECTION_META.get(method, {
        "suite": method.replace("test_Section_", "").replace("_", " "),
        "desc": method,
        "steps": "(no step-level attachments recorded for this test)",
        "objective": method,
    })

    url = _extract_url(item.nodeid)
    status = report.outcome
    error = ""
    if report.failed:
        error = getattr(report, "longreprtext", str(report.longrepr))

    started = datetime.fromtimestamp(call.start, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    duration = round(call.stop - call.start, 2) if call.stop and call.start else 0.0

    # Attach to report so xdist master can collect via pytest_runtest_logreport
    report.user_record = {
        "cls": TEST_CLASS,
        "method": method,
        "suite": meta["suite"],
        "url": url,
        "row": "",
        "status": status,
        "desc": meta["desc"],
        "steps": meta["steps"],
        "detail": _build_detail(meta, status, error),
        "fail": error,
        "start": started,
        "dur": duration,
    }


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Runs on the master node — aggregates worker results for the HTML report."""
    if report.when != "call" and not (report.when == "setup" and report.failed):
        return

    record = getattr(report, "user_record", None)
    if not record:
        method = report.nodeid.split("::")[-1].split("[")[0]
        meta = SECTION_META.get(method, {
            "suite": method,
            "desc": method,
            "steps": "(setup failed)",
            "objective": method,
        })
        record = {
            "cls": TEST_CLASS,
            "method": method,
            "suite": meta["suite"],
            "url": _extract_url(report.nodeid),
            "row": "",
            "status": report.outcome,
            "desc": meta["desc"],
            "steps": meta["steps"],
            "detail": _build_detail(meta, report.outcome, getattr(report, "longreprtext", "")),
            "fail": getattr(report, "longreprtext", "") if report.failed else "",
            "start": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "dur": getattr(report, "duration", 0.0) or 0.0,
        }

    global _record_counter
    _record_counter += 1
    record = {**record, "n": _record_counter}
    _collected_records.append(record)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if hasattr(session.config, "workerinput"):
        return
    if not _collected_records:
        return

    total_time = time.time() - _session_start
    passed = sum(1 for r in _collected_records if r["status"] == "passed")
    failed = sum(1 for r in _collected_records if r["status"] == "failed")
    skipped = sum(1 for r in _collected_records if r["status"] == "skipped")
    unique_urls = len({r["url"] for r in _collected_records if r["url"]})

    subtitle = (
        f"Execution Range: <span id=\"hdrRange\">{_format_range(_collected_records)}</span> "
        f"&middot; <span>1 test class</span> "
        f"&middot; {unique_urls} target URLs "
        f"&middot; {total_time:.0f}s total runtime "
        f"&middot; {passed} passed / {failed} failed / {skipped} skipped"
    )

    output = generate_report(
        _collected_records,
        subtitle=subtitle,
    )
    print(f"\nHTML report generated: {output}")
