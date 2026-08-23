"""
Marcom SEO Pages Frontend — Profit & Loss leaf page UI test suite.

Reads URLs from url.csv and validates 14 page sections per URL.
Generates Marcom_SEO_Report.html via conftest.py hooks.

DOM (Marcom frontend Fundamentals panel):
  #stk-panel-fund, #stk-fund-fin-ovw, #stk-fund-peer, #stk-fund-pl,
  #stk-fund-bs, #stk-fund-cf, #stk-fund-ratios
"""

from __future__ import annotations

import json
import os
import re

import allure
import pandas as pd
import pytest
from playwright.sync_api import Page, expect, sync_playwright

URLS_FILE = os.getenv("URLS_FILE", "url.csv")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")


SLEEP_INTERVAL = int(os.getenv("SLEEP_TIME", "0"))
URLS_BEFORE_SLEEP = int(os.getenv("URLS_BATCH_SIZE", "20"))

_worker_url_count = 0

FINANCIAL_OVERVIEW_CARDS = [
    "Compounded Sales Growth",
    "Compounded Profit Growth",
    "Stock Price CAGR",
    "Return on Equity",
]

PL_SUB_TABS = ["Consolidated", "Standalone", "Quarterly", "Yearly"]

PL_LINE_ITEMS = [
    "Net Revenue",
    "Total Revenue",
    "Net Profit",
    "Operating Profit",
    "Other Income",
    "Profit Before Tax",
    "PBT",
]

BS_LINE_ITEMS = [
    "Total Assets",
    "Share Capital",
    "Shareholder's Funds",
    "Shareholders' Funds",
    "Total Liabilities",
]

CF_LINE_ITEMS = [
    "Cash Flow from operating activities",
    "Cash Flow from investing activities",
    "Cash Flow from financing activities",
    "Cash Flow from Operating Activities",
    "Cash Flow from Investing Activities",
    "Cash Flow from Financing Activities",
]

PEER_COMPARISON_TABS = [
    "Overview",
    "Performance",
    "Valuation",
    "Margins & profitability",
    "Growth",
    "Liquidity",
]

