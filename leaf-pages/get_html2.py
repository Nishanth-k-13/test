from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://fyers.co.in/stocks/gocl-corporation-ltd/dividends')
    
    faq = page.locator('text=FAQ').first
    if faq.count() > 0:
        html = faq.evaluate("el => el.closest('div.container') ? el.closest('div.container').outerHTML : el.parentElement.parentElement.parentElement.outerHTML")
        print("FAQ:", html[:200])
        
    ql = page.locator('text=Quick Links').first
    if ql.count() > 0:
        html2 = ql.evaluate("el => el.parentElement.parentElement.parentElement.outerHTML")
        print("QL:", html2[:200])
        
    browser.close()
