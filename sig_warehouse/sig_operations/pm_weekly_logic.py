"""Pure rules for the weekly PM check (no Frappe imports; unit-tested).

Once a week, on Sunday (the start of the Sunday–Thursday working week), each PM gets three messages:
  1. last week's focus: planned sites, visited or not, and a reason for each miss;
  2. this week's target: the planner's sites for the PM's projects, marked Must, Hold or Remove;
  3. the system's comment on last week's plan, answered with a 1–5 score and one sentence.

Dates are plain `datetime.date` values in Riyadh business time. Python weekdays: Monday=0 ... Sunday=6.
"""
from datetime import date, datetime, timedelta

REASONS = ("access", "material", "team", "TCN", "scope or WO", "other")
DECISIONS = ("Must", "Hold", "Remove")
SCORES = ("1", "2", "3", "4", "5")


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()[:10]
    return datetime.strptime(text, "%Y-%m-%d").date()


def sunday_on_or_before(day):
    """The Sunday that starts the working week containing `day`."""
    day = as_date(day)
    return day - timedelta(days=(day.weekday() - 6) % 7)


def previous_week(week_start):
    return as_date(week_start) - timedelta(days=7)


def in_week(day, week_start):
    start = as_date(week_start)
    return start <= as_date(day) <= start + timedelta(days=6)


def scope_projects(scope_rows, employee):
    """Projects this PM covers. `scope_rows` are dicts with employee, project and active."""
    return {r["project"] for r in scope_rows if r["employee"] == employee and r.get("active") and r.get("project")}


def one_line_per_site(rows):
    seen, out = set(), []
    for row in rows:
        if row["site"] in seen:
            continue
        seen.add(row["site"])
        out.append(row)
    return out


def this_week_lines(snapshot_rows, projects):
    rows = [r for r in snapshot_rows if r["project"] in projects]
    return [{"site": r["site"], "cycle": r.get("cycle") or "", "project": r["project"],
             "planned_day": r.get("planned_day"), "decision": "", "reason": "", "note": ""}
            for r in one_line_per_site(rows)]


def last_week_lines(prev_snapshot_rows, projects, prev_start, visits):
    """Planned sites from last week with a visit count from last week's Site Visits.

    `visits` are dicts with site, project and day (date). A site counts as visited when it has at least one
    visit in last week's Sunday–Thursday window.
    """
    counts = {}
    for v in visits:
        if in_week(v["day"], prev_start):
            counts[v["site"]] = counts.get(v["site"], 0) + 1
    rows = [r for r in prev_snapshot_rows if r["project"] in projects]
    out = []
    for r in one_line_per_site(rows):
        n = counts.get(r["site"], 0)
        out.append({"site": r["site"], "cycle": r.get("cycle") or "", "project": r["project"],
                    "planned_day": r.get("planned_day"), "visited": 1 if n else 0, "visit_count": n,
                    "reason": "", "note": ""})
    return out


def additions(visits, prev_start, planned_sites, projects):
    """Sites the PM's projects visited last week that were not on the plan. The PM can confirm them."""
    counts, project_of = {}, {}
    for v in visits:
        if in_week(v["day"], prev_start) and v["project"] in projects and v["site"] not in planned_sites:
            counts[v["site"]] = counts.get(v["site"], 0) + 1
            project_of[v["site"]] = v["project"]
    return [{"site": s, "project": project_of[s], "visit_count": n, "note": ""} for s, n in sorted(counts.items())]


def system_comment(lines, extra):
    """Plain comment on last week's plan, in English and Arabic."""
    planned = len(lines)
    visited = sum(1 for line in lines if line["visited"])
    misses = [line for line in lines if not line["visited"]]
    reasons = {}
    for line in misses:
        key = line.get("reason") or "no reason yet"
        reasons[key] = reasons.get(key, 0) + 1
    detail = ", ".join(f"{k}: {v}" for k, v in sorted(reasons.items())) or "none"
    en = (f"Last week the plan had {planned} sites; {visited} were visited. "
          f"Misses by reason: {detail}. Visits not on the plan: {len(extra)}.")
    ar = (f"الخطة الأسبوع الماضي شملت {planned} موقعاً، تمت زيارة {visited} منها. "
          f"المواقع غير المزارة حسب السبب: {detail}. زيارات خارج الخطة: {len(extra)}.")
    return {"en": en, "ar": ar, "planned": planned, "visited": visited, "misses": len(misses), "extra": len(extra)}


def valid_score(value):
    return value in (None, "") or str(value) in SCORES


def build_messages(first_name, comment, this_week_count, link):
    """The three weekly messages, Arabic and English, for one PM."""
    name = first_name or ""
    m1 = (f"مراجعة الأسبوع الماضي ({name}): تمت زيارة {comment['visited']} من {comment['planned']} موقعاً. "
          f"يرجى ذكر السبب لكل موقع لم يُزر.\n"
          f"Last week's review ({name}): {comment['visited']} of {comment['planned']} planned sites visited. "
          f"Please give a reason for each miss.\n{link}")
    m2 = (f"هدف هذا الأسبوع: {this_week_count} موقعاً في منطقتك. حدد لكل موقع: ضروري، تعليق، أو إزالة.\n"
          f"This week's target: {this_week_count} sites in your area. Mark each as Must, Hold or Remove.\n{link}")
    m3 = (f"تعليق النظام على الخطة: {comment['ar']} أرسل تقييمك من 1 إلى 5 مع جملة واحدة.\n"
          f"System comment on the plan: {comment['en']} Send your score from 1 to 5 with one sentence.\n{link}")
    return [m1, m2, m3]
