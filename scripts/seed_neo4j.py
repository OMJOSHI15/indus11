"""
Synthetic fraud dataset generator for Neo4j. Owner: Member B

Builds a realistic transaction graph with fraud patterns embedded in it:
  - 500 accounts (ACC-001 .. ACC-500); ring heads + 2 standalone bad actors
    pre-labeled as fraud (5 seeds)
  - ~1000 transactions total
  - 3 money mule rings (circular flows with fee skimming at each hop)
  - 2 shared-device clusters and 1 shared-IP cluster (synthetic identities)
  - CONNECTED_TO edges between ring members and identity-cluster members,
    so the fraud-cluster proximity check has something to traverse

Deterministic (seeded RNG) so every team member gets the same graph.
Safe to re-run — everything is MERGEd.

Run from the project root (Neo4j must be up):
    python -m scripts.seed_neo4j
"""
import asyncio
import random
from datetime import datetime, timedelta

from app.core.neo4j_client import close_driver, ensure_indexes, neo4j_session

random.seed(42)

NUM_ACCOUNTS = 500
NUM_RANDOM_TX = 940  # rings add ~60 more, totalling ~1000

MERCHANT_CATEGORIES = [
    "groceries", "restaurants", "utilities", "retail", "travel", "fuel",
    "entertainment", "healthcare", "wire_transfer", "crypto_exchange",
]

BASE_TIME = datetime(2026, 6, 1)


def account_id(n: int) -> str:
    return f"ACC-{n:03d}"


def build_dataset():
    accounts = [{"account_id": account_id(i)} for i in range(1, NUM_ACCOUNTS + 1)]

    # ── Fraud rings: circular flows where each hop skims a "mule fee" ─────────
    # Ring members are drawn from high account numbers so they don't collide
    # with the MongoDB demo accounts (ACC-001..020).
    rings = [
        [account_id(n) for n in (451, 452, 453, 454)],
        [account_id(n) for n in (461, 462, 463, 464, 465)],
        [account_id(n) for n in (471, 472, 473)],
    ]
    fraud_seeds = {ring[0] for ring in rings}          # ring "heads" are known fraud
    fraud_seeds |= {account_id(481), account_id(482)}  # plus standalone bad actors

    transactions = []
    tx_counter = 0

    def add_tx(sender, receiver, amount, ts, category):
        nonlocal tx_counter
        tx_counter += 1
        transactions.append({
            "tx_id": f"STX-{tx_counter:05d}",
            "sender": sender,
            "receiver": receiver,
            "amount": round(amount, 2),
            "timestamp": ts.isoformat(),
            "category": category,
        })

    # Each ring cycles funds 4 times, losing 5-12% per hop (classic mule skim)
    for ring in rings:
        for cycle in range(4):
            amount = random.uniform(4000, 9000)
            ts = BASE_TIME + timedelta(days=cycle * 3, hours=random.randint(0, 12))
            for i in range(len(ring)):
                sender = ring[i]
                receiver = ring[(i + 1) % len(ring)]
                add_tx(sender, receiver, amount, ts, "wire_transfer")
                amount *= random.uniform(0.88, 0.95)
                ts += timedelta(minutes=random.randint(10, 90))

    # ── Identity clusters: many accounts on one device / IP ──────────────────
    device_clusters = {
        "DEV-FRAUD-A": [account_id(n) for n in (451, 452, 453, 481, 483, 484)],
        "DEV-FRAUD-B": [account_id(n) for n in (461, 462, 482, 485)],
    }
    ip_clusters = {
        "203.0.113.66": [account_id(n) for n in (451, 461, 471, 481, 482, 486, 487, 488)],
    }

    device_usages = [
        {"account_id": acc, "device_id": dev}
        for dev, members in device_clusters.items()
        for acc in members
    ]
    ip_usages = [
        {"account_id": acc, "ip": ip}
        for ip, members in ip_clusters.items()
        for acc in members
    ]

    # Normal accounts get their own device (a few shared 2-person households)
    for i in range(1, 301):
        device_usages.append({
            "account_id": account_id(i),
            "device_id": f"DEV-{(i + 1) // 2:04d}" if i <= 60 else f"DEV-{i:04d}",
        })

    # ── Background noise: everyday transactions ──────────────────────────────
    for _ in range(NUM_RANDOM_TX):
        sender, receiver = random.sample(range(1, NUM_ACCOUNTS + 1), 2)
        category = random.choice(MERCHANT_CATEGORIES)
        amount = random.lognormvariate(4.5, 1.0)  # most under $300, occasional spikes
        ts = BASE_TIME + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        add_tx(account_id(sender), account_id(receiver), amount, ts, category)

    # ── CONNECTED_TO: explicit association edges for cluster traversal ───────
    connections = []
    for ring in rings:
        for i in range(len(ring)):
            connections.append({"a": ring[i], "b": ring[(i + 1) % len(ring)]})
    for members in list(device_clusters.values()) + list(ip_clusters.values()):
        for i in range(len(members) - 1):
            connections.append({"a": members[i], "b": members[i + 1]})

    return accounts, sorted(fraud_seeds), transactions, device_usages, ip_usages, connections


