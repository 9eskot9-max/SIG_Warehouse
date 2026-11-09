# Bank movement router: SNB and Alinma review foundation

## Bank evidence and existing ERP documents — deployed 9 November 2026

### Production read-back

PR #114 is deployed on Active site `neosys.frappe.cloud`, bench `bench-51251-000047-f1f`, with SIG Warehouse `1abfea6fafc354ab48d5aff0bb6f3d60be93e519`. The pre-release backup `5bturq3kqk`, scoped build `be87drsr6v`, and Site Update `6o68oodm8j` succeeded. The update moved the site from bench `000046` to `000047`; the new bench had the exact target revision and only SIG Warehouse pending. The Site Update API returned timestamps `2026-11-09 16:11:11–16:11:22` without a timezone; see `docs/DEPLOY_LOG.md` for the timestamp note.

After deployment, `router_basic_sync.mjs --apply` created 916 SNB review rows. A second identical run returned 916 existing rows, with no source or hint conflicts. The Desk route `/desk/accounts/snb-movement-router` rendered in an authenticated ERP session and displayed 48 Receipts, 442 Payments and 426 Other rows. It also listed existing marked Payment Entries with their bank/date/status. Journal Entries are shown as **Bank unconfirmed**, because their marker does not establish the bank. The 252 ERP document references received from the source remain hints; they have not been independently read back against each document.

The basic Alinma adapter is deployed, including routing unclassified debits to the Other review lane. No Alinma statement rows were ingested because there is no approved live feed/queue in this task; source-account mapping and row-to-document matching are deferred. The adapter does not create or submit ERP accounting documents.

Permission snapshots before and after the release compare with **0 additions and 0 removals**. Fresh Accounts User/Manager and outside-role sessions, Arabic/English rendering, migration repeatability, and full SNB row-to-document linking remain **NOT TESTED**. No accounting entries were created or submitted, and no bank transfer was initiated. Snapshot evidence is local at `ERPNext/backups/permission_release_bank_router_20261109/`.

The existing scheduled checker now runs the guarded SNB sync after a completed SNB run. The sync stops if a lock or evidence conflict is present, and it remains review-only.

## Router engine — ERP-authoritative design, deployment pending

The implementation in `codex/sig-personal-home-v16` is the design recorded in `ERPNext/docs/bank_router_structure_v3_spec_20261109.md`. It supersedes the earlier Am-owned hint-rule prototype described in older working notes. ERP is authoritative for the Bank Counterparty registry, party links, identifiers, routing decisions and audit. Sheet Am supplies statement evidence and receives document-link write-back; the owner does not edit an Am rule registry, and there is no separate approval-list DocType. An enabled Customer or Supplier that the current ERP user can read is selectable.

One `Bank Counterparty` can hold the ERP party plus many identifiers across the company's configured bank accounts and narrative formats. SNB parsing distinguishes `INTERNAL_SNB`, `IPS_LOCAL`, and `LARGE_LOCAL` from statement/parser text; it never classifies a transfer from the SAR 20,000 amount alone. The current patch seeds two SNB account scopes. The statement source determines the hint type (for example payer name, beneficiary/depositor ID, account or IBAN); conflicting identifiers remain for review. Confirming one movement writes its identity to ERP for future engine suggestions. Each movement still needs its own Finance review.

The main queue presents the movement and its related fee/VAT rows together. Deterministic parent links use source evidence and account/reference constraints; ambiguous or unpaired fee lines stay in Other. For an expense Journal Entry route, fee lines are part of the same JE. For a Payment Entry route, bank fees use a separate fee JE so they do not alter the supplier/customer balance. Fee/VAT rows retain their own document status.

The migration patch seeds `Bank Router Settings`, two SNB bank accounts, expense categories and the `Unidentified Receipts` holding Customer (with the ZATCA-required Saudi country field). Unknown payees use `Collective`; unknown payers use that holding Customer. `XXPC` remains marked for the petty-cash workflow. Auto-drafting is disabled by default; no Payment Entry or Journal Entry is created or submitted by the migration. The Alinma adapter is a review-only base and does not establish an Alinma account mapping or ingest rows without an approved source feed.

### Deployment evidence and current recovery state

The site `neosys.frappe.cloud` is Active on `bench-51251-000047-f1f`, still running SIG Warehouse `1abfea6fafc354ab48d5aff0bb6f3d60be93e519`. The production source branch reached `a2be2cbe651c9cd9f1a0ed65d7bd69ac80430cae`; the Cloud group reports build `8btodmgkro`, but the site update did not install it. Update `56d2t52t1p` (19:33–19:34 Riyadh) ran the earlier patch without `custom_country` and recovered. Update `bfak6u0c9a` (19:48–19:49 Riyadh) also recovered; its migration log still shows the pre-fix patch without `custom_country`, confirming stale bench code. The owner authorized continuing the release. A fresh scoped build/update and post-migration read-back remain pending; see `docs/DEPLOY_LOG.md` and `ERPNext/docs/handover_codex_router_deploy_20261109.md`.

