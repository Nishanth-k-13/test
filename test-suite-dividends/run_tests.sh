#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# ---------------------------------------------------------------------------
# Options (env vars or flags):
#   WORKERS / -w N       parallel workers (default: 1). Use "auto" for all cores.
#   SLEEP_TIME / -s N    seconds to sleep between URL batches (default: 0 = off)
#   URLS_BATCH_SIZE / -b N   sleep every N URLs per worker (default: 20)
#   URLS_FILE            path to CSV of URLs (default: url.csv)
#   HEADED=1             show browser UI
#
# Examples:
#   ./run_tests.sh
#   ./run_tests.sh -w 4
#   ./run_tests.sh -w auto -s 6 -b 20
#   WORKERS=4 SLEEP_TIME=6 ./run_tests.sh
#   ./run_tests.sh -w 2 -- -k Header
# ---------------------------------------------------------------------------

WORKERS="${WORKERS:-1}"
SLEEP_TIME="${SLEEP_TIME:-0}"
URLS_BATCH_SIZE="${URLS_BATCH_SIZE:-20}"
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Usage: ./run_tests.sh [options] [-- pytest-args...]

Options:
  -w, --workers N       Number of parallel workers (default: 1, or "auto")
  -s, --sleep N         Sleep N seconds between URL batches (default: 0)
  -b, --batch-size N    Sleep every N URLs per worker (default: 20)
  -h, --help            Show this help

Environment:
  WORKERS, SLEEP_TIME, URLS_BATCH_SIZE, URLS_FILE, HEADED

Examples:
  ./run_tests.sh
  ./run_tests.sh -w 4
  ./run_tests.sh -w auto -s 6 -b 20
  WORKERS=4 SLEEP_TIME=6 ./run_tests.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -w|--workers)
      WORKERS="$2"
      shift 2
      ;;
    -s|--sleep)
      SLEEP_TIME="$2"
      shift 2
      ;;
    -b|--batch-size)
      URLS_BATCH_SIZE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_ARGS+=("$@")
      break
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

export URLS_FILE="${URLS_FILE:-url.csv}"
export SLEEP_TIME
export URLS_BATCH_SIZE

echo "Installing dependencies..."
python3 -m pip install -q -r requirements.txt
python3 -m playwright install chromium

echo ""
echo "Running Marcom SEO Pages Frontend (Dividends) test suite..."
echo "  URLs file   : ${URLS_FILE}"
echo "  Workers     : ${WORKERS}"
echo "  Sleep       : ${SLEEP_TIME}s every ${URLS_BATCH_SIZE} URLs (per worker)"
echo ""

PYTEST_ARGS=(test_marcom_seo_pages.py -v --tb=short)

if [[ "${WORKERS}" != "1" ]]; then
  PYTEST_ARGS+=(-n "${WORKERS}" --dist loadscope)
fi

pytest "${PYTEST_ARGS[@]}" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"

echo ""
echo "Done. Open Marcom_SEO_Report.html in your browser."
