import pytest
import allure
from playwright.sync_api import Page, Browser
import csv
import os


def get_urls_from_csv(file_path="url.csv"):
    """Read URLs from csv file, relative to this test file's directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    abs_path = os.path.join(base_dir, file_path)
    if not os.path.exists(abs_path):
        return ["http://128.199.16.179/stocks/stocks/eldeco-housing-industries-lt"]
    urls = []
    with open(abs_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row and row[0].strip():
                url = row[0].strip()
                if not url.startswith("http"):
                    url = "http://" + url
                urls.append(url)
    return urls if urls else ["http://128.199.16.179/stocks/stocks/eldeco-housing-industries-lt"]

URLS = get_urls_from_csv()


@pytest.fixture(scope="class", params=URLS)
def shared_page(request, browser: Browser) -> Page:
    """Navigate to the stock page once per URL and share across tests in the class."""
    url = request.param
    request.cls.url = url
    page = browser.new_page()
    try:
        page.goto(url, timeout=30000)
        page.wait_for_selector("body", timeout=30000)
    except Exception as e:
        msg = f"Page Load Error: {str(e)}"
        pytest.fail(f"[{url}] {msg}")
    yield page
    page.close()


@allure.feature("About Section - Stock Name Match")
@pytest.mark.usefixtures("shared_page")
class TestAboutStockName:
    """
    Verifies that the core Stock Name shown in the Overview section's page header
    matches the Stock Name displayed in the About card body text.
    """

    @allure.story("Stock Name in Page Header Matches About Card Body")
    def test_stock_name_in_about_text(self, shared_page: Page):
        """
        1. Read the stock name from h1#stock-name (strips ' Share Price' suffix).
        2. Clean the stock name by removing common corporate suffixes (Ltd, Limited, etc).
        3. Read the About card body text from #about-stock-text.
        4. Assert the cleaned page-level stock name is contained inside the About body text.
        """
        # ── 1. Read the page-level stock name from h1#stock-name ──────────────
        try:
            shared_page.wait_for_selector("#stock-name", timeout=10000)
        except Exception:
            pytest.fail(f"[{self.url}] h1#stock-name element not found.")

        h1_text = shared_page.locator("#stock-name").inner_text().strip()
        SHARE_PRICE_SUFFIX = " Share Price"
        if h1_text.lower().endswith(SHARE_PRICE_SUFFIX.lower()):
            page_stock_name = h1_text[: -len(SHARE_PRICE_SUFFIX)].strip()
        else:
            page_stock_name = h1_text.strip()

        # ── 2. Read the About card body text from #about-stock-text ───────────
        try:
            shared_page.wait_for_selector("#about-stock-text", timeout=10000)
        except Exception:
            pytest.fail(f"[{self.url}] #about-stock-text not found inside the About card.")

        about_body_text = shared_page.locator("#about-stock-text").inner_text().strip()

        # ── 3. Clean stock name to get the core company name ──────────────────
        # Remove common suffixes to avoid mismatches like "Industries Lt" vs "Inds.Ltd"
        # or "Mahindra & Mahindra Ltd" vs "Mahindra & Mahindra Limited"
        suffixes_to_remove = [
            "ltd", "ltd.", "limited", "lt", "inds", "inds.", "industries", 
            "co", "co.", "corp", "corporation", "inc", "inc."
        ]
        
        words = page_stock_name.split()
        cleaned_words = []
        for w in words:
            if w.lower() not in suffixes_to_remove:
                cleaned_words.append(w)
            else:
                # Once we hit a corporate suffix, we can usually drop the rest of the name
                break
                
        # Fallback to the original name if cleaning removed everything
        match_key = " ".join(cleaned_words) if cleaned_words else page_stock_name

        # ── 4. Assert core stock name appears in the About body text ──────────
        try:
            allure.attach(
                shared_page.screenshot(),
                name="About Section Screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass

        assert match_key.lower() in about_body_text.lower(), (
            f"[{self.url}] Stock name NOT found in About body text!\n"
            f"  Page Header Name : '{page_stock_name}'\n"
            f"  Match Key (Core) : '{match_key}'\n"
            f"  About Text       : '{about_body_text[:200]}...'"
        )
