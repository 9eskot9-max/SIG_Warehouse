# Handoff — Codex active by owner direction

Codex is the active repository agent at the owner’s direction. The owner can change the holder at any moment; Claude is not currently in the rotation.

| Field | Value |
|---|---|
| Baton holder | **Codex** (owner-directed; Claude inactive) |
| Next holder | **Codex, unless the owner reassigns** |
| Branch | `codex/sig-personal-home-v16` (production source) |
| Latest deployed source commit | Target `12a96c6933bb737ff254bd338889236120c44cfb` (PR #93) on `neosys.frappe.cloud`, bench `bench-51251-000037-f1f`; build pipeline `89bouci9b8`; site update `bh2jd1671m` Success. Cloud Apps page still shows old SIG Warehouse hash `09c0f72`; resolve this read-back discrepancy. |
| Open items for the next holder | Codex remains active; no baton handoff or message to Claude is needed unless the owner reassigns the work. PR #93 is deployed: Field Planner now shows each PM three weekly comment fields (Last week summary, This week plan, Comment on ERP plan), and Excel Setup retains historical Planner leader and Builder/profile compatibility records outside the normal editing flow. Comment inputs were disabled in the checked session because no unique active Employee is linked; actual PM role, linked Employee and comment-save acceptance remain NOT TESTED. Cloud Apps displays stale SIG Warehouse hash `09c0f72` even though pipeline `89bouci9b8` and update `bh2jd1671m` succeeded and the Field Planner route renders the new section; confirm installed revision by an authoritative read. No comment or setup data was saved. Continue prior open items only as requested: actual-user acceptance for People-model/Workbench visibility, PM-confirmed Project exceptions, secure document upload, payroll/User/Finance follow-on actions, onboarding-control linkage, and reconciling Faizan's phone collision before any intake/message or record change. |
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
