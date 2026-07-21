# Indus11 — Handover

## Pending (blocked on GitHub login)
Local git repo is ready: `main` branch, 1 commit, 104 files, `.env`/`.venv`/`node_modules` excluded.

**To finish the GitHub upload** (needs a logged-in GitHub account — cannot be done by the AI):
```bash
cd /Users/joshiom/Projects/SGP/indus11
gh auth login          # GitHub.com → HTTPS → Login with a web browser
gh repo create indus11 --private --source=. --remote=origin --push
```
Then: repo **Settings → Collaborators** → add both teammates + the internal mentor.

Optional — set real commit author before pushing:
```bash
git config user.name "Your Name" && git config user.email "you@algomau.ca"
git commit --amend --reset-author --no-edit
```

Regular uploads after each task:
```bash
git add -A && git commit -m "<what changed>" && git push
```

## How to run the project
```bash
cd /Users/joshiom/Projects/SGP/indus11
./scripts/run_local.sh                 # DBs + seed + API on :8000
cd dashboard && npm run dev             # dashboard on :5173
```
Dashboard http://localhost:5173 · API docs http://localhost:8000/docs · needs Ollama (`llama3`) for AI layer.

## Deliverables (in ~/Downloads)
- `Indus11_Proposal_v2.docx` — CHARUSAT proposal (black, boxed header, workflow + architecture diagrams)
- `WeeklyReport1_{Joshi,Krish,Drashti}.docx` — week 06–12 Jul (requirements/setup)
- `WeeklyReport2_{Joshi,Krish,Drashti}.docx` — week 13–19 Jul (design/schema)
- `docs/Indus11-Review2.pptx` — Review 2 progress deck (in repo)

## Recent code changes
- Currency switched to **INR ₹** (schema/model/dashboard/rule-engine flags; account avgs ×80).
- Dashboard: click a flagged transaction → detail modal; REVIEW rows get **Approve/Block** override (`PATCH /api/v1/transactions/{tx_id}/decision`).
- Analyze form: optional **Reason/note** field, stored + shown in modal.

## Known gaps
- RAG layer sometimes returns `RAG_PIPELINE_ERROR` (Ollama JSON parse) → RAG 0/30; rules + graph still decide.
- Accuracy (precision/recall) not measured yet.
- University: official docs say CHARUSAT/DEPSTAR; the older `Indus11-Review1.pptx` still says Algoma.
