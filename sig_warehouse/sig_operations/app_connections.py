"""Per-user Todoist connection and one-way ERP task delivery."""
import hashlib
import html
import re
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import frappe
import requests
from frappe import _
from frappe.utils import get_url, now_datetime

API = "https://api.todoist.com"
METHOD = "sig_warehouse.sig_operations.app_connections"
TODOIST_OWNER = "9eskot9@gmail.com"
SNB_CATEGORIES = {"erp_import_failed", "erp_import_skipped"}


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


def _plain_task_text(value, limit=500):
    """Turn ERP task HTML into bounded plain text before leaving ERP."""
    value = re.sub(r"<!--.*?-->", " ", str(value or ""), flags=re.S)
    value = re.sub(r"<[^>]*>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _safe_todoist_content(value):
    text = _plain_task_text(value, 500)
    text = re.sub(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", "[bank identifier removed]", text, flags=re.I)
    text = re.sub(r"\b(?:password|passcode|token|secret|api key)\s*[:=]?\s*\S+", "[credential removed]", text, flags=re.I)
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[email removed]", text, flags=re.I)
    text = re.sub(r"(?<!\d)\+?\d{9,15}(?!\d)", "[phone or account number removed]", text)
    return text[:500]


def _stable_uuid(source_key, namespace):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, namespace + ":" + source_key))


def _outbox(source_key):
    name = frappe.db.get_value("SIG Todoist Outbox", {"source_key": source_key}, "name")
    return frappe.get_doc("SIG Todoist Outbox", name) if name else None


def _queue_delivery(doc):
    if doc.delivery_status in ("Delivered", "Sending"):
        return
    doc.delivery_status = "Pending"
    doc.next_attempt_at = None
    doc.save(ignore_permissions=True)
    frappe.enqueue(
        METHOD + ".deliver_outbox",
        queue="short",
        enqueue_after_commit=True,
        outbox_name=doc.name,
    )


def _new_outbox(source_key, source_type, source_name, content, description=""):
    existing = _outbox(source_key)
    if existing:
        return existing, False
    doc = frappe.get_doc({
        "doctype": "SIG Todoist Outbox",
        "source_key": source_key,
        "source_type": source_type,
        "source_name": source_name,
        "recipient": TODOIST_OWNER,
        "task_content": _plain_task_text(content, 500) or "ERP task",
        "task_description": _plain_task_text(description, 1500),
        "delivery_status": "Pending",
        "request_id": _stable_uuid(source_key, "sig-todoist-request"),
    })
    doc.insert(ignore_permissions=True)
    return doc, True


def on_todo_after_insert(doc, method=None):
    """Queue newly-created ERP ToDos assigned to the connected account owner."""
    if doc.get("allocated_to") != TODOIST_OWNER or doc.get("status") == "Closed":
        return
    # SNB intake pre-creates the idempotent issue outbox before inserting its ToDo.
    source_key = frappe.flags.get("sig_todoist_source_key")
    if source_key:
        outbox = _outbox(source_key)
        if outbox:
            outbox.source_type = "SNB import issue"
            outbox.source_name = doc.name
            outbox.task_description = _plain_task_text(
                (outbox.task_description or "") + " ERP ToDo: " + doc.name,
                1500,
            )
            _queue_delivery(outbox)
        return
    if doc.get("reference_type") == "SIG Todoist Outbox":
        return
    content = _safe_todoist_content(doc.get("description")) or "ERP task " + str(doc.name)
    description = "ERP ToDo: " + str(doc.name) + "\n" + get_url("/app/todo/" + str(doc.name))
    outbox, _created = _new_outbox("todo:" + str(doc.name), "ERP ToDo", doc.name, content, description)
    _queue_delivery(outbox)


def on_todo_after_update(doc, method=None):
    """Also catch a task assigned to 9eskot9 after its initial insertion."""
    if doc.get("allocated_to") != TODOIST_OWNER or doc.get("status") == "Closed":
        return
    if _outbox("todo:" + str(doc.name)):
        return
    on_todo_after_insert(doc, method)


