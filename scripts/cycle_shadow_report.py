"""Compare three local JSON exports. Does not connect to or write to ERP.

Usage: python scripts/cycle_shadow_report.py cycles.json events.json visits.json
The flags assert completeness of the corresponding export for all input cycles;
they do not prove it. Output contains cycle names and must be handled as private.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sig_warehouse.sig_warehouse.cycle_shadow import compare_cycles


def _rows(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"{path}: expected a JSON list of objects")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cycles")
    parser.add_argument("events")
    parser.add_argument("visits")
    parser.add_argument("--events-complete", action="store_true")
    parser.add_argument("--visits-complete", action="store_true")
    args = parser.parse_args(argv)
    cycles, events, visits = (_rows(path) for path in (args.cycles, args.events, args.visits))
    result = {
        "coverage_asserted": {"events": args.events_complete, "visits": args.visits_complete},
        "counts": {"cycles": len(cycles), "events": len(events), "visits": len(visits)},
        "findings": compare_cycles(cycles, events, visits, events_complete=args.events_complete,
                                   visits_complete=args.visits_complete),
        "warning": "Candidate differences only; neither export completeness nor correctness is proven.",
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
