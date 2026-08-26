from playwright.sync_api import sync_playwright
import re

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://fyers.co.in/stocks/bajaj-consumer-care-ltd/balance-sheet', wait_until='networkidle')
        bs_section = page.locator("div").filter(has=page.locator("text=Consolidated")).filter(has=page.locator("table")).last
        bs_text = bs_section.inner_text()
        print("bs_text snippet:")
        print(bs_text[:500])
        browser.close()

if __name__ == "__main__":
    debug()
