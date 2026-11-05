# Handoff — Codex active by owner direction

Codex is the active repository agent at the owner’s direction. The owner can change the holder at any moment; Claude is not currently in the rotation.

| Field | Value |
|---|---|
| Baton holder | **Codex** (owner-directed; Claude inactive) |
| Next holder | **Codex, unless the owner reassigns** |
| Branch | `codex/sig-personal-home-v16` (production source) |
| Latest deployed source commit | `8fed927f129582bdbaaffdce610c6ac5133a5d8a` live on `neosys.frappe.cloud`, bench group `bench-51251` (site Active; exact bench ID not returned); build `dp28e232gl`, site update `e6srf08j4p` |
| Open items for the next holder | Codex remains active; no baton handoff or message to Claude is needed unless the owner reassigns the work. PR #85 is deployed: routing revision 2 maps the stale Obed ID to active Employee `Mohammed Obed Shareef` and preserves prior routing history. The scope preview now succeeds; it reports 11 additions and 11 removals against the static baseline from the identity rebind. Permission matrix snapshot diff is 0 role-row removals / 0 grants. Actual-user receipt workflow, migration repeatability and HR/Projects/Finance role acceptance remain NOT TESTED. The operational People model remains gated; employee/project/team/family configuration and Operations/Planner activation remain future work. Secure document upload, payroll/User/Finance follow-on actions and onboarding-control linkage remain open. Reconcile Faizan's phone collision before any intake/message or record change. |
| Waiting on the owner | Weekly PM check per project family (families, recipients and project mapping). Six legacy Payment Entry drafts. 98 draft petty-cash journals. |

## Rules

1. Read this file first. Codex is active at the owner's direction. Claude is not in the current rotation. The owner may reassign the active agent at any time; no separate baton message is required.
2. Keep this table current when the owner changes the active agent or when a release changes the deployed revision. Do not hand work to Claude unless the owner explicitly reassigns it.
3. One move = one task the owner asked for, finished and pushed. Do not start a second task inside a move.
4. Never deploy, schedule a Frappe Cloud update, or edit the Cloud benches unless the owner told you to in this move.
5. Add a row to `docs/DEPLOY_LOG.md` for every Cloud action, in the same last commit.

## Employee configuration and access work

The deployed People routing revision 1 configures the existing employee work-group and petty-cash reviewer matrix, but does not migrate exact Employee Project assignments or replace the hardcoded Operations roster, visibility and display aliases. The next implementation stage remains a reviewed, employee-ID-based migration with access/persona acceptance; see the ERP/HR masters, implementation plan, final release checklist and `docs/PEOPLE_CONFIGURATION_RECONCILIATION.md`.

Stage-one PC routing freeze deployed 5 November 2026. The People routing editor is now read-only and its publication endpoint rejects changes until petty-cash clearance permissions are aligned with published routing. Existing routing and permissions were preserved. This does not migrate employee/project/team/family assignments or replace the hardcoded Operations roster. Keep the family/team/member model, 5G/Colocation aliases, live employee-data reconciliation and permission/persona acceptance as later work. The deployment log records release IDs and remaining acceptance.
