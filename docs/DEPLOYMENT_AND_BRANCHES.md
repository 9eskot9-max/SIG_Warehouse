# Deployment and branch map

Last verified from Frappe Cloud and GitHub: 4 November 2026, Asia/Riyadh. This is a dated read-back; recheck before every release.

See also: [Deploy log](DEPLOY_LOG.md) for every production action, and [Codex and Claude coordination](CODEX_CLAUDE_COORDINATION.md) for who does what.

## Production snapshot (4 November 2026)

- Site: `neosys.frappe.cloud` — Active, on Frappe Cloud bench group `neoweb-v16`.
- Site bench: `bench-51251-000021-f1f`; bench group `neoweb-v16` is Active.
- Latest site update: `6t7cbdidra` — Success, 4 November 2026, 4:26 PM Riyadh. It followed deployment pipeline `3roheu9glr`, which built SIG Warehouse source HEAD `c8f71c4` with zero reported issues.
- Frappe `16.54.0` `2fcb939`; ERPNext `16.53.0` `9cd11b1`; HRMS `16.53.0` `b12d935`. Frappe and HRMS updates are listed by Frappe Cloud as available and are **not applied**.
- SIG Warehouse source deployed by the latest pipeline: `codex/sig-personal-home-v16` at `c8f71c4`; the site's Apps page reported installed commit `6ce8da3`, but the Cloud installed-apps API on 4 November shows `c8f71c4` on bench `bench-51251-000023-f1f`, so the Apps page reading was stale and the code **is installed**.
- ZATCA Integration, live: `codex/v16-b2b-clearance-parity` at `a8f9fb5`.
- SIG WhatsApp, live: `v16-migration` at `9bfd1bd`. SIG QR Design, live: `v16-migration` at `39ecff6`.
- Trial: the site `neosys-v16-trial.frappe.cloud` has left the Frappe Cloud site list. Its bench `bench-51214-000014-f28f3` is still Active with no sites. Removal awaits owner confirmation.

## Branch map (SIG Warehouse, GitHub `9eskot9-max/SIG_Warehouse`), checked 4 November 2026

| Branch | Role today | Relevant revision | Live on production? |
|---|---|---|---|
| `codex/sig-personal-home-v16` | Production source configured in Frappe Cloud. | `c8f71c4` (source built in latest deployment) | Pipeline `3roheu9glr` and site update `6t7cbdidra` succeeded; site is Active. The site's Apps page still reports `6ce8da3`, so the code change at `5fe31ca` is **not confirmed installed**. |
| `main` | GitHub default; not the v16 build source. | `f32c7ea` | Its sole ahead commit is patch-equivalent to the intake guide/UOM list-view change already represented in production. No unique source patch remains to port from current `main`. |
| `v16-migration` | Former v16 staging; no longer built. | `5e63f85` | No unique commits ahead of production. |

Open pull requests: `#71` (draft, to `main`) and `#64`, `#65`, `#66` (drafts, to `v16-migration`) are superseded by work already on the production branch. They are recommended for closing. This needs owner approval.

The full ERP integration master on the production-source branch includes Claude’s 4 November updates. The local `D:\erp\ERPNext\Automation DB\MASTER-ERP-INTEGRATION.md` copy was behind at 3 November; it has been synchronized to that newer text, then updated with deployment pipeline `3roheu9glr`, site update `6t7cbdidra`, and the installed-revision mismatch. A later documentation-only commit records this state; no code changed after the deployment source `c8f71c4`.

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