@frappe.whitelist(methods=["POST"])
def record_snb_issue(run_id=None, category=None, count=None):
    """Accept only sanitized SNB import issue categories from 9eskot9's ERP API user."""
    user = _user()
    if user != TODOIST_OWNER:
        frappe.throw(_("Only the configured SNB integration owner can submit these issues."), frappe.PermissionError)
    run_id = str(run_id or "")
    category = str(category or "")
    if not re.fullmatch(r"RUN-[A-Za-z0-9T._:-]{1,80}", run_id) or category not in SNB_CATEGORIES:
        frappe.throw(_("Invalid SNB issue event."), frappe.ValidationError)
    try:
        skipped = int(count) if count not in (None, "") else 0
    except (TypeError, ValueError):
        frappe.throw(_("Invalid SNB issue count."), frappe.ValidationError)
    if skipped < 0 or skipped > 100000:
        frappe.throw(_("Invalid SNB issue count."), frappe.ValidationError)

    source_key = "snb:" + run_id + ":" + category
    with frappe.cache().lock("sig_todoist_source:" + hashlib.sha256(source_key.encode()).hexdigest(), timeout=30):
        outbox = _outbox(source_key)
        created = not outbox
        if not outbox:
            if category == "erp_import_failed":
                title = "SNB to ERP import failed"
                detail = "Review the SNB import run in the local SNB run report. No bank or beneficiary details were sent."
            else:
                title = "SNB rows need ERP review"
                detail = "{} SNB row(s) were skipped for review. Check the SNB import run in the local run report.".format(skipped)
            outbox, _ = _new_outbox(source_key, "SNB import issue", run_id, title + " — " + run_id, detail)
            todo = frappe.get_doc({
                "doctype": "ToDo",
                "allocated_to": user,
                "status": "Open",
                "priority": "High",
                "description": title + " — " + run_id + "<br>" + detail,
                "reference_type": "SIG Todoist Outbox",
                "reference_name": outbox.name,
            })
            frappe.flags.sig_todoist_source_key = source_key
            try:
                todo.insert(ignore_permissions=True)
            finally:
                frappe.flags.sig_todoist_source_key = None
            outbox.source_name = todo.name
            outbox.task_description = detail + "\nERP ToDo: " + todo.name + "\n" + get_url("/app/todo/" + todo.name)
            _queue_delivery(outbox)
    return {"queued": True, "duplicate": not created}


def _mark_outbox(doc, status, error=None, next_attempt_at=None, http_status=None, task_id=None):
    doc.delivery_status = status
    doc.last_error = (str(error or "")[:500] or None)
    doc.last_http_status = http_status
    doc.next_attempt_at = next_attempt_at
    if task_id:
        doc.todoist_task_id = str(task_id)
    doc.save(ignore_permissions=True)
    frappe.db.commit()


