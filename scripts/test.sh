#!/usr/bin/env bash
# Run the backend test suite against the isolated `test-db` service.
#
# Usage (from the repository root):
#   pnpm test:api                                  # full suite
#   pnpm test:api -- tests/functional -k cascade   # pytest args pass through
#
# Starts `test-db` if it isn't already running, waits for it to become
# healthy, exports TEST_DATABASE_URL, runs pytest, then stops `test-db`
# only if this script started it (the pgdata_test volume is kept).
set -euo pipefail

STARTED_BY_SCRIPT=0

cleanup() {
  status=$?
  if [ "$STARTED_BY_SCRIPT" = 1 ]; then
    docker compose stop test-db
  fi
  exit "$status"
}
trap cleanup EXIT

if [ -z "$(docker compose ps -q test-db --status running)" ]; then
  STARTED_BY_SCRIPT=1
  docker compose up -d --wait test-db
fi

export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://coach:coach@localhost:5433/coach_test}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"

pytest "$@"
