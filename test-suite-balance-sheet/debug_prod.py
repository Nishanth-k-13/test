from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://fyers.co.in/stocks/bajaj-consumer-care-ltd/balance-sheet', wait_until='networkidle')
        print("Consolidated text count:", page.locator("text=Consolidated").count())
        print("stk-fund-bs count:", page.locator("#stk-fund-bs").count())
        print("stk-ovw-peer count:", page.locator("#stk-ovw-peer").count())
        print("stk-fund-peer count:", page.locator("#stk-fund-peer").count())
        browser.close()

if __name__ == "__main__":
    debug()
