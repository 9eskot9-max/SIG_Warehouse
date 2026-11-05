# Handoff — Codex active by owner direction

Codex is the active repository agent at the owner’s direction. The owner can change the holder at any moment; Claude is not currently in the rotation.

| Field | Value |
|---|---|
| Baton holder | **Codex** (owner-directed; Claude inactive) |
| Next holder | **Codex, unless the owner reassigns** |
| Branch | `codex/sig-personal-home-v16` (production source) |
| Latest deployed source commit | `09c0f72496e06ba59f5f21816663177fcba1971d` live on `neosys.frappe.cloud`, bench `bench-51251-000036-f1f`; build pipeline `8ruifr103j`; site update Pull Success (Cloud dashboard; ID not exposed) |
| Open items for the next holder | Codex remains active; no baton handoff or message to Claude is needed unless the owner reassigns the work. PR #89 is deployed and `PEOPLE_MODEL_ACTIVE` is ON. Excel Setup's configured Operations family membership and dated Planner team leadership/identity now feed the live People/Planner adapters; family defaults apply where no Project exception exists. Current enabled membership rows match the existing Operations roster, and Planner has six flexible teams with current leader history. Do not assume every user’s ERP roles are correct: role/profile and User Permission alignment plus actual-user acceptance were NOT TESTED. Next permission acceptance: for each newly included PM/co person, open the Workbench in a fresh authenticated session and verify intended categories and linked records load; confirm a person outside those audiences is denied; confirm unaffected Warehouse/Finance/HR navigation remains as before. No native Role/DocType ptypes, Role Profiles or User Permissions were changed by PR #89. The Frappe Cloud Press API 403 is recorded under `PERM-20261101-04`; no repair attempted. Family-wide team defaults are active; add Project exceptions after PM confirmation. Planner may assign any eligible DC/Incident site and team is a planning reference. No code for the weekly PM check was included. Functional and persona tests were skipped per owner instruction; log acceptance as NOT TESTED. Secure document upload, payroll/User/Finance follow-on actions and onboarding-control linkage remain open. Reconcile Faizan's phone collision before any intake/message or record change. |
| Waiting on the owner | Weekly PM check per project family (families, recipients and project mapping). Six legacy Payment Entry drafts. 98 draft petty-cash journals. |

## Rules

1. Read this file first. Codex is active at the owner's direction. Claude is not in the current rotation. The owner may reassign the active agent at any time; no separate baton message is required.
2. Keep this table current when the owner changes the active agent or when a release changes the deployed revision. Do not hand work to Claude unless the owner explicitly reassigns it.
3. One move = one task the owner asked for, finished and pushed. Do not start a second task inside a move.
4. Never deploy, schedule a Frappe Cloud update, or edit the Cloud benches unless the owner told you to in this move.
5. Add a row to `docs/DEPLOY_LOG.md` for every Cloud action, in the same last commit.

## Employee configuration and access work

The deployed People routing revision 1 configures the existing employee work-group and petty-cash reviewer matrix, but does not migrate exact Employee Project assignments or replace the hardcoded Operations roster, visibility and display aliases. The next implementation stage remains a reviewed, employee-ID-based migration with access/persona acceptance; see the ERP/HR masters, implementation plan, final release checklist and `docs/PEOPLE_CONFIGURATION_RECONCILIATION.md`.

Stage-one PC routing freeze deployed 5 November 2026. The People routing editor is read-only while its publication endpoint protects existing clearance permissions. PR #87 deployed configurable Excel Setup structure and Operations/Planner adapters. PR #89 then enabled the People model and Planner continuity using the configured family/team records. The production Excel Setup currently has nine enabled Operations family memberships matching the existing roster, six Planner teams with current leaders, and no Project-specific team overrides; family defaults therefore apply. No native ERP roles/permissions or employee/project transactions were changed. Actual-user permission acceptance remains NOT TESTED and is recorded in the deployment log.
