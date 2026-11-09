"""TAWAL invoice evidence with distinct, retry-safe Site Cycle reservations."""

import frappe
from sig_warehouse.sig_warehouse.tawal_cycle_plan import plan_site_cycles


def _clean(value):
    return str(value or "").strip()


def _site_key(site_id):
    return "".join(ch for ch in site_id.upper() if ch.isalnum() or ch in "-_")


def _make_cycle(site_id, site_key, po, project_family, erp_project, occurred):
    base = site_key + "|" + (po or "NA") + "|" + str(occurred)[:10].replace("-", "")
    name = base
    for suffix in range(2, 100):
        if not frappe.db.exists("SIG Site Cycle", name):
            break
        name = base + "-" + str(suffix)
    else:
        frappe.throw("Could not allocate a unique TAWAL Site Cycle key for " + site_id)
    count = frappe.db.count("SIG Site Cycle", {"site_key": site_key}) + 1
    scope_id = "TWO-" + site_key + "-" + str(count)
    for offset in range(100):
        if not frappe.db.exists("SIG Site Cycle", {"site_key": site_key, "scope_id": scope_id}):
            break
        scope_id = "TWO-" + site_key + "-" + str(count + offset + 1)
    else:
        frappe.throw("Could not allocate a unique TAWAL temporary scope for " + site_id)
    doc = frappe.get_doc({
        "doctype": "SIG Site Cycle", "cycle_key": name,
        "site_key": site_key, "site_id": site_id, "project": project_family,
        "erp_project": erp_project, "po": po, "wo": "", "wo_source": "",
        "stage": "1 - Initial", "scope_id": scope_id,
        "is_temporary": 1, "resolution_state": "OPEN_TEMP",
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _resolve_family(project):
    fields = frappe.db.get_value("Project", project,
                                ["custom_family", "custom_project_family"], as_dict=True)
    if not fields:
        return ""
    old, new = _clean(fields.custom_family), _clean(fields.custom_project_family)
    return "" if old and new and old.lower() != new.lower() else (new or old)


def _set_message(result, detail, **extra):
    frappe.response["message"] = {"result": result, "detail": detail, **extra}
    return frappe.response["message"]


@frappe.whitelist()
def register_tawal_invoice_evidence():
    """Preserve the existing route and invoice-read authorization contract."""
    invoice_no = _clean(frappe.form_dict.get("invoice_no"))
    phase = _clean(frappe.form_dict.get("phase")).upper()
    if phase not in ("DRAFT", "SUBMITTED"):
        return _set_message("error", "phase must be DRAFT or SUBMITTED.")
    if not invoice_no or not frappe.db.exists("Sales Invoice", invoice_no):
        return _set_message("error", "Sales Invoice was not found.")
    if not frappe.get_list("Sales Invoice", filters={"name": invoice_no},
                           fields=["name"], limit_page_length=1):
        return _set_message("error", "Read permission on this Sales Invoice is required.")

    invoice = frappe.get_doc("Sales Invoice", invoice_no)
    if invoice.customer != "Telecommunications Towers Company / Tawal" or int(invoice.custom_tawal_test or 0):
        return _set_message("error", "Only production Tawal invoices can create cycle evidence.")
    if phase == "DRAFT" and int(invoice.docstatus) != 0:
        return _set_message("error", "Draft evidence requires a draft Sales Invoice.")
    if phase == "SUBMITTED" and int(invoice.docstatus) != 1:
        return _set_message("error", "Submission evidence requires a submitted Sales Invoice.")
    ba = _clean(invoice.custom_tawal_ba)
    project = _clean(invoice.project)
    if not ba or not project or not invoice.items:
        return _set_message("error", "Invoice BA, ERP Project, and invoice lines are required.")
    if _clean(frappe.db.get_value("Project", project, "custom_tawal_ba")) != ba:
        return _set_message("error", "Invoice BA no longer matches its ERP Project BA mapping.")

    # The generic evidence API commits each accepted row internally. A Redis
    # lock therefore protects the full allocation/bridge/event sequence across
    # those commits, including concurrent draft and submit readbacks.
    lock = frappe.cache().lock("sig:tawal-invoice-cycle-allocation", timeout=900, blocking_timeout=60)
    if not lock.acquire(blocking=True):
        return _set_message("partial", "Invoice evidence allocation is busy; safely retry after a minute.")
    try:
        return _register_locked(invoice, invoice_no, phase, ba, project)
    finally:
        lock.release()


def _register_locked(invoice, invoice_no, phase, ba, project):
    safe_invoice = "".join(ch for ch in invoice_no.upper() if ch.isalnum() or ch in "-_")
    phase_marker = "D" if phase == "DRAFT" else "S"
    batch_id = "TAWAL-" + safe_invoice + "-" + phase_marker
    occurred = str(invoice.creation if phase == "DRAFT" else frappe.utils.now())[:19]
    operator = frappe.session.user
    project_family = _resolve_family(project)
    groups = {}
    unresolved = []
    bridge_by_key = {}
    sites_created = 0
    seen_keys = set()

    for line in invoice.items:
        source_key = _clean(line.custom_source_row_key)
        site_link = _clean(line.custom_site)
        requisition = _clean(line.custom_requisition)
        sub_po = _clean(line.custom_site_po)
        if not source_key or not site_link or not requisition or not sub_po:
            unresolved.append("line " + str(line.idx) + ": source key, site, requisition, or sub-PO is missing")
            continue
        if source_key in seen_keys:
            unresolved.append(source_key + ": duplicate source row key in invoice lines")
            continue
        seen_keys.add(source_key)
        site_id = _clean(frappe.db.get_value("SIG Site", site_link, "site_id")) or site_link
        site_key = _site_key(site_id)
        if not site_key:
            unresolved.append("line " + str(line.idx) + ": Site ID is invalid")
            continue
        site_doc = frappe.db.get_value("SIG Site", {"site_id": site_id}, "name")
        if not site_doc and frappe.db.exists("SIG Site", site_id):
            site_doc = site_id
        if not site_doc:
            doc = frappe.get_doc({"doctype": "SIG Site", "site_id": site_id, "site_name": site_id})
            doc.insert(ignore_permissions=True)
            site_doc = doc.name
            sites_created += 1

        matches = frappe.get_all("SIG Tawal Invoice Link", filters={"source_row_key": source_key},
            fields=["name", "source_invoice_no", "sales_invoice", "site_id_source", "cycle",
                    "po", "sub_po", "requisition", "defer_cycle_closure"], limit_page_length=2)
        if len(matches) > 1:
            unresolved.append(site_id + " / " + source_key + ": source row key is duplicated in the invoice bridge")
            continue
        bridge = matches[0] if matches else None
        if bridge and (bridge.source_invoice_no != invoice_no or bridge.sales_invoice != invoice_no
            or _clean(bridge.site_id_source).upper() != site_id.upper()
            or _clean(bridge.po) != ba or _clean(bridge.sub_po) != sub_po
            or _clean(bridge.requisition) != requisition):
            unresolved.append(site_id + " / " + source_key + ": existing bridge identity conflicts with this invoice row")
            continue
        group = groups.setdefault((site_id, site_key), {"rows": [], "bridges": {}, "deferred": False})
        group["rows"].append({"line": line, "source_key": source_key, "site_id": site_id,
                              "site_key": site_key, "site_doc": site_doc,
                              "requisition": requisition, "sub_po": sub_po})
        if bridge:
            group["bridges"][source_key] = bridge
            group["deferred"] = group["deferred"] or bool(int(bridge.defer_cycle_closure or 0))
        bridge_by_key[source_key] = bridge

    allocated = {}
    cycles_created = 0
    deferred_sites = set()
    for (site_id, site_key), group in groups.items():
        all_cycles = frappe.get_all("SIG Site Cycle",
            filters={"site_key": site_key, "po": ba, "erp_project": ["in", [project, ""]], "terminal": 0},
            fields=["name", "wo", "po", "erp_project"], order_by="creation asc, name asc", limit_page_length=0)
        if not all_cycles:
            all_cycles = frappe.get_all("SIG Site Cycle",
                filters={"site_id": site_id, "po": ba, "erp_project": ["in", [project, ""]], "terminal": 0},
                fields=["name", "wo", "po", "erp_project"], order_by="creation asc, name asc", limit_page_length=0)
        existing = {}
        cycle_names = [c.name for c in all_cycles]
        row_keys = {r["source_key"] for r in group["rows"]}
        if cycle_names:
            other_reservations = frappe.get_all("SIG Tawal Invoice Link",
                filters={"cycle": ["in", cycle_names]},
                fields=["cycle", "source_row_key", "sales_invoice"], limit_page_length=0)
            blocked = {link.cycle for link in other_reservations
                       if link.source_row_key not in row_keys or link.sales_invoice != invoice.name}
            cycle_names = [name for name in cycle_names if name not in blocked]
        invalid = False
        for row in group["rows"]:
            bridge = group["bridges"].get(row["source_key"])
            if not bridge or not bridge.cycle:
                continue
            cycle = frappe.db.get_value("SIG Site Cycle", bridge.cycle,
                ["name", "site_key", "site_id", "po", "terminal", "erp_project"], as_dict=True)
            if not cycle:
                unresolved.append(site_id + " / " + row["source_key"] + ": bridge cycle no longer exists")
                invalid = True
                continue
            if cycle.terminal or (cycle.site_key != site_key and cycle.site_id != site_id) or (cycle.po and cycle.po != ba):
                unresolved.append(site_id + " / " + row["source_key"] + ": existing bridge points to a closed or mismatched historical cycle; review required")
                invalid = True
                continue
            if cycle.erp_project and cycle.erp_project != project:
                unresolved.append(site_id + " / " + row["source_key"] + ": bridge ERP Project differs from invoice; review required")
                invalid = True
                continue
            existing[row["source_key"]] = cycle.name
            if cycle.name not in cycle_names:
                cycle_names.append(cycle.name)
        if invalid:
            continue
        if len(set(existing.values())) != len(existing):
            unresolved.append(site_id + ": multiple invoice rows already reserve the same cycle; historical bridge review required")
            continue
        try:
            plan = plan_site_cycles([r["source_key"] for r in group["rows"]], cycle_names,
                                    existing, shortage_deferred=group["deferred"])
        except ValueError as error:
            unresolved.append(site_id + ": cycle reservation needs review: " + str(error))
            continue
        defer_close = plan.defer_closure
        if defer_close:
            deferred_sites.add(site_id)
        planned = dict(plan.assignments)
        for row in group["rows"]:
            source_key = row["source_key"]
            cycle_name = planned[source_key]
            if cycle_name is None:
                cycle_name = _make_cycle(site_id, site_key, ba, project_family, project, occurred)
                cycles_created += 1
            allocated[source_key] = (cycle_name, defer_close, row)
            if cycle_name not in cycle_names:
                cycle_names.append(cycle_name)

    events_created = events_duplicate = links_written = 0
    for line in invoice.items:
        source_key = _clean(line.custom_source_row_key)
        item = allocated.get(source_key)
        if not item:
            continue
        cycle_name, defer_close, row = item
        site_id, site_key = row["site_id"], row["site_key"]
        bridge = bridge_by_key.get(source_key)
        cycle_doc = frappe.get_doc("SIG Site Cycle", cycle_name)
        if not cycle_doc.site:
            cycle_doc.site = row["site_doc"]
        if not cycle_doc.project_ref:
            cycle_doc.project_ref = project
        if not cycle_doc.erp_project:
            cycle_doc.erp_project = project
        cycle_doc.save(ignore_permissions=True)
        if bridge:
            values = {"cycle": cycle_name, "wo": cycle_doc.wo or cycle_name,
                      "defer_cycle_closure": int(defer_close)}
            if not bridge.cycle or _clean(bridge.cycle) != cycle_name or bool(bridge.defer_cycle_closure) != defer_close:
                frappe.db.set_value("SIG Tawal Invoice Link", bridge.name, values, update_modified=False)
                links_written += 1
        else:
            frappe.get_doc({
                "doctype": "SIG Tawal Invoice Link", "source_row_key": source_key,
                "source_row": int(line.idx or 0), "source_invoice_no": invoice_no,
                "invoice_date": invoice.posting_date, "sales_invoice": invoice_no,
                "site": row["site_doc"], "site_id_source": site_id,
                "wo": cycle_doc.wo or cycle_name, "cycle": cycle_name, "po": ba,
                "sub_po": row["sub_po"], "requisition": row["requisition"],
                "source_workbook": "SIG Tawal Invoicing.xlsm / ERP!Table11 (invoice child sequence; absolute Excel row unavailable)",
                "backfill_only": 0, "defer_cycle_closure": int(defer_close),
            }).insert(ignore_permissions=True)
            links_written += 1

        artifact_ref = ("Sales Invoice " + invoice_no + " | Row Key " + source_key
                        + " | Requisition " + row["requisition"] + " | Site Sub-PO " + row["sub_po"])[:140]
        payload = {
            "event_code": "INVOICE_GENERATED", "site_id": site_id, "site_key": site_key,
            "occurred_at": occurred, "recorded_at": frappe.utils.now(),
            "project": project_family, "po": ba, "wo": _clean(cycle_doc.wo),
            "cycle_hint": cycle_name, "cycle_hint_mode": "EXACT_BA_SITE",
            "gross_value": str(line.amount or 0), "artifact_ref": artifact_ref,
            "batch_id": batch_id, "seq": str(int(line.idx or 0)),
            "source_sub": "TAWAL_DRAFT_READBACK" if phase == "DRAFT" else "TAWAL_SUBMISSION_READBACK",
            "source_workbook": "SIG Tawal Invoicing.xlsm / ERP!Table11",
            "operator": operator, "machine": "neosys", "core_version": "EvidenceCore EV1 / Tawal-2",
        }
        old_form = frappe.form_dict.copy()
        frappe.form_dict.clear()
        frappe.form_dict.update(payload)
        frappe.response.pop("message", None)
        try:
            frappe.get_doc("Server Script", "register_evidence_event").execute_method()
            evidence_result = frappe.response.get("message") or {}
        finally:
            frappe.form_dict.clear()
            frappe.form_dict.update(old_form)
        if evidence_result.get("result") not in ("created", "duplicate"):
            unresolved.append(site_id + " / " + source_key + ": EV1 intake failed: " + str(evidence_result))
            continue
        if _clean(evidence_result.get("cycle")) != cycle_name:
            unresolved.append(site_id + " / " + source_key + ": EV1 intake returned a cycle different from its reservation")
            continue
        if evidence_result.get("result") == "created":
            events_created += 1
        else:
            events_duplicate += 1

    frappe.db.commit()
    result = "partial" if unresolved else ("created" if events_created or links_written or cycles_created else "duplicate")
    detail = "phase=" + phase + "; per-row events created=" + str(events_created)
    detail += ", duplicate=" + str(events_duplicate) + "; links written=" + str(links_written)
    detail += "; new cycles=" + str(cycles_created) + "; closed=0; defer-closure sites=" + str(len(deferred_sites))
    detail += "; sites created=" + str(sites_created)
    if unresolved:
        detail += "; review=" + "; ".join(unresolved[:12])
    return _set_message(result, detail, events_created=events_created, events_duplicate=events_duplicate,
                        links_written=links_written, cycles_created=cycles_created, cycles_closed=0,
                        sites_created=sites_created, deferred_sites=sorted(deferred_sites), unresolved=len(unresolved))
