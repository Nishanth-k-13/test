import re

with open("/Users/codingmart/test/test_fyers_all_tabs_detailed.py", "r") as f:
    content = f.read()

replacement = """            try:
                allure.attach(shared_page.screenshot(), name="Section Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        except Exception as e:"""

# Only replace the one with exactly 8 spaces of indentation
content = re.sub(r"^ {8}except Exception as e:$", replacement, content, flags=re.MULTILINE)

with open("/Users/codingmart/test/test_fyers_all_tabs_detailed.py", "w") as f:
    f.write(content)
