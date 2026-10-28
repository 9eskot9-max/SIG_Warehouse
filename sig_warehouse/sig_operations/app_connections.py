"""Per-user Todoist connection. Task synchronization is a separate feature."""
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import frappe
import requests
from frappe import _
from frappe.utils import get_url, now_datetime

API = "https://api.todoist.com"
METHOD = "sig_warehouse.sig_operations.app_connections"


def _user():
    user = frappe.session.user
    if user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        frappe.throw(_("Please sign in to ERP."), frappe.PermissionError)
    if frappe.db.get_value("User", user, "user_type") != "System User":
        frappe.throw(_("This page is available to ERP users."), frappe.PermissionError)
    return user


def _config():
    client_id = frappe.conf.get("todoist_client_id")
    secret = frappe.conf.get("todoist_client_secret")
    return client_id, secret


def _callback_url():
    base = get_url().rstrip("/")
    if urlparse(base).scheme != "https":
        frappe.throw(_("Todoist requires an HTTPS ERP site URL."))
    return base + "/api/method/" + METHOD + ".callback"


def _record(user):
    return frappe.get_doc("SIG App Connection", user) if frappe.db.exists("SIG App Connection", user) else None


def _post_token(payload):
    try:
        response = requests.post(API + "/oauth/access_token", data=payload, timeout=15, allow_redirects=False)
        if response.status_code != 200:
            raise ValueError("token exchange failed")
        data = response.json()
        if not data.get("access_token") or not data.get("refresh_token") or not data.get("expires_in"):
            raise ValueError("incomplete token response")
        return data
    except (requests.RequestException, ValueError, TypeError):
        frappe.throw(_("Todoist authorization could not be completed. Please reconnect."))


def _store_tokens(doc, data):
    doc.access_token = data["access_token"]
    doc.refresh_token = data["refresh_token"]
    doc.expires_at = now_datetime() + timedelta(seconds=max(0, int(data["expires_in"]) - 60))
    doc.save(ignore_permissions=True)


def _access_token(doc):
    if doc.expires_at and now_datetime() < frappe.utils.get_datetime(doc.expires_at):
        return doc.get_password("access_token")
    # Serialize refreshes: Todoist rotates refresh tokens on each successful refresh.
    with frappe.cache().lock("sig_todoist_refresh:" + doc.user, timeout=30):
        doc.reload()
        if doc.expires_at and now_datetime() < frappe.utils.get_datetime(doc.expires_at):
            return doc.get_password("access_token")
        client_id, secret = _config()
        if not client_id or not secret:
            frappe.throw(_("Todoist is not configured."))
        data = _post_token({"client_id": client_id, "client_secret": secret,
                            "grant_type": "refresh_token", "refresh_token": doc.get_password("refresh_token")})
        _store_tokens(doc, data)
        frappe.db.commit()
        return data["access_token"]


def _projects(doc):
    token = _access_token(doc)
    cursor = None
    result = []
    try:
        for _ in range(100):
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            response = requests.get(API + "/api/v1/projects", headers={"Authorization": "Bearer " + token},
                                    params=params, timeout=15, allow_redirects=False)
            if response.status_code != 200:
                raise ValueError("project lookup failed")
            data = response.json()
            result.extend({"id": str(x["id"]), "name": str(x["name"])} for x in data.get("results", []))
            cursor = data.get("next_cursor")
            if not cursor:
                return result
        raise ValueError("too many project pages")
    except (requests.RequestException, ValueError, KeyError, TypeError):
        frappe.throw(_("Unable to load Todoist projects. Please reconnect or try again."))


@frappe.whitelist()
def status():
    user = _user()
    doc = _record(user)
    client_id, secret = _config()
    return {"configured": bool(client_id and secret), "connected": bool(doc),
            "project_name": doc.project_name if doc else None}


@frappe.whitelist(methods=["POST"])
def begin():
    user = _user()
    client_id, secret = _config()
    if not client_id or not secret:
        frappe.throw(_("Todoist is not configured."))
    state = secrets.token_urlsafe(32)
    frappe.cache().set_value("sig_todoist_oauth:" + state, user, expires_in_sec=600)
    return "https://app.todoist.com/oauth/authorize?" + urlencode({
        "client_id": client_id, "scope": "data:read,task:add", "state": state,
        "response_type": "code", "redirect_uri": _callback_url()})


@frappe.whitelist(allow_guest=True, methods=["GET"])
def callback(code=None, state=None, error=None):
    user = _user()
    if not state or len(state) > 128:
        frappe.throw(_("Invalid Todoist authorization request."), frappe.PermissionError)
    key = "sig_todoist_oauth:" + state
    owner = frappe.cache().get_value(key)
    if not owner or not secrets.compare_digest(str(owner), user):
        frappe.throw(_("Todoist authorization expired. Please reconnect."), frappe.PermissionError)
    frappe.cache().delete_value(key)
    if error or not code:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/app-connections"
        return
    client_id, secret = _config()
    if not client_id or not secret:
        frappe.throw(_("Todoist is not configured."))
    data = _post_token({"client_id": client_id, "client_secret": secret,
                        "code": code, "redirect_uri": _callback_url()})
    doc = _record(user) or frappe.get_doc({"doctype": "SIG App Connection", "user": user})
    # Reconnecting may be a different Todoist account; require project selection again.
    doc.project_id = None
    doc.project_name = None
    _store_tokens(doc, data)
    frappe.db.commit()
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/app/app-connections"


@frappe.whitelist()
def projects():
    doc = _record(_user())
    if not doc:
        frappe.throw(_("Connect Todoist first."))
    return _projects(doc)


@frappe.whitelist(methods=["POST"])
def select_project(project_id):
    doc = _record(_user())
    if not doc:
        frappe.throw(_("Connect Todoist first."))
    selected = next ( (p for p in _projects(doc) if p["id"] == str(project_id)), None )
    if not selected:
        frappe.throw(_("That Todoist project is not accessible to this account."))
    doc.project_id = selected["id"]
    doc.project_name = selected["name"]
    doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def disconnect():
    doc = _record(_user())
    if doc:
        doc.delete(ignore_permissions=True)
