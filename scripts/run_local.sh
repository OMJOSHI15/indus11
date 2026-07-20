#!/usr/bin/env bash
#
# Bring up the full Indus11 stack locally for a demo / review rehearsal.
# Assumes MongoDB, Redis, Neo4j and (optionally) Ollama are installed via Homebrew.
#
#   ./scripts/run_local.sh          # start DBs, seed, launch API
#   then in another terminal:  cd dashboard && npm run dev
#
set -e
cd "$(dirname "$0")/.."

echo "▶ starting databases (brew services)…"
brew services start mongodb-community >/dev/null 2>&1 || true
brew services start redis             >/dev/null 2>&1 || true
brew services start neo4j             >/dev/null 2>&1 || true

echo "▶ waiting for Neo4j bolt…"
for i in $(seq 1 30); do
  if .venv/bin/python - <<'PY' >/dev/null 2>&1
import asyncio
from app.core.neo4j_client import neo4j_session, close_driver
async def m():
    async with neo4j_session() as s:
        await (await s.run("RETURN 1")).single()
    await close_driver()
asyncio.run(m())
PY
  then echo "  neo4j ready"; break; fi
  sleep 2
done

echo "▶ seeding MongoDB accounts + Neo4j fraud graph…"
.venv/bin/python -m scripts.seed_mongo
.venv/bin/python -m scripts.seed_neo4j

echo "▶ starting API on http://localhost:8000  (docs at /docs)…"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
