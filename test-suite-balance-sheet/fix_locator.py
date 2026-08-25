file_path = "/Users/codingmart/test/test-suite-balance-sheet/test_balance_sheet_pages.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace('page.wait_for_selector("text=consolidated", timeout=30_000)', 'page.wait_for_selector("text=Consolidated", timeout=30_000)')
content = content.replace('request.cls.bs_section = page.locator("div").filter(has=page.locator("text=\'consolidated\'")).filter(has=page.locator("table")).last', 'request.cls.bs_section = page.locator("div").filter(has=page.locator("text=Consolidated")).filter(has=page.locator("table")).last')
content = content.replace('self._click_sub_tab(self.bs_section, "consolidated")', 'self._click_sub_tab(self.bs_section, "Consolidated")')
content = content.replace('for tab_name in ["consolidated", "standalone"]:', 'for tab_name in ["Consolidated", "Standalone"]:')

with open(file_path, "w") as f:
    f.write(content)
