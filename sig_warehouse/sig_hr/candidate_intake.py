"""HR-controlled candidate intake from the Maytapi WhatsApp Inbox sheet.

Inbound replies are staged on SIG Candidate Intake. No Employee, User, salary
assignment, ledger, reporter map, or transaction is created by the sheet poller.
"""
import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from sig_warehouse.sig_hr.candidate_intake_logic import (
    contains_sensitive_chat_data,
    normalize_phone,
    onboarding_messages,
    parse_emp_data,
    parse_inbox_payload,
)

DOCTYPE = "SIG Candidate Intake"
MESSAGE_DOCTYPE = "SIG Candidate Intake Message"
ALLOWED_ROLES = {"HR Manager", "System Manager"}
OPEN_STATUSES = {"Awaiting Candidate", "Submitted", "HR Review", "Correction Requested"}


def _guard():
    if not ALLOWED_ROLES.intersection(frappe.get_roles()):
        frappe.throw(_("Only HR Manager or System Manager can manage candidate intake."), frappe.PermissionError)


def _mask(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return (digits[:3] + "***" + digits[-2:]) if len(digits) > 5 else "***"


def _phone_collisions(phone, exclude=None, exclude_sender_staging=None):
    key = normalize_phone(phone)
    if not key:
        return ["Invalid phone number"]
    collisions = []
    for row in frappe.get_all("Employee", fields=["name", "employee_name", "cell_number"], limit_page_length=0):
        if normalize_phone(row.cell_number) == key:
            collisions.append("Employee " + row.name + " (" + (row.employee_name or "") + ")")
    # Compare known phone-bearing relations, but never auto-link to a match.
    for doctype, candidate_fields in (
        ("User", ("mobile_no",)),
        ("Contact", ("mobile_no", "phone")),
        ("SIG Field Reporter Map", ("reporter_phone", "phone", "mobile_no", "phone_number", "whatsapp_number")),
        ("SIG PC Sender Staging", ("sender_phone", "phone", "phone_number", "whatsapp_number")),
    ):
        if not frappe.db.exists("DocType", doctype):
            continue
        meta = frappe.get_meta(doctype)
        for fieldname in candidate_fields:
            if not meta.has_field(fieldname):
                continue
            try:
                linked_rows = frappe.get_all(doctype, filters={fieldname: ["is", "set"]}, fields=["name", fieldname], limit_page_length=0)
            except Exception:
                continue
            for linked in linked_rows:
                if doctype == "SIG PC Sender Staging" and linked.name == exclude_sender_staging:
                    continue
                if normalize_phone(linked.get(fieldname)) == key:
                    collisions.append(doctype + " " + linked.name)
    for row in frappe.get_all(DOCTYPE, fields=["name", "candidate_name", "whatsapp_phone", "status"], limit_page_length=0):
        if row.name != exclude and row.status != "Rejected" and normalize_phone(row.whatsapp_phone) == key:
            collisions.append("Candidate case " + row.name)
    return collisions


def _set_duplicate_check(doc):
    collisions = _phone_collisions(doc.whatsapp_phone, doc.name, doc.sender_staging)
    if collisions:
        doc.duplicate_status = "Review Required"
        doc.duplicate_notes = "Phone collision requires HR review: " + "; ".join(collisions[:10])
    else:
        doc.duplicate_status = "Clear"
        doc.duplicate_notes = "No exact active Employee or open Candidate Intake phone match found. Name/identity review is still required."


@frappe.whitelist()
def start_candidate_from_pc_sender(sender_staging):
    """Create a restricted intake linked to an existing unassigned sender row; never send here."""
    _guard()
    if not frappe.db.exists("DocType", "SIG PC Sender Staging"):
        frappe.throw(_("Petty-cash sender staging is unavailable."))
    if not frappe.has_permission("SIG PC Sender Staging", "read"):
        frappe.throw(_("You cannot read petty-cash sender staging."), frappe.PermissionError)
    source = frappe.get_doc("SIG PC Sender Staging", sender_staging)
    source.check_permission("read")
    if source.employee:
        frappe.throw(_("This sender is already linked to an Employee. Review that Employee instead."))
    if source.status != "Staged":
        frappe.throw(_("Only a staged sender can start a candidate intake."))
    if not source.candidate_name or not normalize_phone(source.sender_phone):
        frappe.throw(_("The sender row needs a candidate name and a valid phone."))
    existing = frappe.db.get_value(DOCTYPE, {"sender_staging": source.name}, "name")
    if existing:
        return {"candidate": existing, "already_created": True}
    doc = frappe.get_doc({
        "doctype": DOCTYPE,
        "candidate_name": source.candidate_name,
        "whatsapp_phone": source.sender_phone,
        "sender_staging": source.name,
    })
    doc.insert()
    return {"candidate": doc.name, "already_created": False, "duplicate_status": doc.duplicate_status}


def _audit_send(ref_name, phone, text, attempt_field):
    from sig_whatsapp.maytapi import _audit, _post, _settings, normalize_recipient

    allowed_attempt_fields = {
        "outbound_intro_attempted_at", "outbound_instructions_attempted_at",
        "outbound_template_attempted_at",
    }
    if attempt_field not in allowed_attempt_fields:
        frappe.throw(_("Invalid candidate message step."))
    previous = frappe.db.get_value(DOCTYPE, ref_name, attempt_field)
    now = now_datetime()
    if previous and now - get_datetime(previous) < timedelta(minutes=5):
        return {"accepted": False, "testing_redirect": False, "throttled": True}
    frappe.db.set_value(DOCTYPE, ref_name, attempt_field, now, update_modified=True)

    recipient = normalize_recipient(phone)
    settings = None
    target = recipient
    try:
        settings = _settings()
        target = normalize_recipient(settings.test_phone_number) if settings.test_mode else recipient
        result = _post(settings, {"to_number": target, "type": "text", "message": text})
    except Exception as exc:
        # Return normally so Frappe commits the failure audit instead of rolling it
        # back with an exception response. Never include the outbound message text.
        _audit(DOCTYPE, ref_name, recipient, target, "FAILED", error=str(exc)[:500])
        return {"accepted": False, "testing_redirect": bool(settings and settings.test_mode), "throttled": False}
    status = int(result.get("status", 0))
    if not 200 <= status < 300:
        _audit(DOCTYPE, ref_name, recipient, target, "FAILED", error="Maytapi HTTP " + str(status))
        return {"accepted": False, "testing_redirect": bool(settings.test_mode), "throttled": False}
    try:
        body = frappe.parse_json(result.get("body") or "{}")
        if not isinstance(body, dict) or body.get("success") is False or body.get("status") in ("error", "failed", "failure"):
            raise ValueError("Maytapi rejected the message")
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        message_id = str(body.get("message_id") or body.get("id") or data.get("msgId") or data.get("id") or "")
        if not message_id:
            raise ValueError("Maytapi did not return a message ID")
    except Exception as exc:
        _audit(DOCTYPE, ref_name, recipient, target, "FAILED", error=str(exc)[:500])
        return {"accepted": False, "testing_redirect": bool(settings.test_mode), "throttled": False}
    _audit(DOCTYPE, ref_name, recipient, target, "QUEUED", message_id)
    return {"accepted": True, "testing_redirect": bool(settings.test_mode), "throttled": False}


@frappe.whitelist()
def send_candidate_messages(candidate):
    """Send the neutral confirmation prompt, or the missing post-confirmation messages."""
    _guard()
    doc = frappe.get_doc(DOCTYPE, candidate)
    if not doc.has_permission("write"):
        frappe.throw(_("You cannot update this intake case."), frappe.PermissionError)
    if doc.status not in ("Draft", "Correction Requested", "Awaiting Candidate"):
        frappe.throw(_("Messages can be sent only for a draft or correction case."))
    if not doc.gender or not doc.designation or not doc.department or not doc.proposed_salary or float(doc.proposed_salary or 0) <= 0:
        frappe.throw(_("Enter the HR-assigned gender, designation, department, and positive proposed salary before contacting the candidate."))
    if not doc.salary_period or not doc.salary_currency:
        frappe.throw(_("Set the salary period and currency before contacting the candidate."))
    if doc.duplicate_status != "Clear":
        frappe.throw(_("Phone collision found. Resolve it before sending onboarding details."))
    phone = normalize_phone(doc.whatsapp_phone)
    if doc.consent_to_contact:
        accepted, redirected, throttled = _send_followup_after_confirmation(doc, phone)
        return {"status": doc.status, "sent": "candidate_data_request" if accepted else "failed", "accepted": accepted, "testing_redirect": redirected, "throttled": throttled, "phone": _mask(phone)}
    messages = onboarding_messages(doc.name, doc.candidate_name)
    accepted, redirected = True, False
    if not doc.outbound_intro_sent_at:
        result = _audit_send(doc.name, phone, messages[0], "outbound_intro_attempted_at")
        accepted, redirected = result["accepted"], result["testing_redirect"]
        if accepted:
            doc.db_set("outbound_intro_sent_at", now_datetime(), update_modified=True)
    if not accepted:
        return {"status": doc.status, "sent": "failed", "accepted": False, "testing_redirect": redirected, "throttled": result.get("throttled", False), "phone": _mask(phone)}
    doc.db_set("status", "Awaiting Candidate", update_modified=True)
    return {"status": "Awaiting Candidate", "sent": "confirmation_request", "accepted": True, "testing_redirect": redirected, "phone": _mask(phone)}


def _send_followup_after_confirmation(doc, phone):
    messages = onboarding_messages(doc.name, doc.candidate_name)
    accepted, redirected = True, False
    throttled = False
    for field, attempt_field, text in (
        ("outbound_instructions_sent_at", "outbound_instructions_attempted_at", messages[1]),
        ("outbound_template_sent_at", "outbound_template_attempted_at", messages[2]),
    ):
        if doc.get(field):
            continue
        result = _audit_send(doc.name, phone, text, attempt_field)
        accepted = result["accepted"] and accepted
        redirected = result["testing_redirect"] or redirected
        throttled = throttled or result.get("throttled", False)
        if not result["accepted"]:
            break
        doc.db_set(field, now_datetime(), update_modified=True)
    return accepted, redirected, throttled


def _append_receipt(doc, message_id, received_at, result, category="EMP-DATA"):
    if not message_id or frappe.db.exists(MESSAGE_DOCTYPE, {"message_id": message_id}):
        return False
    try:
        at = get_datetime(received_at)
    except Exception:
        at = now_datetime()
    doc.append("inbound_messages", {
        "message_id": message_id, "received_at": at, "parse_result": result,
        "category": category,
    })
    doc.last_inbound_at = at
    doc.last_inbound_message_id = message_id
    doc.last_parse_result = result
    return True


def _apply_safe_values(doc, values, handoffs):
    case_id = str(values.get("case_id") or "").strip()
    if case_id != doc.name:
        return "CASE_ID_MISMATCH"
    if values.get("legal_name"):
        doc.proposed_legal_name = values["legal_name"][:140]
    if values.get("preferred_name"):
        doc.proposed_preferred_name = values["preferred_name"][:140]
    if values.get("email"):
        email = values["email"].strip().lower()
        if "@" not in email or len(email) > 140:
            return "INVALID_EMAIL"
        doc.proposed_email = email
    if values.get("official_mobile"):
        proposed_phone = normalize_phone(values["official_mobile"])
        if not proposed_phone:
            return "INVALID_OFFICIAL_PHONE"
        doc.proposed_official_phone = proposed_phone
        if proposed_phone != normalize_phone(doc.whatsapp_phone):
            doc.status = "Exception"
            doc.duplicate_status = "Review Required"
            doc.duplicate_notes = "Candidate supplied an official number different from the WhatsApp sender; HR must verify ownership."
    doc.secure_handoff_fields = "\n".join(sorted(set(handoffs)))
    if handoffs:
        doc.last_parse_result = "SECURE_FORM_REQUIRED"
    if doc.status != "Exception":
        doc.status = "HR Review"
    return "STAGED_FOR_HR_REVIEW"


def collect_candidate_replies():
    """Scheduled inbox fetch; idempotently stages only EMP-DATA replies."""
    if not frappe.db.exists("DocType", DOCTYPE) or not frappe.db.exists("DocType", "Maytapi Settings"):
        return {"fetched": 0, "matched": 0, "staged": 0}
    from sig_warehouse.sig_warehouse.field_sessions import _gviz

    # Inbox columns: A ReceivedAt, C Payload, D MsgId, E Conversation, F MsgType.
    rows = _gviz("select A,C,D,E,F where F = 'text' order by A desc limit 2000")
    candidates = frappe.get_all(
        DOCTYPE, filters={"status": ["in", list(OPEN_STATUSES)]},
        fields=["name", "whatsapp_phone"], limit_page_length=0,
    )
    by_phone = {}
    for candidate in candidates:
        key = normalize_phone(candidate.whatsapp_phone)
        if key:
            by_phone.setdefault(key, []).append(candidate.name)
    matched = staged = 0
    for row in reversed(rows):
        if len(row) < 5:
            continue
        inbound = parse_inbox_payload(row[0], row[1], row[2], row[3], row[4])
        if not inbound or not inbound["phone"]:
            continue
        normalized_text = inbound["text"].strip().upper()
        is_confirmation = normalized_text in {"YES", "Y", "1"}
        is_stop = normalized_text in {"STOP", "UNSUBSCRIBE", "NO", "N", "2"}
        parsed = parse_emp_data(inbound["text"])
        if (parsed.get("error") == "NOT_EMP_DATA" and not is_confirmation and not is_stop
                and not contains_sensitive_chat_data(inbound["text"])):
            continue
        targets = by_phone.get(inbound["phone"], [])
        if len(targets) != 1:
            continue
        doc = frappe.get_doc(DOCTYPE, targets[0])
        if doc.status not in OPEN_STATUSES:
            continue
        category = "CONFIRMATION" if is_confirmation else "STOP" if is_stop else "PRIVACY_REVIEW" if parsed.get("error") == "NOT_EMP_DATA" else "EMP-DATA"
        initial_result = "NUMBER_CONFIRMED" if is_confirmation else "CANDIDATE_STOPPED" if is_stop else parsed.get("error") or "PARSED"
        if not _append_receipt(doc, inbound["message_id"], inbound["received_at"], initial_result, category):
            continue
        matched += 1
        if is_stop:
            doc.status = "Rejected"
            doc.last_parse_result = "CANDIDATE_STOPPED"
        elif is_confirmation and not doc.consent_to_contact:
            doc.consent_to_contact = 1
            doc.phone_control_confirmed = 1
            doc.last_parse_result = "NUMBER_CONFIRMED"
            doc.status = "Awaiting Candidate"
            doc.flags.allow_intake_status_transition = True
            doc.flags.allow_intake_system_fields = True
            doc.save(ignore_permissions=True)
            try:
                _send_followup_after_confirmation(doc, inbound["phone"])
            except Exception:
                frappe.log_error(title="SIG Candidate Intake: follow-up send failed", message="Follow-up failed; review the restricted Maytapi send audit.")
            continue
        elif not doc.phone_control_confirmed and parsed.get("ok"):
            doc.status = "Exception"
            doc.last_parse_result = "CONFIRM_PHONE_FIRST"
        elif contains_sensitive_chat_data(inbound["text"]):
            doc.status = "Exception"
            doc.last_parse_result = "PRIVACY_REVIEW_REQUIRED"
        elif not parsed.get("ok"):
            doc.last_parse_result = parsed.get("error") or "INVALID_MESSAGE"
            if doc.status != "Exception":
                doc.status = "Correction Requested"
        else:
            result = _apply_safe_values(doc, parsed["values"], parsed["secure_handoffs"])
            doc.last_parse_result = result
            if result == "STAGED_FOR_HR_REVIEW":
                staged += 1
            else:
                doc.status = "Correction Requested"
        doc.flags.allow_intake_status_transition = True
        doc.flags.allow_intake_system_fields = True
        doc.save(ignore_permissions=True)
    return {"fetched": len(rows), "matched": matched, "staged": staged}


@frappe.whitelist()
def resolve_phone_review(candidate, resolution_note):
    """Let HR close a phone collision with a reason; this never auto-links records."""
    _guard()
    note = str(resolution_note or "").strip()
    if len(note) < 12:
        frappe.throw(_("Enter a review reason of at least 12 characters."))
    doc = frappe.get_doc(DOCTYPE, candidate)
    if not doc.has_permission("write"):
        frappe.throw(_("You cannot update this intake case."), frappe.PermissionError)
    if doc.duplicate_status != "Review Required":
        frappe.throw(_("This case has no phone collision awaiting review."))
    collisions = _phone_collisions(doc.whatsapp_phone, doc.name)
    employee_collisions = [item for item in collisions if item.startswith("Employee ")]
    if employee_collisions:
        frappe.throw(_("An existing Employee still matches this phone. Resolve or reuse that Employee through HR; this intake cannot create a second Employee."))
    doc.duplicate_status = "Clear"
    doc.duplicate_notes = (doc.duplicate_notes or "") + "\nReviewed by {0} at {1}: {2}".format(
        frappe.session.user, now_datetime(), note,
    )
    doc.flags.allow_intake_system_fields = True
    doc.save()
    return {"candidate": doc.name, "duplicate_status": doc.duplicate_status}


@frappe.whitelist()
def approve_candidate(candidate):
    """Record the HR approval decision after a submission and duplicate check."""
    _guard()
    doc = frappe.get_doc(DOCTYPE, candidate)
    if not doc.has_permission("write"):
        frappe.throw(_("You cannot update this intake case."), frappe.PermissionError)
    if doc.status != "HR Review":
        frappe.throw(_("The case must be in HR Review before approval."))
    if not doc.consent_to_contact or not doc.phone_control_confirmed:
        frappe.throw(_("Candidate consent and WhatsApp number confirmation are required."))
    if doc.duplicate_status != "Clear":
        frappe.throw(_("Resolve the duplicate check before approval."))
    if not doc.proposed_legal_name or not doc.proposed_official_phone:
        frappe.throw(_("The candidate's legal name and confirmed official phone are required."))
    if not doc.gender or not doc.designation or not doc.proposed_salary or float(doc.proposed_salary or 0) <= 0:
        frappe.throw(_("HR must enter gender, designation, and a positive proposed salary before approval."))
    if not doc.salary_period or not doc.salary_currency:
        frappe.throw(_("Set the proposed salary period and currency before approval."))
    if not doc.department or not doc.date_of_birth or not doc.date_of_joining:
        frappe.throw(_("Complete the approved Department, verified date of birth, and joining date before approval."))
    doc.status = "Approved"
    doc.flags.allow_intake_status_transition = True
    doc.flags.allow_intake_system_fields = True
    doc.hr_approved_by = frappe.session.user
    doc.hr_approved_at = now_datetime()
    doc.save()
    return {"candidate": doc.name, "status": doc.status}


@frappe.whitelist()
def create_employee_from_candidate(candidate):
    """HR-approved conversion creates only Employee; later onboarding owns access/finance setup."""
    _guard()
    doc = frappe.get_doc(DOCTYPE, candidate)
    if not doc.has_permission("write"):
        frappe.throw(_("You cannot update this intake case."), frappe.PermissionError)
    if doc.employee:
        return {"employee": doc.employee, "already_created": True}
    if doc.status != "Approved":
        frappe.throw(_("HR must set status to Approved after reviewing the candidate submission."))
    if doc.duplicate_status != "Clear" or not doc.consent_to_contact or not doc.phone_control_confirmed:
        frappe.throw(_("Resolve duplicate checks and record consent and phone confirmation first."))
    employee_name = (doc.proposed_legal_name or doc.candidate_name or "").strip()
    phone = normalize_phone(doc.proposed_official_phone or doc.whatsapp_phone)
    missing = []
    for label, value in (("legal name", employee_name), ("date of birth", doc.date_of_birth),
                         ("gender", doc.gender), ("designation", doc.designation),
                         ("joining date", doc.date_of_joining), ("company", doc.company), ("official phone", phone),
                         ("proposed salary", doc.proposed_salary), ("department", doc.department)):
        if not value:
            missing.append(label)
    if missing:
        frappe.throw(_("Complete these HR-reviewed fields first: {0}.").format(", ".join(missing)))
    employee_matches = [
        row.name for row in frappe.get_all("Employee", fields=["name", "cell_number"], limit_page_length=0)
        if normalize_phone(row.cell_number) == phone
    ]
    if employee_matches:
        frappe.throw(_("An existing Employee already has this official phone; resolve or reuse that record before conversion."))
    employee = frappe.get_doc({
        "doctype": "Employee", "employee_name": employee_name, "company": doc.company,
        "date_of_joining": doc.date_of_joining, "date_of_birth": doc.date_of_birth,
        "gender": doc.gender, "designation": doc.designation,
        "cell_number": phone, "status": "Active",
        "department": doc.department,
        "reports_to": doc.reports_to or None,
        "personal_email": doc.proposed_email or None,
        "employment_type": doc.employment_type or None,
    })
    employee.insert()
    assignment_name = None
    if doc.project:
        if not doc.project_role or not doc.assignment_start_date:
            frappe.throw(_("Provide a project role and assignment start date, or clear the Project field."))
        assignment = frappe.get_doc({
            "doctype": "SIG Employee Project Assignment",
            "employee": employee.name,
            "project": doc.project,
            "project_role": doc.project_role,
            "start_date": doc.assignment_start_date,
            "status": "Draft",
            "source": "Project Setup",
        })
        assignment.insert(ignore_permissions=True)
        assignment_name = assignment.name
    doc.employee = employee.name
    doc.project_assignment = assignment_name
    doc.status = "Employee Created"
    doc.flags.allow_intake_status_transition = True
    doc.flags.allow_intake_system_fields = True
    doc.hr_approved_by = frappe.session.user
    doc.hr_approved_at = now_datetime()
    doc.employee_creation_note = "Employee created by HR approval. Verify the existing SIG Employee Onboarding control row. User, Salary Structure Assignment, custody account, mappings, and notifications require their separate onboarding gates."
    doc.save()
    return {"employee": employee.name, "project_assignment": assignment_name, "already_created": False}
