import re

file_path = "/Users/codingmart/test/test-suite-balance-sheet/test_balance_sheet_pages.py"
with open(file_path, "r") as f:
    content = f.read()

# Make ensure_balance_sheet_panel wait for the table instead of just Consolidated, to ensure data loaded
old_ensure = """    @staticmethod
    def ensure_balance_sheet_panel(page: Page) -> None:
        page.wait_for_selector("text=Consolidated", timeout=30_000)"""

new_ensure = """    @staticmethod
    def ensure_balance_sheet_panel(page: Page) -> None:
        page.wait_for_selector("text=Consolidated", timeout=30_000)
        # Wait for table to appear so that data is fully loaded
        bs = page.locator("div").filter(has=page.locator("text=Consolidated")).filter(has=page.locator("table")).last
        bs.wait_for(state="visible", timeout=30_000)
        # Also wait for Peer Comparison section to be attached
        page.wait_for_selector("#stk-ovw-peer", timeout=30_000)
        page.wait_for_timeout(1000)"""

content = content.replace(old_ensure, new_ensure)

# In test_Section_12, PEER_COMPARISON_TABS is probably looking for ["Overview", "Performance", "Valuation"]
# But the Balance Sheet PeerStocks uses ["1 week", "1 month", "1 year"] for its ranges!
# Let's check PEER_COMPARISON_TABS
