# Deployment and branch map

Last verified from Frappe Cloud and GitHub: 7 November 2026, Asia/Riyadh. This is a dated read-back; recheck before every release.

See also: [Deploy log](DEPLOY_LOG.md) for every production action, and [Codex and Claude coordination](CODEX_CLAUDE_COORDINATION.md) for who does what.

## Production snapshot (7 November 2026, 11:46 Asia/Riyadh)

- Site: `neosys.frappe.cloud` — Active on `bench-51251-000041-f1f`; bench group `bench-51251` is Active.
- SIG Warehouse installed revision: `70566a25ec224e83b64757717a8bb7227344d8a6`, merged PR #101. Only SIG Warehouse was built/updated; Frappe, ERPNext and HRMS hashes are unchanged.
- Pre-release backup `063gk3n9v9` succeeded. Build `ahlt3vvq8j` and Site Update `2rvjflsotm` succeeded; update used backup enabled. Press API confirms site Active on the target bench and installed hash matches.
- The existing `/desk/sig-accounting/snb-movement-router` URL returned HTTP 200 HTML; its Page metadata reads “Bank Movement Router” and retains Accounts User, Accounts Manager and System Manager roles. Client-side rendering was NOT TESTED because Computer Use could not verify the active browser URL.
- Alinma received credits and salary-transfer narrative candidates use the shared review API. Other debits remain out of scope. No Alinma item was ingested; the adapter remains preview-first and requires an explicit `--push` for ingestion. No JE/PE drafts or accounting postings are created.
- Focused before/after access snapshots found no Page-role or effective DocType-permission changes. Accounts roles still cannot read Employee; employee-linked decisions remain fail-closed. Fresh Finance persona, linked-record workflow, Arabic/English rendering and migration-repeatability checks are NOT TESTED. No business records changed.

The 04:34 snapshot below records the pre-Alinma SNB router deployment and is retained as historical evidence.

## Production snapshot (7 November 2026, 04:34 Asia/Riyadh)

- Site: `neosys.frappe.cloud` — Active on bench `bench-51251-000040-f1f`; bench group `neoweb-v16` is Active.
- SIG Warehouse: `codex/sig-personal-home-v16` at `8b4ebe53eba55ecb1094df1f74fc2ea8cda62664`, merged PR #99. Only SIG Warehouse was selected for this release; Frappe, ERPNext and HRMS were left unchanged.
- Cloud deployment completed successfully. An onsite pre-deployment backup completed successfully at 04:17 Asia/Riyadh. The Cloud dashboard did not expose backup/build/update IDs in the view used for this release.
- The `/desk/sig-accounting/snb-movement-router` route rendered after migration in an authenticated Administrator session. Its queue was empty. No ERP business records were created or changed.
- The permission snapshot comparison showed only the two expected “missing before” entries becoming available (`SNB Movement Review` and `SNB Movement Review Event`); no existing access grant was removed. The new Page and review DocType grant `Accounts User`, `Accounts Manager`, and `System Manager` read/create/write/report access. Delete/submit/cancel are not granted.
- Actual Accounts User/Accounts Manager fresh-session acceptance and repeat-migration acceptance remain **NOT TESTED**. Accounts roles still cannot read Employee records; employee-linked decisions fail closed until a separate access decision. This router is a review foundation only: it does not create JE/PE drafts, sync the AM snapshot, or post accounting entries.

The 4 November snapshot below is retained as historical release evidence.

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

## Branch map (SIG Warehouse, GitHub `9eskot9-max/SIG_Warehouse`), checked 7 November 2026

| Branch | Role today | Relevant revision | Live on production? |
|---|---|---|---|
| `codex/sig-personal-home-v16` | Production source configured in Frappe Cloud. | `70566a2` installed on bench `000041`; a later documentation-only commit may advance branch HEAD without changing the installed app hash. | PR #101 is merged and deployed; site is Active. The shared Bank Movement Router serves both banks. HTTP route check passed; client-side render, Finance persona and linked-record workflow are NOT TESTED. Review-only; no draft creation or accounting posting. |
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
