"""
Layer 3 — Neo4j Graph Fraud Analyzer
Owner: Member B

Detects fraud rings and entity relationship anomalies using Cypher graph queries.
Returns a score (0-30) plus detected pattern flags.
"""
from app.core.neo4j_client import neo4j_session
from app.schemas.transaction import LayerScore, TransactionRequest


async def run_graph_analyzer(tx: TransactionRequest) -> LayerScore:
    """
    Query Neo4j for fraud ring patterns involving the transaction's accounts,
    device, and IP address. Returns a LayerScore (0-30).
    """
    score = 0
    flags: list[str] = []

    async with neo4j_session() as session:
        # ── Upsert nodes and relationship ─────────────────────────────────────
        await _upsert_transaction_graph(session, tx)

        # ── Check 1: Shared device across multiple account identities ─────────
        if tx.device_id:
            result = await session.run(
                """
                MATCH (d:Device {device_id: $device_id})<-[:USED_DEVICE]-(a:Account)
                RETURN count(DISTINCT a) AS account_count
                """,
                device_id=tx.device_id,
            )
            record = await result.single()
            if record and record["account_count"] > 2:
                score += 15
                flags.append(
                    f"SHARED_DEVICE ({record['account_count']} accounts on device {tx.device_id})"
                )

        # ── Check 2: Circular money flow (A → B → C → A within 4 hops) ───────
        result = await session.run(
            """
            MATCH path = (a:Account {account_id: $sender})-[:SENT*2..4]->(a)
            RETURN count(path) AS cycle_count
            """,
            sender=tx.sender_account_id,
        )
        record = await result.single()
        if record and record["cycle_count"] > 0:
            score += 12
            flags.append("CIRCULAR_FLOW (cycle detected within 4 hops)")

            # ── Check 2b: Money mule signature — amounts shrink at each hop ───
            # Real mule chains skim a fee per hop, so cycles where every leg
            # passes on 75-100% of the previous amount are far stronger signals
            # than incidental cycles (e.g. friends paying each other back).
            result = await session.run(
                """
                MATCH path = (a:Account {account_id: $sender})-[:SENT*2..4]->(a)
                WITH [r IN relationships(path) | r.amount] AS amounts
                WHERE ALL(i IN range(0, size(amounts) - 2)
                          WHERE amounts[i + 1] <= amounts[i]
                            AND amounts[i + 1] >= amounts[i] * 0.75)
                RETURN count(amounts) AS mule_cycles
                """,
                sender=tx.sender_account_id,
            )
            record = await result.single()
            if record and record["mule_cycles"] > 0:
                score += 8
                flags.append(
                    f"MONEY_MULE_PATTERN ({record['mule_cycles']} fee-skimming cycles)"
                )

        # ── Check 3: Shared IP across multiple accounts ────────────────────────
        if tx.ip_address:
            result = await session.run(
                """
                MATCH (ip:IPAddress {address: $ip})<-[:USED_IP]-(a:Account)
                RETURN count(DISTINCT a) AS ip_count
                """,
                ip=tx.ip_address,
            )
            record = await result.single()
            if record and record["ip_count"] > 3:
                score += 8
                flags.append(
                    f"SHARED_IP ({record['ip_count']} accounts on IP {tx.ip_address})"
                )

        # ── Check 4: Receiver linked to known fraud cluster ───────────────────
        result = await session.run(
            """
            MATCH (a:Account {account_id: $receiver})-[:CONNECTED_TO*1..2]->
                  (f:Account {risk_label: 'fraud'})
            RETURN count(f) AS fraud_neighbors
            """,
            receiver=tx.receiver_account_id,
        )
        record = await result.single()
        if record and record["fraud_neighbors"] > 0:
            score += 10
            flags.append(
                f"FRAUD_CLUSTER_PROXIMITY ({record['fraud_neighbors']} fraud neighbors)"
            )

    return LayerScore(score=min(score, 30), max_score=30, flags=flags)


