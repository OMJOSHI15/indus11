# Why the score is weighted 40 / 30 / 30

Asked at Review 1 and not answered at the time. This is the reasoning, written
down so the answer is the same whoever is asked next.

## The split

| Layer | Budget | What it is |
|---|---|---|
| Rule engine | 40 | Blacklist, velocity, amount anomaly, merchant category, risk tier |
| Graph analyzer | 30 | Shared device/IP, circular flows, mule chains, cluster proximity |
| RAG pipeline | 30 | Retrieved fraud patterns assessed by a language model |
| **Composite** | **100** | Mapped to APPROVE (0-39) / REVIEW (40-69) / BLOCK (70+) |

## Why the rule engine carries the most

The three layers differ in how *certain* their evidence is, and the budget
follows that certainty:

- **The rule engine checks facts.** An account either is on the blacklist or
  is not. A sender either exceeded six transactions in ten minutes or did
  not. There is no inference — if the rule fires, the thing it describes is
  true. It gets the largest budget because it is the only layer that can be
  wrong solely because the underlying *data* is wrong.
- **The graph layer infers from structure.** Two accounts sharing a device is
  suspicious, but it is not proof: families share phones, and public
  terminals are shared by strangers. The evidence is real but circumstantial,
  so it is capped lower.
- **The RAG layer infers from similarity.** It retrieves patterns that
  *resemble* the transaction and asks a model to judge. That is the weakest
  form of evidence in the pipeline and the only one that is not reproducible
  from the data alone, so it is capped at the same level as the graph and
  never allowed to decide on its own.

## The property this produces

The rule engine's 40 points sit deliberately below the BLOCK threshold of 70.
That is the point of the split, not a coincidence:

- **No single layer can block a transaction.** Even a maximum-confidence rule
  hit reaches 40, which is REVIEW — a human looks at it. Blocking requires at
  least two independent layers to agree.
- **The blacklist rule lands exactly on the REVIEW boundary** (40), so a
  blacklisted account is always escalated and never silently approved.
- **Graph + RAG together (60) also cannot block**, which is intentional: two
  inferential layers agreeing is not the same as a fact plus an inference.

## Where the numbers came from, honestly

The 40/30/30 split was chosen for the reasoning above, not fitted to data. The
accuracy harness (`scripts/evaluate.py`) sweeps thresholds and reports the
bands that maximise F1 on the synthetic set, and those come out lower than the
configured 40/70 — the synthetic data is far denser in fraud than a real feed,
so its optimum is not one we would adopt. The thresholds stay where the
reasoning puts them, and the sweep is reported alongside as a check rather
than as a target.
