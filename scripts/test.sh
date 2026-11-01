#!/usr/bin/env bash
# Run the backend test suite against the isolated `test-db` service.
#
# Usage (from the repository root):
#   scripts/test.sh                          # full suite
#   scripts/test.sh tests/test_workouts_api.py -k cascade
#   pnpm test:api -- tests/test_workouts_api.py   # same, via pnpm
#
# Starts `test-db` if it isn't already running, waits for it to become
# healthy, exports TEST_DATABASE_URL, runs pytest, then stops `test-db`
# only if this script started it (the pgdata_test volume is kept).
set -euo pipefail

STARTED_BY_SCRIPT=0
if [ -z "$(docker compose ps -q test-db --status running)" ]; then
  docker compose up -d --wait test-db
  STARTED_BY_SCRIPT=1
fi

export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://coach:coach@localhost:5433/coach_test}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"

status=0
pytest "$@" || status=$?

if [ "$STARTED_BY_SCRIPT" = 1 ]; then
  docker compose stop test-db
fi

exit "$status"
