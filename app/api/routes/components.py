"""
Status and restart for the three scoring components. Owner: Member A

"Restart" is in-process: it drops the component's client so the next call opens
fresh connections, then checks that the dependency answers. It deliberately does
not start or stop database processes — that would mean running shell commands
from an HTTP request. If the dependency itself is down, the check says so.
"""
import asyncio
import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.core import neo4j_client, redis_client
from app.core.security import require_api_key
from app.services import rag_pipeline

logger = logging.getLogger(__name__)

# Both routes need the key: the status names hosts, and restart changes state.
router = APIRouter(prefix="/components", tags=["components"],
                   dependencies=[Depends(require_api_key)])

PROBE_TIMEOUT_S = 5


async def _check_rules() -> str:
    await redis_client.get_redis().ping()
    return f"Redis at {settings.redis_host}:{settings.redis_port} is answering"


async def _check_graph() -> str:
    async with neo4j_client.neo4j_session() as session:
        await (await session.run("RETURN 1")).single()
    return f"Neo4j at {settings.neo4j_uri} is answering"


async def _check_rag() -> str:
    count = await asyncio.to_thread(lambda: rag_pipeline._get_collection().count())
    if settings.llm_provider != "ollama":
        return f"ChromaDB has {count} patterns; the {settings.llm_provider} API is not checked"
    async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client:
        (await client.get(f"{settings.ollama_base_url}/api/tags")).raise_for_status()
    return f"ChromaDB has {count} patterns; Ollama at {settings.ollama_base_url} is answering"


async def _reset_rag() -> None:
    rag_pipeline.reset_clients()


# name -> (label, what it depends on, reset, check)
COMPONENTS = {
    "rule_engine": ("Rule engine", "Redis", redis_client.reset_redis, _check_rules),
    "graph_analyzer": ("Graph analyzer", "Neo4j", neo4j_client.close_driver, _check_graph),
    "rag_pipeline": ("Language model", "ChromaDB or Ollama", _reset_rag, _check_rag),
}


async def _status(name: str) -> dict:
    label, depends_on, _, check = COMPONENTS[name]
    start = time.perf_counter()
    try:
        detail, ok = await asyncio.wait_for(check(), timeout=PROBE_TIMEOUT_S), True
    except Exception as e:
        reason = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
        reason = " ".join(reason.split())    # driver errors span several lines
        detail, ok = f"{depends_on} is not reachable ({reason})"[:300], False
    return {"name": name, "label": label, "ok": ok, "detail": detail,
            "checked_ms": round((time.perf_counter() - start) * 1000, 1)}


@router.get("/", summary="Status of the three scoring components")
async def component_status():
    return await asyncio.gather(*(_status(name) for name in COMPONENTS))


@router.post("/{name}/restart", summary="Restart one scoring component")
async def restart_component(name: str):
    if name not in COMPONENTS:
        raise HTTPException(status_code=404,
                            detail=f"Unknown component {name!r}; expected one of {', '.join(COMPONENTS)}")
    try:
        await COMPONENTS[name][2]()
    except Exception as e:       # a broken client may fail to close; the fresh one is what matters
        logger.warning(f"Resetting {name} raised {e}; checking it anyway")
    return await _status(name)
