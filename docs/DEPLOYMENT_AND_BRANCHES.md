# Deployment and branch map

Last verified from Frappe Cloud: 3 November 2026, Asia/Riyadh. This is a dated read-back; recheck before every release.

## Production snapshot

- Site: neosys.frappe.cloud — Active.
- Bench group: neoweb-v16.
- Bench instance: bench-51251-000014-f1f.
- Latest listed site update: Migrate — Success, 3 November 2026, 9:02 PM Riyadh.
- Frappe 16.54.0 — 2fcb939; ERPNext 16.53.0 — 9cd11b1; HRMS 16.53.0 — b12d935.
- SIG Warehouse: codex/sig-personal-home-v16 — 6ce8da3.
- ZATCA Integration: codex/v16-b2b-clearance-parity — a8f9fb5.
- SIG WhatsApp: v16-migration — 9bfd1bd.
- SIG QR Design: v16-migration — 39ecff6.

## Branch policy

The production revisions above are a dated read-back from the site's Apps page on 3 November 2026. After that read-back, documentation-only PR #69 was squash-merged to this Warehouse branch as `2a00717e`. No app source, permission, fixture, migration, Cloud setting, or deployment changed in that merge; the Apps page still showed installed Warehouse revision `6ce8da3` on its final read. Treat the listed hashes as the installed snapshot, not a claim that the new docs-only commit is deployed. Use Frappe Cloud's installed-app view as the source of truth; never infer deployment from a branch name or GitHub default.

For SIG Warehouse, main remains the v15-era line at f32c7eaa. The v16-migration branch is at 48ddaad6; codex/sig-personal-home-v16 is two commits ahead at 6ce8da3 and is the branch installed on production at this read-back. These branches are not mirrors. Do not push a fix to one and assume the other or production received it.

A local v15-era source archive was created before this review. The GitHub main branch remains present because it is the repository default; changing the default or deleting the remote ref is a separate repository-administration step and must not be bundled into a site deployment. Preserve a verified recovery source before removing the remote v15 line.

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
