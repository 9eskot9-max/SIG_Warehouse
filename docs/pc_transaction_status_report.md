# Petty Cash Transaction Status report

The `pc-transaction-status` Desk Page is a read-only report for petty-cash transactions. It shares the existing PC Review audience and transaction scope. It narrows the existing `SIG PC Clearance` Journal Entry custom permission row to read/create only and applies the current employee-scope mapping to that role's JE access.

## Permission model

- Page roles match `pc-invoice-review`: System Manager, Accounts User, Accounts Manager, Operations User, Operations Manager, and SIG PC Clearance.
- The backend requires one of those reviewer roles and reads rows with `frappe.get_list("SIG PC Transaction", ...)`, so the existing `permission_query_conditions` employee assignment remains the row-level gate. Finance roles retain their pre-existing broader scope; Operations and SIG PC Clearance remain restricted to assigned employees and cannot review their own receipts.
- The report does not read Journal Entry lists, accounts, or journal lines. For each visible transaction with a `journal_entry`, it retrieves only `docstatus` using both the JE name and `custom_pc_receipt == transaction.name`. A missing or mismatched origin link is shown as an exception state. This is a narrow domain read and must not be converted into broad Journal Entry read access.
- `SIG PC Clearance` retains JE read and create but loses write and export. JE read/list queries are restricted to origin-linked transactions inside that user's existing employee scope. Native JE create remains available only while `confirm_receipt` performs the existing scoped confirmation; ordinary JE creation without that exact request-local receipt marker is denied. Submit, cancel and delete remain disabled. Finance and audit roles' separate existing matrix is preserved. A guarded migration verifies the full six-role custom matrix before changing the one row and accepts the already-migrated target on repeat runs.
- The report displays the existing PC review group/lead from `pc_review_assignments.json` as delegation context, alongside the actual `reviewed_by` user recorded on the transaction. The assignment matrix is explicitly `task_assignment_only`; it is not used as the authorization source and does not establish a Project. Access remains controlled by `pc_review_scopes.json` and the transaction permission hooks.
- The transaction's `closure_status` remains the review status. The linked JE's current `docstatus` is the accounting status: Draft (pending Finance), Submitted (posted), or Cancelled. This avoids relying on the stale stored `journal_status` field.
- `reviewed_by` is displayed as the approving user's full name. Employee scope, User Permissions and Role Profiles are unchanged. One existing Custom DocPerm row is narrowed as described above; the other JE role rows remain unchanged.

## Local layout revision — 2026-10-20, not deployed

The production Status page was observed alongside PC Review under an authenticated
Administrator session. Status opens a long table before its receipt sections; View
scrolls to a report card. PC Review instead opens an employee selector, date-grouped
receipt queue, one image viewer and transaction details with Previous/Next. The
local revision adopts that workbench structure.

- The interactive screen displays one employee at a time, chosen from the caller's
  existing permitted transaction roster. Employee options remain available after
  changing a period. The initial roster comes from the existing scoped endpoint.
- A date-grouped queue, receipt search and individual status filter synchronize
  the current transaction, its image, approver and register. Pending Review is
  labelled Pending Manager on this page; stored statuses are unchanged.
- The original image opens fitted to the page with PC Review's zoom, fit width,
  actual size, rotate and drag behavior. PDF receipts use the browser PDF viewer.
- The range selector and transaction table sit below the workbench. View or a row
  selection brings that transaction into the viewer above. Previous/Next changes
  selection only.
- The register and print include category, amount including VAT, individual
  status, recorded approver and current linked Journal Entry status.
- Print report creates a document containing the filtered register followed by
  every included receipt in the same order, with transaction details on each
  receipt page. Off-screen print media is created on demand and removed after
  printing. Browsing no longer creates all receipt image/PDF frames.
- Cycle selection remains unavailable until the authoritative employee payment/
  advance source is connected. Every payment to the employee will start a cycle;
  receipt dates and expense journals cannot establish those funding boundaries.
- The existing two-way PC Review / Status navigation remains in place.

Local interface preview: docs/pc_status_review_layout_preview.html.
Standalone print document sample: docs/pc_status_print_document_preview.html.
Both use explicitly simulated transactions and receipt media.

## Release acceptance record

This source change introduces a new Page for the existing PC Review role audience and a read-only whitelist method, and narrows the `SIG PC Clearance` JE custom row. Before deployment, compare the full before/after permission state including Page roles, full standard and custom matrices, user roles/profiles, User Permissions, field permlevels and the active hook/scope source. Test the app migration on staging twice, then run fresh-session checks as each registered audience. Operations User/Manager must see assigned employees only, fail to open unassigned employees and self-review, and see only the linked JE status from assigned transactions. The SIG PC Clearance role must be unable to list/open unrelated JEs, create a JE from the normal form, edit, export, submit or cancel; the existing confirmation must still create one draft. Accounts roles must exercise the same report against their approved existing broader scope. Test the page from the normal Desk menu after reload and verify the print output. Do not treat Administrator or API checks as role acceptance.

The initial status-report release is live as of 2026-10-20 at revision `41d185f5`. This receipt-detail update adds only `source_media_url` to the scoped transaction query and display, plus a return link to PC Review. Test it in production after the release; reviewers should verify original image and PDF loading and the print sequence. An expired source URL is reported as unavailable; the report uses the same source URL as PC Review and does not relocate media.

## Follow-up setup ownership

Fold the durable decisions into an enhanced ERP Setup page (building on Excel Setup): employee phone-source verification, effective-dated reviewer-to-employee delegation, PM/review-group ownership, the eventual authoritative advance/payment source and cycle rule, accounting status display rules, and permission boundaries. Keep those settings as versioned ERP records with validation and audit history. Excel workbook adapters remain consumers of setup data, not a second authority. This is a follow-up design item; the current report reads today's existing routing/scope files and does not introduce a new settings schema.
