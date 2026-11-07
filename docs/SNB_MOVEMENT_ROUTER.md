# SNB movement router: initial ERP implementation

The `snb-movement-router` SIG Accounting Desk page and `SNB Movement Review` records are built from the existing local recognition workbench queue. The integration script `scripts/snb_router_push.mjs` accepts the local queue JSON, defaults to a read-only count preview and requires `--push` plus the existing integration owner's ERP API environment to ingest. No bank request or financial posting is performed by this bridge.

The ERP intake is idempotent by the account-scoped recognition row ID. Repeating identical source evidence keeps prior accountant decisions; differing source evidence for the same identity is surfaced as a conflict instead of being silently overwritten. The page separates credits, payments, own-account movements, unresolved and deferred rows. A review decision is stored in ERP with the user, time and previous decision. The form uses optimistic concurrency; stale edits must be reloaded.

## Scope and release blockers

- This implementation saves review decisions, but **does not create, reconcile, or submit JE/PE drafts**. A bank row or a supplied ERP link is only a hint, not a verified accounting document.
- The current local queue builder requires a Sheet Am JSON export to load beneficiary and transfer-request evidence; its default run has no AM data. Do not call the recognition feed complete until a supported AM snapshot is supplied and the builder is rerun.
- Review the full source JSON for data scope before production ingestion. Accounts User, Accounts Manager and System Manager receive read/write/create on the new review DocType and the new Page; the intake method additionally requires the configured integration owner or System Manager. The controller forbids ordinary form/REST writes outside the router methods. Confirm Finance audiences, effective User Permissions, Company, Account, Customer, Supplier and Employee link visibility, and representative role acceptance before release.
- Every new DocType and standard Page needs migration. No permission writer for existing doctypes is intentionally changed. Snapshot live role matrices and linked records, inspect app hooks, fixtures and migration order, repeat migration on staging, and exercise fresh accountant and denied-persona sessions under the workspace permission gate. These checks are NOT TESTED.
- Source immutability includes the entire `source` object; a changed parser output, enrichment, or family metadata may produce a source conflict. Handle that conflict deliberately rather than replacing statement evidence.
- Own-account pairing, XXPC custody checks, supplier consistency, SADAD mappings, invoice allocation, ERP document read-back, recovery after uncertain draft creation, and all JE/PE draft builders require further implementation and acceptance before draft creation is enabled.

Suggested preview command from the repository root (path to the local queue can vary):

```
node scripts/snb_router_push.mjs D:/erp/ERPNext/data/snb-browser-profile/learning/snb-review-workbench-v1/queue.json
```
