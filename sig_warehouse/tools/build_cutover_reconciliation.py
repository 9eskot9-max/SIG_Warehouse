"""Create a reproducible WH-versus-ERP stock comparison package.

Usage (after exporting a frozen WH stock CSV with item_code,warehouse,qty):

    python tools/build_cutover_reconciliation.py --wh wh_snapshot.csv \
      --erp erp_snapshot.csv --out reconciliation.json

The ERP file is deliberately a frozen export too.  The script makes no ERP
writes and its output hash is what gets recorded through
``apply_reconciliation_summary`` before a cutover can be accepted.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sig_warehouse.reconciliation import compare, summary  # noqa: E402


REQUIRED = {"item_code", "warehouse", "qty"}


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        names = set(reader.fieldnames or [])
        missing = REQUIRED - names
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")
        return list(reader)


def main():
    parser = argparse.ArgumentParser(description="Build a Stage 4 stock reconciliation package")
    parser.add_argument("--wh", required=True, help="Frozen WH CSV: item_code,warehouse,qty")
    parser.add_argument("--erp", required=True, help="Frozen ERP Bin CSV: item_code,warehouse,qty")
    parser.add_argument("--out", required=True, help="Output JSON package")
    args = parser.parse_args()

    wh_path = Path(args.wh)
    erp_path = Path(args.erp)
    rows = compare(read_csv(wh_path), read_csv(erp_path))
    package = {
        "schema": "sig-warehouse-cutover-reconciliation/v1",
        "wh_snapshot_file": wh_path.name,
        "wh_snapshot_sha256": hashlib.sha256(wh_path.read_bytes()).hexdigest(),
        "erp_snapshot_file": erp_path.name,
        "erp_snapshot_sha256": hashlib.sha256(erp_path.read_bytes()).hexdigest(),
        "summary": summary(rows),
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(package["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
