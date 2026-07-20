"""
Layer 4 — RAG Pipeline
Owner: Member C

Uses LangChain + ChromaDB to retrieve relevant fraud patterns and LLM to produce
a risk score (0-30) with natural-language explanation.
"""
import json
import logging
import re

import chromadb
from langchain_openai import ChatOpenAI
from langchain_community.llms.ollama import Ollama
from langchain.prompts import ChatPromptTemplate

from app.config import settings
from app.schemas.transaction import LayerScore, TransactionRequest
from app.schemas.risk import AccountProfile
from app.services.fraud_kb import FRAUD_PATTERNS

logger = logging.getLogger(__name__)

# Annotation quoted: chromadb.PersistentClient is a factory function in 0.5.x,
# so evaluating it in a union at import time raises TypeError.
_chroma_client: "chromadb.api.ClientAPI | None" = None
_collection = None


def _get_collection():
    """Lazy-initialize ChromaDB collection."""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = _chroma_client.get_or_create_collection(
            name="fraud_patterns",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_llm():
    """Return the configured LLM (OpenAI or Ollama)."""
    if settings.llm_provider == "ollama":
        return Ollama(base_url=settings.ollama_base_url, model="llama3")
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
    )


SYSTEM_PROMPT = """You are an expert financial fraud analyst AI.
You will be given:
1. Details of a financial transaction under review.
2. Retrieved fraud pattern documents most similar to this transaction.

Your job is to assess the fraud risk of this transaction using the provided context.

Respond ONLY with a valid JSON object in this exact format:
{{
  "score": <integer 0-30>,
  "explanation": "<2-3 sentence plain-English explanation of the risk assessment>",
  "matched_patterns": ["<pattern1>", "<pattern2>"]
}}

Score guide: 0-9 = low risk, 10-19 = moderate risk, 20-30 = high risk.
"""

# Few-shot examples anchor the score scale and the exact output format —
# without them small models drift into prose or over-score routine payments.
FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (
        "human",
        """Transaction details:
- Amount: 45.20 CAD
- Sender account: ACC-EX1 (avg monthly: 1200.0, risk tier: standard)
- Receiver account: ACC-EX2
- Merchant category: groceries
- Device ID: DEV-EX1
- IP Address: 24.114.80.9

Retrieved fraud patterns (top 3 similar cases):
Pattern 1: Friendly fraud: dispute patterns where a customer regularly initiates chargebacks after transactions with online merchants.

Assess the fraud risk for this transaction.""",
    ),
    (
        "ai",
        '{{"score": 2, "explanation": "A small grocery purchase well within the sender\'s normal monthly spending, from a standard-risk account. Nothing about the amount, merchant, or device suggests fraud.", "matched_patterns": []}}',
    ),
    (
        "human",
        """Transaction details:
- Amount: 9500.0 CAD
- Sender account: ACC-EX3 (avg monthly: 600.0, risk tier: elevated)
- Receiver account: ACC-EX4
- Merchant category: wire_transfer
- Device ID: DEV-EX9
- IP Address: 203.0.113.66

Retrieved fraud patterns (top 3 similar cases):
Pattern 1: Wire fraud: large wire transfers to new recipient accounts in high-risk jurisdictions, often preceded by social engineering.
Pattern 2: Structuring (smurfing): deposits or transfers deliberately kept just below the 10,000 reporting threshold.
Pattern 3: Urgency-driven wire: a customer who has never wired money before suddenly sends an amount several times their monthly average.

Assess the fraud risk for this transaction.""",
    ),
    (
        "ai",
        '{{"score": 24, "explanation": "A wire transfer more than 15x the sender\'s monthly average, kept just under the $10,000 reporting threshold, from an elevated-risk account. This matches wire fraud and structuring patterns strongly.", "matched_patterns": ["wire_fraud", "structuring"]}}',
    ),
]

USER_PROMPT = """Transaction details:
- Amount: {amount} {currency}
- Sender account: {sender_id} (avg monthly: {avg_tx}, risk tier: {risk_tier})
- Receiver account: {receiver_id}
- Merchant category: {merchant_category}
- Device ID: {device_id}
- IP Address: {ip_address}

Retrieved fraud patterns (top 3 similar cases):
{retrieved_patterns}

Assess the fraud risk for this transaction."""


