"""Proposed, side-effect-free stage projection for comparison, not live writes."""

STAGES = ("1 - Initial", "2 - Plan", "3 - Handover", "4 - Invoicing")
PLAN = frozenset(("PIMP_GENERATED", "TCN_GENERATED", "MIR_CONFIRMED",
                  "FIELD_VISIT_COMPLETED", "TAGS_COLLECTED"))
HANDOVER = frozenset(("PHOTOS_FINALIZED", "WARRANTY_GENERATED", "ASBUILT_BOQ_GENERATED"))
INVOICING = frozenset(("GCL_GENERATED", "FIS_GENERATED", "MGCL_GENERATED", "INVOICE_GENERATED"))
PREPARATION = frozenset(("TCN_GENERATED", "MIR_CONFIRMED", "FIELD_VISIT_COMPLETED"))


def project_evidence_stage(event_codes, *, history_complete=False):
    """Project a stage without altering the stored cycle.

    Evidence that a document was generated does not imply approval. Missing
    predecessor evidence is only reported as absent if history_complete is
    explicitly asserted. Life-cycle/closure and prior manual decisions remain
    separate and must be reconciled by a caller before this could be used live.
    """
    codes = frozenset(code for code in event_codes if isinstance(code, str))
    if codes & INVOICING:
        rank = 3
    elif codes & HANDOVER or PREPARATION <= codes:
        rank = 2
    elif codes & PLAN:
        rank = 1
    else:
        rank = 0
    missing = sorted(PREPARATION - codes) if rank >= 2 and history_complete else None
    return {"stage": STAGES[rank], "missing_preparation": missing,
            "history_complete_asserted": bool(history_complete)}
