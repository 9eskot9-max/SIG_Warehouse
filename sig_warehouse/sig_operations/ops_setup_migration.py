"""One-time conversion of a stored Excel Setup to the Operations Setup Hub shape (24 Nov 2026).

Pure: no Frappe. Drops the retired lists and the cached Project family, gives every
Operations row a role (from the roster that used to be hard-coded in the Workbench),
adds the Warehouse owners, and keeps the Planner's earlier position history for the
crews that were migrated from the legacy leader rows. Unmatched people are errors,
never guessed.
"""
import copy

from sig_warehouse.sig_operations.excel_setup_contract import FIELDS

# The hard-coded roster this migration replaces: (family, role) -> names.
ROSTER = {
    ("Capex", "pm"): ("Mohammed Sohail Mohammed Ilyas",),
    ("Capex", "coordinator"): ("Ghlzar Ahmad Fazal Malik", "Sultan Afsar Ashraf Muhammed"),
    ("Incident", "pm"): ("Abdulraheem Mohammed", "Mohammed Sohail Mohammed Ilyas"),
    ("Incident", "coordinator"): ("Arshad ahmed abdulhameed",),
    ("5G / Colocation", "pm"): ("Mohammed Imran Ansary",),
    ("5G / Colocation", "coordinator"): ("Mohamed Walid Khalil Nmer Rahma", "Obed Sharrif"),
}
WAREHOUSE_USERS = ("m.ramzan@sigtele.com", "tahir.shahzad@sigtele.com")
OPEN_START = "2000-01-01"   # earlier positions already belong to a migrated crew


def _norm(value):
    return " ".join(str(value or "").split()).casefold()


def migrate(stored, names, warehouse_employees, today):
    """`names`: {employee_id: employee_name}; `warehouse_employees`: employee ids of WAREHOUSE_USERS."""
    data = copy.deepcopy(stored)
    legacy_teams = {(str(t.get("leader")), _norm(t.get("team"))) for t in data.get("teams", []) if t.get("enabled") and t.get("leader")}
    out = {name: [{k: row[k] for k in FIELDS[name] if k in row} for row in data.get(name, [])] for name in FIELDS}
    unmatched = []
    for row in out["ops_team_members"]:
        if row.get("role"):
            continue
        family = "5G / Colocation" if row.get("family") == "Colocation" else row.get("family")
        roles = [role for (fam, role), people in ROSTER.items()
                 if fam == family and _norm(names.get(row.get("employee"))) in {_norm(p) for p in people}]
        if len(roles) != 1:
            unmatched.append((row.get("family"), row.get("employee"), names.get(row.get("employee"))))
        else:
            row["role"] = roles[0]
        row.setdefault("weekly_pm", False)
    if unmatched:
        raise ValueError("Operations rows not in the previous roster; set their role by hand first: " + repr(unmatched))
    have = {r["employee"] for r in out["ops_team_members"] if r["role"] == "warehouse"}
    for employee in warehouse_employees:
        if employee not in have:
            out["ops_team_members"].append({"id": "ops-warehouse-" + employee, "family": "", "project": "", "employee": employee,
                                            "role": "warehouse", "weekly_pm": False, "effective_from": today,
                                            "effective_to": "", "enabled": True})
    team_names = {t["id"]: _norm(t.get("team_name")) for t in out["operational_teams"]}
    first = {}
    for row in out["team_memberships"]:
        if row.get("role") == "leader" and row.get("enabled", True):
            best = first.get(row["team"])
            if best is None or row["effective_from"] < best["effective_from"]:
                first[row["team"]] = row
        if row.get("role") not in ("leader", "member"):
            row["role"] = "member"
    for team, row in first.items():
        if (row["employee"], team_names.get(team)) in legacy_teams:
            row["effective_from"] = OPEN_START
    return out
