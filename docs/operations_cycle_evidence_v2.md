# Operations cycle evidence rules — 19 October 2026

## Approved behavior

- Site heading: `ZDU004 - 8,640.80 SAR`, with the WO underneath. Omit the separator and amount when no positive evidence-derived gross value exists. Both Operations Workbench and Site Cycles use this layout.
- Four active stages remain Initial, Plan, Handover and Invoicing. Closure is the existing terminal state, outside the active stages.
- TCN + MIR + Visit + Tags advances a cycle to Handover. Alternatively, TCN + MIR + two recorded visits advances it without requiring Tags. Two visits means two accepted visit sessions in the same cycle, including accepted auto-closed visits; it does not mean two messages or two dates.
- Photos are removed from pending work and task counts. Existing photo evidence stays in the history and workbook.
- HO documents or invoice evidence advance to Invoicing. Existing PM decisions and previously reached active stages are preserved as a stage floor. Missing historical evidence never silently demotes them. An old stage-5 label without `terminal=1` cannot close a cycle.
- TCN/MIR/Visit tasks can appear for partial legacy Plan evidence even when Mapping/BOQ evidence is absent. After one visit with TCN/MIR, Tags is the remaining Plan exit task. After Handover starts, supported As-Built work appears. No additional second-visit task or Photos placeholder is manufactured.
- Evidence closes the matching task. Existing cycle closure remains available from the ordinary cycle rows. Age flags pending work; it creates no extra task.

## One rule owner

`cycle_rules.derive_cycle_state` is used by Workbench and Project Progress. The guarded migration embeds that exact function body in the sandboxed evidence writer, so saved stage, dashboard and export use the same rule. It changes only the stage-selection block, retains the existing scope/WO routing, intake authentication, evidence records and business closure behavior, and refuses an unrecognized source layout.

The second visit timestamp comes from the second actual visit in the cycle, not the latest visit, so a third visit does not restart the Handover SLA. Intake uses one bounded query only for multi-visit cycles; the historical migration reads visits once. The existing counters matched all 347 live visit records at the pre-release snapshot, so another visit-count table is unnecessary.

The daily Server Script still referred to `4 - As-Built / asbuilt`; it is corrected to `4 - Invoicing / invoicing`. Existing open cycles have stage anchor, due date and flags reconciled using the same rules and existing SLA settings. Terminal cycles, PM notes and historical evidence are untouched. Re-running the migration is designed to be idempotent.

Excel keeps its existing columns in place and appends numeric WO value (SAR) and Visits. Its task sheet uses the same supported pending work, with no Photos task.

## Pre-release assessment

Site: `neosys.frappe.cloud`, bench `bench-38491-000207-f1f`, production app base `98b3ce4`.

There are 532 open cycles. Stored stages before: Initial 291, Plan 141, Handover 38, Invoicing 62. The old dashboard ignored saved PM progression and showed only 26 in Invoicing.

Proposed stored stages: Initial 266, Plan 158, Handover 41, Invoicing 67. This is 36 forward movements: 23 Initial → Plan, 2 Initial → Handover, 6 Plan → Handover, 5 Handover → Invoicing. No demotions or closures. The full reviewed preview and backups are under `ERPNext/backups/operations_cycle_rules_20261019/` in the parent workspace.

## Permissions and acceptance

Declared permission changes: none. No Page/Workspace/Report role list, DocPerm, Role Profile, User Permission, Employee/project roster or linked-master permission is changed. The new migration writes the two existing Server Scripts and derived operational fields on open SIG Site Cycles. It exposes no new endpoint.

Affected audiences: System Manager, Projects Manager/User, SIG Field Ops (PM/coordinator), and existing Warehouse audiences consuming the derived operational summary. Finance, HR, employee/viewer and integration access baselines remain part of the required snapshot comparison; their transaction behavior is outside this Operations change.

Before snapshot: `permissions.before.json`. Automated rule/migration/Workbench tests, JS checks and actual release checks are recorded in the release evidence. Full Frappe staging migration twice, fresh actual-user workflows for each audience, and Arabic/browser acceptance remain NOT TESTED until explicitly recorded; a successful build or snapshot alone is not acceptance.
