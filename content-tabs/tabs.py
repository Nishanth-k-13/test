import pytest
import csv
import os
import json
import fcntl
from playwright.sync_api import Page

MISSING_DATA_FILE = os.path.join(os.path.dirname(__file__), "tabs_missing.jsonl")

def log_missing_data(url, msg):
    """Safely append missing data for a stock to a JSONL file."""
    try:
        with open(MISSING_DATA_FILE, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps({"url": url, "error": msg}) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"Failed to log missing data: {e}")

def get_urls_from_csv():
    file_path = os.path.join(os.path.dirname(__file__), "urls.csv")
    urls = []
    if not os.path.exists(file_path):
        return urls
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row and row[0].strip():
                url = row[0].strip()
                if not url.startswith("http"):
                    url = "https://" + url
                urls.append(url)
    return urls

URLS = get_urls_from_csv()

@pytest.mark.parametrize("url", URLS)
def test_content_tabs_present(page: Page, url: str):
    """
    Test case to find if the content tabs (#cnt-tab-wrap) are present on the given URL.
    Takes URLs from urls.csv
    """
    try:
        # Navigate to the page
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Check for Content Tabs wrap, which is the container for ContentTabs component
        try:
            page.wait_for_selector("#stk-cnt-wrap", timeout=10000)
        except Exception:
            log_missing_data(url, "Content Tabs Missing (#stk-cnt-wrap not found)")
            pytest.fail(f"Content Tabs Missing (#stk-cnt-wrap not found) on {url}")
            
    except Exception as e:
        if not isinstance(e, pytest.fail.Exception):
            log_missing_data(url, f"Page load error or timeout: {str(e)}")
            pytest.fail(f"Page load error or timeout: {str(e)}")
