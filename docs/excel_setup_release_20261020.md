# Excel Setup implementation — release candidate

Source only, 20 October 2026. **Do not deploy/import this candidate as an accepted release.** The owner explicitly selected deployment later. Base is `origin/main` at `93d9e87`; the previous production observation was `2175bd7`. Review the entire later deployment revision, including the pre-existing main-branch changes.

## Included

- One `/app/excel-setup` Page under the app-owned SIG Operations module: one dataset grid, inline import preview, publication and history dialog. Operations Workbench links to it for its declared editor audience.
- One setup service with shared validation, additive seed import, stale-revision protection, immutable revision records and the `SIG_EXCEL_SETUP_V1` read contract. Canonical Project/PO and Item/UOM references are checked; no stock, finance or evidence writes occur.
- New `SIG Excel Setup` singleton and `SIG Excel Setup Revision` DocType. Publication is server-service-only, including for ordinary REST writes; revisions cannot be amended or deleted through the controllers.
- Any valid ACN passcode/session user can refresh through the protected existing read-anchor API mechanism. No personal ERP API key is needed for configuration refresh. Existing per-person business-posting gates remain unchanged.
- Identical `ExcelSetupSync.bas` engine in both workbook source folders, one host adapter each, and targeted changes to existing ACN, RV80 TCN/Tags and SIGPC Mapping/As-Built consumers.

The API read audience is the declared editor roles plus `SIG Excel Setup Reader` and existing `SIG Stock Viewer` (for the current protected fetch-anchor identity). The API returns only the published workbook projection. It authenticates the fetch identity, not the human name reported by Excel. No key is embedded in this release and no live credential was changed.

## Existing importers retained

RV80 `ERP_ReplaceCataloguesFromERP` and its old alias in `ItemCatalogueSync.bas` remain unchanged. `ERPProjects`, WHC and `ErpCat_FamilyForPo` retain their existing authority; stock refresh remains separate. The new adapter checks each setup Project/PO against `ERPProjects` and instructs the operator to refresh the existing catalogue if a reference is absent. It does not create a second Project registry.

The existing `sig_project_setup_export` / `SIG_PROJECT_SETUP_V1` path and ERP Setup cache remain intact. The exact loaded BAS consumer behind that cache was not present in the reviewed canonical exports: **installed-source provenance remains NOT TESTED**. Preserve and recover it before replacing any current workbook build. The new seed exporter uses that cache's explicit PO/Project references; it does not guess an alias's PO.

The new Page uses constrained Project/Item/contact reference pickers. Project family is derived from the existing Project, and contact name/phone/email are derived from the existing `SIG TAWAL Contact` directory after Project PM-assignment/default or exact stream eligibility checks. Raw legacy seed contacts must resolve uniquely; they cannot create an independent directory or bypass existing contact assignment. Native directory/assignment creation remains its established setup workflow.

## Workbook package

See `integrations/excel/manifest.json`: before/after hashes refer to the canonical source files used in this change, not proof of the loaded workbook build. New modules are in `common/`, `rv80/`, `sigpc/`. Targeted before-to-after diffs for existing modules are in `patches/`. Full updated BAS exports and a local import ZIP are delivered alongside the workspace handoff; unrelated pre-existing workbook source edits were not committed to this app repository.

Import as one matched set, into a backed-up workbook, only at the later workbook rollout:

| Workbook | New modules | Existing modified modules |
|---|---|---|
| RV80 | ExcelSetupSync, ExcelSetupRV80 | ACN, tcnword, csv |
| SIGPC | ExcelSetupSync, ExcelSetupSIGPC | ACN, MappingPipeline, AsBuiltCycle |

Then Debug → Compile VBAProject and verify existing button assignments. The existing RV80 `BuilderPMMaster` and SIGPC `Configure_UplTagLinksMenu` now offer refresh/ERP navigation/status. The common new public importer is `ExcelSetup_RefreshFromERP`; `ExcelSetup_ForceRefresh` repairs a damaged metadata revision by fetching a full bundle. No buttons or loaded VBA were modified by this source-only task.

