# Running Indus11

## The short version

```bash
cd ~/Projects/SGP/indus11
./scripts/run_local.sh
```

Wait for `Ready.` (about 30 seconds cold), then open:

| | |
|---|---|
| **Dashboard** | http://localhost:5175 |
| API docs (Swagger) | http://localhost:8000/docs |

`Ctrl-C` stops the API and dashboard. The three databases keep running in the
background on purpose, so the next start is faster.

That is the whole demo path. Everything below is only for when something breaks
or you need to explain a piece of it.

---

## What the one command actually does

Three layers, started in this order because each depends on the one before it.

**1. Databases** (MongoDB, Neo4j, Redis)
Started as Homebrew background services. They stay up between demos.

```bash
brew services list          # check what is running
```

**2. Backend API** (FastAPI, port 8000)
Loads the fraud-pattern knowledge base, connects to all three databases, then
serves the scoring endpoint.

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**3. Dashboard** (React + Vite, port 5175)
The analyst screen. Talks to the API on port 8000.

```bash
npm run dev --prefix dashboard -- --port 5175
```

If you want them in separate terminals (useful when showing the API and the
dashboard side by side), run steps 2 and 3 in their own windows once the
databases are up.

---

## Checking it is actually working

The dashboard shows a status pill in the top right:

- **Live** - connected to the API, showing real data
- **API offline** - backend unreachable, so it fell back to sample data

The sample-data fallback is deliberate: the dashboard stays presentable even if
the backend is down. But if you are demonstrating live scoring, you want
**Live**.

Quick check from a terminal:

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","service":"indus11"}`

---

## When something goes wrong

### The dashboard says "API offline"

The backend did not start. Look at the log:

```bash
tail -30 /tmp/indus11-api.log
```

Most often a database did not come up. Check:

```bash
brew services list | grep -E "mongo|neo4j|redis"
```

### Neo4j says "started" but nothing works

A known Neo4j bug on this machine, which has caused two outages. Neo4j leaves a
stale pidfile behind on shutdown; the operating system reuses that process ID
for something unrelated; Neo4j then believes it is already running and quietly
refuses to boot, while Homebrew still reports the service as started.

`run_local.sh` clears this automatically. To fix it by hand:

```bash
rm -f /opt/homebrew/Cellar/neo4j/*/libexec/run/neo4j.pid
brew services restart neo4j
```

### MongoDB will not start

Two formulas are installed and only `@7.0` works:

```bash
brew services start mongodb-community@7.0
```

The unversioned `mongodb-community` is broken and can be ignored.

### A port is already in use

Something is still running from a previous session:

```bash
lsof -ti:8000 | xargs kill      # API
lsof -ti:5175 | xargs kill      # dashboard
```

### The data looks wrong or empty

Rebuild the seed data (500 accounts, ~1000 transactions, 3 planted mule rings):

```bash
./scripts/run_local.sh --seed
```

---

## Optional: the language model

Written explanations come from a local model through Ollama. Without it the rule
and graph layers still score every transaction and the decision still returns;
only the written explanation is missing.

```bash
ollama serve        # if not already running
ollama list         # should include llama3
```

---

## Running the tests

No databases required. Useful for showing the suite is green.

```bash
.venv/bin/python -m pytest tests/ -v
```
