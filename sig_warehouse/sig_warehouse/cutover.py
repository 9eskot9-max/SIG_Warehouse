"""Stage 4 cutover controls for the SIG Warehouse app.

This module deliberately records and enforces the ERP side of a warehouse
cutover.  It cannot turn off an Excel macro or prove a physical count; those
are external gates which an authorised operator must attest to in the
cutover document.  A dispatch writer calls :func:`allocate_dn_voucher` only
after the warehouse has an ACTIVE, accepted cutover.
"""
import hashlib
import json
import re

import frappe
from frappe import _
from frappe.utils import cint, now_datetime


COUNTER = "SIG DN Voucher Counter"
ALLOWED_ROLES = ("Stock Manager", "System Manager")


def _require_manager():
    if frappe.session.user == "Guest" or not any(
        role in frappe.get_roles(frappe.session.user) for role in ALLOWED_ROLES
    ):
        frappe.throw(_("Only a Stock Manager or System Manager may operate a warehouse cutover."), frappe.PermissionError)


def _save_with_gate(doc, flag):
    """Permit a narrow server-side state transition, never a client-side one."""
    previous = frappe.flags.get(flag)
    frappe.flags[flag] = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        if previous is None:
            frappe.flags.pop(flag, None)
        else:
            frappe.flags[flag] = previous


def _active_cutover(warehouse):
    row = frappe.db.get_value(
        "SIG Warehouse Cutover",
        {"warehouse": warehouse, "state": "ACTIVE"},
        ["name", "delivery_route_confirmed"],
        as_dict=True,
    )
    if not row:
        frappe.throw(
            _("ERP dispatch is not active for warehouse {0}. Activate its approved cutover first.").format(warehouse),
            frappe.ValidationError,
        )
    return row


def _counter():
    if not frappe.db.exists("SIG DN Voucher Counter", COUNTER):
        frappe.throw(_("SIG DN Voucher Counter has not been initialized."), frappe.ValidationError)
    return frappe.get_doc("SIG DN Voucher Counter", COUNTER)