### Initial seed and cutover

1. Preserve the actual installed VBA and current setup before replacing modules. Confirm the existing Project catalogue/setup import paths and current ERP role/profile baseline.
2. Run `ExcelSetup_ExportSeed` separately in each workbook at rollout. This exports declared setup only, excluding UserPasswords, credentials, Tags transactions and Mapping/stock/finance rows. RV80's one-time exporter asks for an exact canonical PO per Builder alias, resolves it through the existing ERP Setup cache, and reports omitted aliases. These associations must be reconciled before replacing Builder.
3. Operations imports RV80's definitions/defaults/Project associations through the Page preview first, then SIGPC's Tags/material links. Resolve duplicate/conflicting definitions, wrong matchers and PO/UPL scope. The import validator does not select a winning source automatically. Export files can contain business contacts: retain them locally; do not commit them to GitHub.
4. Legacy material links enter as **Manual**, or **Excluded** for X. Operations must verify CUC, UOM, scope and quantity basis before choosing Direct 1:1. Existing Tags AA:AE links are not evidence that material mapping was reviewed.
5. Publish, refresh both workbooks to the same revision, exercise real consuming macros, then save normally. Import reports additions/changes/omissions, preserves valid active Q choices, keeps previous cache/meta, and attempts full target-region restoration on failure. Runtime/rollback acceptance remains pending.

Generated RV80 projections retain Q:V, Y, AB, AR:AS, W:X, AW:AZ. BD's old row-position employee index is cleared when Builder is rebuilt so reordered contacts cannot inherit another row's employee index; verify existing name-based PM resolution. Active contact Q remains local and is not uploaded. Missing former selections are cleared rather than silently selecting a different contact. Project-family decisions still use the existing ERPProjects catalogue.

SIGPC retains the open RV80 runtime Tags bridge, with explicit PO/WO guards and equal setup revisions. It reads scoped rules directly from its normalized cache; only unscoped Tags links are mirrored into AA:AE. It does not flatten scoped material links into global whcd/whupl columns. A site with multiple matching WOs is blocked for reviewed allocation rather than guessed. Tags with blank/foreign PO are excluded; WO MISSING is an explicit exception, not silently overwritten.

PO-specific rule groups replace shared groups for that item; within a PO level, an applicable explicit UPL revision wins over its generic group. Include the complete set of that PO's candidate CUC links when overriding a group. Multiple candidates at the same effective level remain visible and must resolve uniquely against Mapping. Work Type is included where the existing batch requires it. Irrelevant sites and excluded x/X rows do not trigger WO-marker failures for the selected run. SIGPC's API projection contains Project/PO/UPL scope only, excluding RV80 contact/template data.

Google remains the Tags evidence source. Setup refresh does not rename historical Tags or emit evidence. As-Built keeps existing incomplete-source and pending-return protection and writes ABDraft only. Final AB remains PM-owned, with explicit final-export review of the existing blank-AB/design fallback.

Adapter v1 supports shared purpose/reason, CSV wording and TMS/implementer lookup rows. It rejects unsupported routing/free-form template defaults and PO-scoped wording rather than silently ignoring them. Templates remain the existing file workflow. Shared Project/version add/clone actions now route to ERP; local template copying must be handled through the existing template-file workflow, not the retired shared-Builder clone writer. Further consumer migration is needed before enabling additional dataset kinds.

## Declared permissions and writers

