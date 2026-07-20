"""
Indus11 — AI Financial Risk & Fraud Decision Engine
FastAPI application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import accounts, graph, health, stats, transactions
from app.core.database import close_db, init_db
from app.core.neo4j_client import close_driver, ensure_indexes
from app.core.rate_limit import limiter
from app.services.rag_pipeline import seed_knowledge_base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Indus11",
    description="AI Financial Risk & Fraud Decision Engine",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting (slowapi) ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


# ── Startup / shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("Starting Indus11...")
    await init_db()
    logger.info("MongoDB connected (Beanie indexes ready)")
    await ensure_indexes()
    logger.info("Neo4j indexes ready")
    await seed_knowledge_base()
    logger.info("ChromaDB knowledge base ready")
    logger.info("Indus11 is live at http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown():
    await close_driver()
    await close_db()
