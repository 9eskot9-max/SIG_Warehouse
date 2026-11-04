# Deployment and branch map

Last verified from Frappe Cloud and GitHub: 4 November 2026, Asia/Riyadh. This is a dated read-back; recheck before every release.

See also: [Deploy log](DEPLOY_LOG.md) for every production action, and [Codex and Claude coordination](CODEX_CLAUDE_COORDINATION.md) for who does what.

## Production snapshot (4 November 2026)

- Site: `neosys.frappe.cloud` — Active, on Frappe Cloud bench group `neoweb-v16`.
- Site bench: `bench-51251-000027-f1f`; bench group `neoweb-v16` is Active.
- Latest site update: `d3n6varijr` — Success, 4 November 2026, 7:19 PM Riyadh. It followed pipeline `dvq0lo1gs2` and the pre-release backup `8v2o1su190`.
- Frappe `16.54.0` `2fcb939`; ERPNext `16.53.0` `9cd11b1`; HRMS `16.53.0` `b12d935`. Frappe and HRMS updates are listed by Frappe Cloud as available and are **not applied**.
- SIG Warehouse source deployed by the latest update: `codex/sig-personal-home-v16` at `7a37c9a` (full hash `7a37c9abf2167ff1d7c4ab9ef04c5c5c22305851`) on `bench-51251-000027-f1f`. Press API read-back reports the pipeline and update as Success and the site Active on this bench. The pipeline detail card still showed “queued” during read-back; the API and installed bench record showed the successful release.
- Candidate Intake, Employee Project Assignment, Custom Setup and Finance/HR/Warehouse card illustrations are now deployed. No employee intake, Employee, User, payroll, bank/account or project-assignment records were created or changed; no WhatsApp messages were sent. Secure upload remains unimplemented. Route, migration rehearsal and actual-user persona checks are **NOT TESTED** per the owner's instruction for this release.
- ZATCA Integration, live: `codex/v16-b2b-clearance-parity` at `a8f9fb5`.
- SIG WhatsApp, live: `v16-migration` at `9bfd1bd`. SIG QR Design, live: `v16-migration` at `39ecff6`.
- Trial: the site `neosys-v16-trial.frappe.cloud` has left the Frappe Cloud site list. Its bench `bench-51214-000014-f28f3` is still Active with no sites. Removal awaits owner confirmation.

## Branch map (SIG Warehouse, GitHub `9eskot9-max/SIG_Warehouse`), checked 4 November 2026

| Branch | Role today | Relevant revision | Live on production? |
|---|---|---|---|
| `codex/sig-personal-home-v16` | Production source configured in Frappe Cloud. | `7a37c9a` (installed on bench `000027`) | Pipeline `dvq0lo1gs2` and site update `d3n6varijr` succeeded; site is Active. Route and persona acceptance are NOT TESTED. |
| `main` | GitHub default; not the v16 build source. | `f32c7ea` | Its sole ahead commit is patch-equivalent to the intake guide/UOM list-view change already represented in production. No unique source patch remains to port from current `main`. |
| `v16-migration` | Former v16 staging; no longer built. | `5e63f85` | No unique commits ahead of production. |

PR `#72` (employee onboarding/project setup and the three-workbench illustration refresh) was merged to `codex/sig-personal-home-v16` as `7a37c9a` and deployed. Earlier PRs `#71`, `#64`, `#65` and `#66` remain separate historical drafts; their closure is still pending owner review.

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
