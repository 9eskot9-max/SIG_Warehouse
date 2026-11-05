# Handoff — Codex active by owner direction

Codex is the active repository agent at the owner’s direction. The owner can change the holder at any moment; Claude is not currently in the rotation.

| Field | Value |
|---|---|
| Baton holder | **Codex** (owner-directed; Claude inactive) |
| Next holder | **Codex, unless the owner reassigns** |
| Branch | `codex/sig-personal-home-v16` (production source) |
| Latest deployed source commit | `03acfb94a3fb83775388c74d4012589b05cd4f4f` live on `neosys.frappe.cloud`, bench `bench-51251-000034-f1f`; pipeline `90blge9d6a`, site update `98fkfol28i` |
| Open items for the next holder | Codex remains active; no baton handoff or message to Claude is needed unless the owner reassigns the work. PR #85's Obed routing correction and PR #87's Excel Setup/team behavior code are deployed. The Excel Setup now stages Operations family teams with Project-specific replacement groups and dated Planner team leadership/identity; `PEOPLE_MODEL_ACTIVE` remains OFF, so legacy live routing and Planner roster continue to control. No team configuration was populated or activated. Later work: fill/reconcile family and Project rows, resolve historical cycles with missing/ambiguous ERP Project links, compare effective audiences, then review a controlled activation. Weekly PM snapshots retain the stable team ID; the Planner proposal itself can recalculate. Functional tests and actual-user/persona acceptance were NOT RUN per owner instruction; migration repeatability and route rendering remain NOT TESTED. PR #85 actual-user receipt workflow and the HR/Projects/Finance role workflows remain NOT TESTED. Secure document upload, payroll/User/Finance follow-on actions and onboarding-control linkage remain open. Reconcile Faizan's phone collision before any intake/message or record change. |
| Waiting on the owner | Weekly PM check per project family (families, recipients and project mapping). Six legacy Payment Entry drafts. 98 draft petty-cash journals. |

## Rules

1. Read this file first. Codex is active at the owner's direction. Claude is not in the current rotation. The owner may reassign the active agent at any time; no separate baton message is required.
2. Keep this table current when the owner changes the active agent or when a release changes the deployed revision. Do not hand work to Claude unless the owner explicitly reassigns it.
3. One move = one task the owner asked for, finished and pushed. Do not start a second task inside a move.
4. Never deploy, schedule a Frappe Cloud update, or edit the Cloud benches unless the owner told you to in this move.
5. Add a row to `docs/DEPLOY_LOG.md` for every Cloud action, in the same last commit.

## Employee configuration and access work

The deployed People routing revision 1 configures the existing employee work-group and petty-cash reviewer matrix, but does not migrate exact Employee Project assignments or replace the hardcoded Operations roster, visibility and display aliases. The next implementation stage remains a reviewed, employee-ID-based migration with access/persona acceptance; see the ERP/HR masters, implementation plan, final release checklist and `docs/PEOPLE_CONFIGURATION_RECONCILIATION.md`.

Stage-one PC routing freeze deployed 5 November 2026. The People routing editor is read-only while its publication endpoint protects existing clearance permissions. PR #87 subsequently deployed the configurable Excel Setup structure and Operations/Planner adapters, but the adapter gate remains off pending team data and reviewed cutover. Existing routing, project assignments and employee records were not changed by PR #87. The deployment log records release IDs and remaining acceptance.
