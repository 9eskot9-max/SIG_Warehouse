# Final release checklist

Use this gate for every app update, patch, fixture, form, print format, default, page, workspace, integration or permission change. A successful build, migration, Administrator view or API read-back does not prove user acceptance.

## 1. Identify and scope

- [ ] Record the requested outcome and owning app/source.
- [ ] Record the exact production site, current bench, configured app branches, installed revisions and intended target revisions.
- [ ] List changed files and every runtime writer: DocType definitions, fixtures, patches, hooks, scripts, Server Scripts, reports, pages, workspaces and defaults.
- [ ] Declare affected DocTypes, fields/permlevels, reports, pages, workspaces, linked/child records and integrations.
- [ ] Record intended audiences and permitted/forbidden operations for each affected surface.
- [ ] Preserve a supported backup and a practical recovery route before production changes.

## 2. Access and permission baseline

- [ ] Inspect standard and custom permission matrices, including ptypes, permlevels and owner conditions. In Frappe v15, any Custom DocPerm rows replace the standard matrix; never add a sparse first custom matrix.
- [ ] Check roles, Role Profiles, User Permissions, Module Profiles, blocked modules, report role lists, Page roles, Workspace roles, link-field access and runtime permission hooks.
- [ ] Identify every permission writer and migration/import order. Review both removals and additions.
- [ ] Capture complete before-state evidence for the affected records and dependencies. Declare snapshot coverage gaps.
- [ ] Log unexpected denials or unintended grants in the permission incident record before attempting a repair.

## 3. Build and migration

- [ ] Run relevant focused checks and inspect the full release diff.
- [ ] On staging or a recoverable copy, run the actual installation/update path twice. Confirm repeatability and idempotence.
- [ ] Compare full access state after migration and fixtures; resolve every undeclared removal or grant.
- [ ] Record failures and evidence. Do not mask permission errors or add broad bypasses.

## 4. Production update

- [ ] Confirm the exact site is Active and the exact bench, source branches and target hashes match the release.
- [ ] Record the backup/recovery reference and change window.
- [ ] Run the Frappe Cloud build, then the site update/migration. Monitor each to a terminal result.
- [ ] Confirm the site is Active; read back installed app hashes and migration status.
- [ ] Verify the requested Desk route and affected form/page in the live site.

## 5. Actual-user acceptance

Start each check in a fresh authenticated session with the user's identity and effective roles verified. Complete basic access checks for all registered audiences and full linked-record workflows for every affected audience.

- [ ] Open a new form from the normal menu after reload.
- [ ] Wait for defaults and linked-record requests; load/select required linked and child records.
- [ ] Exercise the changed operation and its allowed/denied boundaries without persisting business data unless explicitly authorized.
- [ ] Check relevant language, print, report and integration paths.
- [ ] Record PASS / FAIL / NOT TESTED by persona, operation, route, revision and evidence.
- [ ] Treat any required FAIL or NOT TESTED as an open release gate. Do not claim fixed, verified or accepted.

## 6. Closeout

- [ ] Review post-deployment access additions and removals against the declared change.
- [ ] Link the release evidence from the master and update incident chronology/learning notes.
- [ ] Record remaining risks, owner decisions and untested personas.
- [ ] Confirm the release can be reproduced from the version-controlled source rather than a live-only change.
