# Bank router revamp — current design and release state

Updated 9 November 2026. This note follows the owner-approved ERP-authoritative design in `ERPNext/docs/bank_router_structure_v3_spec_20261109.md` (local workspace) and `docs/SNB_MOVEMENT_ROUTER.md` (repository). Earlier Am-owned payer-rule, approval-list, and bidirectional rule-sync proposals are superseded; do not implement them.

## Owner decisions in force

- ERP is the system of record for counterparties, identifiers, decisions and audit. Sheet Am supplies statement evidence and receives ERP document-link write-back. The owner does not edit an Am payer-rule sheet.
- Any enabled Customer or Supplier that the acting user can read is selectable. No extra approval list is required. A single ERP `Bank Counterparty` can retain multiple identifier hints across the company's bank accounts and narrative formats.
- SNB has three narrative formats: internal SNB transfer, IPS local transfer, and larger local transfer. Classify from statement text/parser evidence, not SAR 20,000 alone. A mapping learned from one reviewed line can suggest matches for other lines; each line still needs review.
- Show related bank-fee/VAT rows on the main movement. Include fees in an expense JE; use a separate fee JE for a Payment Entry route. Do not add fees to a Supplier or Customer balance.
- Keep unknown payer/payee decisions visible with the ERP holding parties (`Unidentified Receipts` and `Collective`). `XXPC` is petty-cash evidence; do not infer Employee ownership or resolve HR custody links here.
- Auto-drafting stays off until the owner chooses an effective date. Deployment must not create or submit Payment Entries or Journal Entries, initiate transfers, or activate auto-drafting.
- Alinma remains a review-only foundation until an approved feed and account mapping exist.

## Evidence captured 9 November

- The Am statement read contained 48 positive movements: 23 incoming internal SNB transfers, 8 IPS local transfers, 11 incoming local transfers, and 6 reversals/other credits. These provide examples of the distinct statement families; amount alone is not a reliable classifier.
- Of 426 fee/VAT rows, 416 had exactly one non-fee main row under the full-source-account plus bank-reference check; 10 remained ambiguous. Keep all statement lines and surface unmatched/ambiguous fees for review.
- The SAR 29,814.11 Khutut receipt on 8 November showed why a narrative match is only a candidate: two enabled ERP Customer records shared the display name, and invoice history did not establish which one was the payer or what it settled. No mapping was created from that investigation.

## Implementation and release

- Router engine, API, DocTypes, page and ZATCA-compatible migration patch are on `codex/sig-personal-home-v16` at `a2be2cbe651c9cd9f1a0ed65d7bd69ac80430cae`, with corrective hardening being prepared on a fast-forward topic branch.
- Production remains Active on `bench-51251-000047-f1f` at `1abfea6`. Cloud group build `8btodmgkro` did not reach the site. Both site update attempts recovered; the later job log confirms it ran the older patch without the required country field. See `docs/SNB_MOVEMENT_ROUTER.md` and `docs/DEPLOY_LOG.md`.
- A static review found that the initial target bypassed PE/JE permissions when retargeting drafts, reprocessed unrelated pending movements after a human route action, and lacked per-movement DB rollback. The corrective branch removes those issues and uses permission-filtered reads. Incident `PERM-20261109-01` is recorded in the local ERP permission register; no permission matrix changes are intended.
- Local focused tests cover parsing, routing, API guards, permission behavior, and rollback boundaries. Live migration, actual Desk rendering, Arabic/English, repeat migration, and fresh Finance persona acceptance remain NOT TESTED until a successful install and safe read-only review.

## Safe next steps

1. Finish and review the corrective topic PR from the current production head; preserve fast-forward-only history and include the actual failed-update records in the durable deploy log.
2. Take and verify a fresh site backup. Build only SIG Warehouse, wait until the exact site destination bench has the target hash, and confirm only SIG Warehouse is pending.
3. Run the site update with backup enabled. If migration fails, stop and diagnose; do not replay partial ERP writes blindly.
4. Read back the installed app hash, patch log, DocTypes, Bank Router Settings, holding Customer country, existing 916 review rows, and absence of router-created PE/JE markers. Keep the router auto-draft setting off and avoid any accounting-document write.
5. Verify the route in an authenticated ERP session, compare the scoped permission snapshot, and record route and persona checks as PASS/FAIL/NOT TESTED. Do not describe untested Finance workflows as verified.

The browser now exposes the Cloud Updates page, so use its Site Update details for failure logs and target status. Never use the legacy `deploy_sig_warehouse_bench.py`; it points at `bench-38491`.
