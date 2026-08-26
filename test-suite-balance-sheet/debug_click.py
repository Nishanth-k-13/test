from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://fyers.co.in/stocks/bajaj-consumer-care-ltd/balance-sheet', wait_until='networkidle')
        bs_section = page.locator("div").filter(has=page.locator("text=Consolidated")).filter(has=page.locator("table")).last
        btn = bs_section.get_by_text("Consolidated", exact=True).first
        print("btn count:", btn.count())
        btn.click()
        page.wait_for_timeout(600)
        bs_text = bs_section.first.inner_text()
        print("bs_text len after click:", len(bs_text))
        
        BS_LINE_ITEMS = ["Total Assets", "Share Capital", "Shareholder's Funds", "Shareholders' Funds", "Total Liabilities"]
        found = [item for item in BS_LINE_ITEMS if item in bs_text]
        print("found:", found)
        
        # Test peer section
        peer_section = page.locator("#stk-ovw-peer")
        print("peer_section count:", peer_section.count())
        peer_section.first.scroll_into_view_if_needed()
        
        browser.close()

if __name__ == "__main__":
    debug()
