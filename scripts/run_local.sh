#!/usr/bin/env bash
#
# Bring the whole Indus11 stack up with one command: databases, API, dashboard.
#
#   ./scripts/run_local.sh           start everything (keeps existing data)
#   ./scripts/run_local.sh --seed    rebuild MongoDB + Neo4j data first
#
# Ctrl-C stops the API and the dashboard. The databases keep running as brew
# services, which is what you want between demos: starting them is the slow part.
#
set -uo pipefail
cd "$(dirname "$0")/.."

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; RED=$'\033[31m'; OFF=$'\033[0m'
ok()   { echo "  ${GREEN}ok${OFF}  $1"; }
info() { echo "  ${DIM}··${OFF}  $1"; }
fail() { echo "  ${RED}!!${OFF}  $1"; }

API_PORT=8000
DASH_PORT=5175

cleanup() {
  echo
  echo "${BOLD}Stopping…${OFF}"
  [[ -n "${API_PID:-}"  ]] && kill "$API_PID"  2>/dev/null && info "API stopped"
  [[ -n "${DASH_PID:-}" ]] && kill "$DASH_PID" 2>/dev/null && info "dashboard stopped"
  info "databases left running (brew services stop neo4j redis mongodb-community@7.0)"
  exit 0
}
trap cleanup INT TERM

wait_for_port() {   # wait_for_port <port> <name> <seconds>
  for _ in $(seq 1 "$3"); do
    nc -z localhost "$1" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

echo
echo "${BOLD}Indus11${OFF} ${DIM}starting local stack${OFF}"
echo

# ── 1. Databases ─────────────────────────────────────────────────────────────
echo "${BOLD}1/4  Databases${OFF}"

# The plain `mongodb-community` formula is installed but broken on this machine;
# @7.0 is the one that actually runs. Try the versioned one first either way.
for formula in mongodb-community@7.0 mongodb-community; do
  if brew services list 2>/dev/null | grep -q "^$formula .*started"; then
    ok "mongodb ($formula) already running"; break
  fi
  if brew services start "$formula" >/dev/null 2>&1; then
    ok "mongodb ($formula) started"; break
  fi
done

if brew services list 2>/dev/null | grep -q "^redis .*started"; then
  ok "redis already running"
else
  brew services start redis >/dev/null 2>&1 && ok "redis started"
fi

# Neo4j writes a pidfile on shutdown and does not always clear it. The OS then
# reuses that PID for an unrelated process, Neo4j sees "already running" and
# refuses to boot — silently, with brew still reporting the service as started.
# This broke the stack twice, so clear a stale pidfile before starting.
PIDFILE=$(find /opt/homebrew/Cellar/neo4j/*/libexec/run -name neo4j.pid 2>/dev/null | head -1)
if [[ -n "$PIDFILE" ]]; then
  STALE_PID=$(cat "$PIDFILE" 2>/dev/null)
  if ! ps -p "$STALE_PID" -o comm= 2>/dev/null | grep -qi "java\|neo4j"; then
    rm -f "$PIDFILE"
    info "cleared stale neo4j pidfile (pid $STALE_PID was not neo4j)"
    brew services restart neo4j >/dev/null 2>&1
  fi
fi
brew services list 2>/dev/null | grep -q "^neo4j .*started" \
  || brew services start neo4j >/dev/null 2>&1

for probe in "27017 mongodb" "6379 redis" "7687 neo4j"; do
  set -- $probe
  if wait_for_port "$1" "$2" 45; then
    ok "$2 listening on $1"
  else
    fail "$2 did not come up on port $1"
    exit 1
  fi
done

# ── 2. Seed (only when asked) ────────────────────────────────────────────────
echo
echo "${BOLD}2/4  Data${OFF}"
if [[ "${1:-}" == "--seed" ]]; then
  info "rebuilding seed data…"
  .venv/bin/python -m scripts.seed_mongo && ok "mongodb seeded"
  .venv/bin/python -m scripts.seed_neo4j && ok "neo4j graph seeded"
else
  ok "using existing data (pass --seed to rebuild it)"
fi

# ── 3. API ───────────────────────────────────────────────────────────────────
echo
echo "${BOLD}3/4  API${OFF}"
if nc -z localhost "$API_PORT" >/dev/null 2>&1; then
  ok "already listening on $API_PORT, reusing it"
else
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" \
    > /tmp/indus11-api.log 2>&1 &
  API_PID=$!
  info "booting (loads Chroma, connects 3 databases, ~20s)…"
  if wait_for_port "$API_PORT" api 90; then
    ok "API on http://localhost:$API_PORT"
  else
    fail "API failed to start. Last lines of /tmp/indus11-api.log:"
    tail -15 /tmp/indus11-api.log
    exit 1
  fi
fi

# ── 4. Dashboard ─────────────────────────────────────────────────────────────
echo
echo "${BOLD}4/4  Dashboard${OFF}"
if nc -z localhost "$DASH_PORT" >/dev/null 2>&1; then
  ok "already listening on $DASH_PORT, reusing it"
else
  npm run dev --prefix dashboard -- --port "$DASH_PORT" \
    > /tmp/indus11-dashboard.log 2>&1 &
  DASH_PID=$!
  if wait_for_port "$DASH_PORT" dashboard 60; then
    ok "dashboard on http://localhost:$DASH_PORT"
  else
    fail "dashboard failed to start. See /tmp/indus11-dashboard.log"
    exit 1
  fi
fi

echo
echo "${BOLD}Ready.${OFF}"
echo "   Dashboard   ${BOLD}http://localhost:$DASH_PORT${OFF}"
echo "   API docs    http://localhost:$API_PORT/docs"
echo
echo "   ${DIM}Ctrl-C stops both. Logs: /tmp/indus11-api.log /tmp/indus11-dashboard.log${OFF}"
echo

# Stay in the foreground so Ctrl-C reaches the trap above.
wait
