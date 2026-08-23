import os
import pyotp
from playwright.sync_api import sync_playwright


LOGIN_URL = "https://login.fyers.in/?cb=https://fyers.in/web/home"

MOBILE_NUMBER ="9342559603"
TOTP_SECRET = "3JDO6BD6GQ436NRKJ3WFOTKX3AQSBX6L"
PIN = 1363


def fill_digit_fields(page, container_id, value):
    """Fill one digit into each input inside a container."""
    digits = list(value)

    fields = page.locator(f"#{container_id} input")

    if fields.count() != len(digits):
        raise RuntimeError(
            f"Expected {len(digits)} fields in #{container_id}, "
            f"but found {fields.count()}"
        )

    for i, digit in enumerate(digits):
        fields.nth(i).fill(digit)


def login(page):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    # --------------------------------------------------
    # 1. Enter mobile number
    # --------------------------------------------------
    mobile = page.locator("#mobile-code")

    mobile.wait_for(state="visible")
    mobile.fill(MOBILE_NUMBER)

    # Continue becomes enabled after valid mobile number
    continue_button = page.locator("#mobileNumberSubmit")

    continue_button.wait_for(state="visible")

    # Wait until the button is enabled
    page.wait_for_function(
        """() => {
            const button = document.querySelector('#mobileNumberSubmit');
            return button && !button.disabled;
        }"""
    )

    continue_button.click()

    # --------------------------------------------------
    # 2. Generate TOTP
    # --------------------------------------------------
    totp = pyotp.TOTP(TOTP_SECRET)
    otp = totp.now()

    print(f"Generated TOTP: {otp}")

    # --------------------------------------------------
    # 3. Enter TOTP
    # --------------------------------------------------
    page.locator("#otp-container").wait_for(state="visible")

    fill_digit_fields(
        page,
        "otp-container",
        otp
    )

    # --------------------------------------------------
    # 4. Wait for PIN screen
    # --------------------------------------------------
    page.locator("#pin-container").wait_for(
        state="visible",
        timeout=15000
    )

    # --------------------------------------------------
    # 5. Enter PIN
    # --------------------------------------------------
    fill_digit_fields(
        page,
        "pin-container",
        PIN
    )

    # --------------------------------------------------
    # 6. Wait for login to complete
    # --------------------------------------------------
    page.wait_for_load_state("networkidle")

    print("Login completed.")
    print("Current URL:", page.url)


with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False
    )

    context = browser.new_context()

    page = context.new_page()

    login(page)

    # Keep browser open if required
    page.wait_for_timeout(5000)

    browser.close()