import pytest
from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://fyers.co.in/stocks/bajaj-consumer-care-ltd/balance-sheet', wait_until='load')
        
        # Mimic ensure_balance_sheet_panel
        page.wait_for_selector("text=Consolidated", timeout=30_000)
        bs = page.locator("div").filter(has=page.locator("text=Consolidated")).filter(has=page.locator("table")).last
        bs.wait_for(state="visible", timeout=30_000)
        
        print("bs count:", bs.count())
        
        bs_text = bs.first.inner_text()
        print("bs_text len:", len(bs_text))
        print("Total Assets in bs_text:", "Total Assets" in bs_text)
        
        browser.close()

if __name__ == "__main__":
    test()
