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

Draft PR #79 adds initial People tables and partial editing of project assignments and reporter mappings. The local draft also adds a System Manager-controlled editor for employee work groups, PC review groups, additional exceptions and reviewer lists. It initializes from the code-owned matrix, stores a published routing revision separately from workbook data, and makes existing PC consumers read that revision after publication. This is **not deployed or accepted**. The editor does not reconcile AM beneficiaries or create/link custody accounts; existing Employee custody links are displayed only where permitted. Excel Setup page role access for HR, onboarding actions, reporter creation, migration/repeatability, independent routing equivalence, rollback/history and actual-persona acceptance remain unfinished. No employee, project, account or petty-cash records have been altered by this draft.

## Owner-directed paste and publication

The prepared JSON package contains the existing 58 Employee IDs, work groups, PC review groups, the two additional-group exceptions and all six existing reviewer groups. It is generated from `sig_warehouse/sig_warehouse/pc_review_assignments.json`; it does not assert specific ERP Project/PO assignments or contain AM beneficiary data. After the feature is available, a System Manager can select **Employee project groups / petty cash**, choose **Paste existing routing**, paste the package, review the staged rows and reviewers, then choose **Save and publish**. Pasting only stages the values in the browser. Publication is the separate action that makes the new routing revision available to PC consumers. The current file remains the fallback until a first revision is published. No automatic production import occurs during deployment.
