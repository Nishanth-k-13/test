"""Pytest hooks — collect results and emit Balance Sheet HTML report."""

from __future__ import annotations

import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from report_generator import _format_range, generate_report

TEST_CLASS = "tests.MarcomSeoBalanceSheetTest"
REPORT_RECORDS_FILE = Path(__file__).with_name("report_records.json")
RETRY_URLS_FILE = Path(__file__).with_name("retry_urls.csv")


def _failed_urls_log_path() -> Path:
    try:
        import test_balance_sheet_pages as suite

        name = getattr(suite, "FAILED_URLS_LOG", "failed-urls.csv")
    except Exception:
        name = os.getenv("FAILED_URLS_LOG", "failed-urls.csv")
    return Path(__file__).with_name(name)

SECTION_META: dict[str, dict[str, str]] = {
    "test_Section_1_Header_and_Meta": {
        "suite": "Header and Meta",
        "desc": "Confirms page title, meta description, and H1 tag",
        "steps": "Load page → Validate title/meta/H1 → Capture screenshot",
        "objective": "Header and Meta validation for balance-sheet leaf pages",
    },
    "test_Section_2_Analytics_Tags": {
        "suite": "Analytics Tags",
        "desc": "Confirms GA/GTM analytics tags are present",
        "steps": "Inspect page HTML → Assert GTM/GA scripts exist",
        "objective": "Analytics Tags audit for balance-sheet leaf pages",
    },
    "test_Section_3_Graph_and_Chart": {
        "suite": "Graph and Chart",
        "desc": "Confirms price chart and time toggles render",
        "steps": "Locate chart canvas/SVG → Validate 1D/1M/1Y toggles",
        "objective": "Graph and Chart section validation",
    },
    "test_Section_4_Content_Tabs": {
        "suite": "Content Tabs",
        "desc": "Confirms Overview/Balance Sheet/Fundamentals and FAQ tabs",
        "steps": "Find tab labels → Validate FAQ tab",
        "objective": "Content Tabs navigation validation",
    },
    "test_Section_5_Live_Stats_and_Market_Cap": {
        "suite": "Live Stats and Market Cap",
        "desc": "Confirms live stats grid with market cap and ratios",
        "steps": "Locate Market Cap → Validate PE Ratio or P/E metrics",
        "objective": "Live Stats and Market Cap section validation",
    },
    "test_Section_6_Financial_Overview": {
        "suite": "Financial Overview",
        "desc": "Confirms financial overview growth cards (Sales, Profit, ROE, CAGR)",
        "steps": "Locate #stk-fund-fin-ovw → Validate growth cards with percentages",
        "objective": "Financial Overview cards validation",
    },
    "test_Section_7_Balance_Sheet_Structure": {
        "suite": "Balance Sheet Structure",
        "desc": "Confirms Balance Sheet section, table, and sub-tabs",
        "steps": "Locate #stk-fund-bs → Validate Consolidated/Standalone/Quarterly/Yearly tabs",
        "objective": "Balance Sheet statement structure validation",
    },
    "test_Section_8_Balance_Sheet_Line_Items_and_Data": {
        "suite": "Balance Sheet Line Items and Data",
        "desc": "Confirms balance sheet line items and numeric table data",
        "steps": "Validate Total Assets/Share Capital rows → Assert table cells contain numbers",
        "objective": "Balance Sheet line items and data validation",
    },
    "test_Section_9_PnL_Statement_Structure": {
        "suite": "P&L Statement Structure",
        "desc": "Confirms Profit & Loss section and table on balance-sheet leaf page",
        "steps": "Locate #stk-fund-pl → Validate P&L table and sub-tabs",
        "objective": "P&L statement structure validation",
    },
    "test_Section_10_Cash_Flow": {
        "suite": "Cash Flow",
        "desc": "Confirms Cash Flow section and operating/investing/financing rows",
        "steps": "Locate #stk-fund-cf → Validate cash flow line items and numeric data",
        "objective": "Cash Flow section validation",
    },
    "test_Section_11_Fundamental_Ratios": {
        "suite": "Fundamental Ratios",
        "desc": "Confirms Fundamental Ratios section and category sub-tabs",
        "steps": "Locate #stk-fund-ratios → Validate ratio categories and table data",
        "objective": "Fundamental Ratios section validation",
    },
    "test_Section_12_Peer_Comparison": {
        "suite": "Peer Comparison",
        "desc": "Confirms peer comparison table and sub-tabs",
        "steps": "Locate #stk-fund-peer → Validate Overview/Performance/Valuation tabs",
        "objective": "Peer Comparison section validation",
    },
    "test_Section_13_FAQs": {
        "suite": "FAQs",
        "desc": "Confirms FAQ accordion and JSON-LD structured data",
        "steps": "Validate FAQ text → Parse FAQPage schema → Check placeholders",
        "objective": "FAQs section and structured data validation",
    },
    "test_Section_14_Footer_Components": {
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

    if hasattr(session.config, "workerinput"):
        return

    log_path = _failed_urls_log_path()
    log_path.write_text("url,section,time\n", encoding="utf-8")


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
        # Fallback when setup fails before makereport attaches user_record
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

    if record.get("status") == "failed" and record.get("url"):
        _append_live_failure(record)


def _append_live_failure(record: dict[str, Any]) -> None:
    """Append url + section to failed-urls.csv as soon as a test fails."""
    log_path = _failed_urls_log_path()
    with log_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            record.get("url", ""),
            record.get("suite", record.get("method", "")),
            record.get("start", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
        ])
        handle.flush()
        os.fsync(handle.fileno())


def _write_retry_urls_from_log() -> None:
    """Unique failed URLs from the live log — used by run_tests.sh for retries."""
    log_path = _failed_urls_log_path()
    if not log_path.exists() or log_path.stat().st_size <= len("url,section,time\n"):
        if RETRY_URLS_FILE.exists():
            RETRY_URLS_FILE.unlink()
        return

    urls: set[str] = set()
    with log_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("url") or "").strip()
            if url:
                urls.add(url)

    if urls:
        RETRY_URLS_FILE.write_text("\n".join(sorted(urls)) + "\n", encoding="utf-8")
    elif RETRY_URLS_FILE.exists():
        RETRY_URLS_FILE.unlink()


