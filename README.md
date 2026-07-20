# Indus11 — AI Financial Risk & Fraud Decision Engine

A real-time fraud detection system combining graph database analysis, RAG-powered LLM decisions, and a multi-factor rule engine.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | Python / FastAPI |
| Graph DB | Neo4j |
| Document DB | MongoDB (Beanie ODM) |
| Cache | Redis |
| LLM / RAG | LangChain + OpenAI (or Ollama) |
| Vector Store | ChromaDB |
| Containers | Docker Compose |

## Quick Start

```bash
# 1. Copy env file and fill in your keys
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Or run locally (requires MongoDB, Neo4j, Redis running)
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 4. Seed test data (MongoDB accounts + Neo4j fraud graph)
python -m scripts.seed_mongo
python -m scripts.seed_neo4j

# 5. Run the dashboard (proxies /api to the FastAPI backend)
cd dashboard && npm install && npm run dev   # http://localhost:5173
```

API docs available at http://localhost:8000/docs

## Database

MongoDB is schemaless, so there is no migration step. The Beanie document models
declare their own indexes (unique `account_id` / `tx_id`, indexed `decision` and
account fields), and `init_db()` creates them automatically on startup.

## Project Structure

```
indus11/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings from .env
│   ├── api/routes/
│   │   ├── transactions.py      # POST /api/v1/transactions/analyze  ← main endpoint
│   │   ├── accounts.py          # Account CRUD
│   │   ├── graph.py             # Graph exploration + fraud label propagation
│   │   ├── stats.py             # Dashboard stats (risk distribution, recent flags)
│   │   └── health.py            # GET /health
│   ├── core/
│   │   ├── database.py          # MongoDB — Motor client + Beanie init
│   │   ├── neo4j_client.py      # Neo4j async driver
│   │   ├── redis_client.py      # Redis cache + sorted-set velocity window
│   │   └── rate_limit.py        # slowapi rate limiter
│   ├── models/                  # Beanie document models
│   ├── schemas/                 # Pydantic request/response schemas (shared contract)
│   └── services/
│       ├── rule_engine.py       # Layer 2 — configurable rule checks (Member A)
│       ├── graph_analyzer.py    # Layer 3 — Neo4j fraud ring detection (Member B)
│       ├── rag_pipeline.py      # Layer 4 — LangChain + ChromaDB + LLM (Member C)
│       ├── fraud_kb.py          # 58-document fraud pattern knowledge base
│       └── decision_engine.py   # Layer 5 — score aggregation (Member C)
├── scripts/
│   ├── seed_mongo.py            # 20 test accounts (all risk scenarios)
│   └── seed_neo4j.py            # Synthetic fraud graph: 500 accounts, ~1000 tx, mule rings
├── dashboard/                   # React dashboard (Vite + Recharts, proxied to the API)
└── tests/
    └── test_fraud.py            # pytest test suite
```

## Team Responsibilities

| Member | Owns |
|--------|------|
| **Member A** | `core/database.py`, `core/redis_client.py`, `models/`, `routes/transactions.py` (persistence), `routes/accounts.py`, Rule Engine, Docker Compose |
| **Member B** | `core/neo4j_client.py`, `services/graph_analyzer.py`, Neo4j schema, synthetic fraud dataset |
| **Member C** | `services/rag_pipeline.py`, `services/decision_engine.py`, ChromaDB seeding, prompt engineering, React dashboard |

## Running Tests

```bash
pytest tests/ -v
```

## Example API Call

```bash
curl -X POST http://localhost:8000/api/v1/transactions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tx_id": "TX-2026-001",
    "sender_account_id": "ACC-001",
    "receiver_account_id": "ACC-002",
    "amount": 9500.00,
    "currency": "CAD",
    "merchant_category": "wire_transfer",
    "device_id": "DEV-XYZ",
    "ip_address": "192.168.1.100"
  }'
```

Example response:
```json
{
  "tx_id": "TX-2026-001",
  "decision": "REVIEW",
  "composite_score": 52,
  "rule_engine": { "score": 20, "max_score": 40, "flags": ["AMOUNT_ANOMALY ($9500 vs avg $500)", "HIGH_RISK_MERCHANT (wire_transfer)"] },
  "graph_analyzer": { "score": 15, "max_score": 30, "flags": ["SHARED_DEVICE (3 accounts on DEV-XYZ)"] },
  "rag_pipeline": { "score": 17, "max_score": 30, "flags": ["wire_fraud", "account_takeover"] },
  "explanation": "Triggered signals: AMOUNT_ANOMALY; HIGH_RISK_MERCHANT; SHARED_DEVICE. This transaction shows characteristics consistent with wire fraud patterns — a large transfer to a new recipient via a high-risk merchant category, using a device shared across multiple accounts.",
  "processing_time_ms": 183.4,
  "timestamp": "2026-06-20T10:00:00Z"
}
```
