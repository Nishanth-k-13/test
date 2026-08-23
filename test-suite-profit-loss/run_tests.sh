#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Installing dependencies..."
python3 -m pip install -q -r requirements.txt
python3 -m playwright install chromium

read -r WORKERS SLEEP_INTERVAL URLS_BEFORE_SLEEP RERUN_FAILURES FAILED_URLS_LOG <<< "$(
  python3 -c "import test_profit_loss_pages as m; print(m.WORKERS, m.SLEEP_INTERVAL, m.URLS_BEFORE_SLEEP, m.RERUN_FAILURES, m.FAILED_URLS_LOG)"
)"

if [[ "${WORKERS}" == "auto" ]]; then
  EFFECTIVE_WORKERS="$(python3 -c "import os; print(os.cpu_count() or 4)")"
else
  EFFECTIVE_WORKERS="${WORKERS}"
fi

PER_WORKER_BATCH=$(( URLS_BEFORE_SLEEP / EFFECTIVE_WORKERS ))
if [[ "${PER_WORKER_BATCH}" -lt 1 ]]; then
  PER_WORKER_BATCH=1
fi

echo ""
echo "Running Profit & Loss page test suite..."
echo "  URLs file : ${URLS_FILE:-url.csv}"
echo "  Workers   : ${WORKERS} (${EFFECTIVE_WORKERS} effective)"
echo "  Sleep     : ${SLEEP_INTERVAL}s every ${URLS_BEFORE_SLEEP} URLs total (~${PER_WORKER_BATCH} per worker)"
echo "  Re-run    : ${RERUN_FAILURES} retry round(s) for failed URLs (0 = off)"
echo "  Failures  : ${FAILED_URLS_LOG} (live url + section)"
echo "  (all from test_profit_loss_pages.py)"
echo ""

PYTEST_ARGS=(test_profit_loss_pages.py -v --tb=short)

if [[ "${WORKERS}" != "1" ]]; then
  PYTEST_ARGS+=(-n "${WORKERS}" --dist loadscope)
fi

export EFFECTIVE_WORKERS="${EFFECTIVE_WORKERS}"
export FAILED_URLS_LOG="${FAILED_URLS_LOG}"
ORIGINAL_URLS_FILE="${URLS_FILE:-url.csv}"
export URLS_FILE="${ORIGINAL_URLS_FILE}"

rm -f "${FAILED_URLS_LOG}" report_records.json retry_urls.csv
unset MERGE_REPORT_RECORDS

retry_round=0
while true; do
  if [[ "${retry_round}" -gt 0 ]]; then
    echo ""
    echo "Retry round ${retry_round}/${RERUN_FAILURES} for failed URLs..."
    export URLS_FILE="retry_urls.csv"
    export MERGE_REPORT_RECORDS="report_records.json"
  fi

  set +e
  pytest "${PYTEST_ARGS[@]}" "$@"
  pytest_exit=$?
  set -e

  if [[ ! -f retry_urls.csv ]] || [[ ! -s retry_urls.csv ]]; then
    break
  fi

  if [[ "${RERUN_FAILURES}" -eq 0 ]] || [[ "${retry_round}" -ge "${RERUN_FAILURES}" ]]; then
    break
  fi

  retry_round=$((retry_round + 1))
done

export URLS_FILE="${ORIGINAL_URLS_FILE}"
unset MERGE_REPORT_RECORDS

if [[ -f "${FAILED_URLS_LOG}" ]] && [[ $(wc -l < "${FAILED_URLS_LOG}" | tr -d ' ') -gt 1 ]]; then
  failure_rows=$(( $(wc -l < "${FAILED_URLS_LOG}" | tr -d ' ') - 1 ))
  echo ""
  echo "${failure_rows} failure(s) logged in ${FAILED_URLS_LOG} (see url + section)."
fi

rm -f retry_urls.csv

echo ""
echo "Done. Open Marcom_SEO_Report.html in your browser."

exit "${pytest_exit:-0}"
