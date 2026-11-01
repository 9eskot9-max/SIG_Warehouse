"""Allow approved warehouse roles to read the derived dispatch stage at permlevel 1.

Material Request already has a Custom DocPerm matrix. Never create its first
custom row, which would shadow standard permissions, or rewrite existing rows.
"""

DOCTYPE = 'Material Request'
ROLES = ('Warehouse Manager', 'Stock User')
FIELD = 'custom_dispatch_stage'
PTYPES = ('read', 'write', 'create', 'delete', 'submit', 'cancel', 'amend',
          'report', 'export', 'import', 'print', 'email', 'share', 'select')


def execute():
    import frappe

    field = frappe.get_meta(DOCTYPE).get_field(FIELD)
    if not field or field.permlevel != 1 or not field.read_only:
        frappe.throw('Dispatch stage field is missing or changed; review access before granting.')
    for role in ROLES:
        if not frappe.db.exists('Role', role):
            frappe.throw(f'{role} role is missing; review access before granting.')
    rows = frappe.get_all('Custom DocPerm', filters={'parent': DOCTYPE},
                          fields=['name', 'role', 'permlevel', 'if_owner', 'read'])
    if not rows:
        frappe.throw('Material Request has no Custom DocPerm baseline; adding a row would replace standard permissions.')
    targets = {}
    for role in ROLES:
        targets[role] = [r for r in rows if r['role'] == role and (r['permlevel'] or 0) == 1
                         and not (r['if_owner'] or 0)]
        if len(targets[role]) > 1:
            frappe.throw(f'Duplicate {role} level-1 permissions; review the baseline.')
    for role in ROLES:
        target = targets[role]
        if target:
            if not target[0]['read']:
                frappe.db.set_value('Custom DocPerm', target[0]['name'], 'read', 1, update_modified=False)
        else:
            frappe.get_doc({'doctype': 'Custom DocPerm', 'parent': DOCTYPE, 'parenttype': 'DocType',
                            'parentfield': 'permissions', 'role': role, 'permlevel': 1, 'if_owner': 0,
                            **{ptype: int(ptype == 'read') for ptype in PTYPES}}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=DOCTYPE)
