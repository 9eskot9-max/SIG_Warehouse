"""Visit type from the TCN: TCN-MDT column I (Remarks) labels the field visits it planned.

RV80 sends Remarks as planned_activity on each TCN_GENERATED event. A field visit whose
leader did not type a type takes it from the TCN of the same site whose planned window
covers the visit day (one day of slack each side). Different types on equally close TCNs
leave the visit unlabelled for review instead of guessing.
"""
from datetime import datetime, timedelta

INSTALL_CODES = {"FF", "HVAC", "DC", "MODULE", "BB", "LIFELOADDC", "LIVELOADDC", "LDP", "CIVIL", "CB"}
SLACK_DAYS = 1
LOOKAROUND_DAYS = 30


def category(code):
    """Remarks code -> SIG Field Visit activity, the same map RV80 uses for the CSV Purpose Reason."""
    code = str(code or "").strip().upper()
    if code == "PAT":
        return "PAT"
    if code == "SURVEY":
        return "SURVEY"
    if code in INSTALL_CODES:
        return "INSTALL"
    if code.startswith("DM") and code[2:] in INSTALL_CODES:
        return "DISMANTLE"
    return None


def match(tcns, visit_day):
    """tcns: [{"activity", "start", "end"}] (dates or datetimes). -> (activity, scope, note)."""
    best, hits = None, []
    for t in tcns:
        code = str(t.get("activity") or "").strip().upper()
        if not code or not t.get("start"):
            continue
        start = _day(t["start"])
        end = max(_day(t.get("end") or t["start"]), start)
        if not start - timedelta(days=SLACK_DAYS) <= visit_day <= end + timedelta(days=SLACK_DAYS):
            continue
        gap = (start - visit_day).days if visit_day < start else max((visit_day - end).days, 0)
        if best is None or gap < best:
            best, hits = gap, [code]
        elif gap == best:
            hits.append(code)
    if not hits:
        return None, "", ""
    codes = sorted(set(hits))
    kinds = {category(c) for c in codes}
    if None in kinds:
        return None, "+".join(codes), "TCN_ACTIVITY_UNMAPPED:" + "+".join(c for c in codes if not category(c))
    if len(kinds) > 1:
        return None, "+".join(codes), "TCN_ACTIVITY_AMBIGUOUS:" + "+".join(codes)
    return kinds.pop(), "+".join(codes), ""


def resolve(site_key, start_at):
    """Live lookup for one visit. -> (activity, scope, note)."""
    import frappe
    day = _day(start_at)
    around = [str(day - timedelta(days=LOOKAROUND_DAYS)), str(day + timedelta(days=LOOKAROUND_DAYS)) + " 23:59:59"]
    rows = frappe.get_all("SIG Evidence Event",
                          filters={"event_code": "TCN_GENERATED", "site_key": site_key,
                                   "planned_activity": ["is", "set"], "occurred_at": ["between", around]},
                          fields=["planned_activity", "occurred_at", "tcn_window_start", "tcn_window_end"],
                          limit_page_length=0)
    return match([{"activity": r.planned_activity, "start": r.tcn_window_start or r.occurred_at,
                   "end": r.tcn_window_end or r.occurred_at} for r in rows], day)


def _day(value):
    if isinstance(value, str):
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    return value.date() if hasattr(value, "date") else value
