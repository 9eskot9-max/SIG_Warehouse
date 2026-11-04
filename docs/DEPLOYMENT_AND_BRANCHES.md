# Deployment and branch map

Last verified from Frappe Cloud and GitHub: 4 November 2026, Asia/Riyadh. This is a dated read-back; recheck before every release.

See also: [Deploy log](DEPLOY_LOG.md) for every production action, and [Codex and Claude coordination](CODEX_CLAUDE_COORDINATION.md) for who does what.

## Production snapshot (4 November 2026)

- Site: `neosys.frappe.cloud` — Active, on Frappe Cloud bench group `neoweb-v16`.
- Site bench: `bench-51251-000028-f1f`; bench group `neoweb-v16` is Active.
- Latest site update: `4t75g1tbge` — Success, 4 November 2026, 8:03 PM Cloud local time (17:03 UTC). It followed pipeline `8pnn6ehs5v` and the pre-release backup `8v2o1su190`.
- Frappe `16.54.0` `2fcb939`; ERPNext `16.53.0` `9cd11b1`; HRMS `16.53.0` `b12d935`. Frappe and HRMS updates are listed by Frappe Cloud as available and are **not applied**.
- SIG Warehouse source installed by the latest update: `codex/sig-personal-home-v16` at `e7365d1` (full hash `e7365d1d7f9edbb6dbb5835e75ec1f061e45578b`) on `bench-51251-000028-f1f`. Cloud reports pipeline `8pnn6ehs5v` and site update `4t75g1tbge` as Success and the site Active. The source branch now has a later documentation-only head; this release installed `e7365d1`.
- Candidate Intake, Employee Project Assignment, Custom Setup and Finance/HR/Warehouse card illustrations and card tints are deployed. No employee intake, Employee, User, payroll, bank/account or project-assignment records were created or changed; no WhatsApp messages were sent. Secure upload remains unimplemented. Finance, HR and Warehouse pages rendered with the updated card styling after refresh. Functional and actual-user persona checks are **NOT TESTED** per the owner's instruction for this release.
- ZATCA Integration, live: `codex/v16-b2b-clearance-parity` at `a8f9fb5`.
- SIG WhatsApp, live: `v16-migration` at `9bfd1bd`. SIG QR Design, live: `v16-migration` at `39ecff6`.
- Trial: the site `neosys-v16-trial.frappe.cloud` has left the Frappe Cloud site list. Its bench `bench-51214-000014-f28f3` is still Active with no sites. Removal awaits owner confirmation.

## Branch map (SIG Warehouse, GitHub `9eskot9-max/SIG_Warehouse`), checked 4 November 2026

| Branch | Role today | Relevant revision | Live on production? |
|---|---|---|---|
| `codex/sig-personal-home-v16` | Production source configured in Frappe Cloud. | `e7365d1` installed on bench `000028`; branch head `0d7fd9e` is later documentation-only work. | Pipeline `8pnn6ehs5v` and site update `4t75g1tbge` succeeded; site is Active. Workbench pages rendered; functional and persona acceptance are NOT TESTED. |
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
