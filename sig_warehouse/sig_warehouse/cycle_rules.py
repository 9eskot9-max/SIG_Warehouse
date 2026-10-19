"""Shared evidence rules for stored cycles, dashboard projections and exports."""


def derive_cycle_state(row):
    # Keep this function self-contained: the migration embeds this same body
    # inside the sandboxed evidence writer, rather than maintaining a second rule.
    sig_visits = int(row.get("sessions_completed") or 0) + int(row.get("sessions_auto_closed") or 0)
    sig_visits = max(sig_visits, 1 if row.get("first_visit_at") else 0)
    sig_tcn = str(row.get("tcn_at") or "")[:19]
    sig_mir = str(row.get("mir_at") or "")[:19]
    sig_visit = str(row.get("first_visit_at") or "")[:19]
    sig_tags = str(row.get("tags_at") or "")[:19]
    sig_handover = []
    if sig_tcn and sig_mir and sig_visits >= 1 and sig_tags:
        sig_handover.append(max(sig_tcn, sig_mir, sig_visit, sig_tags))
    if sig_tcn and sig_mir and sig_visits >= 2:
        sig_second = str(row.get("second_visit_at") or row.get("last_visit_at") or sig_visit)[:19]
        if sig_second:
            sig_handover.append(max(sig_tcn, sig_mir, sig_second))
    # Direct downstream evidence remains valid even for legacy cycles with
    # missing predecessors. Photos are historical evidence, never a pending task.
    for sig_field in ("photos_at", "warranty_at", "asbuilt_at"):
        if row.get(sig_field):
            sig_handover.append(str(row.get(sig_field))[:19])
    sig_final = [str(row.get(sig_field))[:19] for sig_field in ("ho_at", "invoice_at") if row.get(sig_field)]
    sig_plan = [str(row.get(sig_field))[:19] for sig_field in
                ("pimp_at", "tcn_at", "mir_at", "first_visit_at", "tags_at") if row.get(sig_field)]
    if row.get("terminal") in (1, True, "1", "Yes", "yes"):
        stage, anchor = "5 - Closed", None
    elif sig_final:
        stage, anchor = "4 - Invoicing", min(sig_final)
    elif sig_handover:
        stage, anchor = "3 - Handover", min(sig_handover)
    elif sig_plan:
        stage, anchor = "2 - Plan", max(sig_plan)
    else:
        stage = "1 - Initial"
        anchor = str(row.get("mapping_at") or row.get("boq_at") or row.get("last_event_at") or "")[:19] or None
    # Stored PM decisions and previously reached stages are a progression floor.
    # Missing legacy evidence must not silently move an approved cycle backwards.
    # Only terminal closes a cycle; a stale stage-5 label alone cannot close it.
    sig_saved_stage = str(row.get("stage") or "")
    if sig_saved_stage == "4 - As-Built":
        sig_saved_stage = "4 - Invoicing"
    if stage != "5 - Closed" and sig_saved_stage in ("1 - Initial", "2 - Plan", "3 - Handover", "4 - Invoicing"):
        if sig_saved_stage > stage:
            stage = sig_saved_stage
            anchor = str(row.get("stage_anchor_at") or row.get("last_event_at") or "")[:19] or None
    return stage, anchor
