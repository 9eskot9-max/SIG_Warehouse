"""Allow Warehouse Manager to read the derived dispatch stage, at permlevel 1.

Material Request already has a Custom DocPerm matrix. Never create its first
custom row, which would shadow standard permissions, or rewrite existing rows.
"""

DOCTYPE = 'Material Request'
ROLE = 'Warehouse Manager'
FIELD = 'custom_dispatch_stage'
PTYPES = ('read', 'write', 'create', 'delete', 'submit', 'cancel', 'amend',
          'report', 'export', 'import', 'print', 'email', 'share', 'select')


def execute():
    import frappe

    field = frappe.get_meta(DOCTYPE).get_field(FIELD)
    if not field or field.permlevel != 1 or not field.read_only:
        frappe.throw('Dispatch stage field is missing or changed; review access before granting.')
    if not frappe.db.exists('Role', ROLE):
        frappe.throw('Warehouse Manager role is missing; review access before granting.')
    rows = frappe.get_all('Custom DocPerm', filters={'parent': DOCTYPE},
                          fields=['name', 'role', 'permlevel', 'if_owner', 'read'])
    if not rows:
        frappe.throw('Material Request has no Custom DocPerm baseline; adding a row would replace standard permissions.')
    target = [r for r in rows if r['role'] == ROLE and (r['permlevel'] or 0) == 1
              and not (r['if_owner'] or 0)]
    if len(target) > 1:
        frappe.throw('Duplicate Warehouse Manager level-1 permissions; review the baseline.')
    if target:
        if not target[0]['read']:
            frappe.db.set_value('Custom DocPerm', target[0]['name'], 'read', 1, update_modified=False)
    else:
        frappe.get_doc({'doctype': 'Custom DocPerm', 'parent': DOCTYPE, 'parenttype': 'DocType',
                        'parentfield': 'permissions', 'role': ROLE, 'permlevel': 1, 'if_owner': 0,
                        **{ptype: int(ptype == 'read') for ptype in PTYPES}}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=DOCTYPE)

