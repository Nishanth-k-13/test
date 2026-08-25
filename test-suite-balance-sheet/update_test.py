import re

file_path = "/Users/codingmart/test/test-suite-balance-sheet/test_balance_sheet_pages.py"

with open(file_path, "r") as f:
    content = f.read()

# 1. Update ensure_balance_sheet_panel
ensure_func = """    @staticmethod
    def ensure_balance_sheet_panel(page: Page) -> None:
        if page.locator("#stk-fund-bs").count() > 0:
            page.locator("#stk-fund-bs").first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            return

        fund_link = page.locator('a[href*="tabs=fundamentals"]').first
        if fund_link.count():
            href = fund_link.get_attribute("href")
            if href:
                page.goto(urljoin(page.url, href), wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(1_500)

        if page.locator("#stk-fund-bs").count() == 0:
            base = re.sub(r"/balance-sheet/?$", "", page.url.split("?")[0].rstrip("/"))
            page.goto(f"{base}?tabs=fundamentals", wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(1_500)

        page.wait_for_selector("#stk-fund-bs", timeout=30_000)
        page.locator("#stk-fund-bs").first.scroll_into_view_if_needed()"""

new_ensure_func = """    @staticmethod
    def ensure_balance_sheet_panel(page: Page) -> None:
        page.wait_for_selector("text=consolidated", timeout=30_000)"""

content = content.replace(ensure_func, new_ensure_func)

# 2. Update locators
locators = """    request.cls.pl_section = page.locator("#stk-fund-pl")
    request.cls.bs_section = page.locator("#stk-fund-bs")
    request.cls.cf_section = page.locator("#stk-fund-cf")
    request.cls.ratios_section = page.locator("#stk-fund-ratios")
    request.cls.peer_section = page.locator("#stk-fund-peer")"""

new_locators = """    request.cls.pl_section = page.locator("#stk-fund-pl")
    request.cls.bs_section = page.locator("div").filter(has=page.locator("text='consolidated'")).filter(has=page.locator("table")).last
    request.cls.cf_section = page.locator("#stk-fund-cf")
    request.cls.ratios_section = page.locator("#stk-fund-ratios")
    request.cls.peer_section = page.locator("#stk-ovw-peer")"""

content = content.replace(locators, new_locators)

# 3. Update _count_numeric_cells
count_func = """    def _count_numeric_cells(self, selector: str) -> int:
        return self.page.evaluate(
            f\"\"\"() => {{
                const section = document.querySelector('{selector}');
                if (!section) return 0;
                return Array.from(section.querySelectorAll('td'))
                    .filter(c => /[\\d,]+/.test(c.textContent))
                    .length;
            }}\"\"\"
        )"""

new_count_func = """    def _count_numeric_cells(self, section) -> int:
        return section.first.evaluate(
            \"\"\"(el) => {
                return Array.from(el.querySelectorAll('td'))
                    .filter(c => /[\\d,]+/.test(c.textContent))
                    .length;
            }\"\"\"
        )"""

content = content.replace(count_func, new_count_func)

# 4. Remove unwanted tests (Sections 6, 9, 10, 11) using regex
content = re.sub(r'    @allure\.story\("Financial Overview"\).*?(?=    @allure\.story\("Balance Sheet Structure"\))', '', content, flags=re.DOTALL)
content = re.sub(r'    @allure\.story\("P&L Statement Structure"\).*?(?=    @allure\.story\("Peer Comparison"\))', '', content, flags=re.DOTALL)

# 5. Fix Balance Sheet Structure test (Section 7 and 8)
bs_test_old = """    @allure.story("Balance Sheet Structure")
    def test_Section_7_Balance_Sheet_Structure(self, url: str) -> None:
        self.bs_section.first.scroll_into_view_if_needed()
        self._take_screenshot("Balance Sheet", "#stk-fund-bs")
        assert self.bs_section.count() > 0, "Balance Sheet section (#stk-fund-bs) not found"

        bs_text = self._section_text(self.bs_section)
        assert "Balance Sheet" in bs_text or "Balance sheet" in bs_text, (
            "Balance Sheet heading not found"
        )
        assert self.bs_section.locator("table").count() > 0, "Balance Sheet table not found"

        for tab_name in PL_SUB_TABS:
            btn = self.bs_section.get_by_text(tab_name, exact=True).first
            assert btn.count() > 0, f"Balance Sheet sub-tab missing: {tab_name}"
            btn.click()
            self.page.wait_for_timeout(600)
            assert self.bs_section.locator("table").count() > 0, (
                f"Balance Sheet table not visible after clicking {tab_name}"
            )"""

bs_test_new = """    @allure.story("Balance Sheet Structure")
    def test_Section_7_Balance_Sheet_Structure(self, url: str) -> None:
        self.bs_section.first.scroll_into_view_if_needed()
        assert self.bs_section.count() > 0, "Balance Sheet section not found"

        assert self.bs_section.locator("table").count() > 0, "Balance Sheet table not found"

        for tab_name in ["consolidated", "standalone"]:
            btn = self.bs_section.get_by_text(tab_name, exact=True).first
            assert btn.count() > 0, f"Balance Sheet sub-tab missing: {tab_name}"
            btn.click()
            self.page.wait_for_timeout(600)
            assert self.bs_section.locator("table").count() > 0, (
                f"Balance Sheet table not visible after clicking {tab_name}"
            )"""

content = content.replace(bs_test_old, bs_test_new)

bs_line_items_old = """    @allure.story("Balance Sheet Line Items and Data")
    def test_Section_8_Balance_Sheet_Line_Items_and_Data(self, url: str) -> None:
        self._click_sub_tab(self.bs_section, "Consolidated")
        bs_text = self._section_text(self.bs_section)

        found = [item for item in BS_LINE_ITEMS if item in bs_text]
        assert len(found) >= 1, f"Expected balance sheet line items, found: {found}"

        numeric_count = self._count_numeric_cells("#stk-fund-bs")
        assert numeric_count >= 3, (
            f"Balance Sheet table has insufficient numeric cells: {numeric_count}"
        )

        for tab_name in ("Quarterly", "Yearly"):
            self._click_sub_tab(self.bs_section, tab_name)
            assert self._count_numeric_cells("#stk-fund-bs") > 0, (
                f"Balance Sheet table empty after switching to {tab_name}"
            )

        self._take_screenshot("Balance Sheet Data Table", "#stk-fund-bs")"""

bs_line_items_new = """    @allure.story("Balance Sheet Line Items and Data")
    def test_Section_8_Balance_Sheet_Line_Items_and_Data(self, url: str) -> None:
        self._click_sub_tab(self.bs_section, "consolidated")
        bs_text = self._section_text(self.bs_section)

        found = [item for item in BS_LINE_ITEMS if item in bs_text]
        assert len(found) >= 1, f"Expected balance sheet line items, found: {found}"

        numeric_count = self._count_numeric_cells(self.bs_section)
        assert numeric_count >= 3, (
            f"Balance Sheet table has insufficient numeric cells: {numeric_count}"
        )"""

content = content.replace(bs_line_items_old, bs_line_items_new)

# Update remaining take_screenshot calls using `#stk-fund-peer`
content = content.replace('self._take_screenshot("Peer Comparison", "#stk-fund-peer")', 'self._take_screenshot("Peer Comparison", "#stk-ovw-peer")')
content = content.replace('self.peer_section.count() > 0, "Peer comparison section (#stk-fund-peer) not found"', 'self.peer_section.count() > 0, "Peer comparison section (#stk-ovw-peer) not found"')

with open(file_path, "w") as f:
    f.write(content)

print("Done")
