#!/usr/bin/env bash
# Smoke test: boots the app in demo mode on a random port and checks
# the main endpoints. Prints PASS/FAIL per endpoint, exits non-zero on failure.
set -u
cd "$(dirname "$0")/.."

PORT=$((RANDOM % 9000 + 2000))
BASE="http://127.0.0.1:$PORT"

DEMO=1 python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >/dev/null 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null; wait "$PID" 2>/dev/null' EXIT

# Wait for the server (max ~15 s).
for _ in $(seq 1 30); do
  if curl -sf "$BASE/api/health" >/dev/null 2>&1; then break; fi
  sleep 0.5
done

fail=0
check() { # $1 = path, $2 = grep pattern
  if curl -sf "$BASE$1" 2>/dev/null | grep -q -- "$2"; then
    echo "PASS $1"
  else
    echo "FAIL $1 (expected pattern: $2)"
    fail=1
  fi
}

check "/api/health"                     '"status":"ok"'
check "/"                               "Climate Canvas"
check "/report"                         "Тижневий звіт"
check "/api/rooms"                      '"rooms"'
check "/api/timeline?room=Bedroom&metric=temperature&days=7" '"points"'
check "/api/heatmap?room=Kitchen&metric=mold_risk&days=30"   '"values"'
check "/api/outdoor?days=2"             '"points"'
check "/api/forecast?hours=48"          '"points"'
check "/api/report/weekly"              '"avg"'
check "/static/manifest.webmanifest"    '"start_url"'

if [ "$fail" -eq 0 ]; then
  echo "SMOKE: PASS"
else
  echo "SMOKE: FAIL"
fi
exit "$fail"
