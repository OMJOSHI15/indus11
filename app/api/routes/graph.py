"""Graph exploration routes. Owner: Member B"""
from fastapi import APIRouter, HTTPException, Query

from app.core.neo4j_client import neo4j_session
from app.services.graph_analyzer import get_account_neighbors, propagate_fraud_labels

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/account/{account_id}/neighbors", summary="Explore an account's graph neighborhood")
async def account_neighbors(
    account_id: str,
    depth: int = Query(default=1, ge=1, le=3, description="Traversal depth (1-3 hops)"),
):
    """Accounts, devices, and IPs connected to this account within `depth` hops."""
    async with neo4j_session() as session:
        result = await session.run(
            "MATCH (a:Account {account_id: $id}) RETURN a.account_id AS id",
            id=account_id,
        )
        if not await result.single():
            raise HTTPException(status_code=404, detail=f"Account {account_id} not in graph")
    return await get_account_neighbors(account_id, depth)


@router.post("/propagate-labels", summary="Run fraud label propagation")
async def run_label_propagation():
    """
    Materialise CONNECTED_TO edges from shared devices/IPs, then label accounts
    within 2 hops of a known fraud seed as 'fraud_adjacent' with a cluster id.
    """
    return await propagate_fraud_labels()


@router.get("/stats", summary="Graph node and relationship counts")
async def graph_stats():
    async with neo4j_session() as session:
        result = await session.run(
            """
            OPTIONAL MATCH (a:Account) WITH count(a) AS accounts
            OPTIONAL MATCH (d:Device) WITH accounts, count(d) AS devices
            OPTIONAL MATCH (ip:IPAddress) WITH accounts, devices, count(ip) AS ips
            OPTIONAL MATCH ()-[s:SENT]->() WITH accounts, devices, ips, count(s) AS sent
            OPTIONAL MATCH (f:Account) WHERE f.risk_label = 'fraud'
            WITH accounts, devices, ips, sent, count(f) AS fraud_seeds
            OPTIONAL MATCH (fa:Account) WHERE fa.risk_label = 'fraud_adjacent'
            RETURN accounts, devices, ips, sent, fraud_seeds, count(fa) AS fraud_adjacent
            """
        )
        record = await result.single()
    return dict(record) if record else {}
