# Deployment and branch map

Last verified from Frappe Cloud and GitHub: 8 November 2026, 15:55 Asia/Riyadh. This is a dated read-back; recheck before every release.

See also: [Deploy log](DEPLOY_LOG.md) for every production action, and [Codex and Claude coordination](CODEX_CLAUDE_COORDINATION.md) for who does what.

## Production snapshot (8 November 2026, 15:55 Asia/Riyadh)

- Site: `neosys.frappe.cloud` — Active on `bench-51251-000045-f1f`; bench group `bench-51251` is Active.
- SIG Warehouse installed revision: `35d8747e753dfbaaae1d380243b01df0e8e6b74b`, merged PR #109. Only SIG Warehouse was selected for the build and update; Frappe, ERPNext and HRMS were unchanged.
- Pre-release onsite backup succeeded at 15:17 (Cloud UI did not expose a backup ID). Scoped build pipeline `3gpbleqfj5` succeeded; site Pull succeeded at 15:52; in-place migration `8qpttdf28r` succeeded in 27 seconds with failing-patch skip disabled.
- The TAWAL resolver now uses the active Project-family default unless a dated PO rule overrides or clears it. Live Excel Setup read-back shows Omar Abbad as the 5G / Colocation family default effective 5 November and an empty PO TAWAL PM rules table. The previous Muhannad value came from legacy Project/assignment contact data; it was incorrectly labelled as a PO exception despite no dated PO rule.
- Captured permission snapshot diff: 0 removals and 0 additions. `/desk/sig-operations/excel-setup` rendered in the authenticated Administrator session. Actual non-admin persona acceptance, migration repeatability and the active RV80 workbook import/compile remain NOT TESTED.
- No ERP business records were created or changed. Local permission evidence is in `ERPNext/backups/permission_release_tcn_family_contact_20261108/`.

## Historical production snapshot (8 November 2026, 09:35 Asia/Riyadh)

- Site: `neosys.frappe.cloud` — Active on `bench-51251-000044-f1f`; bench group `bench-51251` is Active.
- SIG Warehouse installed revision: `15e19ad9dcb78dfa84561bd7ccb9e519e7477434`, merged PR #107. Only SIG Warehouse changed from the preceding active bench; Frappe, ERPNext and HRMS stayed unchanged.
- Pre-release backup `5ijcqqru0c`, scoped build `cjttcdn4t5`, and Site Update `cpv4g6kcho` succeeded. Installed-app read-back matches the full target hash.
- The SNB Movement Router now supports optional Purchase Order advance references and Purchase Invoice allocations for supplier payments. TX Manager can carry a selected reference through Am and the existing importer path. The review remains separate from Payment Entry creation and submission.
- Permission snapshot diff: 0 removals and 7 expected additions (Accounts User/Manager read-only Purchase Order permissions and the three review-reference fields). The router route rendered in an authenticated ERP session. Finance-role workflow, linked-document selection and migration-repeatability acceptance remain NOT TESTED per owner direction; see `docs/SNB_MOVEMENT_ROUTER.md` and the local snapshot evidence.
- TX Manager is running locally at `http://127.0.0.1:4317`; its outbox was empty at launch. No bank transfer or ERP business record was created.

## Previous production snapshot (7 November 2026, 23:56 Asia/Riyadh)

- Site: `neosys.frappe.cloud` — Active on `bench-51251-000043-f1f`; bench group `bench-51251` is Active.
- SIG Warehouse installed revision: `88faf84585ab7b4aaf09c013160abcdf0978aa6b`, merged PR #104. Only SIG Warehouse was built/updated; Frappe, ERPNext and HRMS were left unchanged.
- Pre-release backup `crrs762ot0`, build `bt9oh5qltj`, and Site Update `37mjr9uvku` succeeded. Press API confirms the site is Active on the target bench and the installed hash matches.
- Field Planner now provides shared weekly comments for Capex, Incident and 5G / Colocation. A new DocType remains directly readable/reportable only by System Manager; the endpoint uses the existing Planner role and Site Cycle read gate. No existing Page roles or DocType matrices changed.
- Extended permission snapshot diff has one expected removal (the “missing” marker for the new DocType) and the declared new DocType read/report and field entries. API reads of all three family scopes passed as `9eskot9@gmail.com` (ERP Admin/System Manager). Client-side Desk route rendering and fresh-session Operations persona checks remain NOT TESTED; the GPT-owned browser could not open the Cloud dashboard during this run.
- The prior PR #103 deployment is now recorded retroactively in `docs/DEPLOY_LOG.md`; its OpenAI suggestion and warehouse persona checks remain NOT TESTED.

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

## Branch map (SIG Warehouse, GitHub `9eskot9-max/SIG_Warehouse`), checked 8 November 2026

| Branch | Role today | Relevant revision | Live on production? |
|---|---|---|---|
| `codex/sig-personal-home-v16` | Production source configured in Frappe Cloud. | `35d8747` installed on bench `000045`; latest application change is PR #109. | PR #109 is merged and deployed; site is Active. The TCN TAWAL resolver uses Project-family defaults with dated PO rules as exceptions. Excel Setup confirms Omar Abbad for 5G / Colocation and no configured PO rule rows. The route rendered as Administrator; actual non-admin persona and RV80 workbook import/compile remain NOT TESTED. |
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
