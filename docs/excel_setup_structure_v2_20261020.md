# Excel Setup structural v2 — 20 October 2026

Source implementation; production deployment, actual-user and workbook acceptance are recorded separately. This supersedes the combined Project/Builder model in the initial release. The same app-owned `/app/excel-setup` page and existing Operations editor/reader audiences remain.

## Separate setup lists

| List | Key and responsibility |
|---|---|
| ERP Projects | Canonical ERP Project reference, derived PO/family, reviewed UPL revision. Does not create Projects or replace the native catalogue/setup feeds. |
| Builder profiles | Stable profile ID, reusable local alias, template token and internal PM default. No Project or PO required. |
| Builder contacts | Profile ID plus existing TAWAL directory contact. Genuine unresolved legacy snapshots remain visible for reconciliation; they cannot clear the workbook. Native Project PM assignments are not modified. |
| Project → Builder assignments | Explicit Project/profile references, optional native Project stream and derived stream alias. Many Projects may reuse a profile; multiple profiles need explicit stream/profile selection at export. |
| Existing Tags/defaults/item links | Their existing scoped rule model is retained. Google Sheets remains evidence authority. |

Builder R:V/Y form the source profile/contact block. AC is an independent sorted PO validation list, AB a separate vocabulary; neither is joined to R by row. Implementer, staff and geography lists remain separate. The v2 seed exporter emits no Project/profile links.

## Migration and compatibility

`split_excel_setup_structure` retains the v1 publication unchanged in immutable revision history. It publishes only deduplicated canonical Project/PO/UPL scope facts plus existing unrelated rule datasets. It creates no profiles, contacts or guessed assignments. The migration is a no-op on a second run. A genuine source seed then fills the independent lists.

`SIG_EXCEL_SETUP_V2`, schema/adapter 2, reject old adapter requests, old seed imports and historical v1 revision exports. RV80 `complete=false` until profiles, contacts and Tags exist and every enabled contact has an existing directory link. The importer checks this before any cache or target-range write. SIGPC receives canonical scope and its Tags/material rules, excluding Builder contacts/templates.

RV80 rebuilds Q:V/Y by profile/contact, once per profile rather than once per Project link. Existing valid local active-contact choices are retained. BD is a local UserPasswords index, retained by alias only when its PM is unchanged. AB/AC and unrelated source lists are never cleared or overwritten. Canonical ERP family controls PO classification; the explicitly selected profile controls contacts/template defaults. PO-based TCN exports stop on absent or ambiguous assignments.

## Data restoration prepared

Read-only source capture recovered 10 profiles / 15 distinct profile-contact rows. Fourteen rows match the existing directory; One legacy contact has no exact directory match and remains pending. Four explicit assignments are prepared: owner-confirmed PO 1000170 → mobily and PO 1000157 → 5g; existing native stream keys WBB and ITC beneath PO 10001045. Other links remain unassigned. All 34 current canonical Projects are included for scope setup. No contacts or data files are committed to GitHub.

## Permission and acceptance boundary

No Page/Workspace/DocType permission matrices, role/profile grants, authentication or fetch-key scope changes. The existing editor gate protects all writes/reference reads; fetch remains projected and role-gated. RV80 readers receive the configured reusable profile/contact set independently of Project links, as required for shared ACN setup imports; SIGPC readers still receive no Builder contact/template data. The migration changes only Excel Setup publication data. Legacy contact snapshots do not create a new native directory or Project assignments.

Offline contract/security/migration tests pass; migration twice is covered with Frappe stubs. Actual staging migration, Operations fresh-session linked workflow, Arabic/RTL, VBA compile, workbook refresh/rollback and downstream TCN export remain NOT TESTED. Production/API/Administrator read-back must not be described as full release acceptance.

Manual BAS handoff: import the v2 common engine in both workbooks, RV80 adapter, SIGPC adapter and the updated tcnword module into backed-up matching builds. Existing ACN/crypto/JSON modules and prior consumers remain required. User performs this rollout.
