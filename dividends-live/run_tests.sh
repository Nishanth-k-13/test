
python3 -m playwright install chromium

echo "Starting initial test run..."

pytest test_dividends.py -n 1 --alluredir=allure-results

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
        if len(row) > 1 and (row[1] != '200' or row[2] == 'N/A' or not row[2]):
            failed.append(row[0])
        else:
            good.append(row)

if failed:
    with open('retry_urls.csv', 'w') as f:
        for u in failed:
            if u.strip():
                f.write(u.strip() + '\n')
    with open('good_urls_temp.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(good)
    print(f'Found {len(failed)} failed URLs. Retrying...')
    sys.exit(1)
else:
    print('No failed URLs found.')
    sys.exit(0)
"

if [ $? -eq 1 ]; then
    export URLS_FILE="retry_urls.csv"
    echo "Running pytest again for failed URLs..."
    pytest test_dividends.py -n auto --alluredir=allure-results
    
    echo "Merging results..."
    python3 -c "
import csv
import os

all_rows = []
if os.path.exists('good_urls_temp.csv'):
    with open('good_urls_temp.csv', 'r') as f:
        all_rows.extend(list(csv.reader(f)))

if os.path.exists('seo_report.csv'):
    with open('seo_report.csv', 'r') as f:
        reader = csv.reader(f)
        try:
            next(reader) # skip header
            all_rows.extend(list(reader))
        except StopIteration:
            pass

with open('seo_report.csv', 'w', newline='') as f:
    csv.writer(f).writerows(all_rows)

if os.path.exists('retry_urls.csv'): os.remove('retry_urls.csv')
if os.path.exists('good_urls_temp.csv'): os.remove('good_urls_temp.csv')
"
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
