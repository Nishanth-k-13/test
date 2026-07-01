import pytest
import allure
from playwright.sync_api import Page, Browser, expect
import csv
import os
import json
import fcntl

MISSING_DATA_FILE = "missing_data_report.jsonl"

def log_missing_data(url, section):
    """Safely append missing data for a stock to a JSONL file."""
    try:
        with open(MISSING_DATA_FILE, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps({"url": url, "missing_section": section}) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass

def get_urls_from_csv(file_path="urls.csv"):
    if not os.path.exists(file_path):
        return ["https://fyers.co.in/stocks/mahindra-mahindra-ltd"]
    urls = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row and row[0].strip():
                url = row[0].strip()
                if not url.startswith("http"):
                    url = "http://" + url
                urls.append(url)
    return urls if urls else ["https://fyers.co.in/stocks/mahindra-mahindra-ltd"]

URLS = get_urls_from_csv()

def check_data(page: Page, selector: str, url: str, missing_msg: str, timeout=4000):
    """Wait for a selector to appear, log it if missing."""
    try:
        page.wait_for_selector(selector, timeout=timeout)
    except Exception:
        try:
            allure.attach(page.screenshot(), name="Error Screenshot", attachment_type=allure.attachment_type.PNG)
        except Exception:
            pass
        log_missing_data(url, missing_msg)
        pytest.fail(missing_msg)

@pytest.fixture(scope="class", params=URLS)
def shared_page(request, browser: Browser) -> Page:
    """Navigate to the stock page once per URL and share the page across all tests in the class."""
    url = request.param
    request.cls.url = url
    page = browser.new_page()
    try:
        page.goto(url, timeout=30000)
        page.wait_for_selector("body", timeout=30000)
    except Exception as e:
        log_missing_data(url, f"Page Load Error: {str(e)}")
    yield page
    page.close()

@allure.feature("Comprehensive Stock Tabs Testing")
@pytest.mark.usefixtures("shared_page")
class TestStockTabsComprehensive:
    
    @allure.story("1. Global Header")
    def test_global_header(self, shared_page: Page):
        try:
            shared_page.wait_for_selector("#stk-tab-list, h1", timeout=10000)
        except Exception:
            log_missing_data(self.url, "Global Header Missing")
            pytest.fail("Global Header Missing")

    @allure.story("2. Overview Tab")
    def test_overview_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-ovw").count() > 0:
                shared_page.click("#stk-tab-ovw", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-ovw", timeout=5000)
                
                # Check for critical overview data
                check_data(shared_page, "#stk-panel-ovw div, #stk-panel-ovw p", self.url, "Overview - Missing Content")
                
                # Check for NSE / BSE Toggle button
                try:
                    toggle = shared_page.locator("#stock-exchange-toggle")
                    expect(toggle).to_be_visible(timeout=5000)
                    
                    # Verify it contains either NSE or BSE
                    text = toggle.inner_text().strip()
                    if "NSE" not in text and "BSE" not in text:
                        pytest.fail(f"Overview - Toggle button missing 'NSE' or 'BSE' text (Found: '{text}')")
                except Exception as e:
                    msg = "Overview - Missing NSE/BSE Toggle Button"
                    try:
                        allure.attach(shared_page.screenshot(), name="Toggle Missing", attachment_type=allure.attachment_type.PNG)
                    except Exception:
                        pass
                    log_missing_data(self.url, msg)
                    pytest.fail(msg)
            else:
                log_missing_data(self.url, "Overview Tab Missing")
                pytest.fail("Overview Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "Overview Tab Could Not Be Loaded")
                pytest.fail("Overview Tab Could Not Be Loaded")
            raise

    @allure.story("3. Fundamentals Tab")
    def test_fundamentals_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-fund").count() > 0:
                shared_page.click("#stk-tab-fund", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-fund", timeout=5000)
                
                # Check for each financial sub-section individually
                sections_to_check = [
                    ("#stk-panel-fund-fin-ovw", "Financial Overview"),
                    ("#stk-panel-fund-peer", "Peer Comparison"),
                    ("#stk-panel-fund-pl", "Profit & Loss"),
                    ("#stk-panel-fund-bs", "Balance Sheet"),
                    ("#stk-panel-fund-cf", "Cash Flow"),
                    ("#stk-panel-fund-ratios", "Fundamental Ratios")
                ]
                
                for section_id, name in sections_to_check:
                    try:
                        # Wait for any skeleton loaders to disappear
                        skeleton = shared_page.locator(f"{section_id} .animate-pulse")
                        if skeleton.count() > 0:
                            skeleton.first.wait_for(state="hidden", timeout=10000)
                            
                        # If the section contains "No results found", the data is genuinely missing
                        not_found = shared_page.locator(f"{section_id}").filter(has_text="No results found")
                        if not_found.count() > 0 and not_found.is_visible():
                            msg = f"Fundamentals - Missing {name} Data"
                            try:
                                allure.attach(shared_page.screenshot(), name=f"{name} Missing", attachment_type=allure.attachment_type.PNG)
                            except Exception:
                                pass
                            log_missing_data(self.url, msg)
                            pytest.fail(msg)
                    except Exception as e:
                        if isinstance(e, pytest.fail.Exception):
                            raise
                        msg = f"Fundamentals - Timeout or error checking {name}"
                        log_missing_data(self.url, msg)
                        pytest.fail(msg)
            else:
                log_missing_data(self.url, "Fundamentals Tab Missing")
                pytest.fail("Fundamentals Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "Fundamentals Content Failed to Load")
                pytest.fail("Fundamentals Content Failed to Load")
            raise

    @allure.story("4. Technicals Tab")
    def test_technicals_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-tech").count() > 0:
                shared_page.click("#stk-tab-tech", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-tech", timeout=5000)
                
                # Check for technical gauges/indicators
                check_data(shared_page, "#stk-panel-tech svg, #stk-panel-tech canvas, #stk-panel-tech [class*='meter'], #stk-panel-tech [class*='gauge']", self.url, "Technicals - No Gauges/Data")
            else:
                log_missing_data(self.url, "Technicals Tab Missing")
                pytest.fail("Technicals Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "Technicals Content Failed to Load")
                pytest.fail("Technicals Content Failed to Load")
            raise

    @allure.story("5. Corporate Actions Tab")
    def test_corporate_actions_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-corp").count() > 0:
                shared_page.click("#stk-tab-corp", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-corp", timeout=5000)
                
                # Check for corporate action tables
                check_data(shared_page, "#stk-panel-corp table, #stk-panel-corp [class*='table']", self.url, "Corporate Actions - No Data Table")
            else:
                log_missing_data(self.url, "Corporate Actions Tab Missing")
                pytest.fail("Corporate Actions Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "Corporate Actions Content Failed to Load")
                pytest.fail("Corporate Actions Content Failed to Load")
            raise

    @allure.story("6. Charts Tab")
    def test_charts_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-chart").count() > 0:
                shared_page.click("#stk-tab-chart", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-chart", timeout=5000)
            else:
                log_missing_data(self.url, "Charts Tab Missing")
                pytest.fail("Charts Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "Charts Content Failed to Load")
                pytest.fail("Charts Content Failed to Load")
            raise

    @allure.story("7. F&O Tab")
    def test_fo_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-fo").count() > 0:
                shared_page.click("#stk-tab-fo", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-fo", timeout=5000)
                
                # Check for image or AuthToast links (Access Platform / Login)
                check_data(shared_page, "#stk-panel-fo img, #stk-panel-fo a", self.url, "F&O - No Options Chain Data")
            else:
                log_missing_data(self.url, "F&O Tab Missing")
                pytest.fail("F&O Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "F&O Content Failed to Load")
                pytest.fail("F&O Content Failed to Load")
            raise

    @allure.story("8. Shareholding Tab")
    def test_shareholding_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-hold").count() > 0:
                shared_page.click("#stk-tab-hold", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-hold", timeout=5000)
                
                # Check for shareholding patterns / pie charts
                check_data(shared_page, "#stk-panel-hold canvas, #stk-panel-hold svg, #stk-panel-hold [class*='chart']", self.url, "Shareholding - No Chart Data")
            else:
                log_missing_data(self.url, "Shareholding Tab Missing")
                pytest.fail("Shareholding Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "Shareholding Content Failed to Load")
                pytest.fail("Shareholding Content Failed to Load")
            raise

    @allure.story("9. News Tab")
    def test_news_tab(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-news").count() > 0:
                shared_page.click("#stk-tab-news", timeout=5000)
                shared_page.wait_for_selector("#stk-panel-news", timeout=5000)
                check_data(shared_page, "#stk-panel-news h3", self.url, "News - No News Articles")
            else:
                log_missing_data(self.url, "News Tab Missing")
                pytest.fail("News Tab Missing")
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "News Content Failed to Load")
                pytest.fail("News Content Failed to Load")
            raise

    @allure.story("10. FAQs")
    def test_faqs(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-faq").count() > 0:
                shared_page.click("#stk-tab-faq", timeout=5000)
            
            # Check for general SEO content panels (they typically start with stk-cnt)
            check_data(shared_page, "[id^='stk-cnt']", self.url, "SEO Content / FAQs Missing")
            
            # Enforce exactly 5 FAQs
            try:
                shared_page.wait_for_selector("[id^='stk-cnt'] button", timeout=4000)
                faq_count = shared_page.locator("[id^='stk-cnt'] button").count()
                if faq_count != 5:
                    msg = f"FAQs - Expected 5 FAQs, found {faq_count}"
                    log_missing_data(self.url, msg)
                    pytest.fail(msg)
            except Exception as inner_e:
                if isinstance(inner_e, pytest.fail.Exception):
                    raise
                msg = "FAQs - Count check failed or no FAQs found"
                log_missing_data(self.url, msg)
                pytest.fail(msg)
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "FAQs Content Failed to Load")
                pytest.fail("FAQs Content Failed to Load")
            raise

    @allure.story("11. SEO Content Tabs")
    def test_seo_content(self, shared_page: Page):
        try:
            if shared_page.locator("#stk-tab-faq").count() > 0:
                shared_page.click("#stk-tab-faq", timeout=5000)
                
            # Enforce that "Share Price Today" content tab exists
            try:
                shared_page.wait_for_selector("button:has-text('Share Price Today')", timeout=4000)
            except Exception:
                msg = "SEO Content - Missing 'Share Price Today' tab"
                log_missing_data(self.url, msg)
                pytest.fail(msg)
            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:
            if not isinstance(e, pytest.fail.Exception):
                log_missing_data(self.url, "SEO Content Failed to Load")
                pytest.fail("SEO Content Failed to Load")
            raise
