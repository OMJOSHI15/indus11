# Indus11 — Claude Code Handover

## What this project is

Indus11 is a semester group project: an AI-powered financial fraud detection system built with Python/FastAPI. It analyzes financial transactions in real time and returns an APPROVE / REVIEW / BLOCK decision with a natural-language explanation.

## Stack

| Component | Technology |
|-----------|-----------|
| API | Python 3.12 / FastAPI |
| Document DB | MongoDB (via Beanie async ODM) |
| Graph DB | Neo4j (fraud ring detection) |
| Cache | Redis |
| RAG / LLM | LangChain + ChromaDB + OpenAI (or local Ollama) |
| Containers | Docker Compose |
| Tests | pytest + pytest-asyncio |

## Architecture — 5-layer pipeline

Every transaction flows through all layers concurrently via `asyncio.gather()`:

```
Client POST /api/v1/transactions/analyze
        │
        ▼
Layer 1  FastAPI Gateway        → validates schema, loads account profiles (Redis → MongoDB)
        │
        ├──► Layer 2  Rule Engine        → velocity, amount anomaly, blacklist, merchant  (0-40 pts)
        ├──► Layer 3  Neo4j Graph        → shared device, circular flows, fraud clusters  (0-30 pts)
        └──► Layer 4  RAG Pipeline       → ChromaDB retrieval + LLM scoring + explanation (0-30 pts)
        │
        ▼
Layer 5  Decision Engine        → composite score → APPROVE(0-39) / REVIEW(40-69) / BLOCK(70+)
        │
        ▼
        MongoDB persist + response returned
```

## File map

```
app/
  main.py                    # FastAPI app, startup hooks (DB tables, Neo4j indexes, ChromaDB seed)
  config.py                  # Pydantic Settings — reads from .env

  api/routes/
    transactions.py          # POST /analyze, GET /{tx_id}, GET /  ← main endpoint
    accounts.py              # Account CRUD + blacklist toggle
    health.py                # GET /health

  core/
    database.py              # Motor client + Beanie init_db()/close_db()
    neo4j_client.py          # Async Neo4j driver + ensure_indexes()
    redis_client.py          # cache_set/get/delete + increment_velocity()

  models/
    transaction.py           # Beanie Document — transactions collection
    account.py               # Beanie Document — accounts collection

  schemas/
    transaction.py           # TransactionRequest, AnalysisResponse, LayerScore, Decision enum
    risk.py                  # AccountProfile, RiskSummary

  services/
    rule_engine.py           # Layer 2 — Member A owns this
    graph_analyzer.py        # Layer 3 — Member B owns this
    rag_pipeline.py          # Layer 4 — Member C owns this (also seeds ChromaDB on startup)
    decision_engine.py       # Layer 5 — Member C owns this

tests/
  test_fraud.py              # 8 pytest tests for rule engine + decision engine
```

## Team split (3 members)

- **Member A** — FastAPI server, MongoDB schema, Redis caching, Rule Engine, Docker Compose, accounts route
- **Member B** — Neo4j schema, Cypher fraud queries, graph_analyzer.py, synthetic fraud dataset generation
- **Member C** — LangChain RAG pipeline, ChromaDB, prompt engineering, Decision Engine, React dashboard

## What's done (scaffolded)

- [x] Full folder structure
- [x] `requirements.txt` with all dependencies
- [x] `.env.example` with all config keys
- [x] `docker-compose.yml` — MongoDB, Neo4j, Redis, API
- [x] `Dockerfile`
- [x] All 5 service layers implemented (skeleton-level, functional)
- [x] All Pydantic schemas (shared API contract)
- [x] Beanie document models for Transaction and Account
- [x] Redis cache helpers
- [x] Neo4j async driver + index creation
- [x] ChromaDB seeded with 8 fraud pattern documents on startup
- [x] `tests/test_fraud.py` — 8 passing unit tests

## What still needs to be built

### Member A
- [x] MongoDB via Beanie ODM (schemaless — indexes declared on the models are created automatically on startup by `init_db()`; no migration step needed)
- [x] Rate limiting middleware (slowapi — global 120/min, 30/min on /analyze; `app/core/rate_limit.py`)
- [x] Velocity window logic using Redis sorted sets (exact rolling window in `redis_client.increment_velocity`)
- [x] Seed script for test accounts in MongoDB (`scripts/seed_mongo.py` — 20 accounts covering all risk tiers + blacklist)

### Member B
- [x] Synthetic fraud dataset generator (`scripts/seed_neo4j.py`) — 500 accounts, ~1000 transactions, 3 mule rings, shared device/IP clusters, deterministic (seed 42)
- [x] More Cypher fraud patterns (mule detection now also matches fee-skimming cycles — amounts shrinking 75-100% per hop)
- [x] Graph API endpoints (`app/api/routes/graph.py`: GET /api/v1/graph/account/{id}/neighbors, POST /graph/propagate-labels, GET /graph/stats)
- [x] Neo4j fraud label propagation (`graph_analyzer.propagate_fraud_labels` — materialises CONNECTED_TO from shared device/IP, labels 2-hop neighbors `fraud_adjacent` with cluster id)

### Member C
- [x] Expand ChromaDB knowledge base to 50+ fraud pattern documents (58 docs in `app/services/fraud_kb.py`, upserted on startup)
- [x] Improve LLM prompt with few-shot examples (2 worked examples anchoring score scale + JSON format)
- [x] Ollama fallback (automatic: if the OpenAI call fails, the pipeline retries against local Ollama; still needs a live end-to-end test with Ollama running)
- [x] React dashboard (`dashboard/` — Vite + React + Recharts: risk distribution charts, recent flags table, analyze form; `npm run dev`, proxies /api → :8000)
- [x] Dashboard endpoints: GET /api/v1/stats/risk-distribution, GET /api/v1/stats/recent-flags (`app/api/routes/stats.py`)

## Running locally

```bash
# Start all services
docker-compose up -d

# Or bare Python
cp .env.example .env   # fill in keys
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Running tests

```bash
pytest tests/ -v
```

## Key config to know

- `REVIEW_THRESHOLD=40`, `BLOCK_THRESHOLD=70` — change in `.env` to tune sensitivity
- `LLM_PROVIDER=ollama` + `OLLAMA_BASE_URL` to run fully free/local
- ChromaDB persists to `./data/chroma` (Docker volume mounted)
- Redis TTL for account cache: 300 seconds (in `redis_client.py`)
- Velocity window: 10 minutes, limit: 5 transactions (in `rule_engine.py`)

## Example curl

```bash
curl -X POST http://localhost:8000/api/v1/transactions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tx_id": "TX-001",
    "sender_account_id": "ACC-001",
    "receiver_account_id": "ACC-002",
    "amount": 9500.00,
    "currency": "CAD",
    "merchant_category": "wire_transfer",
    "device_id": "DEV-XYZ",
    "ip_address": "10.0.0.1"
  }'
```
