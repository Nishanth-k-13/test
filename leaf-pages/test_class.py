import pytest
from playwright.sync_api import sync_playwright

URLS = ["https://fyers.co.in/stocks/gocl-corporation-ltd/dividends"]

@pytest.mark.parametrize("url", URLS, scope="class")
class TestDividendPage:
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(self, request, url):
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch()
        page = browser.new_page()
        response = page.goto(url, wait_until="domcontentloaded")
        request.cls.page = page
        yield
        browser.close()
        playwright.stop()

    def test_header(self):
        assert self.page.title()
        
    def test_graph(self):
        assert self.page.locator("body").inner_text()
