import re

file_path = "/Users/codingmart/test/test-suite-balance-sheet/test_balance_sheet_pages.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace ensure_balance_sheet_panel entirely
new_ensure = """    @staticmethod
    def ensure_balance_sheet_panel(page: Page) -> None:
        page.wait_for_selector("text=Consolidated", timeout=30_000)
        # Wait for table to appear so that data is fully loaded
        bs = page.locator("div").filter(has=page.locator("text=Consolidated")).filter(has=page.locator("table")).last
        bs.wait_for(state="visible", timeout=30_000)
        # Also wait for Peer Comparison section to be attached
        page.wait_for_selector("#stk-ovw-peer", timeout=30_000)
        page.wait_for_timeout(1000)"""

content = re.sub(
    r'    @staticmethod\n    def ensure_balance_sheet_panel.*?def _take_screenshot',
    new_ensure + "\n\n    def _take_screenshot",
    content,
    flags=re.DOTALL
)

with open(file_path, "w") as f:
    f.write(content)
