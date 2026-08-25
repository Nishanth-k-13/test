from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://fyers.co.in/stocks/bajaj-consumer-care-ltd/balance-sheet', wait_until='networkidle')
        print("Peer count:", page.locator("#stk-ovw-peer").count())
        
        # What is the HTML around here?
        print("Body contains peer?", "stk-ovw-peer" in page.content())
        browser.close()

if __name__ == "__main__":
    debug()
