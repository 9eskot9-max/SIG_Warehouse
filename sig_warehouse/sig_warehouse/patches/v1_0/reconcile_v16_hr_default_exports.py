"""Remove HRMS v16's implicit export defaults from its nine new HR rows.

Keep HRMS's explicit onboarding rights and all other permission rows. Refuse
an unfamiliar matrix instead of resetting permissions. See PERM-20261101-02.
"""

ROLES = {
    'Role': ('HR User', 'HR Manager'),
    'Currency': ('HR User', 'HR Manager'),
    'Project': ('HR User', 'HR Manager'),
    'Task': ('HR User', 'HR Manager'),
    'Email Account': ('HR Manager',),
}
PTYPES = ('read', 'write', 'create', 'delete', 'submit', 'cancel', 'amend',
          'report', 'export', 'import', 'print', 'email', 'share', 'select')


def expected_rights(doctype):
    return {'read', 'write', 'create', 'delete'} if doctype in ('Project', 'Task') else {'read'}


def execute():
    import frappe

    changes = []
    # Validate the entire scope before performing any write.
    for doctype, roles in ROLES.items():
        rows = frappe.get_all('Custom DocPerm', filters={'parent': doctype},
                              fields=['name', 'role', 'permlevel', 'if_owner', *PTYPES])
        if not rows:
            frappe.throw(f'{doctype} has no custom permission matrix; review before reconciling HR exports.')
        for role in roles:
            found = [r for r in rows if r['role'] == role and not (r['permlevel'] or 0)
                     and not (r['if_owner'] or 0)]
            if len(found) != 1:
                frappe.throw(f'Expected exactly one {role} permission row for {doctype}; review before migration.')
            row = found[0]
            actual = {p for p in PTYPES if p != 'export' and row.get(p)}
            if actual != expected_rights(doctype) or row.get('export') not in (0, 1, None):
                frappe.throw(f'Unexpected {role} permission matrix for {doctype}; review before migration.')
            if row.get('export'):
                changes.append((doctype, row['name']))
    for doctype, name in changes:
        frappe.db.set_value('Custom DocPerm', name, 'export', 0, update_modified=False)
        frappe.clear_cache(doctype=doctype)
