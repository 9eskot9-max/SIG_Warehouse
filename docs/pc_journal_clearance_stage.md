# Petty-cash receipt confirmation to draft Journal Entry

Staged 2026-10-19 on `codex/pc-journal-clearance`, based on production app commit
`98b3ce4fffa1562a444c679de0b75a5429c0da84`. **Not deployed.** The owner's latest
direction is to stage the systemic fix first and handle existing PI/payment
inconsistencies later.

## Operating result

The assigned reviewer presses Confirm once. The server resolves the sender from
ERP Employee Mobile or an Employee-linked Contact, validates the existing expense
and Employee custody accounts, creates one **draft Journal Entry**, and closes
the receipt review in the same HTTP transaction. The journal links back to the
original `SIG PC Transaction`, retaining its original invoice/evidence and source
ID. Finance reviews and submits the journal separately. No Supplier, Purchase
Invoice, Payment Entry or GL posting is created by confirmation.

The existing SIGPC accounting policy is preserved: debit the **gross receipt** to
the mapped expense account and credit the Employee's configured 1322 custody leaf.
VAT evidence remains on the receipt and is described in the journal; this stage
does not claim input VAT automatically. Company, cost center, SAR account currency,
account classification and native Journal Entry permissions remain prerequisites.
No balances are invented and no accounting permission checks are suppressed.

## Scope of the staged source

- `pc_journal.py` owns confirmation, rejection, pending-list retrieval and Employee
  scope checks. Normal Journal Entry `.insert()` runs as the logged-in reviewer.
  Receipt review audit fields are written by the guarded command, as required for
  the existing read-only `SIG PC Clearance` transaction grant.
- The approved 2026-10-17 roster is compiled into 58 explicit Employee-to-reviewer
  ID assignments in `pc_review_scopes.json`. These are review boundaries, **not**
  onboarding/readiness claims. Enabled User linkage and active real Employee
  identity are checked at request time; self-confirmation is denied.
- Native PC transaction lists, counts and direct-record reads use the same scope
  for operational reviewers. Existing Accounts User/Manager and System Manager
  access is retained; Administrator remains the native Frappe recovery identity.
  No DocPerm, Custom DocPerm, User, Role Profile or User Permission rows are edited.
- The review Page and native transaction form call the same commands. Old short
  API names are redirected through Frappe's `override_whitelisted_methods`; the
  three old Server Scripts and old form Client Script are disabled by migration.
  Stale old clients must refresh to supply the receipt's expected `modified` value.
- A receipt row lock, source fingerprint, unique journal origin fields and review
  request digest prevent duplicate drafts/retry overwrites. Stale decisions fail
  before journal insertion. Native insert failures propagate and do not mark the
  receipt confirmed. The HTTP request owns commit/rollback; no code commits,
  submits or posts accounting entries.
- The older marked SIGPC cycle writer and receipt writer serialize on custody
  account locks and reject overlapping cycle dates. Unknown legacy period formats
  are held for Finance. This is conservative overlap protection, not an assertion
  that arbitrary unmarked manual journals can be semantically deduplicated.
- Migration adds only three Journal Entry origin/audit fields and disables old
  scripts after validating their contracts. Existing accounting links/documents
  and all permission matrices are preserved. No historical review is reconfirmed.

The original receipt storage remains the existing transport. Scoped ERP records
do not revoke external CDN URLs already disclosed, and this stage does **not**
claim a private-media migration, full onboarding setup or a whole-system privacy
closure. Native Journal Entry audiences retain their existing access; this change
does not introduce new broad Journal Entry Read grants.

## Existing accounting inventory

Read-only production inventory, 2026-10-19:

- 151 Needs Review, 970 Rejected, 6 Closed receipts.
- The six Closed receipts link to 6 draft Purchase Invoices and 6 draft Payment
  Entries. All twelve are `docstatus=0`; their GL row count is zero.
- No `[SIGPC ...]`-marked Journal Entries and no `SIG PC Clearance` register rows
  were found by the recorded queries. This is not a claim about unmarked manual
  financial documents.
- The six conversions are expressly deferred. The new command refuses to create
  journals for any receipt with an existing PI, payment or unrelated journal link.
  Future conversion must re-read state/dependencies and use supported lifecycle
  operations; unsubmitted documents cannot use submitted-document cancellation.

Evidence outside Git:
`ERPNext/backups/permission_release_pc_je_20261019/before.json` and
`accounting_inventory_before.json`. No business data was modified by that audit.

## Validation and remaining release checks

Offline: `python -B -m pytest sig_warehouse/tests/test_pc_journal.py -q` — **34 PASS**.
Checks cover native insertion without a permission bypass, draft-only output,
receipt/source linkage, native-create denial, exact retries, changed retries,
existing PI/PE/JE links, stale versions, missing original evidence, ambiguous and
inactive Employees, unrelated reviewers, self-review, source-roster consistency,
money validation, native-list/direct-read agreement, cycle overlap and repeatable
migration contracts. JavaScript syntax and `git diff --check`: **PASS**.

These are isolated tests with a Frappe stub. Actual database locks, unique indexes,
request rollback, app migration twice, installed native controller behavior,
fresh-form link/default requests, English/Arabic UI and actual-user acceptance
are **NOT TESTED**. They are required before acceptance under
`ERPNext/docs/deployment_permission_guide.md` and the persona regression mandate.
The earlier Admin-only test direction is not reported as actual-user acceptance.

Before any production release: reconcile the target app revision/pipeline,
capture complete raw/effective access plus hook semantics, backup, prove the
migration on staging twice, then exercise the native draft workflow and rejection
boundaries as the affected reviewers and Finance audiences. Compare all access
after the full migration and open `/app/pc-invoice-review` in the live Desk.
Stage status must not be described as deployed, fixed live or fully verified.
