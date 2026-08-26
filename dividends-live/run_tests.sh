
python3 -m playwright install chromium

echo "Starting initial test run..."

pytest test_dividends.py -n auto --alluredir=allure-results

echo "Checking for failed URLs to retry..."
python3 -c "
import csv
import sys
import os

failed = []
good = []
header = None
if not os.path.exists('seo_report.csv'):
    sys.exit(0)

with open('seo_report.csv', 'r') as f:
    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        sys.exit(0)
    for row in reader:
        # Check if row represents a failure (non-200, N/A, Error)
        if len(row) > 3 and (row[3] != '200' or row[3] == 'N/A' or row[3] == 'Error'):
            failed.append(row[0])
        else:
            good.append(row)

if failed:
    with open('retry_urls.csv', 'w') as f:
        for u in failed:
            if u.strip():
                f.write(u.strip() + '\n')
    print(f'Found {len(failed)} failed URLs. Retrying...')
    sys.exit(1)
else:
    print('No failed URLs found.')
    sys.exit(0)
"

if [ $? -eq 1 ]; then
    export URLS_FILE="retry_urls.csv"
    export RETRY_MODE="1"
    echo "Running pytest again for failed URLs..."
    pytest test_dividends.py -n auto --alluredir=allure-results
    
    echo "Deduplicating seo_report.csv..."
    python3 -c "
import csv
rows = []
header = None
seen_urls = set()
with open('seo_report.csv', 'r') as f:
    reader = csv.reader(f)
    try:
        header = next(reader)
        for row in reader:
            rows.append(row)
    except StopIteration:
        pass

# Deduplicate keeping the LAST occurrence
unique_rows = []
for row in reversed(rows):
    if row and row[0] not in seen_urls:
        unique_rows.append(row)
        seen_urls.add(row[0])

unique_rows.reverse()
with open('seo_report.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    if header:
        writer.writerow(header)
    writer.writerows(unique_rows)
"
    rm -f retry_urls.csv
fi

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
