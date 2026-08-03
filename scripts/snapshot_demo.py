"""
Capture a static snapshot of the dashboard's data for demo mode.

The deployed dashboard is a static site — it has no backend — so it reads this
snapshot instead of calling the API. Run this against a live local stack whenever
the demo should reflect newer results:

    python -m scripts.snapshot_demo

Requires the API to be running (see scripts/run_local.sh or docker compose up).
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"
OUT = Path(__file__).resolve().parent.parent / "dashboard" / "public" / "demo-data.json"


def fetch(path: str):
    with urllib.request.urlopen(API_BASE + path, timeout=30) as response:
        return json.load(response)


def main() -> int:
    try:
        snapshot = {
            "_note": (
                "Static snapshot of a real local run, read by the dashboard when "
                "VITE_DEMO=1. Regenerate with: python -m scripts.snapshot_demo"
            ),
            "risk_distribution": fetch("/stats/risk-distribution"),
            "accuracy": fetch("/stats/accuracy"),
            "recent_flags": fetch("/stats/recent-flags?limit=20"),
        }
    except urllib.error.URLError as exc:
        print(f"Could not reach the API at {API_BASE} — is the stack running? ({exc})")
        return 1

    # The per-row scores exist so thresholds can be re-swept offline; the dashboard
    # never renders them and they would dominate the file size.
    if isinstance(snapshot["accuracy"], dict):
        snapshot["accuracy"].pop("scored", None)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, default=str))

    distribution = snapshot["risk_distribution"]
    print(f"Wrote {OUT}")
    print(f"  {distribution['total']} transactions  {distribution['decisions']}")
    print(f"  {len(snapshot['recent_flags'])} flagged transactions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
