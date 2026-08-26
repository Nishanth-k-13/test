from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://fyers.co.in/stocks/bajaj-consumer-care-ltd/balance-sheet', wait_until='load')
        peer = page.locator("#stk-ovw-peer")
        print("Count:", peer.count())
        if peer.count() > 0:
            print("Is visible:", peer.first.is_visible())
            print("Is attached:", peer.first.evaluate("el => el.isConnected"))
        browser.close()

if __name__ == "__main__":
    debug()
