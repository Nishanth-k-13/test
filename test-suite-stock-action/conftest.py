"""Pytest hooks — collect results and emit Financial Results HTML report."""

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

TEST_CLASS = "tests.MarcomSeoResultsTest"
REPORT_RECORDS_FILE = Path(__file__).with_name("report_records.json")
RETRY_URLS_FILE = Path(__file__).with_name("retry_urls.csv")


def _failed_urls_log_path() -> Path:
    try:
        import test_results_pages as suite

        name = getattr(suite, "FAILED_URLS_LOG", "failed-urls.csv")
    except Exception:
        name = os.getenv("FAILED_URLS_LOG", "failed-urls.csv")
    return Path(__file__).with_name(name)


SECTION_META: dict[str, dict[str, str]] = {
    "test_Section_1_Header_and_Meta": {
        "suite": "Header and Meta",
        "desc": "Confirms page title, meta description, and H1 tag",
        "steps": "Load page → Validate title/meta/H1",
        "objective": "Header and Meta validation for stock action leaf pages",
    },
    "test_Section_2_Tabs": {
        "suite": "Tabs (Splits and Rights)",
        "desc": "Confirms Splits and Rights tabs render",
        "steps": "Locate Splits tab → Validate Rights tab",
        "objective": "Splits and Rights tabs navigation validation",
    },
    "test_Section_3_Live_Stats": {
        "suite": "Live Stats",
        "desc": "Confirms share price live stats section renders",
        "steps": "Locate Share Price Live Stats grid",
        "objective": "Live Stats section validation",
    },
    "test_Section_4_Key_Ratios": {
        "suite": "Key Ratios",
        "desc": "Confirms market cap and key ratios overview block",
        "steps": "Locate Share Market Cap & Key Ratios Overview",
        "objective": "Key Ratios section validation",
    },
    "test_Section_5_SWOT": {
        "suite": "SWOT Analysis",
        "desc": "Confirms SWOT analysis component renders",
        "steps": "Locate Stock Analysis (SWOT)",
        "objective": "SWOT analysis section validation",
    },
    "test_Section_6_Peer_Stocks": {
        "suite": "Peer Stocks",
        "desc": "Confirms peer stocks comparison component",
        "steps": "Locate Peer Stocks block",
        "objective": "Peer Stocks component validation",
    },
    "test_Section_7_Content_Tabs": {
        "suite": "Content Tabs",
        "desc": "Confirms detail content tabs like Overview are present",
        "steps": "Locate Overview tab",
        "objective": "Content Tabs component validation",
    },
    "test_Section_8_Other_Stocks_and_Calculators": {
        "suite": "Other Stocks and Calculators",
        "desc": "Confirms other stocks links and calculators in footer",
        "steps": "Traverse Other stocks links → Traverse Calculators links",
        "objective": "Footer elements and related links validation",
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
    log_path.write_text("url,sections,time\n", encoding="utf-8")


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

    if record.get("status") == "failed" and record.get("url"):
        _append_live_failure(record)


def _append_live_failure(record: dict[str, Any]) -> None:
    import fcntl
    import ast
    log_path = _failed_urls_log_path()
    url = record.get("url", "")
    section = record.get("suite", record.get("method", ""))
    time_str = record.get("start", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    
    if not log_path.exists():
        log_path.write_text("url,sections,time\n", encoding="utf-8")
        
    with log_path.open("r+", encoding="utf-8", newline="") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        reader = csv.reader(handle)
        rows = list(reader)
        
        found = False
        for i, row in enumerate(rows):
            if i == 0: continue
            if len(row) >= 2 and row[0] == url:
                found = True
                try:
                    sections = ast.literal_eval(row[1]) if row[1].startswith('[') else [row[1]]
                except Exception:
                    sections = [row[1]] if row[1] else []
                if section not in sections:
                    sections.append(section)
                rows[i][1] = str(sections)
                rows[i][2] = time_str
                break
                
        if not found:
            rows.append([url, str([section]), time_str])
            
        handle.seek(0)
        handle.truncate()
        writer = csv.writer(handle)
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle, fcntl.LOCK_UN)


def _write_retry_urls_from_log() -> None:
    log_path = _failed_urls_log_path()
    if not log_path.exists() or log_path.stat().st_size <= len("url,sections,time\n"):
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
        title="Test Execution Report — Stock Action Pages",
        eyebrow="Automated Test Suite · Marcom SEO Pages Frontend · Stock Action",
        subtitle=subtitle,
    )
    print(f"\nHTML report generated: {output}")
