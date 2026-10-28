import frappe
from frappe import _
from frappe.utils import getdate, today

ALLOWED = {"Accounts User", "Accounts Manager", "System Manager"}

def _guard():
    if not ALLOWED.intersection(frappe.get_roles()):
        frappe.throw(_("You do not have access to Client Collections."), frappe.PermissionError)

@frappe.whitelist()
def get_open_invoices(start=0, limit=100):
    """Read-only collection queue, based only on submitted ERP Sales Invoices."""
    _guard()
    start = max(int(start), 0)
    limit = min(max(int(limit), 1), 100)
    rows = frappe.get_list("Sales Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0]},
        fields=["name", "customer", "customer_name", "posting_date", "due_date", "currency", "grand_total", "outstanding_amount", "status"],
        order_by="due_date asc, posting_date asc, name asc", start=start, page_length=limit + 1)
    has_more = len(rows) > limit
    rows = rows[:limit]
    for row in rows:
        due = getdate(row.due_date) if row.due_date else None
        row["age_days"] = (getdate(today()) - due).days if due else None
        row["collection_status"] = "Past Due" if due and due < getdate(today()) else ("Due Date Missing" if not due else "Upcoming")
    return {"rows": rows, "start": start, "limit": limit, "has_more": has_more,
        "has_previous": start > 0}

@frappe.whitelist()
def prepare_whatsapp(invoice_names, send_to, letter_type="Reminder", language="English"):
    """Build a client reminder preview for a manually entered destination number."""
    _guard()
    import json
    names = json.loads(invoice_names) if isinstance(invoice_names, str) else invoice_names
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        frappe.throw(_("Invalid invoice selection."))
    phone = "".join(c for c in str(send_to or "") if c.isdigit())
    if len(phone) < 8 or len(phone) > 15:
        frappe.throw(_("Enter a valid client WhatsApp number with country code."))
    if len(names) != len(set(names)):
        frappe.throw(_("An invoice can only be selected once."))
    if letter_type not in {"Invoice Delivery", "Friendly Reminder", "Overdue Reminder", "Reminder"}:
        frappe.throw(_("Select a valid letter type."))
    if language not in {"English", "Arabic", "Bilingual"}:
        frappe.throw(_("Select a valid letter language."))
    if not names or len(names) > 20:
        frappe.throw(_("Select between 1 and 20 invoices."))
    invoices = []
    customer = None
    for name in names:
        doc = frappe.get_doc("Sales Invoice", name)
        doc.check_permission("read")
        if doc.docstatus != 1 or doc.outstanding_amount <= 0:
            frappe.throw(_("{0} is not a submitted invoice with an outstanding balance.").format(name))
        if customer and customer != doc.customer:
            frappe.throw(_("Select invoices for one customer at a time."))
        if invoices and invoices[0]["currency"] != doc.currency:
            frappe.throw(_("Select invoices in one currency at a time."))
        customer = doc.customer
        invoices.append({"name": doc.name, "posting_date": doc.posting_date, "due_date": doc.due_date,
            "currency": doc.currency, "outstanding_amount": doc.outstanding_amount})
    lines = "\n".join("{0}: {1}".format(x["name"], frappe.utils.fmt_money(x["outstanding_amount"], currency=x["currency"])) for x in invoices)
    overdue = any(x["due_date"] and getdate(x["due_date"]) < getdate(today()) for x in invoices)
    message = (_("Dear Client,\n\nPlease find the invoice copy/copies attached. Our records show the following outstanding invoice balance(s):\n{0}\n\nTotal outstanding: {1}\n\nPlease advise the expected payment date or let us know if any supporting information is required.\n\nRegards,\nSIG Finance")
        .format(lines, frappe.utils.fmt_money(sum(float(x["outstanding_amount"]) for x in invoices), currency=invoices[0]["currency"])))
    return {"customer": customer, "recipient": phone, "letter_type": letter_type,
        "language": language, "invoices": invoices, "total_outstanding": sum(float(x["outstanding_amount"]) for x in invoices),
        "message": message, "overdue": overdue,
        "send_enabled": False, "note": _("Preview only. Sending is not enabled in this local build.")}
