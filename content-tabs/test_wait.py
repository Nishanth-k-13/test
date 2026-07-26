from playwright.sync_api import sync_playwright

def check(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            # wait 20s
            page.wait_for_selector("#cnt-tab-wrap", timeout=20000)
            print(f"FOUND cnt-tab-wrap on {url}")
        except Exception as e:
            print(f"MISSING cnt-tab-wrap on {url}")
        browser.close()

check("https://fyers.in/stocks/kovai-medical-center-hospital-ltd")