RATIO_CATEGORIES = [
    "Profitability",
    "Liquidity",
    "Valuation",
    "Growth",
    "Efficiency",
    "Leverage",
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
    return re.sub(r"/profit-loss/?$", "", url.rstrip("/"))


def _alternate_domain(url: str) -> str:
    if "fyers.in/" in url:
        return url.replace("fyers.in/", "fyers.co.in/")
    if "fyers.co.in/" in url:
        return url.replace("fyers.co.in/", "fyers.in/")
    return url


def load_page(page: Page, url: str):
    """Load profit-loss leaf URL; fall back to stock page if leaf 404s."""
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

    # Optional throttle between URL batches (per worker)
    if (
        SLEEP_INTERVAL > 0
        and _worker_url_count > 1
        and (_worker_url_count - 1) % URLS_BEFORE_SLEEP == 0
    ):
        print(
            f"Worker processed {_worker_url_count - 1} URLs. "
            f"Sleeping for {SLEEP_INTERVAL}s..."
        )
        page.wait_for_timeout(SLEEP_INTERVAL * 1000)

    response, loaded_url = load_page(page, url)
    request.cls.status_code = response.status
    request.cls.loaded_url = loaded_url

    page.wait_for_timeout(1_500)
    TestMarcomProfitLossPages.ensure_fundamentals_panel(page)

    safe_url = loaded_url.replace("https://", "").replace("http://", "").replace("/", "_")
    request.cls.safe_url = safe_url
    request.cls.page = page
    request.cls.body_text = page.locator("body").inner_text()
    request.cls.pl_section = page.locator("#stk-fund-pl")
    request.cls.bs_section = page.locator("#stk-fund-bs")
    request.cls.cf_section = page.locator("#stk-fund-cf")
    request.cls.ratios_section = page.locator("#stk-fund-ratios")
    request.cls.peer_section = page.locator("#stk-fund-peer")

    yield


@pytest.mark.parametrize("url", URLS, scope="class")
@allure.feature("Marcom SEO Pages Frontend")
@allure.story("Profit & Loss Leaf Page Verification")
class TestMarcomProfitLossPages:
    screenshot_path = ""

    @staticmethod
    def ensure_fundamentals_panel(page: Page) -> None:
        """Ensure Fundamentals panel and P&L block are visible."""
        if page.locator("#stk-fund-pl").count() > 0:
            page.locator("#stk-fund-pl").first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            return

        for tab_name in ("Fundamentals", "Profit & Loss"):
            tab = page.get_by_role("tab", name=tab_name).first
            if tab.count():
                tab.click()
                page.wait_for_timeout(1_500)
                if page.locator("#stk-fund-pl").count() > 0:
                    break

        if page.locator("#stk-fund-pl").count() == 0:
            page.wait_for_selector("#stk-fund-pl", timeout=30_000)

        page.locator("#stk-fund-pl").first.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

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

    def _count_numeric_cells(self, selector: str) -> int:
        return self.page.evaluate(
            f"""() => {{
                const section = document.querySelector('{selector}');
                if (!section) return 0;
                return Array.from(section.querySelectorAll('td'))
                    .filter(c => /[\\d,]+/.test(c.textContent))
                    .length;
            }}"""
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

    @allure.story("Analytics Tags")
    def test_Section_2_Analytics_Tags(self, url: str) -> None:
        html_content = self.page.content()
        self._take_screenshot("Analytics Source", "head")
        assert (
            "googletagmanager.com" in html_content or "google-analytics.com" in html_content
        ), "GA/GTM tags are missing"

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
        pl_tab = self.page.locator("text=Profit & Loss")
        fundamentals = self.page.locator("text=Fundamentals")
        assert (
            overview.count() > 0 or pl_tab.count() > 0 or fundamentals.count() > 0
        ), "Main content tabs (Overview / Profit & Loss / Fundamentals) not found"

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

    @allure.story("Financial Overview")
    def test_Section_6_Financial_Overview(self, url: str) -> None:
        self._take_screenshot("Financial Overview", "#stk-fund-fin-ovw")
        overview = self.page.locator("#stk-fund-fin-ovw")
        overview_text = overview.first.inner_text() if overview.count() else self.body_text

        found_cards = [card for card in FINANCIAL_OVERVIEW_CARDS if card in overview_text]
        assert len(found_cards) >= 2, (
            f"Expected financial overview cards, found: {found_cards}"
        )

        if overview.count():
            cards_data = self.page.evaluate(
                """() => {
                    const section = document.querySelector('#stk-fund-fin-ovw');
                    if (!section) return [];
                    const cards = [];
                    section.querySelectorAll('h2 span').forEach(title => {
                        const card = title.closest('.border');
                        if (!card) return;
                        const metrics = {};
                        card.querySelectorAll('.flex.justify-between').forEach(row => {
                            const spans = row.querySelectorAll('span');
                            if (spans.length >= 2) {
                                metrics[spans[0].textContent.trim()] = spans[1].textContent.trim();
                            }
                        });
                        cards.push({ title: title.textContent.trim(), metrics });
                    });
                    return cards;
                }"""
            )
            for card in cards_data:
                assert card.get("metrics"), f"No metrics for card: {card.get('title')}"
                for value in card["metrics"].values():
                    assert "%" in value, f"Metric value missing %: {value}"

    @allure.story("P&L Statement Structure")
    def test_Section_7_PnL_Statement_Structure(self, url: str) -> None:
        self._take_screenshot("PnL Statement", "#stk-fund-pl")
        assert self.pl_section.count() > 0, "Profit & Loss section (#stk-fund-pl) not found"

        pl_text = self._section_text(self.pl_section)
        assert "Profit" in pl_text and "Loss" in pl_text, (
            "Profit & Loss heading not found in section"
        )
        assert self.pl_section.locator("table").count() > 0, "P&L data table not found"

        for tab_name in PL_SUB_TABS:
            btn = self.pl_section.get_by_text(tab_name, exact=True).first
            assert btn.count() > 0, f"P&L sub-tab missing: {tab_name}"
            btn.click()
            self.page.wait_for_timeout(600)
            assert self.pl_section.locator("table").count() > 0, (
                f"P&L table not visible after clicking {tab_name}"
            )

    @allure.story("P&L Line Items and Data")
    def test_Section_8_PnL_Line_Items_and_Data(self, url: str) -> None:
        self._click_sub_tab(self.pl_section, "Consolidated")
        pl_text = self._section_text(self.pl_section).lower()

        found_items = [item for item in PL_LINE_ITEMS if item.lower() in pl_text]
        assert len(found_items) >= 2, f"Expected P&L line items, found: {found_items}"

        numeric_count = self._count_numeric_cells("#stk-fund-pl")
        assert numeric_count >= 5, f"P&L table has too few numeric cells: {numeric_count}"

        for tab_name in ("Quarterly", "Yearly"):
            self._click_sub_tab(self.pl_section, tab_name)
            assert self._count_numeric_cells("#stk-fund-pl") > 0, (
                f"P&L table empty after switching to {tab_name}"
            )

        self._take_screenshot("PnL Data Table", "#stk-fund-pl")

    @allure.story("Balance Sheet")
    def test_Section_9_Balance_Sheet(self, url: str) -> None:
        self.bs_section.first.scroll_into_view_if_needed()
        self._take_screenshot("Balance Sheet", "#stk-fund-bs")
        assert self.bs_section.count() > 0, "Balance Sheet section (#stk-fund-bs) not found"

        bs_text = self._section_text(self.bs_section)
        assert "Balance Sheet" in bs_text or "Balance sheet" in bs_text, (
            "Balance Sheet heading not found"
        )
        assert self.bs_section.locator("table").count() > 0, "Balance Sheet table not found"

        found = [item for item in BS_LINE_ITEMS if item in bs_text]
        assert len(found) >= 1, f"Expected balance sheet line items, found: {found}"

        for tab_name in PL_SUB_TABS:
            btn = self.bs_section.get_by_text(tab_name, exact=True).first
            if btn.count():
                btn.click()
                self.page.wait_for_timeout(400)

        assert self._count_numeric_cells("#stk-fund-bs") >= 3, (
            "Balance Sheet table has insufficient numeric data"
        )

    @allure.story("Cash Flow")
    def test_Section_10_Cash_Flow(self, url: str) -> None:
        self.cf_section.first.scroll_into_view_if_needed()
        self._take_screenshot("Cash Flow", "#stk-fund-cf")
        assert self.cf_section.count() > 0, "Cash Flow section (#stk-fund-cf) not found"

        cf_text = self._section_text(self.cf_section)
        assert "Cash Flow" in cf_text or "Cash flow" in cf_text, (
            "Cash Flow heading not found"
        )
        assert self.cf_section.locator("table").count() > 0, "Cash Flow table not found"

        found = [item for item in CF_LINE_ITEMS if item in cf_text]
        assert len(found) >= 1, f"Expected cash flow line items, found: {found}"
        assert self._count_numeric_cells("#stk-fund-cf") >= 3, (
            "Cash Flow table has insufficient numeric data"
        )

    @allure.story("Fundamental Ratios")
    def test_Section_11_Fundamental_Ratios(self, url: str) -> None:
        self.ratios_section.first.scroll_into_view_if_needed()
        self._take_screenshot("Fundamental Ratios", "#stk-fund-ratios")
        assert self.ratios_section.count() > 0, (
            "Fundamental Ratios section (#stk-fund-ratios) not found"
        )

        ratios_text = self._section_text(self.ratios_section)
        assert "Ratio" in ratios_text or "ratio" in ratios_text, (
            "Fundamental Ratios heading not found"
        )

        found_categories = [cat for cat in RATIO_CATEGORIES if cat in ratios_text]
        assert len(found_categories) >= 1 or self.ratios_section.locator("table").count() > 0, (
            "Fundamental Ratios categories or table not found"
        )

        for cat in found_categories[:3]:
            btn = self.ratios_section.get_by_text(cat, exact=False).first
            if btn.count():
                btn.click()
                self.page.wait_for_timeout(400)

        assert self._count_numeric_cells("#stk-fund-ratios") >= 2, (
            "Fundamental Ratios table has insufficient numeric data"
        )

    @allure.story("Peer Comparison")
    def test_Section_12_Peer_Comparison(self, url: str) -> None:
        self.peer_section.first.scroll_into_view_if_needed()
        self._take_screenshot("Peer Comparison", "#stk-fund-peer")
        assert self.peer_section.count() > 0, "Peer comparison section (#stk-fund-peer) not found"

        peer_text = self._section_text(self.peer_section)
        assert "Peer" in peer_text or "peer" in peer_text, (
            "Peer comparison heading not found"
        )

        found_tabs = [tab for tab in PEER_COMPARISON_TABS if tab in peer_text]
        assert len(found_tabs) >= 2, f"Expected peer sub-tabs, found: {found_tabs}"

        for tab_name in found_tabs[:3]:
            btn = self.peer_section.get_by_text(tab_name, exact=True).first
            if btn.count():
                btn.click()
                self.page.wait_for_timeout(500)

        peer_rows = self.peer_section.locator(".seo-table-row-hover").count()
        assert peer_rows >= 2, f"Peer comparison table has too few rows: {peer_rows}"

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

    @allure.story("Footer Components")
    def test_Section_14_Footer_Components(self, url: str) -> None:
        self._take_screenshot("Footer Section", "footer, text=Calculators", parent_levels=3)
        assert "©" in self.body_text or "Calculators" in self.body_text, (
            "Footer components missing"
        )

        similar_count = (
            self._count_items_in_section("Other stocks")
            or self._count_items_in_section("Peer Stocks")
        )
        assert similar_count > 0, "Similar/Peer stocks section is missing or empty"

        lower_body = self.body_text.lower()
        assert "1 week" in lower_body, "Peer Stocks '1 week' toggle is missing"
        assert "1 month" in lower_body, "Peer Stocks '1 month' toggle is missing"
        assert "1 year" in lower_body, "Peer Stocks '1 year' toggle is missing"

        calcs_count = self._count_items_in_section("Calculators")
        assert calcs_count > 0, "Calculators section is missing or empty"
