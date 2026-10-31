#!/usr/bin/env python3
"""Read-only export of the customisations that live only in the ERP database.

SIG's operations backbone (SIG Site, SIG Site Cycle, SIG Field Visit, SIG PC Transaction, ...)
and its scripts, workspaces and notifications are defined in the production database, not in
this repository. This script copies their DEFINITIONS (never business records) to JSON files
so they can be reviewed and tested against ERPNext v16.

Safety:
  * Only HTTP GET requests are sent (enforced in get()). Nothing is changed on the site.
  * Credentials come from environment variables and are never written to disk.
  * Values that look like secrets (tokens, passwords, API keys) are replaced with
    "<REDACTED>"; every replacement is listed in _redactions.txt for you to review
    BEFORE sharing or committing the output folder.

Usage (run on your own PC):
  export ERP_URL=https://your-site.frappe.cloud
  export ERP_API_KEY=...        # a read-only user's key
  export ERP_API_SECRET=...
  python3 export_metadata.py --out erp_metadata_export
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# (doctype, filters). Metadata doctypes only.
TARGETS = [
    ("DocType", [["custom", "=", 1]]),
    ("Custom Field", []),
    ("Property Setter", []),
    ("Custom DocPerm", []),
    ("Server Script", []),
    ("Client Script", []),
    ("Workspace", []),
    ("Number Card", []),
    ("Dashboard Chart", []),
    ("Dashboard", []),
    ("Notification", []),
    ("Print Format", [["standard", "=", "No"]]),
    ("Report", [["is_standard", "=", "No"]]),
    ("Page", [["standard", "=", "No"]]),
    ("Role", []),
    ("Role Profile", []),
    ("Module Profile", []),
    ("Workflow", []),
    ("Email Template", []),
    ("Letter Head", []),
]

SECRET_KEY = re.compile(r"(?i)(token|secret|password|passwd|api[_-]?key|authorization|bearer|client_secret|private[_-]?key)")
ASSIGNMENT = re.compile(
    r"""(?ix)(?P<k>["']?[\w.-]*(token|secret|password|passwd|api[_-]?key|authorization|client_secret|private[_-]?key)[\w.-]*["']?)
        \s*(?P<sep>[:=])\s*(?P<q>["'])(?P<v>[^"'\n]{8,})(?P=q)""")
BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")
LONG_TOKEN = re.compile(r"""(?P<q>["'])(?P<v>[A-Za-z0-9_\-]{32,})(?P=q)""")


class Client:
    def __init__(self, url, key, secret):
        self.url = url.rstrip("/")
        self.auth = f"token {key}:{secret}"

    def get(self, path, params=None):
        query = "?" + urllib.parse.urlencode(params) if params else ""
        req = urllib.request.Request(self.url + path + query, method="GET")
        assert req.get_method() == "GET"  # read-only by construction
        req.add_header("Authorization", self.auth)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)


def redact(value, where, found):
    """Recursively replace secret-looking strings; record what was replaced."""
    if isinstance(value, dict):
        return {k: redact(v, f"{where}.{k}", found) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, f"{where}[{i}]", found) for i, v in enumerate(value)]
    if not isinstance(value, str):
        return value

    def sub_assign(m):
        found.append((where, "assignment " + m.group("k").strip("\"'")))
        return f'{m.group("k")}{m.group("sep")} {m.group("q")}<REDACTED>{m.group("q")}'

    def sub_bearer(m):
        found.append((where, "bearer token"))
        return "Bearer <REDACTED>"

    def sub_long(m):
        found.append((where, "long token-like string"))
        return f'{m.group("q")}<REDACTED>{m.group("q")}'

    value = ASSIGNMENT.sub(sub_assign, value)
    value = BEARER.sub(sub_bearer, value)
    if where.rsplit(".", 1)[-1] in ("script", "client_script", "message", "condition", "content", "html", "css", "js", "javascript"):
        value = LONG_TOKEN.sub(sub_long, value)
    return value


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")[:120] or "unnamed"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="erp_metadata_export")
    ap.add_argument("--url", default=os.environ.get("ERP_URL"))
    args = ap.parse_args()
    key, secret = os.environ.get("ERP_API_KEY"), os.environ.get("ERP_API_SECRET")
    if not (args.url and key and secret):
        sys.exit("Set ERP_URL, ERP_API_KEY and ERP_API_SECRET (a read-only user's key).")

    client = Client(args.url, key, secret)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    counts, errors, found = {}, [], []

    for doctype, filters in TARGETS:
        try:
            rows = client.get(f"/api/resource/{urllib.parse.quote(doctype)}", {
                "fields": json.dumps(["name"]), "filters": json.dumps(filters), "limit_page_length": 0,
            })["data"]
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            errors.append({"doctype": doctype, "stage": "list", "error": str(exc)[:200]})
            print(f"  ! {doctype}: list failed ({exc})")
            continue
        folder = os.path.join(out, slug(doctype))
        os.makedirs(folder, exist_ok=True)
        saved = 0
        for row in rows:
            name = row["name"]
            try:
                doc = client.get(f"/api/resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(name, safe='')}")["data"]
            except (urllib.error.URLError, KeyError, ValueError) as exc:
                errors.append({"doctype": doctype, "name": name, "stage": "get", "error": str(exc)[:200]})
                continue
            doc = redact(doc, f"{doctype}:{name}", found)
            with open(os.path.join(folder, slug(name) + ".json"), "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=1, ensure_ascii=False, sort_keys=True)
            saved += 1
        counts[doctype] = {"listed": len(rows), "saved": saved}
        print(f"  {doctype}: {saved}/{len(rows)}")

    try:
        versions = client.get("/api/method/frappe.utils.change_log.get_versions").get("message")
    except (urllib.error.URLError, ValueError) as exc:
        versions = f"unavailable: {exc}"
    manifest = {"site": args.url, "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "versions": versions, "counts": counts, "errors": errors, "redactions": len(found)}
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    with open(os.path.join(out, "_redactions.txt"), "w", encoding="utf-8") as fh:
        fh.write("Review these before sharing the folder. Each entry was replaced with <REDACTED>.\n")
        fh.writelines(f"{where}\t{rule}\n" for where, rule in found)
    print(f"\nWrote {out}\n  {sum(c['saved'] for c in counts.values())} definitions, "
          f"{len(errors)} errors, {len(found)} redactions (see _redactions.txt).")
    print("Open _redactions.txt and skim a few Server Script files before sharing the folder.")


if __name__ == "__main__":
    main()
