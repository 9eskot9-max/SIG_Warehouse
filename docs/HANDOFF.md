# Handoff — Codex active by owner direction

Codex is the active repository agent at the owner’s direction. The owner can change the holder at any moment; Claude is not currently in the rotation.

PR #120 was deployed on 10 November 2026. The installed SIG Warehouse revision is `ea9daba8dbc8e5753bcf7cfdd4726bc1c8d3f470` on bench `bench-51251-000056-f1f`. The Stock Entry print renderer for STE-2026-1072 returned valid HTML; PDF file completion and dispatch queue rendering/warehouse-user acceptance remain NOT TESTED. The permission comparison found no additions or removals. See the latest row in `docs/DEPLOY_LOG.md` for Cloud job IDs and evidence. The TX Manager interface is running locally at `127.0.0.1:4317`; this source has no separate remote deployment target. Codex remains the active agent; production releases remain owner-controlled.

| Field | Value |
|---|---|
| Baton holder | **Codex** (owner-directed; Claude inactive) |
| Next holder | **Codex, unless the owner reassigns** |
| Branch | `codex/sig-personal-home-v16` (production source) |
| Latest deployed source commit | `ea9daba8dbc8e5753bcf7cfdd4726bc1c8d3f470` live on `neosys.frappe.cloud`, bench `bench-51251-000056-f1f`; PR #120; only SIG Warehouse changed in this release. |
| Open items for the next holder | Warehouse-user acceptance and dispatch queue route/search rendering for PR #120 remain NOT TESTED; PDF download completion is also NOT TESTED. Fresh Accounts User/Manager workflow, linked PO/PI selection, Arabic/English rendering, migration repeatability and outside-role denial remain NOT TESTED; the SNB router remains review-only and does not create or submit Payment Entries. TX Manager is local to this workstation. Field Planner fresh Operations persona acceptance and PR #89 People role/profile acceptance remain NOT TESTED. See `docs/DEPLOY_LOG.md` and `docs/SNB_MOVEMENT_ROUTER.md`. |
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
