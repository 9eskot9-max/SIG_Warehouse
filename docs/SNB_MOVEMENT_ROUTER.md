# Bank movement router: SNB and Alinma review foundation

The existing `/desk/sig-accounting/snb-movement-router` page is being made bank-neutral while preserving its route and its current `SNB Movement Review` storage/audit model. SNB and Alinma records share the review screen, but each item carries an explicit `source.bank` and the page can filter by bank. Historical SNB rows without that field display as SNB.

`scripts/snb_router_push.mjs` remains the SNB bridge. `scripts/alinma_router_push.mjs` adapts the local Alinma review queue, sends only received credits and salary-transfer candidates, and defaults to a read-only summary. Its `--push` option uses the same owner-only ingest endpoint and stable identity rules. It sends only the last four digits of the Alinma account number; no full account number, OTP, or credentials enter the review source. Other Alinma debits stay outside this router. No bank request, ERP draft, or financial posting is performed by either bridge.

The ERP intake is idempotent by the source-scoped recognition row ID. Repeating identical source evidence keeps prior accountant decisions; differing source evidence for the same identity is surfaced as a conflict instead of being silently overwritten. The page separates banks and the existing Receipts, Payments, Own Accounts, Other and Deferred lanes. A review decision is stored in ERP with the user, time and previous decision. The form uses optimistic concurrency; stale edits must be reloaded.

## Scope and release blockers

- This implementation saves review decisions, but **does not create, reconcile, or submit JE/PE drafts**. A bank row or a supplied ERP link is only a hint, not a verified accounting document.
- SNB's current local queue builder requires a Sheet Am JSON export to load beneficiary and transfer-request evidence; Alinma's initial received-credit and salary-candidate lanes do not depend on SNB beneficiary or transfer data. Customer, invoice, payroll, and ERP account matching remain unimplemented for Alinma.
- Review the full source JSON for data scope before production ingestion. The deployed permission baseline is unchanged: Accounts User, Accounts Manager and System Manager have read/write/create/report on `SNB Movement Review`; the same three roles can open the existing Page. Delete/submit/cancel are not granted. The intake method additionally requires the configured integration owner or System Manager. No new DocType or role grant is added here. The controller forbids ordinary form/REST writes outside the router methods.
- **Acceptance status: NOT TESTED.** Fresh-session Accounts User/Accounts Manager workflows, System Manager and denied outside-role behavior, linked Customer/Company/Account reads, Arabic/English rendering, repeated ingestion and changed-source conflict handling must be checked before release acceptance. Any Alinma salary or received-credit accounting route remains a human decision; there is no ERP draft creation.
- Source immutability includes the entire `source` object; a changed parser output, enrichment, or family metadata may produce a source conflict. The Alinma adapter uses account + date + reference + signed amount identity, masks the account to its last four digits in ERP evidence, and does not send salary-transfer initiation data. Handle a conflict deliberately rather than replacing statement evidence.
- Own-account pairing, XXPC custody checks, supplier consistency, SADAD mappings, invoice allocation, ERP document read-back, recovery after uncertain draft creation, and all JE/PE draft builders require further implementation and acceptance before draft creation is enabled.

Suggested preview command from the repository root (path to the local queue can vary):

```
node scripts/snb_router_push.mjs D:/erp/ERPNext/data/snb-browser-profile/learning/snb-review-workbench-v1/queue.json
node scripts/alinma_router_push.mjs D:/erp/ERPNext/data/alinma/learning/review-queue.json
```

An Alinma ERP push requires the same configured integration-owner credentials and explicit `--push`; do not run it until the source has been reviewed and the non-admin acceptance gate has been completed.

## Access baseline and acceptance record for Alinma alignment

Baseline source: production `DEPLOYMENT_AND_BRANCHES.md` (7 November 2026) and the matching `permission_release_snb_movement_router_20261107/after.json` snapshot. This change leaves Page roles, DocType permissions, linked-record permissions, Reports, and Workspaces unchanged.

| Surface / audience | Baseline access | Intended change | Acceptance |
|---|---|---|---|
| `snb-movement-router` Page — Accounts User, Accounts Manager, System Manager | Page roles list those three roles | Same route and role list; add bank filter/source label | NOT TESTED in fresh role sessions |
| `SNB Movement Review` — those three roles | read, write, create, report; no delete/submit/cancel | No permission change; Alinma source rows use the same guarded review API | NOT TESTED in fresh role sessions |
| `SNB Movement Review Event` child rows | Inherits its parent workflow; no independent role rows | No change | NOT TESTED |
| Finance Workbench navigation card | Same three `roleAny` roles and same existing Page route | Relabel card to Bank Movement Router | NOT TESTED from normal menu |
| Customer, Supplier, Employee, Company, Account and Currency links | Existing effective access only | No new grant; edits still require normal read checks for any selected links | NOT TESTED for Accounts User/Manager |
| Reports and Workspaces | None added or changed | None | No change |
| Movement integration identity | Configured integration owner or System Manager may ingest; ordinary callers denied | Same gate for Alinma queue | NOT TESTED against live identities |
| Outside-role user | No Page/DocType role access from this feature | Must remain denied | NOT TESTED |

The selected Alinma importer sends a masked account ending, bank statement reference/narrative, signed amount and date. A Page render or successful owner API call does not close the access gate. Before a release is accepted, test a fresh Accounts User and Accounts Manager session from the Finance menu, verify received-credit and salary-candidate rows, exercise the relevant linked-record lookup without saving business transactions, verify System Manager behavior, and confirm an outside-role denial. Repeat the checks in Arabic/English as applicable. Migration repeatability and all persona checks remain NOT TESTED.
