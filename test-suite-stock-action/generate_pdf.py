import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def generate_pdf():
    html_path = Path("Marcom_SEO_Report.html").resolve()
    pdf_path = Path("Marcom_SEO_Report.pdf").resolve()
    
    if not html_path.exists():
        print(f"Error: {html_path.name} not found.")
        return

    print(f"Generating PDF from {html_path.name}...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{html_path}")
        
        # Wait for the page and dynamic content to finish loading
        page.wait_for_load_state("networkidle")
        
        # Export as PDF with background colors included
        page.pdf(path=str(pdf_path), format="A4", print_background=True, scale=0.8)
        browser.close()
        
    print(f"Successfully created: {pdf_path.name}")

if __name__ == "__main__":
    generate_pdf()
