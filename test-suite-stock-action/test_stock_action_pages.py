"""
Marcom SEO Pages Frontend — Stock Action leaf page UI test suite.

This suite verifies the presence and visibility of critical UI components on the Stock Action pages:
- Section 1: Header and Meta (Page Title, H1 tag)
- Section 2: Tabs (Splits and Rights)
- Section 3: Live Stats (Share Price Live Stats)
- Section 4: Key Ratios (Share Market Cap & Key Ratios Overview)
- Section 5: SWOT Analysis (Stock Analysis (SWOT) component)
- Section 6: Peer Stocks (Peer Stocks component)
- Section 7: Content Tabs (Overview tab)
"""

from __future__ import annotations

import os
import re
import time
import allure
import pandas as pd
import pytest
from playwright.sync_api import Page, expect, sync_playwright

URLS_FILE = os.getenv("URLS_FILE", "url.csv")
URLS_BEFORE_SLEEP = int(os.getenv("URLS_BEFORE_SLEEP", "500"))
SLEEP_TIME_MS = int(os.getenv("SLEEP_TIME_MS", "5000"))
WORKER_COUNT = os.getenv("WORKER_COUNT", "auto")
PAGE_WAIT_MS = 300
_urls_processed = 0
_playwright = None
_browser = None

def get_urls() -> list[str]:
    if not os.path.exists(URLS_FILE):
        return []
    try:
        df = pd.read_csv(URLS_FILE, header=None)
        return df[0].dropna().astype(str).str.strip().tolist()
    except Exception:
        return []

URLS = get_urls()

def _blocked_resource(route) -> None:
    if route.request.resource_type in {"image", "media", "font"}:
        route.abort()
    else:
        route.continue_()

def _get_browser():
    global _playwright, _browser
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=os.getenv("HEADED", "") != "1")
    return _browser

def _shutdown_browser() -> None:
    global _playwright, _browser
    if _browser is not None:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright is not None:
        try:
            _playwright.stop()
        except Exception:
            pass
        _playwright = None

def pytest_sessionfinish(session, exitstatus) -> None:
    _shutdown_browser()

@pytest.fixture(autouse=True, scope="class")
def setup_browser(request, url: str):
    global _urls_processed
    _urls_processed += 1
    
    if URLS_BEFORE_SLEEP > 0 and _urls_processed > 1 and (_urls_processed - 1) % URLS_BEFORE_SLEEP == 0:
        time.sleep(SLEEP_TIME_MS / 1000.0)

    browser = _get_browser()
    page = browser.new_page()
    page.route("**/*", _blocked_resource)

    def teardown() -> None:
        try:
            page.close()
        except Exception:
            pass

    request.addfinalizer(teardown)
    
    response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    assert response and response.status == 200, f"Page load failed for {url}"
    page.wait_for_timeout(PAGE_WAIT_MS)
    
    request.cls.page = page
    yield


