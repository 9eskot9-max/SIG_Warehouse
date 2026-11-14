"""Pure rules for the daily no-visit WhatsApp message (no Frappe imports, unit-tested).

A person is nudged when ALL of these hold:
  * they are an enabled crew's current leader in published Excel Setup, with an active Employee and phone;
  * they are not in the exclude list and not on approved leave / a holiday today;
  * no field visit, field session or WhatsApp field report was recorded for them today;
  * they were not already messaged for today in the same mode.
"""

MESSAGE_EN = (
    "SIG: no site visit has been recorded for you today ({day}). "
    "Please reply with the site and activity you worked on, or the reason (leave, office work, no work)."
)
MESSAGE_AR = (
    "SIG: لم يتم تسجيل زيارة موقع لك اليوم ({day}). "
    "فضلاً أرسل الموقع والنشاط الذي عملت عليه، أو السبب (إجازة، عمل مكتبي، لا يوجد عمل)."
)


def compose_message(day, test_for=None):
    text = MESSAGE_EN.format(day=day) + "\n\n" + MESSAGE_AR.format(day=day)
    return f"[TEST - would go to {test_for}]\n{text}" if test_for else text


def parse_ids(value):
    """Employee IDs separated by commas, spaces or new lines."""
    return {part.strip() for part in str(value or "").replace(",", " ").split() if part.strip()}


def planner_leaders(setup, day):
    """Return uniquely assigned leaders of enabled crews on the given ISO date."""
    crews = {str(t.get("id")) for t in setup.get("operational_teams", []) if t.get("id") and t.get("enabled")}
    leaders = {team: set() for team in crews}
    for row in setup.get("team_memberships", []):
        team, start, end = str(row.get("team") or ""), str(row.get("effective_from") or "")[:10], str(row.get("effective_to") or "")[:10]
        if (team in leaders and row.get("enabled") and row.get("role") == "leader" and row.get("employee")
                and start and start <= day and (not end or day <= end)):
            leaders[team].add(str(row["employee"]))
    return {next(iter(people)) for people in leaders.values() if len(people) == 1}


def decide(employees, roster, active_today, on_leave_or_holiday, exclude, already_sent, max_recipients=40):
    """Return (rows, truncated). Each row: {employee, employee_name, phone, decision, reason}.

    decision is 'send' or 'skip'. `employees` is a list of dicts with name, employee_name, cell_number, status.
    """
    roster_ids = set(roster)
    rows, sendable = [], 0
    for emp in sorted(employees, key=lambda e: str(e.get("employee_name") or e["name"])):
        name = emp["name"]
        if name not in roster_ids:
            continue
        row = {"employee": name, "employee_name": emp.get("employee_name"), "phone": emp.get("cell_number"),
               "decision": "skip", "reason": ""}
        if emp.get("status") != "Active":
            row["reason"] = "not active"
        elif name in exclude:
            row["reason"] = "excluded"
        elif not emp.get("cell_number"):
            row["reason"] = "no phone number"
        elif name in on_leave_or_holiday:
            row["reason"] = "leave or holiday"
        elif name in active_today:
            row["reason"] = "visit/report recorded today"
        elif name in already_sent:
            row["reason"] = "already messaged today"
        else:
            row["decision"], row["reason"] = "send", "no visit recorded today"
            sendable += 1
        rows.append(row)
    truncated = sendable > max_recipients
    if truncated:
        count = 0
        for row in rows:
            if row["decision"] == "send":
                count += 1
                if count > max_recipients:
                    row["decision"], row["reason"] = "skip", "over the per-run cap"
    return rows, truncated
