# Literature Review — comparison with commercial fraud systems

Het Shah asked at Review 1 for a comparison table against the commercial
systems, rather than the paragraph the deck currently carries. This is that
table, plus the honest reading of where Indus11 actually sits.

## Comparison

| | FICO Falcon | Feedzai | Featurespace ARIC | **Indus11** |
|---|---|---|---|---|
| Core method | Supervised neural nets on consortium card data | ML platform with streaming feature engineering | Adaptive Behavioural Analytics, per-entity behavioural models | Rules + graph + retrieval-augmented LLM |
| Graph analysis | Limited, mostly entity linking | Yes, network features | Behavioural rather than graph-first | Native — Neo4j, cycles, shared device/IP, cluster proximity |
| Explanation | Reason codes (fixed vocabulary) | Reason codes + feature attribution | Model-level interpretability | Natural-language, validated against triggered flags |
| Adapts to new fraud | Retraining cycle | Retraining / rule updates | Self-learning on live behaviour | Knowledge base is edited, no retraining |
| Latency | Sub-100 ms, production-hardened | Sub-100 ms | Real-time | 124 ms mean, 189 ms p95 (measured) |
| Training data needed | Large labelled consortium dataset | Large labelled dataset | Large behavioural history | None for the rules and graph; the knowledge base is written, not learned |
| Deployment | Proprietary, licensed | Proprietary, licensed | Proprietary, licensed | Open stack, runs locally |
| Auditability | Score + reason codes | Score + attribution | Score + model reporting | Every layer's score and flags persisted per transaction |

## Where Indus11 genuinely differs

Two things, and only two:

1. **The explanation is generated, not selected from a fixed list.** Commercial
   systems return reason codes an analyst has to interpret. Indus11 returns a
   written explanation — and, since Review 1, one that is checked against the
   flags that actually fired before it is shown, so it cannot confidently
   describe something that did not happen.
2. **New fraud patterns are added by writing them down.** The knowledge base is
   58 text documents. Adding a pattern is an edit, not a retraining cycle.

## Where it does not compete, stated plainly

- **Accuracy is measured on synthetic data.** 52 fraud in 208 transactions is
  far denser than a real payment feed, so the precision figure is optimistic
  and is not comparable to a production benchmark.
- **No consortium data.** The commercial systems' real advantage is seeing card
  fraud across thousands of institutions. Nothing in this architecture
  substitutes for that.
- **Latency is measured on one machine, single user.** 124 ms mean is the
  deterministic path on a laptop, not a throughput figure under production
  load.
- **The language model is the slowest and least reliable component**, which is
  why it was moved out of the decision path entirely rather than optimised.

## References

- Van Vlasselaer et al., "APATE: A novel approach for automated credit card
  transaction fraud detection using network-based extensions," *Decision
  Support Systems*, 2015 — reports AUC above 0.98 combining network and
  intrinsic features, the basis for this project's graph layer.
- FICO, "Falcon Fraud Manager product documentation," 2026.
- Feedzai, "Feedzai Railgun / OpenML platform overview," 2026.
- Featurespace, "ARIC Risk Hub — Adaptive Behavioural Analytics," 2026.
