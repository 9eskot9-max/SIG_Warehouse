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

The app-wide navigation script replaces the standard module link list with a
compact icon-only rail (accessible names and hover labels) only on
sig-hub, the five workbench routes, and Petty Cash Status. It restores the native
list on other routes and when its allowed-destination lookup fails. Search,
notifications, user menu and the original dock remain Frappe controls. Pages
are filtered through the existing Hub permission check; no role, DocPerm,
Page, Workspace, fixture or migration permission is changed.

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

Migration repeatability: NOT TESTED. Live route rendering: NOT TESTED.
Role-based workflow acceptance: NOT TESTED. No deployment authorized in this
work session.
