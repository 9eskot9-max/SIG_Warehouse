# Bank router revamp — current design and release state

Updated 9 November 2026. This note follows the owner-approved ERP-authoritative design in `ERPNext/docs/bank_router_structure_v3_spec_20261109.md` (local workspace) and `docs/SNB_MOVEMENT_ROUTER.md` (repository). Earlier Am-owned payer-rule, approval-list, and bidirectional rule-sync proposals are superseded; do not implement them.

## Owner decisions in force

- ERP is the system of record for counterparties, identifiers, decisions and audit. Sheet Am supplies statement evidence and receives ERP document-link write-back. The owner does not edit an Am payer-rule sheet.
- Any enabled Customer or Supplier that the acting user can read is selectable. No extra approval list is required. A single ERP `Bank Counterparty` can retain multiple identifier hints across the company's bank accounts and narrative formats.
- SNB has three narrative formats: internal SNB transfer, IPS local transfer, and larger local transfer. Classify from statement text/parser evidence, not SAR 20,000 alone. A mapping learned from one reviewed line can suggest matches for other lines; each line still needs review.
- Show related bank-fee/VAT rows on the main movement. Include fees in an expense JE; use a separate fee JE for a Payment Entry route. Do not add fees to a Supplier or Customer balance.
- Keep unknown payer/payee decisions visible with the ERP holding parties (`Unidentified Receipts` and `Collective`). `XXPC` is petty-cash evidence; do not infer Employee ownership or resolve HR custody links here.
- Owner clarified that the SAB account ending `0001` and the Al Rajhi account named “Mohammed Algain Rahji” are his personal accounts used to fund company petty cash, separate from his personal-loan account/transactions. Keep custody/funding separate from Employee and loan-account identity; do not resolve the held transfers or assign an Employee automatically.
- Auto-drafting stays off until the owner chooses an effective date. Deployment must not create or submit Payment Entries or Journal Entries, initiate transfers, or activate auto-drafting.
- Alinma remains a review-only foundation until an approved feed and account mapping exist.

## Evidence captured 9 November

- The Am statement read contained 48 positive movements: 23 incoming internal SNB transfers, 8 IPS local transfers, 11 incoming local transfers, and 6 reversals/other credits. These provide examples of the distinct statement families; amount alone is not a reliable classifier.
- Of 426 fee/VAT rows, 416 had exactly one non-fee main row under the full-source-account plus bank-reference check; 10 remained ambiguous. Keep all statement lines and surface unmatched/ambiguous fees for review.
- The SAR 29,814.11 Khutut receipt on 8 November showed why a narrative match is only a candidate: two enabled ERP Customer records shared the display name, and invoice history did not establish which one was the payer or what it settled. No mapping was created from that investigation.

## Implementation and release

- PR #117 merged as `17405d19da92244ee02d7dbe41b9136ca92d3c8c` and is deployed on Active site `neosys.frappe.cloud`, bench `bench-51251-000049-f1f`. Cloud reports the installed SIG Warehouse hash matches the full target with no update pending. Deployment IDs and the stale-code failures are in `docs/DEPLOY_LOG.md`.
- The migrate patch ran; `Unidentified Receipts` has `custom_country=Saudi Arabia`; Bank Router Settings has both SNB account mappings; automatic drafting remains off. No PE/JE was created or submitted during deployment.
- The Desk route renders, but the review engine has not run on the 916 existing SNB rows. They remain `PENDING` with no linked ERP document; the page shows Needs you 0, Drafts 0, Posted 0 and Deferred 916. Do not claim those rows are routed or linked. A review-only engine batch is a separate production write; preserve held custody/employee cases and keep draft creation disabled.
- The focused permission comparison against the post-PR114 snapshot has zero removals and 13 expected read-only review-field additions. A different older snapshot had different explicit DocType coverage, so its broad diff is not comparable. Actual ERP identity/role, Finance personas, Arabic/English, repeated migration, and end-to-end matching remain NOT TESTED. Static finding PERM-20261109-01 is recorded in the local ERP permission register.

## Safe next steps

1. Decide whether to run a review-only engine batch on the existing 916 SNB rows. With auto-drafting off, it writes classifications/suggestions and review audit data, not accounting documents.
2. Before any batch, inspect candidates and protect the owner-held custody/employee cases. Do not infer an Employee, assign petty-cash funding, or confuse company petty cash with the personal-loan account.
3. If authorized, read back every batch outcome, errors/conflicts and PE/JE counts. Keep auto-drafting off and list unresolved rows for Finance.
4. Build the Alinma source/mapping workflow only after an approved feed and account mapping exist; the current adapter does not ingest Alinma rows.

The browser now exposes the Cloud Updates page, so use its Site Update details for failure logs and target status. Never use the legacy `deploy_sig_warehouse_bench.py`; it points at `bench-38491`.
