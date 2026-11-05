# Final release checklist

## People model cutover — deployed 5 November 2026; access acceptance open

- [x] Pre-release production check: `neosys.frappe.cloud` was Active; authenticated Administrator opened Excel Setup revision 13. Its nine Operations family memberships matched the existing code roster by Employee ID. Six enabled flexible Planner teams and six current leader rows matched the six enabled legacy leaders. These checks established staged configuration, not access acceptance.
- [x] Read-only EPA check: EPA-00579–00587 are all Cancelled. Preserve them as audit history. Do not recreate exact Employee–Project links from PC-family clues.
- [x] Reconciled the intended first-cutover semantics: enabled Operations family rows replace the matching hardcoded Operations roster; family members see both PM and coordinator task categories. Project exceptions, when configured, replace that family's team for that Project. Current setup has no replacement rows.
- [x] Confirmed Planner may assign any eligible site in its DC or Incident mode. Team project coverage is reference data, not a site-eligibility restriction. The local adapter keeps the initial matching leader's existing team position history while later leader periods remain date-bounded.
- [ ] Verify affected Employee/User effective roles and run actual-user acceptance for newly shared task queues. Active Employee and linked User records were confirmed, but roles/access were not audited. Native ERP role/DocType permissions do not change in this release; the feature changes application-level task audience filtering. This acceptance is NOT TESTED per owner instruction.
- [ ] Verify PC inheritance and overrides, scope preview/recovery and actual reviewer/Finance workflows. User/profile permissions and linked Employee/Project access remain independent.
- [ ] Release the cancelled Employee Project Assignment overlap correction, then verify the native workflow. Cancelled EPA-00579–00587 remain as audit history.
- [ ] Keep Warehouse routing on its separate hardcoded `WAREHOUSE_USERS` path; it is not replaced by the nine Operations family rows and needs its own future review.
- [ ] Persisted Planner plans and TAWAL–ERP automatic PO registration remain deferred. See `docs/PEOPLE_MODEL_CUTOVER_REVIEW_20261105.md`.

Deployment read-back (5 November): site Active on `bench-51251-000036-f1f`; SIG Warehouse installed at `09c0f72496e06ba59f5f21816663177fcba1971d`; build pipeline `8ruifr103j`; the Excel Setup route reloaded and rendered. `PEOPLE_MODEL_ACTIVE` is enabled. No native ERP role or DocType permission rows changed. Actual-user permission acceptance remains open and NOT TESTED.

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


## 7. People model — first-stage implementation complete, acceptance pending

- [x] Reconcile current Operations team members and Planner leaders against live Excel Setup by Employee ID. Current family memberships match the prior Operations roster; Planner leader rows match the six enabled legacy leaders.
- [x] Implement the configuration in the existing Excel Setup People interface and switch the hardcoded Operations roster, audience and display consumers to validated configuration while preserving PC, field reporting and related consumers and their intended semantics.
- [x] Preserve unrelated data boundaries: no EPA records were recreated; nine cancelled EPAs remain historical. The feature gate changes application-level Operations task visibility and Planner roster sourcing, not PC routing, native ERP permissions or the separate Warehouse roster.
- [ ] Run fresh-session affected-user acceptance for Operations tasks and Planner. This is NOT TESTED per owner instruction; production visibility and successful user access are not verified.
- [ ] Configure Project-specific Operations team replacements only when a PM identifies a real exception; currently family defaults apply to all projects in the family. Do not infer exact employee–project assignments from PC groups.
- [ ] Treat PC inheritance/reviewer flows, Warehouse routing, Field Reporter maps, persisted Planner plans and TAWAL–ERP PO registration as separate integrations or deferred work, not part of this feature-gate cutover.

Current state: PR #89 is deployed and the adapter gate is ON. The live setup contains nine Operations family memberships and six flexible Planner leader rows. The Employee Project Assignment view showed nine cancelled historical rows and no active assignments. Family members now share both PM and coordinator task categories across their family; a Project exception replaces that family's team for that Project. Warehouse routing remains on its separate code-owned path, and PC routing remains separately configured. Deployment and route rendering are confirmed; actual-user access acceptance is NOT TESTED, so do not claim permission behavior is verified or accepted.
