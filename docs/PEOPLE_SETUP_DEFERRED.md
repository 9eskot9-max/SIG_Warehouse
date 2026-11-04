# People setup inside Excel Setup — deferred implementation

**Status: deferred, not implemented.** This records the owner's direction on 4 November 2026. No production records, configuration or permissions were changed. The read-only preview prototype was removed before upload because it did not meet the requested configurable workflow.

## Agreed direction

Extend the existing **Excel Setup** page and its Setup list dropdown. Use the page's current table editor, ERP lookups, add/import, validation, revision history and explicit publish interaction as the interaction model. Keep Workbook Setup in the page. Add People sections to that same interface, with each section reading and writing through the existing owning records and permissions. Do not create a second employee registry or place confidential HR/finance details in the workbook bundle.

## Sections to stage

| Section | User view | Existing source and required behavior |
|---|---|---|
| Employees | Separate employee table and employee detail view. | Native Employee is canonical. Link to the native Employee form for governed HR changes; show only permitted fields. |
| Project assignments | Employee relationship table, surfaced from each employee and searchable across employees/projects. | `SIG Employee Project Assignment` for dated employee/project/role records. First reconcile verified existing assignments; never infer a Project from a Capex/Incident reviewer group or Field Planner roster. Revisit the current one-active-Team-Leader-per-Project rule with actual operating practice. |
| Candidate onboarding | Separate workflow entry. | `SIG Candidate Intake`; restricted HR data, consent, duplicate phone checks, explicit messages/review and explicit Employee conversion. Do not treat the setup table as a replacement for that workflow. |
| Employee readiness | Integrated status panel and exceptions with drill-through. | Existing `SIG Employee Onboarding` controls. Display its current checks and their results; do not create parallel checklist rows. |
| User access | Employee detail status and gated access action. | Native User and Role Profile. Keep User provisioning and Role Profile changes under IT/HR controls; saving a profile can rederive roles. |
| Payroll | Restricted employee detail summary and gated payroll action. | Native Salary Structure Assignment. Candidate proposed salary must not auto-create payroll records. |
| Field reporting | Employee phone/reporting section, plus a mapping exceptions table. | `SIG Field Reporter Map` used by field feeds and site visits. Resolve phone ownership and duplicates before changing mappings. |
| PC review groups | Employee's current petty-cash reviewer scope and group membership, editable after review. | `sig_warehouse/pc_review_assignments.json` is the current code-owned source (58 employees; routing version `pc-review-2026-11-02-v2`) consumed by `pc_review_routing`, `pc_task_queue` and `pc_journal`. Preserve current routing exactly through preview/reconciliation and switch every consumer atomically to the published source. Group scope is not ERP Project membership and grants no permission. |
| Field teams | Existing roster remains visible to its current operators. | The Excel Setup `teams` dataset feeds the Field Planner and is excluded from RV80/SIGPC exports. Preserve its current contract unless separately migrated and verified. Do not equate a field team with a person's Project assignment. |
| Workbook | Existing workbook sections remain. | Preserve RV80/SIGPC bundle contracts. People, salary, identity, access, bank and reviewer data must never enter workbook exports. |

## Data and publish rules

- Show current source records before edit. Resolve Employee IDs, project links and mappings against ERP masters. Match by stable IDs; use names only as labels.
- Before moving the PC roster from JSON, compare all 58 employee rows and reviewer groups and preview additions, changes, missing/inactive employees, duplicate identities and routing results. Keep unknown senders on the existing unassigned fallback. Do not rewrite routing rules in the same step as importing data.
- Use separate permission checks for each section and each write. The Excel Setup role must not grant HR salary, identity, User, payroll or finance access. Candidate Intake and Employee data have separate field-level controls. Verify linked Employee, Project, User and account read access for every audience.
- Keep separate revisions/concurrency guards for independently owned sensitive datasets, or otherwise prove an update to one section cannot overwrite another section's concurrent changes. Maintain audit/source/approver history and make imports idempotent.
- A displayed card or section is navigation/presentation only; it grants no record permission. Do not implement generic write-through JSON that bypasses DocType controllers, workflow transitions or audit fields.

## Delivery sequence

1. Reconcile open Excel Setup PR #71 before merging any overlapping work. Latest owner direction is Codex-only; no message to Claude is needed unless the owner reassigns work.
2. Capture current employee/project/mapping data and permission baselines. Confirm exact existing assignment sources and the operational meaning of roles/groups with HR, Projects and Finance.
3. Build the shared dropdown sections and independent service APIs. Start with non-sensitive relationships and preview-only PC reconciliation; keep the live JSON consumer active until equivalence is proven.
4. Add an import preview and controlled publication for reviewed mappings; cut every consumer over together and retain rollback to the exact old revision.
5. Integrate candidate intake, onboarding status, reporter maps, User and payroll as linked workflows with their owning permissions; never merge all record types into one broad setup document.
6. Complete migration rehearsal, access snapshots and fresh-session persona checks for System Manager, HR Manager, HR User, Projects Manager, Projects User, Finance and relevant operations audiences. Record PASS/FAIL/NOT TESTED. Deploy only under a separate explicit release instruction.

## Not part of this deferred change

No employee, assignment, user, payroll, bank/account, reporter-map or reviewer mapping data was altered. No messages were sent. The earlier read-only prototype was not uploaded. This plan does not mark the existing onboarding implementation as accepted or tested.
