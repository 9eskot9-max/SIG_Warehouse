"""STAGED, not listed in patches.txt: a TCN's install scope never silently overwrites a different one.

Today every TCN writes its type (TCN-MDT column I) onto the cycle it lands on, and a TCN without a WO lands on the
site+BA's oldest open cycle, so a CB TCN can replace HVAC. With this guard, for an install code (or its DM form):
  * cycle undecided (blank, SURVEY or an unknown code) or the same code -> as today, the TCN sets the type;
  * cycle already decided on a different scope (another install code, or PAT = that work is finished):
      - TCN placed by site+BA only: move it to another open cycle with the same code, else to an undecided one that
        is not Parked and still in stage 1 or 2;
      - otherwise (TCN names a WO or a cycle, or no such cycle exists): keep the cycle's type, flag TCN_SCOPE_CONFLICT.
Non-install codes (SURVEY, PAT, unknown) never overwrite a decided scope. No cycle is ever created by this rule,
and the TCN event itself always keeps its raw code. To release: add this module to patches.txt.
"""
import frappe

MARKER = "# SIG_TCN_SCOPE_GUARD_V1"
SELECT_ANCHOR = "    cycdoc = frappe.get_doc('SIG Site Cycle', cyc)\n"
WRITE_ANCHOR = "        if pact:\n            cycdoc.set('planned_activity', pact)\n"
FLAG_ANCHOR = "    cycdoc.set('cycle_flags', ','.join(flags))\n"

# Flat code on purpose: Frappe safe_exec cannot reliably call functions defined inside a Server Script.
GUARD = '''    # SIG_TCN_SCOPE_GUARD_V1
    tcn_write_scope = True
    tcn_scope_flag = ''
    if event_code == 'TCN_GENERATED':
        install_codes = ('FF', 'HVAC', 'DC', 'MODULE', 'BB', 'LIVELOADDC', 'LDP', 'CIVIL', 'CB')
        tcn_code = str(frappe.form_dict.get('planned_activity') or '').strip().upper()[:40].replace('LIFELOADDC', 'LIVELOADDC')
        now_code = str(frappe.db.get_value('SIG Site Cycle', cyc, 'planned_activity') or '').strip().upper().replace('LIFELOADDC', 'LIVELOADDC')
        decided = now_code in install_codes or now_code == 'PAT' or (now_code[:2] == 'DM' and now_code[2:] in install_codes)
        is_install = tcn_code in install_codes or (tcn_code[:2] == 'DM' and tcn_code[2:] in install_codes)
        if tcn_code and decided and tcn_code != now_code:
            tcn_write_scope = False
            if is_install:
                same_cycle = ''
                free_cycle = ''
                if po and not cycle_hint and not wo:
                    for other in frappe.get_all('SIG Site Cycle', filters={'po': po, 'site_key': sk, 'terminal': 0},
                                                fields=['name', 'planned_activity', 'stage', 'sig_lifecycle'], order_by='creation asc, name asc',
                                                limit_page_length=100):
                        if other.name == cyc:
                            continue
                        code = str(other.planned_activity or '').strip().upper().replace('LIFELOADDC', 'LIVELOADDC')
                        taken = code in install_codes or code == 'PAT' or (code[:2] == 'DM' and code[2:] in install_codes)
                        if code == tcn_code and not same_cycle:
                            same_cycle = other.name
                        # an empty target must still be waiting for field work: never reopen a parked cycle or
                        # load a scope onto one already in handover or invoicing
                        elif (not taken and not free_cycle and other.sig_lifecycle != 'Parked'
                              and str(other.stage or '1').strip()[:1] in ('1', '2')):
                            free_cycle = other.name
                if same_cycle or free_cycle:
                    cyc = same_cycle or free_cycle
                    tcn_write_scope = True
                    tcn_scope_flag = 'TCN_SCOPE_MOVED'
                else:
                    tcn_scope_flag = 'TCN_SCOPE_CONFLICT'

'''


def rewrite(source):
    """Insert the guard into register_evidence_event; refuse unless every anchor appears exactly once."""
    if MARKER in source:
        return source
    for anchor in (SELECT_ANCHOR, WRITE_ANCHOR, FLAG_ANCHOR):
        if source.count(anchor) != 1:
            raise ValueError("Evidence writer anchor is missing or ambiguous: " + anchor.strip())
    source = source.replace(SELECT_ANCHOR, GUARD + SELECT_ANCHOR, 1)
    source = source.replace(WRITE_ANCHOR, "        if pact and tcn_write_scope:\n            cycdoc.set('planned_activity', pact)\n", 1)
    return source.replace(FLAG_ANCHOR, "    if tcn_scope_flag and tcn_scope_flag not in flags:\n"
                                       "        flags.append(tcn_scope_flag)\n" + FLAG_ANCHOR, 1)


def execute():
    script = "register_evidence_event"
    if not frappe.db.exists("Server Script", script):
        frappe.throw("Cannot add the TCN scope guard: register_evidence_event is missing.")
    original = frappe.db.get_value("Server Script", script, "script") or ""
    try:
        source = rewrite(original)
    except ValueError as error:
        frappe.throw(str(error))
    if source != original:
        frappe.db.set_value("Server Script", script, "script", source)
