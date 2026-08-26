import os
import csv
import pytest

OUTPUT_CSV = "seo_report.csv"

def pytest_sessionstart(session):
    """Initialize CSV and write headers before tests start."""
    if os.environ.get("RETRY_MODE") == "1":
        return
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "URL", "Final URL", "Redirected", "Status Code", "Meta Title", "Meta Description",
            "OG", "TW", "Favicon", "H1", "Template Content", "FAQ Count", "GA or GTM",
            "Quick Links", "Similar Stocks", "Calculators"
        ])