async def get_account_neighbors(account_id: str, depth: int = 1) -> dict:
    """
    Return the accounts/devices/IPs connected to an account within `depth` hops,
    for the graph API and dashboard visualisation.
    """
    depth = max(1, min(depth, 3))  # interpolated into the pattern, so clamp hard
    async with neo4j_session() as session:
        result = await session.run(
            f"""
            MATCH (a:Account {{account_id: $account_id}})
            OPTIONAL MATCH path = (a)-[*1..{depth}]-(n)
            WHERE n <> a
            UNWIND relationships(path) AS rel
            WITH DISTINCT n, rel
            RETURN
                labels(n)[0] AS label,
                properties(n) AS props,
                type(rel) AS rel_type
            LIMIT 200
            """,
            account_id=account_id,
        )
        neighbors = [
            {"label": r["label"], "properties": r["props"], "via": r["rel_type"]}
            async for r in result
            if r["label"] is not None
        ]
    return {"account_id": account_id, "depth": depth, "neighbors": neighbors}


async def propagate_fraud_labels() -> dict:
    """
    Fraud label propagation:
      1. MERGE CONNECTED_TO edges between accounts sharing a device or IP.
      2. Mark every account within 2 association hops of a known-fraud seed as
         'fraud_adjacent' and record which seed's cluster it belongs to.
    """
    async with neo4j_session() as session:
        # Step 1 — materialise association edges from shared devices/IPs
        result = await session.run(
            """
            MATCH (a:Account)-[:USED_DEVICE|USED_IP]->(x)<-[:USED_DEVICE|USED_IP]-(b:Account)
            WHERE a.account_id < b.account_id
            MERGE (a)-[:CONNECTED_TO]->(b)
            MERGE (b)-[:CONNECTED_TO]->(a)
            RETURN count(DISTINCT [a, b]) AS pairs
            """
        )
        record = await result.single()
        edges_created = record["pairs"] if record else 0

        # Step 2 — propagate from fraud seeds outward
        result = await session.run(
            """
            MATCH (f:Account {risk_label: 'fraud'})
            SET f.fraud_cluster = coalesce(f.fraud_cluster, f.account_id)
            WITH f
            MATCH (f)-[:CONNECTED_TO*1..2]-(n:Account)
            WHERE n.risk_label IS NULL
            SET n.risk_label = 'fraud_adjacent',
                n.fraud_cluster = f.fraud_cluster
            RETURN count(DISTINCT n) AS labeled
            """
        )
        record = await result.single()
        labeled = record["labeled"] if record else 0

    return {"association_pairs": edges_created, "newly_labeled": labeled}


async def _upsert_transaction_graph(session, tx: TransactionRequest) -> None:
    """Merge transaction, account, device, and IP nodes into Neo4j."""
    await session.run(
        """
        MERGE (sender:Account {account_id: $sender})
        MERGE (receiver:Account {account_id: $receiver})
        MERGE (t:Transaction {tx_id: $tx_id})
        SET t.amount = $amount, t.timestamp = $timestamp
        MERGE (sender)-[:SENT {tx_id: $tx_id, amount: $amount}]->(receiver)
        """,
        sender=tx.sender_account_id,
        receiver=tx.receiver_account_id,
        tx_id=tx.tx_id,
        amount=tx.amount,
        timestamp=tx.timestamp.isoformat(),
    )
    if tx.device_id:
        await session.run(
            """
            MERGE (a:Account {account_id: $account_id})
            MERGE (d:Device {device_id: $device_id})
            MERGE (a)-[:USED_DEVICE]->(d)
            """,
            account_id=tx.sender_account_id,
            device_id=tx.device_id,
        )
    if tx.ip_address:
        await session.run(
            """
            MERGE (a:Account {account_id: $account_id})
            MERGE (ip:IPAddress {address: $ip_address})
            MERGE (a)-[:USED_IP]->(ip)
            """,
            account_id=tx.sender_account_id,
            ip_address=tx.ip_address,
        )
