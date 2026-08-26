from __future__ import annotations

import json
import os
import re
from urllib.parse import urljoin

import allure
import pandas as pd
import pytest
from playwright.sync_api import Page, expect, sync_playwright

URLS_FILE = os.getenv("URLS_FILE", "url.csv")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")


SLEEP_INTERVAL = 5
URLS_BEFORE_SLEEP = 20
WORKERS = 5
RERUN_FAILURES = 1
FAILED_URLS_LOG = "failed-urls.csv"

_worker_url_count = 0


def _effective_workers() -> int:
    env = os.getenv("EFFECTIVE_WORKERS")
    if env and str(env).isdigit():
        return max(1, int(env))
    if isinstance(WORKERS, int):
        return max(1, WORKERS)
    if isinstance(WORKERS, str) and WORKERS.isdigit():
        return max(1, int(WORKERS))
    if WORKERS == "auto":
        return max(1, os.cpu_count() or 4)
    return 1


def _urls_per_worker_before_sleep() -> int:
    return max(1, URLS_BEFORE_SLEEP // _effective_workers())


RESULTS_LINE_ITEMS = [
    "Revenue",
    "Net Revenue",
    "Total Revenue",
    "Net Profit",
    "Operating Profit",
    "EBITDA",
    "EPS",
    "Profit Before Tax",
    "PBT",
]

PEER_COMPARISON_TABS = [
    "1 week",
    "1 month",
    "1 year",
]

def get_urls() -> list[str]:
    if not os.path.exists(URLS_FILE):
        return []
    try:
        df = pd.read_csv(URLS_FILE, header=None)
        return df[0].dropna().astype(str).tolist()
    except Exception as exc:
        print(f"Error reading {URLS_FILE}: {exc}")
        return []


URLS = get_urls()


def _base_stock_url(url: str) -> str:
    return re.sub(r"/financial-results/?$", "", url.rstrip("/"))


def _alternate_domain(url: str) -> str:
    if "fyers.in/" in url:
        return url.replace("fyers.in/", "fyers.co.in/")
    if "fyers.co.in/" in url:
        return url.replace("fyers.co.in/", "fyers.in/")
    return url


def load_page(page: Page, url: str):
    candidates = [url, _alternate_domain(url), _base_stock_url(url), _base_stock_url(_alternate_domain(url))]
    seen: set[str] = set()
    last_response = None

    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            response = page.goto(candidate, wait_until="load", timeout=60_000)
            last_response = response
            if response and response.status == 200:
                return response, candidate
        except Exception:
            continue

    assert last_response is not None, f"Could not load any variant of {url}"
    assert last_response.status == 200, (
        f"Page load failed with status {last_response.status} for {url}"
    )
    return last_response, url


@pytest.fixture(autouse=True, scope="class")
def setup_browser(request, url: str):
    global _worker_url_count
    _worker_url_count += 1

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=os.getenv("HEADED", "") != "1")
    page = browser.new_page()

    page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in ["image", "media"]
        else route.continue_(),
    )

    def teardown() -> None:
        try:
            browser.close()
            playwright.stop()
        except Exception:
            pass

    request.addfinalizer(teardown)

    batch_size = _urls_per_worker_before_sleep()
    if (
        SLEEP_INTERVAL > 0
        and _worker_url_count > 1
        and (_worker_url_count - 1) % batch_size == 0
    ):
        workers = _effective_workers()
        print(
            f"Processed {URLS_BEFORE_SLEEP} URLs total "
            f"({batch_size} per worker x {workers} workers). "
            f"Sleeping for {SLEEP_INTERVAL}s..."
        )
        page.wait_for_timeout(SLEEP_INTERVAL * 1000)

    response, loaded_url = load_page(page, url)
    request.cls.status_code = response.status
    request.cls.loaded_url = loaded_url

    page.wait_for_timeout(1_500)
    TestMarcomResultsPages.ensure_results_panel(page)

    safe_url = loaded_url.replace("https://", "").replace("http://", "").replace("/", "_")
    request.cls.safe_url = safe_url
    request.cls.page = page
    request.cls.body_text = page.locator("body").inner_text()
    
    # Try to find the results section table wrapper
    # We look for Quarterly/Yearly since Results pages typically have these
    request.cls.results_section = page.locator("div").filter(has=page.locator("text=Quarterly")).filter(has=page.locator("table")).last
    if request.cls.results_section.count() == 0:
        # Fallback to Yearly if Quarterly not found
        request.cls.results_section = page.locator("div").filter(has=page.locator("text=Yearly")).filter(has=page.locator("table")).last

    request.cls.peer_section = page.locator("#stk-ovw-peer")

    yield