The target source review found and is correcting two pre-deployment safety gaps: draft retargeting used PE/JE permission bypasses and unrelated pending rows were reprocessed by a human route action; batch processing also lacked per-movement DB savepoints. The correction removes the bypass, limits user-triggered processing to the reviewed row, uses permission-filtered reads, and rolls back a movement's partial DB writes on failure. No role or permission matrix changes are intended. The incident is tracked as `PERM-20261109-01` in the local ERP permission register.

Focused route and engine tests pass locally; live migration, actual Desk rendering, Arabic/English presentation, repeat migration, Finance persona behavior and linked-record permission behavior remain NOT TESTED until the new build is installed and safely checked. The router release must not create or submit accounting documents or initiate bank transfers as part of deployment.

The engine reconciles statement lines against existing Payment Entries and Journal Entries using account/date/amount/reference evidence and statement markers; a marker alone does not prove which bank account a Journal Entry used. The page shows status for linked documents only when the current user's permission-filtered lookup can read them. The separate `ERPNext/scripts/snb/router_basic_sync.mjs` bridge imports account-scoped evidence from Sheet Am and calls the owner-only ingest method with `--apply`; it never creates or submits accounting documents. An inbound Am document reference is only a candidate until the engine validates it against ERP. Repeated identical source evidence preserves Finance decisions; changed source or conflicting hints stop for review.

The Alinma adapter also carries unclassified debits to Other rather than silently dropping them. It still requires an operator-asserted account and a prepared local queue; no Alinma accounting draft import, customer/salary match, or automatic capture is implemented. Source-account selection, live synchronization, linked-record behavior and fresh Finance persona acceptance remain NOT TESTED until separately recorded. No permissions are added by this change.

The existing `/desk/sig-accounting/snb-movement-router` page is bank-neutral while preserving its route and its current `SNB Movement Review` storage/audit model. SNB and Alinma records share the review screen, but each item carries an explicit `source.bank` and the page can filter by bank. Historical SNB rows without that field display as SNB.

`scripts/snb_router_push.mjs` remains the original SNB bridge. `scripts/alinma_router_push.mjs` adapts the local Alinma review queue and defaults to a read-only summary. Its `--push` option uses the same owner-only ingest endpoint and stable identity rules. It sends only the last four digits of the Alinma account number; no full account number, OTP, or credentials enter the review source. Credits, salary candidates, and unclassified debits enter separate review lanes. No bank request, ERP draft, or financial posting is performed by either bridge.

The ERP intake is idempotent by the source-scoped recognition row ID. Repeating identical source evidence keeps prior accountant decisions; differing source evidence for the same identity is surfaced as a conflict instead of being silently overwritten. The page separates banks and the existing Receipts, Payments, Own Accounts, Other and Deferred lanes. A review decision is stored in ERP with the user, time and previous decision. The form uses optimistic concurrency; stale edits must be reloaded.

## Supplier-reference release read-back — 8 November 2026

PR #107 is deployed on Active site `neosys.frappe.cloud`, bench `bench-51251-000044-f1f`, SIG Warehouse `15e19ad9dcb78dfa84561bd7ccb9e519e7477434`. The scoped build `cjttcdn4t5`, pre-release backup `5ijcqqru0c`, and Site Update `cpv4g6kcho` succeeded. The router route rendered in an authenticated ERP session after the update.

The live permission snapshot has zero removals and the expected Purchase Order read-only additions for Accounts User and Accounts Manager. The snapshot also records the three new review-reference fields. Fresh Finance-role PO/PI selection, linked-record permission behavior, Arabic/English rendering and migration repeatability remain **NOT TESTED** per owner direction. The feature remains review-only: it does not create, submit or reconcile Payment Entries. Snapshot evidence is local at `ERPNext/backups/permission_release_snb_po_linking_20261108/`.

For outgoing supplier movements, the review page can now list permission-visible submitted Purchase Orders and open Purchase Invoices matching the selected Supplier, Company, and bank currency. Purchase Orders are labeled as advance references; Purchase Invoices use a reviewer-entered amount bounded by current outstanding. The optional selection is stored in the review record and audit history. If TX Manager supplied an allocation in the matched transfer request, the router displays it as a suggestion pending accountant confirmation. No selection means unallocated. Purchase Receipt is not offered. This is a review link only: the router still does not create or submit Payment Entries, and selection is never proof of settlement.

## Scope and boundaries