@pytest.mark.parametrize("url", URLS, scope="class")
@allure.feature("Marcom SEO Pages Frontend")
@allure.story("Stock Action Pages UI Suite")
class TestMarcomStockActionPages:
    page: Page

    @allure.title("Verify Section 1: Header and Meta")
    @allure.description(
        "Objective: Verify the basic meta information and main header of the Stock Action page.\n\n"
        "What This Test Verifies:\n"
        "- Ensures the page title is populated and correctly set.\n"
        "- Confirms the presence and visibility of the main H1 heading, which indicates the page has loaded successfully."
    )
    def test_Section_1_Header_and_Meta(self):
        with allure.step("Check title presence"):
            expect(self.page).to_have_title(re.compile(r".+"))
        with allure.step("Check H1 presence"):
            h1 = self.page.locator("h1")
            expect(h1).to_be_visible(timeout=5000)

    @allure.title("Verify Section 2: Tabs (Splits and Rights)")
    @allure.description(
        "Objective: Verify the presence and visibility of key interactive tabs in Section 2.\n\n"
        "What This Test Verifies:\n"
        "- Checks if the 'Splits' tab button is present and visible on the page.\n"
        "- Checks if the 'Rights' tab button is present and visible on the page.\n\n"
        "These tabs are critical for users to access historical data related to stock splits and rights issues."
    )
    def test_Section_2_Tabs(self):
        with allure.step("Check Splits tab"):
            splits = self.page.locator('button:has-text("Splits")').first
            expect(splits).to_be_visible(timeout=5000)
        with allure.step("Check Rights tab"):
            rights = self.page.locator('button:has-text("Rights")').first
            expect(rights).to_be_visible(timeout=5000)

    @allure.title("Verify Section 3: Live Stats")
    @allure.description(
        "Objective: Verify the Share Price Live Stats section is available.\n\n"
        "What This Test Verifies:\n"
        "- Checks for the visibility of the 'Share Price Live Stats' text block.\n"
        "This section provides users with the current price, day's high/low, and other real-time statistics."
    )
    def test_Section_3_Live_Stats(self):
        with allure.step("Check Live Stats block"):
            stats = self.page.locator('text="Share Price Live Stats"').first
            expect(stats).to_be_visible(timeout=5000)

    @allure.title("Verify Section 4: Key Ratios")
    @allure.description(
        "Objective: Verify the Key Ratios overview section is loaded correctly.\n\n"
        "What This Test Verifies:\n"
        "- Looks for the 'Share Market Cap & Key Ratios Overview' block.\n"
        "This section provides fundamental indicators like P/E ratio, market cap, and book value."
    )
    def test_Section_4_Key_Ratios(self):
        with allure.step("Check Key Ratios block"):
            ratios = self.page.locator('text="Share Market Cap & Key Ratios Overview"').first
            expect(ratios).to_be_visible(timeout=5000)

    @allure.title("Verify Section 5: SWOT Analysis")
    @allure.description(
        "Objective: Verify the SWOT Analysis section is visible.\n\n"
        "What This Test Verifies:\n"
        "- Ensures the 'Stock Analysis (SWOT)' component is present on the page.\n"
        "SWOT helps users understand the Strengths, Weaknesses, Opportunities, and Threats for the given stock."
    )
    def test_Section_5_SWOT(self):
        with allure.step("Check SWOT component"):
            swot = self.page.locator('text="Stock Analysis (SWOT)"').first
            expect(swot).to_be_visible(timeout=5000)

    @allure.title("Verify Section 6: Peer Stocks")
    @allure.description(
        "Objective: Verify the Peer Stocks section is loaded.\n\n"
        "What This Test Verifies:\n"
        "- Validates the visibility of the 'Peer Stocks' component.\n"
        "This allows users to compare the current stock with other companies in the same sector."
    )
    def test_Section_6_Peer_Stocks(self):
        with allure.step("Check Peer Stocks component"):
            peers = self.page.locator('text="Peer Stocks"').first
            expect(peers).to_be_visible(timeout=5000)

    @allure.title("Verify Section 7: Content Tabs")
    @allure.description(
        "Objective: Verify the presence of detailed content tabs.\n\n"
        "What This Test Verifies:\n"
        "- Specifically checks for the 'Overview' tab button to ensure the detailed tab structure is available."
    )
    def test_Section_7_Content_Tabs(self):
        with allure.step("Check Content Tabs component"):
            overview = self.page.locator('button:has-text("Overview")').first
            expect(overview).to_be_visible(timeout=5000)

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


    @allure.title("Verify Section 8: Other Stocks and Calculators")
    @allure.description(
        "Objective: Verify the presence of footer sections including Other Stocks and Calculators.\n\n"
        "What This Test Verifies:\n"
        "- Uses DOM traversal to count the number of valid items under the 'Other stocks' section.\n"
        "- Uses DOM traversal to count the number of valid items under the 'Calculators' section.\n"
        "Fails if these sections are missing or empty."
    )
    def test_Section_8_Other_Stocks_and_Calculators(self):
        with allure.step("Check Other stocks section"):
            other_stocks_count = self._count_items_in_section("Other stocks")
            assert other_stocks_count > 0, "Other stocks section is missing or empty"
        with allure.step("Check Calculators section"):
            calcs_count = self._count_items_in_section("Calculators")
            assert calcs_count > 0, "Calculators section is missing or empty"