async def seed() -> None:
    accounts, fraud_seeds, transactions, device_usages, ip_usages, connections = build_dataset()

    await ensure_indexes()
    async with neo4j_session() as session:
        await session.run(
            "UNWIND $accounts AS row MERGE (a:Account {account_id: row.account_id})",
            accounts=accounts,
        )
        await session.run(
            """
            UNWIND $ids AS id
            MATCH (a:Account {account_id: id})
            SET a.risk_label = 'fraud'
            """,
            ids=fraud_seeds,
        )
        # Batch transactions to keep each Cypher call small
        for i in range(0, len(transactions), 200):
            await session.run(
                """
                UNWIND $txs AS row
                MATCH (s:Account {account_id: row.sender})
                MATCH (r:Account {account_id: row.receiver})
                MERGE (t:Transaction {tx_id: row.tx_id})
                SET t.amount = row.amount, t.timestamp = row.timestamp,
                    t.category = row.category
                MERGE (s)-[:SENT {tx_id: row.tx_id, amount: row.amount,
                                  timestamp: row.timestamp}]->(r)
                """,
                txs=transactions[i : i + 200],
            )
        await session.run(
            """
            UNWIND $rows AS row
            MATCH (a:Account {account_id: row.account_id})
            MERGE (d:Device {device_id: row.device_id})
            MERGE (a)-[:USED_DEVICE]->(d)
            """,
            rows=device_usages,
        )
        await session.run(
            """
            UNWIND $rows AS row
            MATCH (a:Account {account_id: row.account_id})
            MERGE (ip:IPAddress {address: row.ip})
            MERGE (a)-[:USED_IP]->(ip)
            """,
            rows=ip_usages,
        )
        await session.run(
            """
            UNWIND $rows AS row
            MATCH (a:Account {account_id: row.a})
            MATCH (b:Account {account_id: row.b})
            MERGE (a)-[:CONNECTED_TO]->(b)
            MERGE (b)-[:CONNECTED_TO]->(a)
            """,
            rows=connections,
        )

        result = await session.run(
            """
            MATCH (a:Account) WITH count(a) AS accounts
            MATCH ()-[s:SENT]->() WITH accounts, count(s) AS sent
            MATCH (f:Account {risk_label: 'fraud'})
            RETURN accounts, sent, count(f) AS fraud
            """
        )
        record = await result.single()

    await close_driver()
    print(
        f"Seeded Neo4j: {record['accounts']} accounts, {record['sent']} transactions, "
        f"{record['fraud']} fraud-labeled seeds, {len(connections)} association edges."
    )


if __name__ == "__main__":
    asyncio.run(seed())
