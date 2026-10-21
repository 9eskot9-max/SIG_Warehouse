"""Point the public /verify Web Page at the app's guest method instead of the old Server Script.

The page was first built on the Server Script API ``sig_verify``. The app now owns the check
(sig_warehouse.sig_verify.api.verify). Idempotent; does nothing when the page is absent or already
repointed. The old Server Script is left in place (disable it after the post-deploy probe).
"""
import frappe

OLD = "/api/method/sig_verify"
NEW = "/api/method/sig_warehouse.sig_verify.api.verify"


def execute():
    name = frappe.db.get_value("Web Page", {"route": "verify"}, "name")
    if not name:
        return
    script = frappe.db.get_value("Web Page", name, "javascript") or ""
    if OLD in script:
        frappe.db.set_value("Web Page", name, "javascript", script.replace(OLD, NEW), update_modified=False)
