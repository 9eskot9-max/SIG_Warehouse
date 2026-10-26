# PC receipt clearance and funding guard regression

## Failure and cause

On 2026-10-26 the in-app PC Review banner confirmed impersonation of
`arshad.ahmed@sigtele.com`. The console rejection at
`2026-10-26T11:16:07.963Z` reached `confirm_receipt` / `Journal Entry.insert`,
then failed in `pc_funding.validate_journal_entry` with “Only Finance can
designate a Journal Entry as petty-cash funding.”

Frappe v15 populates new Employee Link fields from the caller's Employee User
Permission. Arshad's single Employee restriction supplies `custom_pc_employee`
even when the Journal Entry is a receipt-clearance draft with top-up unchecked.
The original hook treated every nonempty funding field on a new document as an
explicit funding edit. Admin/Finance callers did not expose that regression.

The PC Review call wrapper also relied on the argument to `frappe.call.error`.
Frappe v15's 403 handler invokes that callback without an argument; the page
therefore lost the server error and displayed “HTTP unknown.”

PR #51's Company-select diagnosis was incorrect. Employee, Employee Self Service
and Projects User already grant Arshad Company read, which implies select.
Every enabled SIG PC Clearance role holder in the before snapshot already has
Company read/select from another existing role. The Company grant is removed by
a guarded migration that verifies the full custom matrix before deleting only
the redundant SIG PC Clearance select-only row.

## Resulting behavior

- New funding fields are compared with Frappe's actual caller defaults; blank
  values and unchecked Check representations are normalized.
- The existing receipt-scoped native Journal Entry create gate remains active.
- Explicit changes to any funding metadata, and all marked top-ups, require
  Finance. Valid Finance funding still runs the accounting and source checks.
- PC Review reads failures from the returned jqXHR so a 403 retains its actual
  message and status.

No Page, Workspace, Role Profile, User role, Employee scope, User Permission,
Journal Entry permission, or funding field contract is changed. The only
declared permission removal is the redundant Company row introduced by PR #51.

## Acceptance record

Before/after evidence directory:
`ERPNext/backups/permission_release_pc_funding_guard_20261026/`.

- API preflight and complete before access/default snapshot: PASS.
- Reviewer funding-default reproducer plus existing PC draft boundary tests:
  PASS, 62 Python cases. Includes the combined confirmation and funding hook.
- Frappe v15 403 callback / real error message regression: PASS.
- Company matrix restore, repeat execution, and drift rejection simulation: PASS.
- Python/JavaScript syntax and whitespace: PASS.
- Actual Arshad confirmation before correction: FAIL (console evidence above).
- Actual Arshad confirmation after deployment: NOT TESTED until repeated by an
  authorized reviewer; do not claim workflow acceptance from API or admin reads.
- Staging migration twice: NOT TESTED; no staging site is available.
- Basic access for the other registered audiences and actual Finance funding
  workflow: NOT TESTED; their matrices must match the declared baseline after
  migration. Offline checks are not actual-persona acceptance.

The governing policy is the mandatory permission acceptance section in
`ERPNext/docs/erpnext_final_implementation_plan.md#permission-regression-mandate`.
The incident remains open until the actual reviewer reproducer passes.
