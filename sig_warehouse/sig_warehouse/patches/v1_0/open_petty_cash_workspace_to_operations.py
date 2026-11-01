"""v16: let Operations users see the SIG Petty Cash workspace and give it the two petty-cash pages.

Petty cash is used by people outside Finance. The pages and the SIG PC Transaction doctype already allow
Operations User/Manager, but the workspace (which the rail icon opens) listed only finance roles, so for
them the icon would not appear.
"""
import json

import frappe

WS = "SIG Petty Cash"
ROLES = ("Operations User", "Operations Manager")
PAGES = (("Petty Cash Review", "pc-invoice-review", "pc-p1"), ("Petty Cash Status", "pc-transaction-status", "pc-p2"))


def execute():
    if not frappe.db.exists("Workspace", WS):
        return
    doc = frappe.get_doc("Workspace", WS)
    have = {r.role for r in doc.roles}
    for role in ROLES:
        if role not in have and frappe.db.exists("Role", role):
            doc.append("roles", {"role": role})
    labels = {s.label for s in doc.shortcuts}
    content = json.loads(doc.content or "[]")
    ids = {b.get("id") for b in content}
    for label, page, block_id in PAGES:
        if label not in labels and frappe.db.exists("Page", page):
            doc.append("shortcuts", {"label": label, "type": "Page", "link_to": page})
        if block_id not in ids:
            content.insert(4, {"id": block_id, "type": "shortcut", "data": {"shortcut_name": label, "col": 4}})
    doc.content = json.dumps(content)
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.clear_cache()
