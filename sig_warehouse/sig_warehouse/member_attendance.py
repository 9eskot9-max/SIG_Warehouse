"""Gate for crediting a leader's Start/End to crew members. Local only, OFF by default.

Owner decision 25 Nov 2026: a leader's Start/End counts for every active member of the crew
that day. The absence rule is not decided yet, so absent_on() is a placeholder that marks
nobody absent. Nothing calls credited_members() yet; switching it on is a separate release.
Members never receive messages or drive planning (those filter role == leader only).
"""

# shortcut: a code switch, not a DocType field, until the absence rule is decided; upgrade to a settings field when it is switched on.
MEMBER_CREDIT_ENABLED = False


def _active(row, day):
    if not row.get("enabled") or row.get("role") != "member" or not row.get("employee"):
        return False
    start = str(row.get("effective_from") or "")
    end = str(row.get("effective_to") or "")
    return (not start or start <= day) and (not end or day <= end)


def members_on(setup, team, day):
    """Active crew members of one crew on an ISO day (YYYY-MM-DD), sorted and unique."""
    return sorted({str(r["employee"]) for r in setup.get("team_memberships", [])
                   if r.get("team") == team and _active(r, day)})


def absent_on(employee, day):
    """Placeholder until the absence rule is decided: nobody is absent."""
    return False


def credited_members(setup, team, day, enabled=None, absent=absent_on):
    """Members a leader's Start/End should credit on this day. Empty while the gate is off."""
    if not (MEMBER_CREDIT_ENABLED if enabled is None else enabled):
        return []
    return [e for e in members_on(setup, team, day) if not absent(e, day)]
