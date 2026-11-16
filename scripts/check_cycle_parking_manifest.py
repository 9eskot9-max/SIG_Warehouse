"""Check a proposed legacy parking manifest against a local cycle snapshot.

Both input files must be JSON arrays; this command does not connect to ERP or
modify records. A clean result is conditional on independently established
snapshot completeness and does not itself authorize or perform a migration.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sig_warehouse.sig_warehouse.cycle_parking_manifest import validate_parking_manifest


def load_list(path):
    with open(path, encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
        raise ValueError(f"{path}: expected a JSON array of objects")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("cycles")
    args = parser.parse_args()
    manifest, cycles = load_list(args.manifest), load_list(args.cycles)
    issues = validate_parking_manifest(manifest, cycles)
    print(json.dumps({"manifest_count": len(manifest), "snapshot_count": len(cycles),
                      "issues": issues, "snapshot_completeness_verified": False}, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