@pytest.mark.parametrize("url", URLS, scope="class")
@allure.feature("Marcom SEO Pages Frontend")
@allure.story("Financial Results Leaf Page Verification")
class TestMarcomResultsPages:
    screenshot_path = ""

    @staticmethod
    def ensure_results_panel(page: Page) -> None:
        try:
            page.wait_for_selector("text=Quarterly", timeout=15_000)
            res = page.locator("div").filter(has=page.locator("text=Quarterly")).filter(has=page.locator("table")).last
            res.wait_for(state="visible", timeout=15_000)
        except Exception:
            page.wait_for_selector("text=Yearly", timeout=15_000)
            res = page.locator("div").filter(has=page.locator("text=Yearly")).filter(has=page.locator("table")).last
            res.wait_for(state="visible", timeout=15_000)
        
        # Wait for Peer Comparison section to be attached if present
        try:
            page.wait_for_selector("#stk-ovw-peer", timeout=10_000)
        except Exception:
            pass
        page.wait_for_timeout(1000)

    def _take_screenshot(
        self, name: str, locator_str: str | None = None, parent_levels: int = 0
    ) -> None:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        safe_name = name.replace(" ", "_").replace("/", "_")
        path = f"{SCREENSHOT_DIR}/screenshot_{self.safe_url}_{safe_name}.png"
        try:
            if locator_str and self.page.locator(locator_str).count() > 0:
                el = self.page.locator(locator_str).first
                if parent_levels > 0:
                    el = el.locator("xpath=" + "/".join([".."] * parent_levels))
                el.scroll_into_view_if_needed()
                self.page.wait_for_timeout(500)
                el.screenshot(path=path)
            else:
                self.page.screenshot(path=path, full_page=True)
        except Exception:
            self.page.screenshot(path=path, full_page=True)

        allure.attach.file(path, name=name, attachment_type=allure.attachment_type.PNG)
        self.screenshot_path = path

    def _section_text(self, section) -> str:
        if section.count():
            return section.first.inner_text()
        return self.body_text

    def _click_sub_tab(self, section, tab_name: str) -> None:
        btn = section.get_by_text(tab_name, exact=True).first
        if btn.count():
            btn.click()
            self.page.wait_for_timeout(600)

    def _count_numeric_cells(self, section) -> int:
        return section.first.evaluate(
            """(el) => {
                return Array.from(el.querySelectorAll('td, div'))
                    .filter(c => /[\d,]+/.test(c.textContent))
                    .length;
            }"""
        )

    def _count_items_in_section(self, section_title: str) -> int:
        js_code = f"""() => {{
            const headings = Array.from(document.querySelectorAll('h2, h3, h4'));
            const heading = headings.find(h =>
                h.textContent.toLowerCase().includes('{section_title}'.toLowerCase())
            );
            if (!heading) return 0;
            const parent = heading.parentElement;
            if ('{section_title}'.toLowerCase().includes('peer stocks')) {{
                const links = Array.from(parent.querySelectorAll('a[href*="/stocks/"]'));
                return new Set(links.map(a => a.href)).size;
            }}
            const links = parent.querySelectorAll('a');
            if (links.length > 0) return links.length;
            return parent.querySelectorAll('li').length;
        }}"""
        return self.page.evaluate(js_code)

    @allure.story("Header and Meta")
    def test_Section_1_Header_and_Meta(self, url: str) -> None:
        allure.dynamic.title(f"Header & Meta — {url}")
        title = self.page.title()
        assert title and len(title.strip()) > 10, f"Page title missing or too short: '{title}'"

        meta_desc = self.page.locator("meta[name='description']")
        assert meta_desc.count() > 0, "Meta description tag is missing"
        content = meta_desc.first.get_attribute("content")
        assert content and len(content.strip()) > 10, "Meta description is empty or too short"

        h1 = self.page.locator("h1")
        expect(h1).to_have_count(1, timeout=2_000)
        self._take_screenshot("Header Section", "h1")
        assert len(h1.first.inner_text().strip()) > 0, "H1 tag is empty"


    @allure.story("Graph & Chart")
    def test_Section_3_Graph_and_Chart(self, url: str) -> None:
        self._take_screenshot("Graph Section", "canvas, svg")
        has_chart = (
            self.page.locator("canvas").count() > 0 or self.page.locator("svg").count() > 0
        )
        has_toggles = "1D" in self.body_text and "1M" in self.body_text and "1Y" in self.body_text
        assert has_chart or has_toggles, "Graph/chart or time toggles (1D, 1M, 1Y) are missing"

    @allure.story("Content Tabs")
    def test_Section_4_Content_Tabs(self, url: str) -> None:
        self._take_screenshot("Tabs Section", "text=Overview", parent_levels=4)
        overview = self.page.locator("text=Overview")
        res_tab = self.page.locator("text=Financial Results").or_(self.page.locator("text=Results"))
        fundamentals = self.page.locator("text=Fundamentals")
        assert (
            overview.count() > 0 or res_tab.count() > 0 or fundamentals.count() > 0
        ), "Main content tabs (Overview / Financial Results / Fundamentals) not found"

        faq_tab = self.page.locator("text=FAQ")
        assert faq_tab.count() > 0, "Content tab 'FAQ' is missing"

    @allure.story("Live Stats and Market Cap")
    def test_Section_5_Live_Stats_and_Market_Cap(self, url: str) -> None:
        self._take_screenshot("Live Stats Section", "text=Market Cap", parent_levels=5)
        market_cap = self.page.locator("text=Market Cap")
        mcap_alt = self.page.locator("text=M.Cap")
        assert market_cap.count() > 0 or mcap_alt.count() > 0, (
            "Live Stats 'Market Cap' section not found"
        )

        has_ratio = (
            self.page.locator("text=PE Ratio").count() > 0
            or self.page.locator("text=P/E").count() > 0
            or self.page.locator("text=P/B").count() > 0
            or self.page.locator("text=Price to Book").count() > 0
        )
        assert has_ratio, "Live Stats ratio data (PE/P/E/P/B) missing"


    @allure.story("Financial Results Structure")
    def test_Section_7_Results_Structure(self, url: str) -> None:
        self.results_section.first.scroll_into_view_if_needed()
        assert self.results_section.count() > 0, "Financial Results section not found"

        assert self.results_section.locator("table").count() > 0, "Financial Results table not found"

        for tab_name in ["Quarterly", "Yearly"]:
            btn = self.results_section.get_by_text(tab_name, exact=True).first
            if btn.count() > 0:
                btn.click()
                self.page.wait_for_timeout(600)
                assert self.results_section.locator("table").count() > 0, (
                    f"Financial Results table not visible after clicking {tab_name}"
                )

    @allure.story("Financial Results Line Items and Data")
    def test_Section_8_Results_Line_Items_and_Data(self, url: str) -> None:
        btn = self.results_section.get_by_text("Quarterly", exact=True).first
        if btn.count() > 0:
            self._click_sub_tab(self.results_section, "Quarterly")
        elif self.results_section.get_by_text("Yearly", exact=True).first.count() > 0:
            self._click_sub_tab(self.results_section, "Yearly")

        res_text = self._section_text(self.results_section)

        found = [item for item in RESULTS_LINE_ITEMS if item in res_text]
        assert len(found) >= 1, f"Expected results line items, found: {found}"

        numeric_count = self._count_numeric_cells(self.results_section)
        assert numeric_count >= 3, (
            f"Financial Results table has insufficient numeric cells: {numeric_count}"
        )


    @allure.story("Peer Comparison")
    def test_Section_12_Peer_Comparison(self, url: str) -> None:
        self.peer_section.first.scroll_into_view_if_needed()
        self._take_screenshot("Peer Comparison", "#stk-ovw-peer")
        assert self.peer_section.count() > 0, "Peer comparison section (#stk-ovw-peer) not found"

        peer_text = self._section_text(self.peer_section)
        assert "Similar Companies" in peer_text or "Peer" in peer_text, (
            "Peer comparison heading not found"
        )

        found_tabs = [tab for tab in PEER_COMPARISON_TABS if tab in peer_text]
        assert len(found_tabs) >= 2, f"Expected peer sub-tabs, found: {found_tabs}"

        for tab_name in found_tabs:
            btn = self.peer_section.get_by_text(tab_name, exact=True).first
            if btn.count():
                btn.click()
                self.page.wait_for_timeout(600)
                assert self.peer_section.locator(".flex-1").count() > 0, (
                    f"Peer comparison table not visible after clicking {tab_name}"
                )


    @allure.story("FAQs")
    def test_Section_13_FAQs(self, url: str) -> None:
        self._take_screenshot("FAQs Section", "text=FAQ", parent_levels=3)
        assert "FAQ" in self.body_text or "Frequently Asked Questions" in self.body_text, (
            "FAQs not found"
        )

        faq_count = 0
        for script_text in self.page.locator("script[type='application/ld+json']").all_inner_texts():
            if "FAQPage" in script_text:
                try:
                    data = json.loads(script_text)
                    if "mainEntity" in data:
                        faq_count = max(faq_count, len(data["mainEntity"]))
                except json.JSONDecodeError:
                    pass
        assert faq_count > 0, "No FAQs found in structured data (JSON-LD)"

        lower_body = self.body_text.lower()
        for placeholder in ("lorem ipsum", "undefined", "null", "placeholder text", "dummy text"):
            assert placeholder not in lower_body, f"Found placeholder text '{placeholder}'"
