# Week 8 — measured results and fixes

Everything here was blocked before this week on "once the stack is running
end to end again". The stack is running, so these are measurements rather
than estimates.

## 1. The decision-path split works — 113x faster

`scripts/benchmark_latency.py`, 29 requests after a warm-up:

| | Review 1 | Now |
|---|---|---|
| Mean | 14,046 ms | **124 ms** |
| Median | — | 114 ms |
| p95 | — | 189 ms |
| Max | — | 287 ms |
| Within the 500 ms budget | no | **29/29** |

The language model no longer sits in the decision path. It scores in the
background and updates the stored record; the dashboard now shows a
"scoring…" state on the RAG row until it lands, then fills in the final score
and explanation without a refresh.

## 2. Which graph pattern produces the most false positives

This was asked directly at Review 1 and answered "shared device". **That
answer was wrong.** Measured with `scripts/false_positives.py`, replaying the
208-transaction labelled set through the graph layer:

| Pattern | Fired on fraud | Fired on legit | False-positive rate |
|---|---|---|---|
| CIRCULAR_FLOW | 27 | 22 | **44.9%** |
| SHARED_DEVICE | 10 | 0 | 0.0% |
| SHARED_IP | 15 | 0 | 0.0% |
| MONEY_MULE_PATTERN | 26 | 0 | 0.0% |
| FRAUD_CLUSTER_PROXIMITY | 36 | 0 | 0.0% |

Shared-device detection produced **no** false positives. Circular-flow
produced almost all of them.

### Why, and the fix

The cycle query had no time constraint, so it matched any path that
eventually returned to the sender across the graph's entire history. On the
seeded graph, 1,486 transactions produced **51,146 cycles**. Any legitimate
account that both sent and received money over three months eventually forms
one.

This turned out to be the *same* root cause as the mentor's other question
about Neo4j retention at a million transactions — unbounded graph
accumulation, showing up as a false-positive problem before it ever shows up
as a storage problem.

The fix constrains a cycle to a laundering-shaped window: all hops within 72
hours of the transaction, in chronological order.

| | FP rate | Graph layer latency |
|---|---|---|
| Original (no window) | 44.9% | 260 ms on a ring member |
| Windowed, first attempt | 0.0% | 1,800 ms — blew the budget |
| Windowed + existence check | **10.3%** | **~20 ms** |

The first windowed version was correct but counted every matching path. The
decision only needs to know whether a cycle *exists*, so it now stops at the
first hit and prunes by an ISO-8601 string cutoff during expansion instead of
parsing dates per path. Net: false positives down 4.4x, graph layer 13x
faster than it was before any of this.

## 3. Identical transactions now score identically

Het Shah asked whether submitting the same transaction twice gives the same
score. The honest answer at the time was "2 to 5 points apart". Measured, it
was worse — the same wire transfer scored **26, 20, 20, 21, 22**.

The cause was a one-line omission: the OpenAI client was created with
`temperature=0`, the local Ollama client was not, so it ran at Ollama's
default of roughly 0.8. At that temperature the model also sometimes echoed a
few-shot example verbatim — one live transaction came back scored as "a small
grocery purchase" when it was a ₹9,500 wire transfer.

Both clients now come from one helper with `temperature=0`. Re-measured:
**20, 20, 20, 20, 20** — spread of zero.

## 4. The explanation guard had a hole

The check added after Review 1 — that the written explanation must reference
a flag that actually fired — passed that grocery explanation. The flag was
`HIGH_RISK_MERCHANT`, and the explanation contained the word "risk" (in
"standard-risk account"), which was enough to match.

The guard now ignores generic risk vocabulary and matches on the flag's
detail as well as its code, so `HIGH_RISK_MERCHANT (wire_transfer)` is
satisfied by an explanation that says "wire transfer" and not by one that
merely says "risk".

## 5. Two robustness bugs found by running it properly

- **Unbounded background work.** Replaying 208 transactions queued 208
  concurrent language-model calls and killed the API process. Background RAG
  work is now capped by a semaphore.
- **A failed background task left records stuck.** Nothing awaits the task,
  so an exception left `rag_pending` true forever. It now clears the flag and
  keeps the deterministic decision.
- **The evaluation harness was silently measuring the wrong thing.** After
  the split it scored the immediate response, which is missing the RAG
  layer's 30 points — reporting recall 0.462 against 0.865 for the same
  pipeline, purely as an artefact. It now waits for the background layer.

## Still open

- The full accuracy re-run against the fixed pipeline is queued behind ~40
  minutes of local language-model calls; the harness fix is in, the number is
  not yet reported here.
- No BLOCK decisions are produced on the synthetic set, which remains the
  known scoring-mechanism limitation already recorded in the specification.