def _find_task_by_marker(token, project_id, marker):
    cursor = None
    for _ in range(20):
        params = {"project_id": project_id, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        try:
            response = requests.get(API + "/api/v1/tasks", headers={"Authorization": "Bearer " + token},
                                    params=params, timeout=15, allow_redirects=False)
            if response.status_code != 200:
                return None
            data = response.json()
        except (requests.RequestException, ValueError, TypeError):
            return None
        for task in data.get("results", []):
            if marker in str(task.get("description") or ""):
                return task.get("id")
        cursor = data.get("next_cursor")
        if not cursor:
            return None
    return None


def _deliver_one(doc):
    user_connection = _record(doc.recipient)
    if not user_connection or not user_connection.project_id:
        _mark_outbox(doc, "Waiting", "Connect Todoist and choose a project in App Connections.",
                     now_datetime() + timedelta(minutes=15))
        return
    try:
        token = _access_token(user_connection)
    except Exception:
        _mark_outbox(doc, "Retry", "Todoist token refresh failed.", now_datetime() + timedelta(minutes=10))
        return
    marker = "ERP source key: " + doc.source_key
    description = (doc.task_description or "").strip()
    description = (description + "\n" if description else "") + marker
    payload = {"content": doc.task_content, "description": description, "project_id": user_connection.project_id}
    try:
        response = requests.post(API + "/api/v1/tasks", json=payload,
                                 headers={"Authorization": "Bearer " + token,
                                          "X-Request-ID": doc.request_id},
                                 timeout=20, allow_redirects=False)
    except (requests.Timeout, requests.ConnectionError):
        # A timeout may occur after Todoist created the task. Reconcile by the
        # stable source marker before any retry so an uncertain write is never duplicated.
        found = _find_task_by_marker(token, user_connection.project_id, marker)
        if found:
            _mark_outbox(doc, "Delivered", None, task_id=found)
        else:
            _mark_outbox(doc, "Unknown", "Todoist did not confirm the write. Search the ERP source key before retrying.")
        return
    except requests.RequestException as exc:
        _mark_outbox(doc, "Retry", type(exc).__name__, now_datetime() + timedelta(minutes=10))
        return

    if response.status_code in (200, 201):
        try:
            task_id = response.json().get("id")
        except (ValueError, AttributeError):
            task_id = None
        if task_id:
            _mark_outbox(doc, "Delivered", None, http_status=response.status_code, task_id=task_id)
        else:
            _mark_outbox(doc, "Unknown", "Todoist accepted a response without a task ID; reconcile before retrying.",
                         http_status=response.status_code)
    elif response.status_code == 429:
        try:
            delay = max(30, min(int(response.headers.get("Retry-After", "300")), 3600))
        except ValueError:
            delay = 300
        _mark_outbox(doc, "Retry", "Todoist rate limited the task request.",
                     now_datetime() + timedelta(seconds=delay), response.status_code)
    elif response.status_code >= 500:
        _mark_outbox(doc, "Unknown", "Todoist returned a server error; reconcile before retrying.",
                     http_status=response.status_code)
    else:
        message = "Todoist rejected the task request. Reconnect if authorization was revoked."
        _mark_outbox(doc, "Blocked", message, http_status=response.status_code)


def deliver_outbox(outbox_name):
    """Background worker. Unknown outcomes are held for review, never blindly replayed."""
    with frappe.cache().lock("sig_todoist_outbox:" + str(outbox_name), timeout=60):
        doc = frappe.get_doc("SIG Todoist Outbox", outbox_name)
        if doc.delivery_status in ("Delivered", "Blocked", "Unknown", "Sending"):
            return
        if doc.next_attempt_at and frappe.utils.get_datetime(doc.next_attempt_at) > now_datetime():
            return
        doc.delivery_status = "Sending"
        doc.attempt_count = int(doc.attempt_count or 0) + 1
        doc.last_attempt_at = now_datetime()
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        _deliver_one(doc)


def dispatch_pending():
    """Scheduler retry for known transient errors and unconnected users."""
    now = now_datetime()
    rows = frappe.get_all("SIG Todoist Outbox", filters={"delivery_status": ["in", ["Pending", "Retry", "Waiting"]]},
                          fields=["name", "next_attempt_at"], limit_page_length=200)
    for row in rows:
        if not row.next_attempt_at or frappe.utils.get_datetime(row.next_attempt_at) <= now:
            frappe.enqueue(METHOD + ".deliver_outbox", queue="short", outbox_name=row.name)


@frappe.whitelist()
def status():
    user = _user()
    doc = _record(user)
    client_id, secret = _config()
    deliveries = frappe.get_all(
        "SIG Todoist Outbox",
        filters={"recipient": user},
        fields=["source_type", "source_name", "task_content", "delivery_status", "last_error", "modified"],
        order_by="modified desc",
        limit_page_length=20,
    )
    return {"configured": bool(client_id and secret), "connected": bool(doc),
            "project_name": doc.project_name if doc else None, "deliveries": deliveries}


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
