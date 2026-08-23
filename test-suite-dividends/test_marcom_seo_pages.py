"""
Marcom SEO Pages Frontend — dividend leaf page UI test suite.

Reads URLs from url.csv and validates 9 page sections per URL.
Generates an HTML report (Marcom_SEO_Report.html) via conftest.py hooks.
"""

from __future__ import annotations

import json
import os

import allure
import pandas as pd
import pytest
from playwright.sync_api import Page, expect, sync_playwright

URLS_FILE = os.getenv("URLS_FILE", "url.csv")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")

# Throttling: sleep every N URLs (per worker) to avoid rate limiting
SLEEP_INTERVAL = int(os.getenv("SLEEP_TIME", "0"))
URLS_BEFORE_SLEEP = int(os.getenv("URLS_BATCH_SIZE", "20"))

_worker_url_count = 0


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

    response = page.goto(url, wait_until="load", timeout=60_000)
    status_code = response.status if response else "Error"
    request.cls.status_code = status_code

    assert response is not None, "Response is None"
    assert response.status == 200, f"Page load failed with status {response.status}"

    page.wait_for_timeout(1_000)

    safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")
    request.cls.safe_url = safe_url
    request.cls.page = page
    request.cls.body_text = page.locator("body").inner_text()

    yield


@pytest.mark.parametrize("url", URLS, scope="class")
@allure.feature("Marcom SEO Pages Frontend")
@allure.story("Dividend Leaf Page Verification")
class TestMarcomSeoPages:
    screenshot_path = ""

    def _take_screenshot(self, name: str, locator_str: str | None = None, parent_levels: int = 0) -> None:
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
        dividends = self.page.locator("text=Dividends")
        assert overview.count() > 0 or dividends.count() > 0, (
            "Content tabs ('Overview' or 'Dividends') not found"
        )

        faq_tab = self.page.locator("text=FAQ")
        assert faq_tab.count() > 0, "Content tab 'FAQ' is missing"

    @allure.story("Live Stats and Market Cap")
    def test_Section_5_Live_Stats_and_Market_Cap(self, url: str) -> None:
        self._take_screenshot("Live Stats Section", "text=Market Cap", parent_levels=5)
        market_cap = self.page.locator("text=Market Cap")
        assert market_cap.count() > 0, "Live Stats 'Market Cap' section not found"

        pe_ratio = self.page.locator("text=P/E")
        pb_ratio = self.page.locator("text=P/B")
        assert pe_ratio.count() > 0 or pb_ratio.count() > 0, (
            "Live Stats data (P/E or P/B) missing"
        )

    @allure.story("Dividend Metrics")
    def test_Section_6_Dividend_Metrics(self, url: str) -> None:
        self._take_screenshot("Dividend Metrics", "text=Div. Yield", parent_levels=5)
        div_yield = self.page.locator("text=Div. Yield")
        div_per_share = self.page.locator("text=Dividend Per Share")
        declared_divs = self.page.locator("text=Declared Dividends")
        assert (
            div_yield.count() > 0 or div_per_share.count() > 0 or declared_divs.count() > 0
        ), "Dividend metrics section is missing or empty"

    @allure.story("History Table")
    def test_Section_7_History_Table(self, url: str) -> None:
        self._take_screenshot("History Table", "text=Corporate Actions", parent_levels=5)
        corp_actions = self.page.locator("text=Corporate Actions")
        assert corp_actions.count() > 0, "History Table 'Corporate Actions' heading missing"

        ex_date = self.page.locator("text=Ex-Date")
        record_date = self.page.locator("text=Record Date")
        assert ex_date.count() > 0 or record_date.count() > 0, (
            "History table columns (Ex-Date / Record Date) missing"
        )

    @allure.story("FAQs")
    def test_Section_8_FAQs(self, url: str) -> None:
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

    def _count_items_in_section(self, section_title: str) -> int:
        js_code = f"""() => {{
            const headings = Array.from(document.querySelectorAll('h2, h3, h4'));
            const heading = headings.find(h =>
                h.textContent.toLowerCase().includes('{section_title}'.toLowerCase())
            );
            if (!heading) return 0;
            const parent = heading.parentElement;
            if ('{section_title}'.toLowerCase().includes('other stocks') ||
                '{section_title}'.toLowerCase().includes('peer stocks')) {{
                const links = Array.from(parent.querySelectorAll('a[href*="/stocks/"]'));
                const uniqueHrefs = new Set(links.map(a => a.href));
                if (uniqueHrefs.size > 0) return uniqueHrefs.size;
            }}
            const links = parent.querySelectorAll('a');
            if (links.length > 0) return links.length;
            return parent.querySelectorAll('li').length;
        }}"""
        return self.page.evaluate(js_code)

    @allure.story("Footer Components")
    def test_Section_9_Footer_Components(self, url: str) -> None:
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
