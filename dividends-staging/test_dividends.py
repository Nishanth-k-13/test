import pytest
from playwright.sync_api import Page
import pandas as pd
import allure
import os
import csv

URLS_FILE = os.getenv("URLS_FILE", "urls.csv")
OUTPUT_CSV = "seo_report.csv"

def get_urls():
    if not os.path.exists(URLS_FILE):
        return []
    try:
        df = pd.read_csv(URLS_FILE, header=None)
        return df[0].dropna().tolist()
    except Exception as e:
        print(f"Error reading {URLS_FILE}: {e}")
        return []

URLS = get_urls()



@pytest.mark.parametrize("url", URLS)
@allure.feature("Dividend Page SEO Automation")
@allure.story("Extract SEO and Template Data")
def test_seo_data_extraction(page: Page, url: str):
    allure.dynamic.title(f"Extract SEO Data from {url}")
    
    result = {
        "URL": url,
        "Status Code": "",
        "Meta Title": "",
        "Meta Description": "",
        "OG": False,
        "TW": False,
        "Favicon": False,
        "H1": "",
        "Template Content": False,
        "FAQ Count": 0,
        "GA or GTM": False,
        "Quick Links": False,
        "Similar Stocks": False,
        "Calculators": False
    }

    try:
        with allure.step(f"Navigate to {url}"):
            # Block unnecessary resources to drastically speed up page loads
            page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                else route.continue_())
                
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            result["Status Code"] = response.status if response else "N/A"
        
        with allure.step("Wait for page to settle"):
            # A short explicit wait is much faster than waiting for all background pixels to load
            page.wait_for_timeout(1000)
            
        with allure.step("Extract SEO Data"):
            result["Meta Title"] = page.title()
            
            desc_locator = page.locator("meta[name='description']")
            if desc_locator.count() > 0:
                result["Meta Description"] = desc_locator.first.get_attribute("content")
            
            og_locator = page.locator("meta[property='og:title']")
            result["OG"] = "Yes" if og_locator.count() > 0 else "No"
            
            tw_locator = page.locator("meta[name='twitter:title']")
            result["TW"] = "Yes" if tw_locator.count() > 0 else "No"
            
            fav_locator = page.locator("link[rel*='icon']")
            result["Favicon"] = fav_locator.first.get_attribute("href") if fav_locator.count() > 0 else "N/A"
            
            h1_locator = page.locator("h1")
            if h1_locator.count() > 0:
                result["H1"] = h1_locator.first.inner_text().strip()
                
            body_text = page.locator("body").inner_text()
            result["Template Content"] = len(body_text.strip()) > 100
            
            # FAQ Count from JSON-LD schema
            faq_count = 0
            for script_text in page.locator("script[type='application/ld+json']").all_inner_texts():
                if 'FAQPage' in script_text:
                    try:
                        import json
                        data = json.loads(script_text)
                        if 'mainEntity' in data:
                            faq_count = max(faq_count, len(data['mainEntity']))
                    except:
                        pass
            result["FAQ Count"] = faq_count
            
            html_content = page.content()
            has_gtm = "googletagmanager.com" in html_content or "google-analytics.com" in html_content
            result["GA or GTM"] = "Yes" if has_gtm else "No"
            
            def count_items_in_section(section_title):
                # We will use JS evaluation to find the heading and accurately count items below it
                js_code = f"""() => {{
                    const headings = Array.from(document.querySelectorAll('h2, h3, h4'));
                    const heading = headings.find(h => h.textContent.toLowerCase().includes('{section_title}'.toLowerCase()));
                    if (!heading) return 0;
                    
                    let count = 0;
                    // Usually items are in a list, grid, or table in the parent or next sibling
                    const parent = heading.parentElement;
                    
                    if ('{section_title}'.toLowerCase().includes('other stocks') || '{section_title}'.toLowerCase().includes('peer stocks')) {{
                        // Count the number of stock links in this section (excluding time toggles)
                        const links = Array.from(parent.querySelectorAll('a[href*="/stocks/"]'));
                        // Filter unique hrefs to avoid double counting image + text links
                        const uniqueHrefs = new Set(links.map(a => a.href));
                        if (uniqueHrefs.size > 0) return uniqueHrefs.size;
                        
                        // Fallback: Check Next.js state if DOM counting fails
                        const nextData = document.getElementById('__NEXT_DATA__');
                        if (nextData) {{
                            try {{
                                const data = JSON.parse(nextData.textContent);
                                const peers = JSON.stringify(data).match(/"peerStocks":{{.*?"body":\\[(.*?)\\]\\]}}/);
                                if (peers) {{
                                    return peers[1].split('],[').length - 1; // -1 to exclude the current stock itself
                                }}
                            }} catch(e) {{}}
                        }}
                    }}
                    
                    const links = parent.querySelectorAll('a');
                    if (links.length > 0) return links.length;
                    return parent.querySelectorAll('li').length;
                }}"""
                return page.evaluate(js_code)
                
            result["Quick Links"] = count_items_in_section("Quick Links")
            result["Similar Stocks"] = count_items_in_section("Other stocks") or count_items_in_section("Peer Stocks")
            result["Calculators"] = count_items_in_section("Calculators")
            
            screenshot = page.screenshot(full_page=True)
            allure.attach(screenshot, name="Page Screenshot", attachment_type=allure.attachment_type.PNG)
            
    except Exception as e:
        allure.attach(str(e), name="Extraction Error", attachment_type=allure.attachment_type.TEXT)
        result["Status Code"] = "Error"
    
    finally:
        # Append to CSV
        with open(OUTPUT_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                result["URL"], result["Status Code"], result["Meta Title"], result["Meta Description"],
                result["OG"], result["TW"], result["Favicon"], result["H1"], result["Template Content"],
                result["FAQ Count"], result["GA or GTM"], result["Quick Links"], result["Similar Stocks"],
                result["Calculators"]
            ])
            
        import json
        allure.attach(json.dumps(result, indent=4), name="Extracted Data JSON", attachment_type=allure.attachment_type.JSON)
        
        # Add to Allure Parameters for easy viewing
        for key, value in result.items():
            allure.dynamic.parameter(key, str(value))
            
        # Create a beautiful markdown table to display in the Allure Report
        md_table = "| Metric | Value |\\n|---|---|\\n"
        for key, value in result.items():
            md_table += f"| **{key}** | {value} |\\n"
        allure.attach(md_table, name="SEO Metrics Table", attachment_type=allure.attachment_type.TEXT)
        
        # Attach the CSV to allure report incrementally so it's always available
        with open(OUTPUT_CSV, "rb") as f:
            allure.attach(f.read(), name="SEO Report CSV (Accumulated)", attachment_type=allure.attachment_type.CSV)