def _merge_records(
    previous: list[dict[str, Any]], current: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = {(r.get("url", ""), r.get("method", "")): r for r in previous}
    for record in current:
        merged[(record.get("url", ""), record.get("method", ""))] = record
    return sorted(
        merged.values(),
        key=lambda r: (r.get("url", ""), r.get("method", "")),
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if hasattr(session.config, "workerinput"):
        return
    if not _collected_records:
        return

    records = list(_collected_records)
    merge_path = os.getenv("MERGE_REPORT_RECORDS")
    if merge_path and Path(merge_path).exists():
        previous = json.loads(Path(merge_path).read_text(encoding="utf-8"))
        records = _merge_records(previous, records)

    REPORT_RECORDS_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_retry_urls_from_log()

    total_time = time.time() - _session_start
    passed = sum(1 for r in records if r["status"] == "passed")
    failed = sum(1 for r in records if r["status"] == "failed")
    skipped = sum(1 for r in records if r["status"] == "skipped")
    unique_urls = len({r["url"] for r in records if r["url"]})

    subtitle = (
        f"Execution Range: <span id=\"hdrRange\">{_format_range(records)}</span> "
        f"&middot; <span>1 test class</span> "
        f"&middot; {unique_urls} target URLs "
        f"&middot; {total_time:.0f}s total runtime "
        f"&middot; {passed} passed / {failed} failed / {skipped} skipped"
    )

    output = generate_report(
        records,
        title="Test Execution Report — Balance Sheet Pages",
        eyebrow="Automated Test Suite · Marcom SEO Pages Frontend · Balance Sheet",
        subtitle=subtitle,
    )
    print(f"\nHTML report generated: {output}")
