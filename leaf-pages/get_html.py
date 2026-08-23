from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://fyers.co.in/stocks/gocl-corporation-ltd/dividends')
    
    faq = page.locator('text=FAQ').first
    if faq.count() > 0:
        html = faq.evaluate("el => el.closest('section') ? el.closest('section').outerHTML : (el.closest('div.container') ? el.closest('div.container').outerHTML : 'no section')")
        print("FAQ Section length:", len(html))
        
    ql = page.locator('text=Quick Links').first
    if ql.count() > 0:
        html2 = ql.evaluate("el => el.closest('footer') ? el.closest('footer').outerHTML : (el.closest('section') ? el.closest('section').outerHTML : 'no footer')")
        print("Quick Links Section length:", len(html2))
        
    browser.close()
