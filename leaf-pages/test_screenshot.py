from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://fyers.co.in/stocks/gocl-corporation-ltd/dividends')
    
    faq = page.locator('text=FAQ').first
    if faq.count() > 0:
        faq.locator("xpath=../..").screenshot(path="faq_parent2.png")
        faq.locator("xpath=../../..").screenshot(path="faq_parent3.png")
        
    ql = page.locator('text=Quick Links').first
    if ql.count() > 0:
        ql.locator("xpath=../..").screenshot(path="ql_parent2.png")
        ql.locator("xpath=../../..").screenshot(path="ql_parent3.png")
        
    browser.close()
