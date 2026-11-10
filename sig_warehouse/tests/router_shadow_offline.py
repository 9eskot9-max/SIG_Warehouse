"""Read a JSON snapshot on stdin and print aggregate shadow results only."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "sig_accounting"))
from bank_router.evidence_shadow import build_registry, compare_requests, propose, score

data = json.load(sys.stdin)
registry = build_registry(data["counterparties"], data["identifiers"], data["beneficiaries"])
movements = []
confirmed = []
for row in data["movements"]:
    movements.append({"source": json.loads(row.get("source_json") or "{}")})
    confirmed.append(row.get("counterparty") if row.get("route_source") == "MANUAL" else "")
proposals = [propose(m["source"], registry) for m in movements]
request_matches = compare_requests(movements, data["requests"], registry)
print(json.dumps({"movements": len(movements), "outcomes": dict(Counter(x["status"] for x in proposals)),
                  "finance_confirmed_score": score(proposals, confirmed),
                  "request_candidates": dict(Counter(x["status"] for x in request_matches))}))