def _erp_bin_snapshot(warehouse):
    """Return the current non-zero ERP Bin position and its stable hash.

    This is the explicit ERP-only opening path for a warehouse that has no
    legacy WH workbook to reconcile.  The snapshot is taken server-side from
    Bin, so the caller cannot supply or alter the opening quantities.
    """
    rows = frappe.get_all(
        "Bin",
        filters={"warehouse": warehouse},
        fields=["item_code", "warehouse", "actual_qty"],
        limit_page_length=0,
    )
    lines = [
        {
            "item_code": str(row.item_code or ""),
            "warehouse": str(row.warehouse or warehouse),
            "qty": str(row.actual_qty or "0"),
        }
        for row in rows
        if row.item_code and row.actual_qty
    ]
    lines.sort(key=lambda row: (row["item_code"], row["warehouse"]))
    payload = json.dumps(lines, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return lines, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def suggested_next_number():
    """Return a conservative seed from existing ERP mirror source IDs.

    Stock Entry names are ERP ``STE-*`` series, so human DN vouchers are found
    in ``custom_source_id``.  The result is advisory: the cutover owner still
    checks the WH high-water mark before seeding the single ERP counter.
    """
    maximum = 0
    rows = frappe.get_all(
        "Stock Entry",
        filters={"custom_source_id": ["like", "SIG-DN%"]},
        fields=["custom_source_id"],
        limit_page_length=0,
    )
    for row in rows:
        value = str(row.custom_source_id or "")
        match = re.search(r"DN\d{2}-(\d+)", value, re.I)
        if match:
            maximum = max(maximum, cint(match.group(1)))
    return maximum + 1


@frappe.whitelist()
def seed_dn_voucher_counter(next_number, prefix="DN26-", digits=4):
    """Initialize/reseed the one global DN number allocator before cutover.

    Reseeding is blocked once any warehouse has been activated.  This prevents
    a later setup action from moving the sequence backwards while ERP is the
    writer for even one warehouse.
    """
    _require_manager()
    next_number = cint(next_number)
    digits = cint(digits)
    if next_number < 1 or digits < 1 or not re.match(r"^DN\d{2}-$", str(prefix or ""), re.I):
        frappe.throw(_("Use a positive next number, positive width, and a prefix such as DN26-."), frappe.ValidationError)
    if frappe.db.exists("SIG Warehouse Cutover", {"state": "ACTIVE"}):
        frappe.throw(_("Cannot reseed the DN counter while a warehouse cutover is active."), frappe.ValidationError)

    doc = _counter() if frappe.db.exists("SIG DN Voucher Counter", COUNTER) else frappe.get_doc({
        "doctype": "SIG DN Voucher Counter", "name": COUNTER,
    })
    doc.prefix = prefix.upper()
    doc.digits = digits
    doc.next_number = next_number
    doc.seeded_from_erp_next = suggested_next_number()
    doc.seeded_by = frappe.session.user
    doc.seeded_at = now_datetime()
    doc.save(ignore_permissions=True)
    return {"result": "seeded", "next_number": next_number, "erp_suggested_next": doc.seeded_from_erp_next}


def _cutover_ready(doc):
    missing = []
    if doc.state not in ("READY", "ACTIVE"):
        missing.append("state=READY")
    if not doc.reconciliation or frappe.db.get_value("SIG Warehouse Reconciliation", doc.reconciliation, "state") != "ACCEPTED":
        missing.append("accepted reconciliation")
    if not doc.wh_writer_disabled_confirmed:
        missing.append("WH writer disabled confirmation")
    if not doc.delivery_route_confirmed:
        missing.append("ERP delivery route confirmation")
    if not frappe.db.exists("SIG DN Voucher Counter", COUNTER):
        missing.append("seeded DN voucher counter")
    return missing


@frappe.whitelist()
def create_erp_only_reconciliation(warehouse, notes=None):
    """Create a reviewable ERP-only opening baseline for one warehouse.

    This does not silently weaken the original WH-reconciled route.  It is a
    separate, explicit mode for the owner's decision to retire the legacy WH
    writer without using a workbook snapshot.  The server captures the ERP
    Bin position and records a hash; acceptance is still a separate manager
    action through ``accept_reconciliation``.
    """
    _require_manager()
    warehouse = str(warehouse or "").strip()
    if not warehouse or not frappe.db.exists("Warehouse", warehouse):
        frappe.throw(_("A valid ERP Warehouse is required."), frappe.ValidationError)
    if frappe.db.exists("SIG Warehouse Cutover", {"warehouse": warehouse, "state": "ACTIVE"}):
        frappe.throw(_("This warehouse already has an ACTIVE cutover."), frappe.ValidationError)
    if frappe.db.exists("SIG Warehouse Reconciliation", {"warehouse": warehouse, "baseline_mode": "ERP_ONLY", "state": "ACCEPTED"}):
        frappe.throw(_("An accepted ERP-only baseline already exists for this warehouse."), frappe.ValidationError)
    lines, digest = _erp_bin_snapshot(warehouse)
    doc = frappe.get_doc({
        "doctype": "SIG Warehouse Reconciliation",
        "warehouse": warehouse,
        "as_of": now_datetime(),
        "baseline_mode": "ERP_ONLY",
        "state": "REVIEW",
        "erp_snapshot_sha256": digest,
        "erp_line_count": len(lines),
        "wh_line_count": 0,
        "matched_line_count": 0,
        "mismatch_line_count": 0,
        "notes": str(notes or "").strip(),
    })
    if not doc.notes:
        frappe.throw(_("Record the owner-approved ERP-only baseline reason in notes."), frappe.ValidationError)
    doc.insert(ignore_permissions=True)
    return {
        "result": "review",
        "reconciliation": doc.name,
        "baseline_mode": "ERP_ONLY",
        "erp_line_count": len(lines),
        "erp_snapshot_sha256": digest,
        "as_of": doc.as_of,
    }


@frappe.whitelist()
def apply_reconciliation_summary(reconciliation, wh_snapshot_sha256, erp_line_count,
                                 wh_line_count, matched_line_count, mismatch_line_count):
    """Store output from the reproducible offline reconciliation package.

    This deliberately cannot accept a reconciliation.  It only records the
    measured result and moves the document to REVIEW.
    """
    _require_manager()
    doc = frappe.get_doc("SIG Warehouse Reconciliation", reconciliation)
    values = [cint(erp_line_count), cint(wh_line_count), cint(matched_line_count), cint(mismatch_line_count)]
    if any(value < 0 for value in values) or not re.fullmatch(r"[0-9a-fA-F]{64}", str(wh_snapshot_sha256 or "")):
        frappe.throw(_("Reconciliation counts must be non-negative and the WH snapshot hash must be SHA-256."), frappe.ValidationError)
    doc.wh_snapshot_sha256 = wh_snapshot_sha256.lower()
    doc.erp_line_count, doc.wh_line_count, doc.matched_line_count, doc.mismatch_line_count = values
    doc.state = "REVIEW"
    _save_with_gate(doc, "sig_warehouse_reconciliation_transition")
    return {"result": "review", "reconciliation": doc.name, "mismatch_line_count": doc.mismatch_line_count}


@frappe.whitelist()
def accept_reconciliation(reconciliation):
    """Accept a reviewed reconciliation with a documented exception register."""
    _require_manager()
    doc = frappe.get_doc("SIG Warehouse Reconciliation", reconciliation)
    if doc.state != "REVIEW":
        frappe.throw(_("A reconciliation in REVIEW state is required."), frappe.ValidationError)
    if doc.baseline_mode == "ERP_ONLY":
        if not doc.erp_snapshot_sha256 or not doc.erp_line_count or not doc.notes:
            frappe.throw(_("The ERP-only baseline hash, line count and owner reason are required."), frappe.ValidationError)
    elif not doc.wh_snapshot_file or not doc.wh_snapshot_sha256:
        frappe.throw(_("A frozen WH snapshot and reviewed summary are required."), frappe.ValidationError)
    if cint(doc.mismatch_line_count) and not doc.exception_register:
        frappe.throw(_("Mismatches require an accepted exception register before cutover."), frappe.ValidationError)
    doc.state = "ACCEPTED"
    doc.accepted_by = frappe.session.user
    doc.accepted_at = now_datetime()
    _save_with_gate(doc, "sig_warehouse_reconciliation_transition")
    return {"result": "accepted", "reconciliation": doc.name}


@frappe.whitelist()
def attest_cutover_gate(cutover, gate):
    """Record an authorised external gate; it does not perform external actions.

    ``wh_writer_disabled`` means the workbook/mirror writer was disabled and
    archived by its owner. ``delivery_route`` means the ERP sender's recipient
    routing and print format were proved for this warehouse. An explicit
    ``ERP_PRINT_ONLY`` route proves the native ERP print format and deliberately
    does not claim that WhatsApp delivery is enabled.
    """
    _require_manager()
    doc = frappe.get_doc("SIG Warehouse Cutover", cutover)
    if doc.state in ("ACTIVE", "RETIRED"):
        frappe.throw(_("Cutover gates cannot be changed after activation."), frappe.ValidationError)
    if gate == "wh_writer_disabled":
        doc.wh_writer_disabled_confirmed = 1
        doc.wh_writer_disabled_at = now_datetime()
    elif gate == "delivery_route":
        if doc.delivery_route_mode == "ERP_PRINT_ONLY":
            if not frappe.db.exists("Print Format", {"name": "SIG Material Issue"}):
                frappe.throw(_("The SIG Material Issue ERP print format is not installed."), frappe.ValidationError)
        elif not doc.delivery_route_evidence:
            frappe.throw(_("Attach delivery-route proof before attesting this gate."), frappe.ValidationError)
        doc.delivery_route_confirmed = 1
    else:
        frappe.throw(_("Unknown cutover gate."), frappe.ValidationError)
    _save_with_gate(doc, "sig_warehouse_cutover_transition")
    return {"result": "attested", "gate": gate, "cutover": doc.name}


@frappe.whitelist()
def set_erp_print_only_route(cutover):
    """Select the explicit ERP-native print-only delivery route.

    This is intentionally a cutover action rather than a client-side field
    edit.  The route is valid only when the ERP print format is installed and
    the cutover is still DRAFT; activation remains a separate gate.
    """
    _require_manager()
    doc = frappe.get_doc("SIG Warehouse Cutover", cutover)
    if doc.state != "DRAFT":
        frappe.throw(_("The ERP print-only route can only be selected on a DRAFT cutover."), frappe.ValidationError)
    if not frappe.db.exists("Print Format", {"name": "SIG Material Issue"}):
        frappe.throw(_("The SIG Material Issue ERP print format is not installed."), frappe.ValidationError)
    doc.delivery_route_mode = "ERP_PRINT_ONLY"
    _save_with_gate(doc, "sig_warehouse_cutover_transition")
    return {"result": "route_selected", "cutover": doc.name, "delivery_route_mode": doc.delivery_route_mode}


@frappe.whitelist()
def mark_cutover_ready(cutover):
    """Mark a cutover READY after its evidence is complete, before activation."""
    _require_manager()
    doc = frappe.get_doc("SIG Warehouse Cutover", cutover)
    if doc.state != "DRAFT":
        frappe.throw(_("Only a DRAFT cutover can be marked READY."), frappe.ValidationError)
    # Temporarily treat READY as a valid state for the common gate validator.
    doc.state = "READY"
    missing = _cutover_ready(doc)
    if missing:
        doc.state = "DRAFT"
        frappe.throw(_("Cutover is not ready: {0}").format(", ".join(missing)), frappe.ValidationError)
    _save_with_gate(doc, "sig_warehouse_cutover_transition")
    return {"result": "ready", "cutover": doc.name}


@frappe.whitelist()
def activate_cutover(cutover):
    """Make ERP the DN allocator for one warehouse after all Stage 4 gates pass."""
    _require_manager()
    doc = frappe.get_doc("SIG Warehouse Cutover", cutover)
    if not frappe.has_permission("Warehouse", "write", doc=doc.warehouse, user=frappe.session.user):
        frappe.throw(_("Not permitted to activate cutover for this warehouse."), frappe.PermissionError)
    missing = _cutover_ready(doc)
    if missing:
        frappe.throw(_("Cutover cannot activate: {0}").format(", ".join(missing)), frappe.ValidationError)
    doc.state = "ACTIVE"
    doc.activated_by = frappe.session.user
    doc.activated_at = now_datetime()
    _save_with_gate(doc, "sig_warehouse_cutover_transition")
    return {"result": "active", "warehouse": doc.warehouse, "cutover": doc.name}


def allocate_dn_voucher(warehouse):
    """Allocate a DN voucher inside the caller's database transaction.

    The caller must create/submit its Stock Entry in the *same* transaction.
    Gaps after a later validation failure are acceptable; duplicate vouchers
    are not.  ``SELECT ... FOR UPDATE`` serializes all warehouses against the
    one company-wide DN sequence.
    """
    _active_cutover(warehouse)
    frappe.db.sql(
        "SELECT next_number FROM `tabSIG DN Voucher Counter` WHERE name=%s FOR UPDATE",
        COUNTER,
    )
    row = frappe.db.get_value("SIG DN Voucher Counter", COUNTER, ["prefix", "digits", "next_number"], as_dict=True)
    if not row:
        frappe.throw(_("SIG DN Voucher Counter has not been initialized."), frappe.ValidationError)
    number = cint(row.next_number)
    voucher = f"{row.prefix}{number:0{cint(row.digits)}d}"
    frappe.db.set_value("SIG DN Voucher Counter", COUNTER, "next_number", number + 1, update_modified=False)
    return voucher


def delivery_is_authorized(warehouse):
    """Used by the later WhatsApp integration; delivery is never enabled by a draft cutover."""
    return bool(_active_cutover(warehouse).delivery_route_confirmed)