| Layer | Declared change |
|---|---|
| New Page | System Manager, Operations Manager/User, Projects Manager, SIG Excel Setup Editor. |
| New DocTypes | Read-only standard matrices for those roles; writes exclusively through checked service endpoints. No Custom DocPerm on an existing DocType. |
| Service | Editor role check on every edit/import/history endpoint; read-role check on published export. Guest and Employee-only access denied. |
| New roles | SIG Excel Setup Editor (Desk) and SIG Excel Setup Reader (API-only role). Created before model sync, represented in app fixtures and ensured by patch. |
| Profiles | Append only Editor to existing SIG Admin (Operations Admin), SIG PM, SIG Coordinator, SIG Stock Ops and SIG Ops Coordinator profiles. Missing profiles are skipped, not invented or renamed. Insert the declared child row without calling RoleProfile.save, avoiding its whole-user role replacement fanout. |
| Linked Users | Append only that capability to enabled System Users currently on those profiles, preserving every existing role row and profile. Role Profile gains make the addition durable on later profile saves. |
| Existing permissions | No ptype removal/grant on Project, Item, stock, finance, HR, Page/Workspace or transaction records. Existing Operations Workbench roles are unchanged. |

Writers: `before_install`/`before_migrate` role creation; new standard Page/DocType JSON; two-role fixture; final post-model-sync patch `add_excel_setup`; new-controller guards and service role checks. No blanket Role Profile reassignment or sparse custom-row repair. Unexpected Custom DocPerm on either new DocType aborts the patch for full-matrix review.

The profile migration uses a targeted child-row insert because the [Frappe v15 RoleProfile controller](https://github.com/frappe/frappe/blob/version-15/frappe/core/doctype/role_profile/role_profile.py) queues a replacement of linked users' role sets on normal save. This release must not trigger that unrelated replacement. Later normal User/Profile saves remain part of the required staging regression gate.

Before deployment snapshot new/existing Page, DocType, standard/custom permissions, role/profile and Has Role/User Permission records, field levels, Workspace visibility and applicable hooks. Review all target-branch writers/fixtures, run the migration path twice on staging, and compare both additions and removals. Verify roles survive normal profile/user saves. Follow the workspace deployment permission guide; a zero-removal report alone is not acceptance.

## Validation and remaining gates

Offline checks and their exact counts are recorded in the workspace implementation report. Required **NOT TESTED** gates:

| Audience/check | Status and required evidence |
|---|---|
| Operations Admin / Hamid | NOT TESTED: fresh session Page add/edit/publish, linked records; purchasing limits and finance read-only retained. |
| PM / Coordinator / SIG Stock Ops / SIG Ops Coordinator | NOT TESTED: actual profile/roles, fresh normal-menu entry, setup edits, native lookups, workbook refresh, Tags/docs and PM-approved quantities; English/Arabic/RTL. |
| Ordinary ACN importer | NOT TESTED: valid passcode without personal ERP key refreshes; invalid/expired session denied; import alone gives no ERP edit rights. |
| Warehouse / Ramzan / Tahir | NOT TESTED: MR/dispatch/returns and linked-record flows unaffected; Tahir's PO limit and cross-employee boundary retained. |
| Finance User / Baligh | NOT TESTED: new invoice/default tax/link workflow and intended reports retained; Arabic cold-load checks. |
| Finance Manager / Humaira or Safwacc | NOT TESTED: finance actions and existing Operations access retained. |
| HR | NOT TESTED: normal HR workflow/private Employee boundary retained. |
| Employee / viewers | NOT TESTED: own-record/report access retained; no setup edits or unrelated grants. |
| Integration identities | NOT TESTED: actual read-anchor role, setup fetch and existing API paths; no secret exposure. |
| Frappe migration/controllers/DB | NOT TESTED: real site install/upgrade twice, concurrent publication/rollback and persisted effective permissions. |
| Loaded Excel build / VBA | NOT TESTED: exact installed modules, Debug Compile, button wiring, refresh/restore and output acceptance. |

Any required FAIL or NOT TESTED prevents a fixed/verified or deployment-accepted claim. No production configuration, user/profile, business records, credentials or workbook cells were changed in this task.
