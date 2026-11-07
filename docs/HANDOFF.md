# Handoff — Codex active by owner direction

Codex is the active repository agent at the owner’s direction. The owner can change the holder at any moment; Claude is not currently in the rotation.

Codex deployed PR #104 on 7 November 2026, adding family-shared weekly comments to Field Planner. The installed SIG Warehouse revision is `88faf84585ab7b4aaf09c013160abcdf0978aa6b` on bench `bench-51251-000043-f1f`. A retroactive PR #103 deployment row and the PR #104 release row are in `docs/DEPLOY_LOG.md`. Field Planner API family reads passed as `9eskot9@gmail.com` (ERP Admin/System Manager), but client-side route rendering and fresh Operations persona acceptance remain NOT TESTED. Codex remains the active agent; production releases remain owner-controlled.

| Field | Value |
|---|---|
| Baton holder | **Codex** (owner-directed; Claude inactive) |
| Next holder | **Codex, unless the owner reassigns** |
| Branch | `codex/sig-personal-home-v16` (production source) |
| Latest deployed source commit | `88faf84585ab7b4aaf09c013160abcdf0978aa6b` live on `neosys.frappe.cloud`, bench `bench-51251-000043-f1f`; PR #104; only SIG Warehouse was updated on 7 November 2026. |
| Open items for the next holder | Field Planner family comment API reads pass as the ERP Admin/System Manager API identity; client-side route rendering and fresh-session checks for Projects User, Projects Manager and SIG Field Ops remain NOT TESTED. The existing Page roles and Site Cycle read gate still govern access. PR #101 Bank Movement Router remains review-only and does not create JE/PE drafts; actual Accounts User/Manager workflows, outside-role behavior, Arabic/English rendering, AM snapshot sync, verified draft creation/readback, duplicate recovery, account pairing, invoice allocation and route-specific validation remain open. PR #89 People-routing role/profile acceptance remains NOT TESTED. See `docs/DEPLOY_LOG.md` rows for PR #103 and #104 and `docs/SNB_MOVEMENT_ROUTER.md`. |
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
