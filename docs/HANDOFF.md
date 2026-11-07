# Handoff — Codex active by owner direction

Codex is the active repository agent at the owner’s direction. The owner can change the holder at any moment; Claude is not currently in the rotation.

Codex deployed PR #99, the initial SNB movement router, to production on 7 November 2026. It saves accountant decisions but does not yet create or post JE/PE drafts; see `docs/SNB_MOVEMENT_ROUTER.md` for remaining work and acceptance gates. Codex remains the active agent; production releases remain owner-controlled.

| Field | Value |
|---|---|
| Baton holder | **Codex** (owner-directed; Claude inactive) |
| Next holder | **Codex, unless the owner reassigns** |
| Branch | `codex/sig-personal-home-v16` (production source) |
| Latest deployed source commit | `8b4ebe53eba55ecb1094df1f74fc2ea8cda62664` live on `neosys.frappe.cloud`, bench `bench-51251-000040-f1f`; only SIG Warehouse was updated on 7 November 2026. |
| Open items for the next holder | Codex remains active; no baton handoff or message to Claude is needed unless the owner reassigns the work. PR #99 is deployed: the SNB Movement Router is a review-only foundation and does not create JE/PE drafts or post accounting entries. Its route rendered in the Administrator session with an empty queue. The Accounts User/Accounts Manager fresh-session acceptance and repeat-migration checks are NOT TESTED. Accounts roles still cannot read Employee, so employee-linked decisions fail closed; do not broaden Employee access without a separate reviewed change. AM snapshot synchronization, verified draft creation/readback, duplicate recovery, account-pairing review, invoice allocation, and route-specific validations remain incomplete. PR #89's People routing remains live; its role/profile acceptance remains NOT TESTED as previously recorded. See `docs/SNB_MOVEMENT_ROUTER.md` and the 7 November row in `docs/DEPLOY_LOG.md`. |
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
