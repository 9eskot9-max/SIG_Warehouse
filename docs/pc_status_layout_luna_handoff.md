# Luna handoff — PC Status layout, 2026-10-20

LOCAL ONLY. Do not describe these changes as deployed. The user requested
local completion so Luna can perform the later deployment. Branch:
codex/pc-status-review-layout-local; checkout:
D:\erp\ERPNext\SIG_Warehouse_pc_status_report.

## Observed before editing

Authenticated Administrator session, production /app/pc-invoice-review and
/app/pc-transaction-status. Review has employee/date queue, selected receipt
viewer, toolbar and Previous/Next. Status instead shows the full table before
receipt cards. It loaded 1,142 cards across employees. Selecting Faizan reduced
the table to eight rows, and View scrolled to a large receipt card. This is the
layout mismatch the user reported.

## Changed locally

Only Status JS/CSS and documentation/previews. No API, permission hooks, role
lists, migration, Page JSON, business records or live configuration changed.
The interactive layout now follows PC Review with one selected employee and one
receipt viewer; read-only status/approver details; period controls and table below.
Print builds sequential receipt pages only when requested.

Open these files directly in a normal browser:
- docs/pc_status_review_layout_preview.html — interactive design using the
  actual changed Page JS/CSS, with a minimal Frappe adapter and simulated records.
- docs/pc_status_print_document_preview.html — standalone sample document
  generated from the same render/print functions; table followed by receipt pages.

Do not export the preview adapter or simulated data into Frappe. The real Page
continues to call the existing transaction_status_report method.

## Checks

PASS: Node syntax and git whitespace checks.
PASS: seven local DOM functional scenarios: initial one-receipt rendering,
Next/status/approver, status/search synchronization, date range, roster persistence
and unavailable cycle, sequential print media preparation/cleanup, denied request
clearing stale data and disabling print. Evidence:
../backups/pc_status_local_check_20261020/check.cjs and result.txt.
The DOM adapter only supplies the HTMLSelectElement.value setter omitted by
Linkedom. This does not render CSS or provide ERP role acceptance.

NOT TESTED: new local CSS rendering and actual browser/PDF print pagination.
The browser tool rejected local file navigation under its URL policy. No
workaround was attempted. Review the two files directly before release.
PDF iframe content printing remains browser dependent; check a real PDF receipt.

## Permission incident remains open

Immediately before this layout request the owner reported that Waleed and others
had lost permissions and requested rework. The subsequent direction was to finish
the design locally and let Luna deploy later. This branch does not repair or
certify that incident.

Declared audiences remain System Manager, Accounts User/Manager, Operations
User/Manager and SIG PC Clearance, with existing assigned-employee scope. The
actual current non-admin workflow is NOT TESTED. Do not infer access from this
Administrator observation or from the six Page role rows.

Prior release evidence:
../backups/permission_release_pc_status_report_20261020/.
Its recorded change removed Journal Entry write/export from SIG PC Clearance.
That is a diagnostic lead, not proof of the reported current cause. Check actual
User identity, governing Role Profile, held roles, User Permissions, effective
DocPerm, Page/Workspace roles and runtime scope/command hooks before any repair.
Preserve complete standard/custom matrices; no sparse Custom DocPerm replacement
or blanket bypass. Follow ../docs/deployment_permission_guide.md and the
mandatory persona/learning-loop gate. Snapshot live access before and after
deployment; verify Waleed's actual scoped read and draft-confirm workflow and all
affected reviewer/Finance audiences in fresh authenticated sessions.

All registered audience workflows (Finance User/Manager, Warehouse, Hamid,
PM/coordinators, HR, employee/viewer, integrations) remain NOT TESTED for this
local release. Role/profile/configuration writers are unchanged by these layout
files. Required access acceptance remains pending; this handoff is local source
completion, not a fixed/verified production claim.
