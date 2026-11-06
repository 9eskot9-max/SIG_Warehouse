# Deployment and branch map

Last verified from Frappe Cloud and GitHub: 4 November 2026, Asia/Riyadh. This is a dated read-back; recheck before every release.

See also: [Deploy log](DEPLOY_LOG.md) for every production action, and [Codex and Claude coordination](CODEX_CLAUDE_COORDINATION.md) for who does what.

## Production snapshot (4 November 2026, 21:37 Asia/Riyadh)

- Site: `neosys.frappe.cloud` — Active, on Frappe Cloud bench group `neoweb-v16`.
- Site bench: `bench-51251-000030-f1f`; bench group `neoweb-v16` is Active.
- Latest site update: `0kb4f0p4ru` — Success; pipeline `dddifl1q9e`; pre-release backup `f88kvtuvap` and site-update backup `7gcoh4lidp` both Success with files. Cloud reported no skipped backup or failing patch.
- Frappe `16.54.0` `2fcb939`; ERPNext `16.53.0` `9cd11b1`; HRMS `16.53.0` `b12d935`. These apps were unchanged.
- SIG Warehouse installed revision: `codex/sig-personal-home-v16` at `4d39efa84f3491ef32f1ecfc180112f751fe5ebe` on bench `000030`. Only SIG Warehouse was built and updated.
- Excel Setup now contains the People sections. The existing 58-row employee work-group/PC-routing matrix and six reviewer rosters were published in `SIG People Routing Setup` as revision 1 (`people-setup-1`); the two approved Incident additional-group exceptions are retained. Read-back confirms the persisted revision. No Employee, User, exact Project assignment, Account, Journal Entry or petty-cash transaction records were created or changed.
- The Excel Setup route and People section rendered in the authenticated Administrator session. No functional tests were run. Migration repeatability and HR/Projects/Finance non-admin persona acceptance are **NOT TESTED**. Candidate onboarding, secure upload, payroll/User/Finance follow-on actions and onboarding-control linkage remain incomplete.
- ZATCA Integration, live: `codex/v16-b2b-clearance-parity` at `a8f9fb5`.
- SIG WhatsApp, live: `v16-migration` at `9bfd1bd`. SIG QR Design, live: `v16-migration` at `39ecff6`.
- Trial: the site `neosys-v16-trial.frappe.cloud` has left the Frappe Cloud site list. Its bench `bench-51214-000014-f28f3` is still Active with no sites. Removal awaits owner confirmation.

## Production snapshot addendum (6 November 2026; Cloud API timestamp timezone not reported)

- Site `neosys.frappe.cloud` is Active on `bench-51251-000039-f1f`.
- SIG Warehouse `4809721c9dcff7348d54355167fe909b23656f22` is installed from `codex/sig-personal-home-v16`; only SIG Warehouse was built and updated.
- Build `0k83bd30iq`, pre-release backup `cjqr4ls1j9`, and site update `1rksi0g05t` all returned Success.
- PR #97 changes only PDF sharing code and the asset cache version. Tests and actual-user/UI acceptance were not run per owner instruction; check the print Share flow in Edge before considering the interface verified. See `docs/DEPLOY_LOG.md`.

## Branch map (SIG Warehouse, GitHub `9eskot9-max/SIG_Warehouse`), checked 4 November 2026

| Branch | Role today | Relevant revision | Live on production? |
|---|---|---|---|
| `codex/sig-personal-home-v16` | Production source configured in Frappe Cloud. | `4d39efa` installed on bench `000030`; latest source and installed hashes match. | Pipeline `dddifl1q9e` and site update `0kb4f0p4ru` succeeded; site is Active. Excel Setup People route rendered as Administrator and routing revision 1 read back. Functional workflows and non-admin persona acceptance are NOT TESTED. |
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
