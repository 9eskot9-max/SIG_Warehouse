# Deployment and branch map

Last verified from Frappe Cloud and GitHub: 5 November 2026. This is a dated read-back; recheck before every release.

See also: [Deploy log](DEPLOY_LOG.md) for every production action, and [Codex and Claude coordination](CODEX_CLAUDE_COORDINATION.md) for who does what.

## Production snapshot (5 November 2026)

- Site: `neosys.frappe.cloud` — Active, in Frappe Cloud bench group `bench-51251` (the latest read-back did not return the exact bench ID).
- Latest site update: `eu6iefujp8` — Success; pipeline `btua0gfko3`; pre-deploy backup completed (dashboard timestamp 2026-11-05 03:46; backup ID not returned in the recorded read-back).
- Frappe `16.54.0` `2fcb939`; ERPNext `16.53.0` `9cd11b1`; HRMS `16.53.0` `b12d935`. These apps were unchanged.
- SIG Warehouse installed revision: `codex/sig-personal-home-v16` at `5c98091c409dfd714d77d93871619988ce915304`. Only SIG Warehouse was built and updated; Frappe, ERPNext and HRMS were unchanged.
- Excel Setup now contains the People sections. The existing 58-row employee work-group/PC-routing matrix and six reviewer rosters were published in `SIG People Routing Setup` as revision 1 (`people-setup-1`); the two approved Incident additional-group exceptions are retained. Read-back confirms the persisted revision. No Employee, User, exact Project assignment, Account, Journal Entry or petty-cash transaction records were created or changed.
- The Excel Setup route rendered in an authenticated session and showed the existing People routing data. The previously observed People editor showed the old read-only UI, potentially from a stale session. The deployed source includes routing publication/recovery and uses the published matrix for PC clearance authorization; the separate operational team model gate remains false. Permission snapshot diff: no role-row grants/removals and one expected read-only `history_json` field addition. No functional tests were run. Migration repeatability and fresh-session HR/Projects/Finance/Operations persona acceptance are **NOT TESTED**. Candidate onboarding, secure upload, payroll/User/Finance follow-on actions and onboarding-control linkage remain incomplete. See PR #83 and the [deploy log](DEPLOY_LOG.md).
- ZATCA Integration, live: `codex/v16-b2b-clearance-parity` at `a8f9fb5`.
- SIG WhatsApp, live: `v16-migration` at `9bfd1bd`. SIG QR Design, live: `v16-migration` at `39ecff6`.
- Trial: the site `neosys-v16-trial.frappe.cloud` has left the Frappe Cloud site list. Its bench `bench-51214-000014-f28f3` is still Active with no sites. Removal awaits owner confirmation.

## Branch map (SIG Warehouse, GitHub `9eskot9-max/SIG_Warehouse`), checked 4 November 2026

| Branch | Role today | Relevant revision | Live on production? |
|---|---|---|---|
| `codex/sig-personal-home-v16` | Production source configured in Frappe Cloud. | `5c98091c409dfd714d77d93871619988ce915304` installed; latest source and installed hashes match. | Pipeline `btua0gfko3` and site update `eu6iefujp8` succeeded; site is Active. PC routing publication and matrix-based authorization code is deployed; the separate operational team model remains gated. Functional workflows, migration repeatability and non-admin persona acceptance are NOT TESTED. |
| `main` | GitHub default; not the v16 build source. | `f32c7ea` | Its sole ahead commit is patch-equivalent to the intake guide/UOM list-view change already represented in production. No unique source patch remains to port from current `main`. |
| `v16-migration` | Former v16 staging; no longer built. | `5e63f85` | No unique commits ahead of production. |

PR `#74` (workbench card tints, RTL-aware card accents and the Codex-only handoff update) was merged as `e7365d1` and deployed to bench `000028`. PR `#72` and earlier releases are historical. Earlier PRs `#71`, `#64`, `#65` and `#66` remain separate historical drafts; their closure is still pending owner review.

The ERP integration and HR automation masters on the production-source branch describe the deployed onboarding workflow and its open follow-ups. Frappe and HRMS were not updated.

## Warnings

- **Any push to the production branch reaches the next Frappe Cloud build**, because the build takes the branch HEAD. Review a commit before it lands on that branch, and confirm the HEAD before building.
- A GitHub push alone does not deploy. Deployment is a Frappe Cloud build followed by a site update.
- Keep one production branch. Do not maintain the same fix on `main` and on the production branch.

## Proposed branch policy (4 November 2026, awaiting owner approval; not yet adopted)

1. One production branch, named `production/v16`, the GitHub default, protected: pull requests only, no force push, a review required.
2. Before renaming or deleting `main`, tag its current history and review any commits unique by both ancestry and patch. The current comparison finds one ancestry-only commit, already patch-equivalent on production; make no branch deletion or rename until the owner approves.
3. Every change starts as a topic branch from production (`codex/<topic>` or `feature/<topic>`). One open PR per topic. Merge to production, then delete the branch.
4. One writer per branch. Codex and local sessions never push to the same branch at the same time. Use `--force-with-lease` only on your own branches.
5. Before each build, confirm the production HEAD matches the merged PR and that the commit list is the expected one.
6. Session rules go in `CLAUDE.md` and `AGENTS.md` in this repository, so Codex and Claude start from the same rules.

## Release sequence

1. Compare the proposed changes with the exact production app hashes and check for overlapping PRs/patches.
2. Complete [Final release checklist](FINAL_RELEASE_CHECKLIST.md), including the permission baseline, migration writers, repeatability and persona coverage.
3. Push the release to the configured app branch. A GitHub push alone does not deploy.
4. In Frappe Cloud, build the bench/app revision and wait for a terminal result.
5. Run the site update/migration and wait for a terminal result.
6. Confirm the site Active, app hashes, migration state and affected Desk routes.
7. Complete actual-user acceptance and attach evidence. Record any NOT TESTED checks as open.

## Where deployment lives

This app uses Frappe Cloud bench builds and site updates. There is no app-specific GitHub Actions deployment workflow in this repository. Discoverable release instructions are in scripts/deploy/README.md; credentials belong in an approved secret store or Cloud settings and must never be committed. Do not run one-off local scripts against production unless their source, target and permissions have been reviewed under the checklist.