- The review engine may create a marked JE/PE draft only after the owner explicitly enables auto-drafting from an effective date. The migration defaults that setting off, and this deployment must not create, reconcile, or submit accounting documents. A bank row or a supplied ERP link remains a hint until the engine verifies the document through permission-filtered ERP reads.
- SNB source evidence currently arrives from the Sheet Am bridge. The separate staged local sync is not required to maintain ERP party identity; ERP owns that registry. Alinma's initial received-credit and salary-candidate lanes do not depend on SNB beneficiary or transfer data. Customer, invoice, payroll, and ERP account matching remain unimplemented for Alinma.
- Review the full source JSON for data scope before production ingestion. Accounts User, Accounts Manager and System Manager retain read/write/create/report on `SNB Movement Review`; the same three roles can open the existing Page. The feature adds only read access at permlevel 0 for Accounts User and Accounts Manager on Purchase Order. Its migration preserves the complete existing Custom DocPerm matrix and stops if that baseline differs. User Permissions continue to filter the Purchase Order lookup. Delete/submit/cancel on the review DocType are not granted. The intake method additionally requires the configured integration owner or System Manager. The controller forbids ordinary form/REST writes outside the router methods.
- **Acceptance status: NOT TESTED.** Fresh-session Accounts User/Accounts Manager workflows, System Manager and denied outside-role behavior, linked Supplier/Company/Purchase Order/Purchase Invoice reads, Arabic/English rendering, repeated ingestion and changed-source conflict handling remain follow-up acceptance. Deployment does not claim those workflows are verified. Any Alinma salary or received-credit accounting route remains a human decision; there is no ERP draft creation.
- Source immutability includes the entire `source` object; a changed parser output, enrichment, or family metadata may produce a source conflict. The Alinma adapter uses account + date + reference + signed amount identity, masks the account to its last four digits in ERP evidence, and does not send salary-transfer initiation data. Handle a conflict deliberately rather than replacing statement evidence.
- Own-account pairing, HR custody-account links, SADAD mappings and recovery after an uncertain external draft write remain limited or deferred. The engine marks `XXPC` evidence for the petty-cash workflow but does not assign an Employee. Review-page PO/PI link selection is not a Payment Entry or a reconciliation action.

Suggested preview command from the repository root (path to the local queue can vary):

```
node scripts/snb_router_push.mjs D:/erp/ERPNext/data/snb-browser-profile/learning/snb-review-workbench-v1/queue.json
node scripts/alinma_router_push.mjs D:/erp/ERPNext/data/alinma/learning/review-queue.json
```

An Alinma ERP push requires the same configured integration-owner credentials and explicit `--push`; do not run it until the source has been reviewed and the non-admin acceptance gate has been completed.

## Access baseline for review and supplier references

Baseline source: production `DEPLOYMENT_AND_BRANCHES.md` (7 November 2026) and the matching `permission_release_snb_movement_router_20261107/after.json` snapshot. The existing Page roles, review DocType permissions, Reports, and Workspaces remain unchanged. This supplier-reference extension adds only read access to Purchase Order for Accounts User and Accounts Manager; the migration compares the full reviewed Custom DocPerm matrix and stops without changes if it differs.

| Surface / audience | Baseline access | Intended change | Acceptance |
|---|---|---|---|
| `snb-movement-router` Page — Accounts User, Accounts Manager, System Manager | Page roles list those three roles | Same route and role list; add bank filter/source label | NOT TESTED in fresh role sessions |
| `SNB Movement Review` — those three roles | read, write, create, report; no delete/submit/cancel | No permission change; Alinma source rows use the same guarded review API | NOT TESTED in fresh role sessions |
| `SNB Movement Review Event` child rows | Inherits its parent workflow; no independent role rows | No change | NOT TESTED |
| Finance Workbench navigation card | Same three `roleAny` roles and same existing Page route | Relabel card to Bank Movement Router | NOT TESTED from normal menu |
| Customer, Purchase Invoice, Supplier, Employee, Company, Account and Currency links | Existing effective access only | No change; edits still require normal read checks for selected links | NOT TESTED for Accounts User/Manager |
| Purchase Order | Accounts User and Accounts Manager did not have read access in the live baseline | Add read only at permlevel 0 for both roles; preserve all existing roles and ptypes through an exact-baseline migration | Live snapshot PASS; Finance lookup workflow NOT TESTED |
| Purchase Order Item and Purchase Invoice Item | Existing linked child DocTypes | No permission change | NOT TESTED |
| Reports and Workspaces | None added or changed | None | No change |
| Movement integration identity | Configured integration owner or System Manager may ingest; ordinary callers denied | Same gate for Alinma queue | NOT TESTED against live identities |
| Outside-role user | No Page/DocType role access from this feature | Must remain denied | NOT TESTED |

The selected Alinma importer sends a masked account ending, bank statement reference/narrative, signed amount and date. A Page render or successful owner API call does not close the access gate. For this release, fresh Accounts User and Accounts Manager workflows, System Manager behavior, outside-role denial, Arabic/English rendering, and migration repeatability are NOT TESTED. Deployment records the access change but does not claim persona acceptance or end-to-end workflow verification.
