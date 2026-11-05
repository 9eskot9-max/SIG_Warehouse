# Employee project group and petty cash — intended scope

The owner has clarified that an employee's operational project/work group (for example Capex or Incident) and petty-cash review routing should be configured together in the existing Excel Setup page. Project cycles and the Field Planner are separate workflows; do not make their setup a prerequisite to assigning an employee to an operational group or routing petty cash.

## Employee setup

One employee-oriented row should show the Employee, operational project/work group, petty-cash review group and any explicit additional review groups, the employee's custody-account link, and relevant reporting contact status. The operational group supplies the default petty-cash review group. Show any approved exception explicitly and do not silently replace it when a group changes. HR/Operations owns the operational assignment; Finance owns the custody account and reviews any routing exceptions. Each section enforces its existing record permissions.

## Existing data and current consumers

The current `pc_review_assignments.json` contains 58 employee rows, their `work_group` and `pc_review_group`, additional review groups where configured, and the reviewer roster for Capex, Incident, Colocation, Warehouse, General and Unassigned. `pc_review_routing.load_matrix()` supplies `pc_task_queue` and `pc_journal`; it is currently code-owned. The new configuration must start by importing and reconciling those exact rows and reviewers, preserving approved exceptions, unresolved sender fallback, exclusion of self-review, and all current permissions. Then switch the consumers to the same published setup source; changing a displayed row alone is not integration.

An operational group such as Capex may contain multiple ERP Projects/POs. A specific Project link, where required, is additional detail and must not be guessed from the group. The employee's verified `custom_custody_account` is the finance account anchor; do not create a ledger or post a transaction merely because an operational group was selected.

## Separate workflows

- Project cycles describe site work and evidence, not employee membership or petty-cash reviewer setup.
- Field Planner's team roster and position describe operational scheduling and check-ins. Its existing setup and consumer remain independently governed; the employee group may be displayed as context when appropriate.
- Candidate onboarding, Employee readiness, reporter mappings, User access and payroll appear in the same setup experience subject to their own record permissions and workflow gates.

## Status

PR #79 is deployed as SIG Warehouse `4d39efa` on `neosys.frappe.cloud`, bench `bench-51251-000030-f1f`. The Excel Setup route rendered in an authenticated Administrator session, and its People section displayed **Employee project groups / petty cash** and **Paste existing routing**. The 58-row existing matrix and six reviewer rosters were pasted and published as `SIG People Routing Setup` revision 1 (`people-setup-1`). The two approved Incident additional-group exceptions are preserved. This makes the existing PC consumers read the published configuration; the effective core employee group and reviewer mappings match the previous source. No Employee, User, exact Project assignment, Account, Journal Entry or petty-cash transaction records were created or changed. This is an Administrator route/readback only: functional behavior, migration repeatability, non-admin HR/Projects/Finance access and complete persona acceptance remain **NOT TESTED**. AM beneficiaries/custody accounts, secure onboarding, reporter creation, HR page access, payroll/User actions, and full history/rollback remain unfinished.

## Owner-directed paste and publication

The locally prepared JSON package in `D:/erp/outputs/people-setup-existing-routing.json` contains the existing 58 Employee IDs, work groups, PC review groups, the two approved additional-group exceptions and all six existing reviewer groups. It does not assert ERP Project/PO assignments or contain AM beneficiary data. On 4 November 2026, the System Manager pasted it into **Employee project groups / petty cash**, reviewed the rows and reviewers, and selected **Save and publish**. The ERP API returned revision 1 and `people-setup-1`; the code-owned matrix remains the fallback if the persisted configuration is absent. This is initial source migration only; no financial transaction was created or submitted.
