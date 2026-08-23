import pytest
from playwright.sync_api import sync_playwright, expect
import pandas as pd
import allure
import os
import json

URLS_FILE = "url.csv"

def get_urls():
    if not os.path.exists(URLS_FILE):
        return []
    try:
        df = pd.read_csv(URLS_FILE, header=None)
        return df[0].dropna().tolist()
    except Exception as e:
        print(f"Error reading {URLS_FILE}: {e}")
        return []

URLS = get_urls()

@pytest.fixture(autouse=True, scope="class")
def setup_browser(request, url):
    # We start playwright inside the fixture and attach to request.cls to share it across the class
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch()
    page = browser.new_page()
    
    # Block only media and large unnecessary resources to speed up page loads, keeping CSS/fonts for layout checks
    page.route("**/*", lambda route: route.abort() 
        if route.request.resource_type in ["image", "media"] 
        else route.continue_())
    
    def teardown():
        try:
            browser.close()
            playwright.stop()
        except Exception:
            pass
            
    request.addfinalizer(teardown)
    
    response = page.goto(url, wait_until="load", timeout=60000)
    status_code = response.status if response else "Error"
    request.cls.status_code = status_code
    
    assert response is not None, "Response is None"
    assert response.status == 200, f"Page load failed with status {response.status}"
    page.wait_for_timeout(1000) # Wait for JS to render dynamic sections and tabs
    
    safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")
    request.cls.safe_url = safe_url
    request.cls.page = page
    request.cls.body_text = page.locator("body").inner_text()
    
    yield