async def run_rag_pipeline(
    tx: TransactionRequest,
    sender: AccountProfile,
) -> LayerScore:
    """
    Retrieve top-k similar fraud patterns from ChromaDB and use an LLM
    to assess fraud risk. Returns a LayerScore (0-30) with explanation.
    """
    try:
        collection = _get_collection()

        # Build query from transaction features
        query_text = (
            f"transaction amount {tx.amount} {tx.currency} "
            f"merchant {tx.merchant_category or 'unknown'} "
            f"risk tier {sender.risk_tier} "
            f"device {tx.device_id or 'unknown'}"
        )

        # Retrieve top 3 similar fraud patterns
        results = collection.query(
            query_texts=[query_text],
            n_results=min(3, collection.count()),
            include=["documents", "metadatas"],
        )

        retrieved = "\n\n".join(
            f"Pattern {i+1}: {doc}"
            for i, doc in enumerate(results["documents"][0])
        ) if results["documents"][0] else "No similar patterns found in knowledge base."

        # Build and invoke chain (few-shot examples between system and query)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            *FEW_SHOT_EXAMPLES,
            ("human", USER_PROMPT),
        ])

        content = await _invoke_with_fallback(prompt, {
            "amount": tx.amount,
            "currency": tx.currency,
            "sender_id": tx.sender_account_id,
            "avg_tx": sender.avg_monthly_transaction,
            "risk_tier": sender.risk_tier,
            "receiver_id": tx.receiver_account_id,
            "merchant_category": tx.merchant_category or "N/A",
            "device_id": tx.device_id or "N/A",
            "ip_address": tx.ip_address or "N/A",
            "retrieved_patterns": retrieved,
        })

        # Parse structured JSON response
        parsed = _parse_llm_json(content)

        return LayerScore(
            score=min(int(parsed.get("score", 0)), 30),
            max_score=30,
            flags=parsed.get("matched_patterns", []),
            # Store explanation on the score for use by Decision Engine
        ), parsed.get("explanation", "No explanation provided.")

    except Exception as e:
        logger.warning(f"RAG pipeline error: {e} — defaulting to score 0")
        return LayerScore(score=0, max_score=30, flags=["RAG_PIPELINE_ERROR"]), str(e)


async def _invoke_with_fallback(prompt: ChatPromptTemplate, inputs: dict) -> str:
    """
    Invoke the configured LLM; if it fails (no API key, quota, network) and the
    primary provider isn't already Ollama, retry once against local Ollama so
    the pipeline keeps working fully offline.
    """
    try:
        response = await (prompt | _get_llm()).ainvoke(inputs)
    except Exception as e:
        if settings.llm_provider == "ollama":
            raise
        logger.warning(f"{settings.llm_provider} LLM failed ({e}) — falling back to Ollama")
        ollama = Ollama(base_url=settings.ollama_base_url, model="llama3")
        response = await (prompt | ollama).ainvoke(inputs)
    return response.content if hasattr(response, "content") else str(response)


def _parse_llm_json(content: str) -> dict:
    """
    Extract the first JSON object from an LLM response. Tolerates markdown
    code fences and surrounding prose, which local models emit routinely.
    """
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {content[:200]!r}")
    return json.loads(match.group(0))


async def seed_knowledge_base() -> None:
    """
    Seed ChromaDB with the fraud pattern knowledge base (see fraud_kb.py).
    Upserts by document id, so new patterns added to the KB flow into existing
    installs on next startup.
    """
    collection = _get_collection()
    if collection.count() >= len(FRAUD_PATTERNS):
        return

    collection.upsert(
        ids=[p["id"] for p in FRAUD_PATTERNS],
        documents=[p["text"] for p in FRAUD_PATTERNS],
        metadatas=[{"type": p["type"]} for p in FRAUD_PATTERNS],
    )
    logger.info(f"Seeded ChromaDB with {len(FRAUD_PATTERNS)} fraud patterns.")
