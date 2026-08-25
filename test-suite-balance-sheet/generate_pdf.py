from playwright.sync_api import sync_playwright
import os

def generate_pdf():
    html_path = os.path.abspath('Marcom_SEO_Report.html')
    html_file = f"file://{html_path}"
    pdf_file = "Marcom_SEO_Report.pdf"
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_file, wait_until='networkidle')
        page.pdf(path=pdf_file, format="A4", print_background=True)
        browser.close()
        print(f"PDF report generated: {pdf_file}")

if __name__ == "__main__":
    if os.path.exists("Marcom_SEO_Report.html"):
        generate_pdf()
    else:
        print("HTML report not found, skipping PDF generation.")