@pytest.mark.parametrize("url", URLS, scope="class")
@allure.feature("Dividend Page Full UI and Data Verification")
class TestDividendPage:

    def _take_screenshot(self, name, locator_str=None, parent_levels=0):
        import os
        os.makedirs("screenshots", exist_ok=True)
        safe_name = name.replace(' ', '_').replace('/', '_')
        path = f"screenshots/screenshot_{self.safe_url}_{safe_name}.png"
        try:
            if locator_str and self.page.locator(locator_str).count() > 0:
                el = self.page.locator(locator_str).first
                if parent_levels > 0:
                    xpath = "xpath=" + "/".join([".."] * parent_levels)
                    el = el.locator(xpath)
                el.scroll_into_view_if_needed()
                self.page.wait_for_timeout(500)
                el.screenshot(path=path)
            else:
                self.page.screenshot(path=path, full_page=True)
        except Exception:
            self.page.screenshot(path=path, full_page=True)
            
        allure.attach.file(path, name=name, attachment_type=allure.attachment_type.PNG)
        self.screenshot_path = path

    @allure.story("Header and Meta Data")
    def test_Section_1_Header_and_Meta(self, url):
        allure.dynamic.title(f"Verify Header & Meta on {url}")
        title = self.page.title()
        assert title and len(title.strip()) > 10, f"Page title is too short or missing: '{title}'"
        
        meta_desc = self.page.locator("meta[name='description']")
        assert meta_desc.count() > 0, "Meta description tag is missing"
        content = meta_desc.first.get_attribute("content")
        assert content and len(content.strip()) > 10, "Meta description is empty or too short"
        
        h1 = self.page.locator("h1")
        expect(h1).to_have_count(1, timeout=2000)
        self._take_screenshot("Header Section", "h1")
        assert len(h1.first.inner_text().strip()) > 0, "H1 tag is empty"

    @allure.story("Analytics Tags")
    def test_Section_2_Analytics_Tags(self, url):
        html_content = self.page.content()
        self._take_screenshot("Analytics Source", "head")
        assert "googletagmanager.com" in html_content or "google-analytics.com" in html_content, "GA/GTM tags are missing"

    @allure.story("Graph & Chart")
    def test_Section_3_Graph_and_Chart(self, url):
        self._take_screenshot("Graph Section", "canvas, svg")
        has_svg_or_canvas = self.page.locator("canvas").count() > 0 or self.page.locator("svg").count() > 0
        has_time_toggles = "1D" in self.body_text and "1M" in self.body_text and "1Y" in self.body_text
        assert has_svg_or_canvas or has_time_toggles, "Graph/Chart element or its time controls (1D, 1M, 1Y) are missing"
        
        # Interactive Check: Click 1M toggle if present
        toggle_1m = self.page.locator("text=1M").first
        if toggle_1m.count() > 0:
            try:
                toggle_1m.click(timeout=3000)
                self.page.wait_for_timeout(500)
            except:
                pass

    @allure.story("Content Tabs")
    def test_Section_4_Content_Tabs(self, url):
        self._take_screenshot("Tabs Section", "text=Overview", parent_levels=4)
        # Validate that the main content tabs exist
        overview = self.page.locator("text=Overview")
        dividends = self.page.locator("text=Dividends")
        assert overview.count() > 0 or dividends.count() > 0, "Content tabs ('Overview' or 'Dividends') not found"
        
        # Interactive Check: Click the Overview tab to ensure it's clickable
        if overview.count() > 0:
            try:
                overview.first.scroll_into_view_if_needed()
                overview.first.click(timeout=3000)
                self.page.wait_for_timeout(500)
            except:
                pass
        
        # Validate FAQs tab is present
        faq_tab = self.page.locator("text=FAQ")
        assert faq_tab.count() > 0, "Content tab 'FAQ' is missing"

    @allure.story("Live Stats and Market Cap")
    def test_Section_5_Live_Stats_and_Market_Cap(self, url):
        self._take_screenshot("Live Stats Section", "text=Market Cap", parent_levels=5)
        # Validate multiple key metrics are present to ensure the entire section loaded
        market_cap = self.page.locator("text=Market Cap")
        assert market_cap.count() > 0, "Live Stats 'Market Cap' section not found"
        
        # Check for other stats in the grid
        pe_ratio = self.page.locator("text=P/E")
        pb_ratio = self.page.locator("text=P/B")
        assert pe_ratio.count() > 0 or pb_ratio.count() > 0, "Live Stats data (P/E or P/B) missing, section might be empty"

    @allure.story("Dividend Metrics (Yield, etc.)")
    def test_Section_6_Dividend_Metrics(self, url):
        self._take_screenshot("Dividend Metrics", "text=Div. Yield", parent_levels=5)
        # Validate that dividend-specific metrics exist
        div_yield = self.page.locator("text=Div. Yield")
        div_per_share = self.page.locator("text=Dividend Per Share")
        declared_divs = self.page.locator("text=Declared Dividends")
        
        # Ensure at least some of the metric blocks are rendered
        assert div_yield.count() > 0 or div_per_share.count() > 0 or declared_divs.count() > 0, "Dividend metrics section is completely missing or empty"

    @allure.story("History Table")
    def test_Section_7_History_Table(self, url):
        self._take_screenshot("History Table", "text=Corporate Actions", parent_levels=5)
        # Validate heading and table columns
        corp_actions = self.page.locator("text=Corporate Actions")
        assert corp_actions.count() > 0, "History Table 'Corporate Actions' heading missing"
        
        ex_date = self.page.locator("text=Ex-Date")
        record_date = self.page.locator("text=Record Date")
        assert ex_date.count() > 0 or record_date.count() > 0, "History Table data columns (Ex-Date / Record Date) missing"

    @allure.story("FAQs")
    def test_Section_8_FAQs(self, url):
        self._take_screenshot("FAQs Section", "text=FAQ", parent_levels=3)
        assert "FAQ" in self.body_text or "Frequently Asked Questions" in self.body_text, "FAQs not found"
        
        # Interactive Check: Click on the first question to simulate user expanding the accordion
        questions = self.page.locator("text=?")
        if questions.count() > 0:
            try:
                q = questions.first
                q.scroll_into_view_if_needed()
                q.click(timeout=3000)
                self.page.wait_for_timeout(500)
            except:
                pass

        faq_count = 0
        for script_text in self.page.locator("script[type='application/ld+json']").all_inner_texts():
            if 'FAQPage' in script_text:
                try:
                    data = json.loads(script_text)
                    if 'mainEntity' in data:
                        faq_count = max(faq_count, len(data['mainEntity']))
                except:
                    pass
        assert faq_count > 0, "No FAQs found in structured data (JSON-LD)"
        
        lower_body = self.body_text.lower()
        placeholders = ["lorem ipsum", "undefined", "null", "placeholder text", "dummy text"]
        for ph in placeholders:
            assert ph not in lower_body, f"Found placeholder text '{ph}' in the page content!"

    def _count_items_in_section(self, section_title):
        js_code = f"""() => {{
            const headings = Array.from(document.querySelectorAll('h2, h3, h4'));
            const heading = headings.find(h => h.textContent.toLowerCase().includes('{section_title}'.toLowerCase()));
            if (!heading) return 0;
            const parent = heading.parentElement;
            if ('{section_title}'.toLowerCase().includes('other stocks') || '{section_title}'.toLowerCase().includes('peer stocks')) {{
                const links = Array.from(parent.querySelectorAll('a[href*="/stocks/"]'));
                const uniqueHrefs = new Set(links.map(a => a.href));
                if (uniqueHrefs.size > 0) return uniqueHrefs.size;
                const nextData = document.getElementById('__NEXT_DATA__');
                if (nextData) {{
                    try {{
                        const data = JSON.parse(nextData.textContent);
                        const peers = JSON.stringify(data).match(/"peerStocks":{{.*?"body":\\[(.*?)\\]\\]}}/);
                        if (peers) return peers[1].split('],[').length - 1;
                    }} catch(e) {{}}
                }}
            }}
            const links = parent.querySelectorAll('a');
            if (links.length > 0) return links.length;
            return parent.querySelectorAll('li').length;
        }}"""
        return self.page.evaluate(js_code)

    @allure.story("Footer Components")
    def test_Section_9_Footer_Components(self, url):
        self._take_screenshot("Footer Section", "text=Quick Links", parent_levels=3)
        assert "Quick Links" in self.body_text or "©" in self.body_text, "Footer components missing"
        quick_links_count = self._count_items_in_section("Quick Links")
        assert quick_links_count > 0, "Quick Links section is missing or empty"

        similar_count = self._count_items_in_section("Other stocks") or self._count_items_in_section("Peer Stocks")
        assert similar_count > 0, "Similar/Peer stocks section is missing or empty"
        assert "1 week" in self.body_text.lower(), "Peer Stocks '1 week' toggle is missing"
        assert "1 month" in self.body_text.lower(), "Peer Stocks '1 month' toggle is missing"
        assert "1 year" in self.body_text.lower(), "Peer Stocks '1 year' toggle is missing"

        calcs_count = self._count_items_in_section("Calculators")
        assert calcs_count > 0, "Calculators section is missing or empty"
