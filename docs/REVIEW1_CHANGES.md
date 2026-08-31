# Review 1 — Changes Implemented

Source: Project Review 1 with industry expert Het Shah (8 August 2026) and Krish's
follow-up Q&A (15 August 2026). This covers the concrete engineering items only —
not the admin/attendance discussion.

## 1. Decision path split — 500ms budget

**Problem raised:** the full pipeline measured 14s end-to-end because the RAG/LLM
call sat inside the decision path. Not viable for a financial approve/review/block
decision that needs to return in seconds.

**Fix — `app/api/routes/transactions.py`:**
- `POST /analyze` now runs only the rule engine and graph analyzer in the blocking
  path (`asyncio.gather`), decides and persists from those two alone, then returns.
- The RAG/LLM call moved into `_finish_rag_layer`, dispatched via FastAPI
  `BackgroundTasks` — it runs *after* the response has already gone back to the
  client, then updates the same MongoDB record (score, decision, explanation)
  once the LLM finishes.
- New field `rag_pending: bool` on `AnalysisResponse`
  (`app/schemas/transaction.py`) and `Transaction`
  (`app/models/transaction.py`) — `True` until the background task lands.
  `GET /transactions/{tx_id}` reflects the final state once it flips to `False`.

The 14-second LLM call no longer gates the response at all.

## 2. Neo4j degrade-on-failure

**Problem raised:** the dashboard has no defined behaviour if Neo4j goes down
mid-session — confirmed at Review 1 as a real, unhandled gap (the graph layer had
no try/except, unlike the RAG layer's documented fallback).

**Fix — `app/services/graph_analyzer.py`:**
- The whole Cypher block is now wrapped in try/except, matching the RAG layer's
  existing fallback pattern. A Neo4j outage now returns
  `LayerScore(score=0, flags=["GRAPH_ANALYZER_ERROR"])` instead of raising
  through `asyncio.gather()` and crashing the whole `/analyze` request.

## 3. LLM explanation validated against triggered flags

**Problem raised:** the written explanation comes straight from the LLM, which can
drift from what the deterministic layers actually flagged — nothing was checking
that the prose agreed with the evidence.

**Fix — `app/services/decision_engine.py`:**
- `make_decision` now checks that the LLM's explanation references at least one
  triggered flag by name (root-matched — e.g. "blacklist" matches
  `BLACKLISTED_ACCOUNT`). If it doesn't, the response falls back to the flag
  summary alone instead of showing a confident paragraph that contradicts the
  evidence. Skipped automatically while `rag_pending=True` — the placeholder text
  isn't meant to match anything yet.

## Tests

Added to `tests/test_fraud.py`:
- `test_graph_analyzer_degrades_on_neo4j_failure`
- `test_explanation_falls_back_when_it_ignores_triggered_flags`
- `test_explanation_kept_when_it_matches_flags`
- `test_pending_rag_explanation_skips_validation`

Full suite: 31 passed (`pytest tests/ -v`).

## Answered analytically (not code — Mongo was down, no live measurement run)

**Which graph pattern produces the most false positives?**
`SHARED_DEVICE` — its threshold (more than 2 accounts on one device) is the
loosest of the four checks and needs no corroborating signal, unlike
`CIRCULAR_FLOW` / `MONEY_MULE_PATTERN`, which require an actual repeated cycle.
Multiple legitimate users sharing one device (family, shared work machine, kiosk)
trip it easily. Matches what was already told to the reviewer at Review 1.

**Why is the score weighted 40 / 30 / 30 (rule / graph / RAG)?**
The rule engine's checks (blacklist, velocity) are near-ground-truth facts, so
it carries full weight and an instant-max path. The graph and RAG layers are
inferential pattern-matches, so each is capped lower to reflect lower certainty.
Structurally, the rule engine alone (max 40) can never reach BLOCK (70) without
graph or RAG corroborating it — a deliberate no-single-signal-blocks design,
except the blacklist case, which lands exactly on the REVIEW boundary.

## Not implemented

The FICO Falcon / Feedzai / Featurespace comparison table for the Literature
Review is a documentation change (SRS), not code — not done here.
