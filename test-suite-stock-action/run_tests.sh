#!/usr/bin/env bash
set -e

VENV_PYTHON="/Users/codingmart/test/test-suite-balance-sheet/.venv/bin/python3"
VENV_PYTEST="/Users/codingmart/test/test-suite-balance-sheet/.venv/bin/pytest"

# Configuration variables
export URLS_BEFORE_SLEEP="${URLS_BEFORE_SLEEP:-500}"
export SLEEP_TIME_MS="${SLEEP_TIME_MS:-5000}"
export WORKER_COUNT="${WORKER_COUNT:-auto}"

$VENV_PYTHON -m playwright install chromium

echo "Starting initial test run..."
rm -rf allure-results/* || true
$VENV_PYTEST test_stock_action_pages.py -n "$WORKER_COUNT" --dist loadscope --alluredir=allure-results

echo "Checking for failed URLs to retry..."
$VENV_PYTHON -c "
import csv
import sys
import os

failed = []
good = []
header = None
if not os.path.exists('failed-urls.csv'):
    sys.exit(0)

with open('failed-urls.csv', 'r') as f:
    reader = csv.reader(f)
    try:
        header = next(reader)
        for row in reader:
            if len(row) > 0:
                failed.append(row[0])
    except StopIteration:
        pass

if failed:
    with open('retry_urls.csv', 'w') as f:
        for u in set(failed):
            f.write(f'{u}\n')
    sys.exit(1)
sys.exit(0)
"

if [ $? -eq 1 ]; then
    export URLS_FILE="retry_urls.csv"
    export RETRY_MODE="1"
    echo "Running pytest again for failed URLs..."
    $VENV_PYTEST test_stock_action_pages.py -n "$WORKER_COUNT" --dist loadscope --alluredir=allure-results
    
    rm -f retry_urls.csv
fi

echo "Allure report generated in allure-report/ directory."
