#!/usr/bin/env python3
"""Read-only before/after comparison of the numbers that must not change in an upgrade.

Run `snapshot` against production (v15), then against the v16 trial site that was restored
from a backup taken at the same moment, then `compare` the two files. Only GET requests are
sent. Files contain totals and document names, never document contents.

  export ERP_URL=... ERP_API_KEY=... ERP_API_SECRET=...      # a read-only user's key
  python3 reconcile.py snapshot --company "Your Company" --fiscal-year 2026 --out prod.json
  (point ERP_URL at the trial site)
  python3 reconcile.py snapshot --company "Your Company" --fiscal-year 2026 --out trial.json
  python3 reconcile.py compare prod.json trial.json
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

COUNTED = {  # doctype -> count only submitted (docstatus=1) when True
    "Sales Invoice": True, "Purchase Invoice": True, "Payment Entry": True, "Journal Entry": True,
    "Stock Entry": True, "Purchase Receipt": True, "Delivery Note": True, "Material Request": True,
    "Purchase Order": True, "Asset": True, "Employee": False, "Item": False, "Supplier": False,
    "Customer": False, "Project": False, "GL Entry": False, "Stock Ledger Entry": False,
}
TOLERANCE = 0.01


def get(path, params=None):
    url = os.environ["ERP_URL"].rstrip("/") + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, method="GET")
    assert req.get_method() == "GET"  # read-only by construction
    req.add_header("Authorization", f"token {os.environ['ERP_API_KEY']}:{os.environ['ERP_API_SECRET']}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def rows(doctype, fields, filters=None):
    return get(f"/api/resource/{urllib.parse.quote(doctype)}", {
        "fields": json.dumps(fields), "filters": json.dumps(filters or []), "limit_page_length": 0})["data"]


def snapshot(args):
    snap = {"site": os.environ["ERP_URL"], "company": args.company}
    snap["counts"] = {}
    for doctype, submitted_only in COUNTED.items():
        filters = [["docstatus", "=", 1]] if submitted_only else []
        snap["counts"][doctype] = get("/api/method/frappe.client.get_count",
                                      {"doctype": doctype, "filters": json.dumps(filters)})["message"]
        print(f"  count {doctype}: {snap['counts'][doctype]}")
    snap["stock"] = {f"{r['item_code']}|{r['warehouse']}": [round(r["actual_qty"] or 0, 4), round(r["stock_value"] or 0, 2)]
                     for r in rows("Bin", ["item_code", "warehouse", "actual_qty", "stock_value"])}
    for doctype in ("Sales Invoice", "Purchase Invoice"):
        snap["outstanding " + doctype] = {r["name"]: round(r["outstanding_amount"] or 0, 2) for r in rows(
            doctype, ["name", "outstanding_amount"], [["docstatus", "=", 1], ["outstanding_amount", "!=", 0]])}
    snap["assets"] = {r["name"]: [r["status"], round(r["value_after_depreciation"] or 0, 2)]
                      for r in rows("Asset", ["name", "status", "value_after_depreciation"], [["docstatus", "=", 1]])}
    filters = {"company": args.company, "fiscal_year": args.fiscal_year, "show_zero_values": 0,
               "with_period_closing_entry_for_opening": 1, "with_period_closing_entry_for_current_period": 1,
               "show_unclosed_fy_pl_balances": 1, "include_default_book_entries": 1}
    report = get("/api/method/frappe.desk.query_report.run", {
        "report_name": "Trial Balance", "filters": json.dumps(filters), "ignore_prepared_report": "true"})["message"]
    snap["trial_balance"] = {r["account"]: [round(r.get("closing_debit") or 0, 2), round(r.get("closing_credit") or 0, 2)]
                             for r in report.get("result", []) if isinstance(r, dict) and r.get("account")}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=1, sort_keys=True)
    print(f"Wrote {args.out}")


def flatten(value):
    return value if isinstance(value, list) else [value]


def differs(a, b):
    a, b = flatten(a), flatten(b)
    if len(a) != len(b):
        return True
    return any((abs(x - y) > TOLERANCE) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else x != y
               for x, y in zip(a, b))


def compare(args):
    a, b = (json.load(open(p, encoding="utf-8")) for p in (args.a, args.b))
    bad = 0
    for section in sorted(set(a) | set(b)):
        if section in ("site", "company"):
            continue
        sa, sb = a.get(section, {}), b.get(section, {})
        keys = sorted(set(sa) | set(sb))
        diffs = [(k, sa.get(k, "MISSING"), sb.get(k, "MISSING")) for k in keys if differs(sa.get(k, "MISSING"), sb.get(k, "MISSING"))]
        print(f"{'OK  ' if not diffs else 'DIFF'} {section}: {len(keys)} entries, {len(diffs)} differ")
        for k, x, y in diffs[:25]:
            print(f"       {k}: {x}  ->  {y}")
        bad += len(diffs)
    print("\nRESULT:", "IDENTICAL" if not bad else f"{bad} differences - investigate before cutover")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--company", required=True)
    s.add_argument("--fiscal-year", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=snapshot)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    c.set_defaults(fn=compare)
    args = ap.parse_args()
    if args.cmd == "snapshot" and not all(os.environ.get(k) for k in ("ERP_URL", "ERP_API_KEY", "ERP_API_SECRET")):
        sys.exit("Set ERP_URL, ERP_API_KEY and ERP_API_SECRET (a read-only user's key).")
    args.fn(args)
