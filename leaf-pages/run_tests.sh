
python3 -m playwright install chromium

echo "Starting full UI test suite for leaf pages..."
# Run the tests in parallel and generate allure results
pytest full-test.py -n auto --alluredir=allure-results

# Generate HTML report
if command -v allure &> /dev/null
then
    allure generate allure-results --clean -o allure-report
    echo "Allure report generated in allure-report/ directory."
    echo "To view the report, run: allure serve allure-results"
else
    echo "Allure command-line tool is not installed. Skipping HTML report generation."
    echo "Install it via: brew install allure"
fi
