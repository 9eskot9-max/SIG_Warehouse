"""Reconcile the approved ERPNext permission compatibility rows after migrations."""

import frappe


DOCTYPE = "Payment Terms Template"
PTYPES = (
    "read", "write", "create", "delete", "submit", "cancel", "amend",
    "report", "export", "import", "print", "email", "share", "select",
)


def _grants(*ptypes):
    return {ptype: int(ptype in ptypes) for ptype in PTYPES}


# Keep ERPNext's named role access introduced in v15.123.0 and the site's
# pre-existing Employee Self Service lookup. Restore the prior All row exactly;
# this row provides the same shared lookup/report actions the site had before
# ERPNext's metadata sync removed it.
APPROVED = {
    "System Manager": _grants("read", "write", "create", "delete", "report", "export", "print", "email", "share"),
    "Accounts User": _grants("read", "write", "create", "delete", "report", "export", "print", "email", "share"),
    "Accounts Manager": _grants("read", "write", "create", "delete", "report", "export", "print", "email", "share"),
    "Employee Self Service": _grants("export", "select"),
    "Maintenance Manager": _grants("read"),
    "Maintenance User": _grants("read"),
    "Purchase Manager": _grants("read"),
    "Purchase User": _grants("read"),
    "Sales Manager": _grants("read"),
    "Sales User": _grants("read"),
    "Sales Master Manager": _grants("select"),
    "Purchase Master Manager": _grants("select"),
    "All": _grants("report", "export", "print", "email", "share", "select"),
}


def reconcile_payment_terms_template_permissions():
    """Preserve the complete reviewed matrix; fail closed on unreviewed drift."""
    rows = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": DOCTYPE},
        fields=["name", "role", "permlevel", "if_owner"] + list(PTYPES),
        order_by="idx asc",
    )

    by_role = {}
    for row in rows:
        if int(row.permlevel or 0) != 0 or int(row.if_owner or 0):
            frappe.throw(
                f"{DOCTYPE} permission reconciliation stopped: nonzero permlevel/owner row needs review."
            )
        if row.role not in APPROVED:
            frappe.throw(
                f"{DOCTYPE} permission reconciliation stopped: unreviewed role {row.role!r}."
            )
        if row.role in by_role:
            frappe.throw(
                f"{DOCTYPE} permission reconciliation stopped: duplicate row for {row.role!r}."
            )
        by_role[row.role] = row

    missing = set(APPROVED) - set(by_role) - {"All"}
    if missing:
        frappe.throw(
            f"{DOCTYPE} permission reconciliation stopped: expected role rows missing: "
            + ", ".join(sorted(missing))
        )

    for role, grants in APPROVED.items():
        row = by_role.get(role)
        if role == "All" and row is None:
            frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": DOCTYPE,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "permlevel": 0,
                "if_owner": 0,
                **grants,
            }).insert(ignore_permissions=True)
            continue

        if row is None:
            continue
        current = {ptype: int(row.get(ptype) or 0) for ptype in PTYPES}
        if current == grants:
            continue
        if role != "All":
            frappe.throw(
                f"{DOCTYPE} permission reconciliation stopped: {role!r} differs from the reviewed matrix."
            )

        doc = frappe.get_doc("Custom DocPerm", row.name)
        for ptype, value in grants.items():
            doc.set(ptype, value)
        doc.save(ignore_permissions=True)

    frappe.clear_cache(doctype=DOCTYPE)

