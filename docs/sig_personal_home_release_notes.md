# SIG personal home and flat navigation

Prepared against SIG Warehouse production read-back ecc06e2 on 1 November 2026.
This is a local candidate; the installed revision must be reconfirmed before release.

The existing SIG app route opens sig-hub. It now shows permitted workbench
entries, the user's open ToDo records, a native new ToDo action where create is
allowed, and the other permitted SIG Hub destinations. The five principal
workbenches are Operations, Finance, HR, Warehouse and Petty Cash. Setup is a
separate System Manager shortcut. The personal focus items are ordinary ToDos,
not a separate private notes system. Returning to the page refreshes the list.
The app tile uses the owner-confirmed SIG symbol.

The intended navigation keeps Frappe's existing five SIG app icons as the main
rail and removes the extra workspace/subpage sidebar on My Page and the SIG
workbench routes. The initial v16 release loaded the new asset but failed at
startup (`frappe.ready is not a function`), so that sidebar remained visible.
The follow-up uses v16's immediate router lifecycle, hides the duplicate
sidebar for all users on those SIG routes, and replaces the top-left ERPNext
wordmark with the approved SIG mark alone. Native Frappe navigation returns on
other routes. No role, DocPerm, Page, Workspace, fixture or migration
permission is changed. The PDF Share control is a print-preview toolbar action;
it is not part of the printed document. A direct live preview showed the
toolbar control, but a clean preview through the normal document flow is still
needed to resolve the owner's report that it is missing.

## Permission and release gate

Intended audiences: all existing sig-hub Page users; Operations: System Manager,
Projects Manager, Projects User and SIG Field Ops; Finance: System Manager,
Accounts User, Accounts Manager and SIG Finance Viewer; HR: System Manager,
HR Manager and HR User; Warehouse: System Manager, Stock User, Stock Manager,
Warehouse Manager and SIG Stock Viewer; Petty Cash: System Manager, Accounts
User/Manager, Operations User/Manager and SIG PC Clearance. These are source
Page roles at the candidate revision, not a current live effective-access
snapshot. My Page reads ToDo using the current user's normal list permission
and record filters, and offers a new form only with ToDo create permission.
Employee self-service retains its existing role-filtered link. Setup visibility
in this candidate is limited to System Manager; other navigation remains native.

Before deployment, follow deployment_permission_guide.md and the learning-loop
access gate: confirm production app revisions and migration writers; snapshot
the live Page, Workspace, Report and DocType matrices including ToDo and linked
records; compare after migration for both unintended grants and removals; and
test fresh sessions for each registered audience. Exercise a brand-new form,
its defaults and linked-record lookup, and return through the normal menu after
reload. Also verify English, Arabic/RTL, mobile, keyboard, search, notifications,
user menu, all app navigation, native sidebar restoration, and workbench links.
The setup shortcut and SIG app landing route must be tested against installed
Frappe v16.54. No site-wide Default App or login redirect is changed; setting
SIG as a user's default app is a separate site/user setting and is not yet
verified.

Initial release deployment: `1b5f4daaf90505614ae0e115d7d8d80b86c62ce1` on
2026-11-01; migration and permission snapshots passed, but the live route
revealed the v16 navigation startup error above. This follow-up is the
corrective release. Migration repeatability and role-based workflow acceptance
remain NOT TESTED; do not equate deployment status with user acceptance.
