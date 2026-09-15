# Stage 4 — ERP-only cutover runbook

This is a controlled, per-warehouse change. Do not activate the cutover merely
because the app is installed.

1. Choose the opening-baseline mode. For a legacy WH-reconciled warehouse,
   freeze the WH stock snapshot and preserve it as CSV with
   `item_code,warehouse,qty` in stock UOM; export an ERP Bin snapshot using
   those same columns and the same cutoff time. For an ERP-only warehouse,
   do not fabricate a WH file: call `create_erp_only_reconciliation` so the
   server captures and hashes the current non-zero ERP Bin position, and put
   the owner-approved reason in `notes`.
2. For the WH-reconciled mode, run `tools/build_cutover_reconciliation.py`,
   attach the frozen WH snapshot and exception register, and record the
   measured totals with `apply_reconciliation_summary`. For ERP-only mode,
   review the server-captured line count and SHA-256 instead; no WH line or
   exception register is implied by the mode.
3. Have the Stock/Finance owner accept the reconciliation. This is the point
   at which an accepted mismatch (or the explicit ERP-only opening decision)
   becomes an accountable business decision.
4. Seed the single company-wide DN counter. Its seed must be greater than both
   the ERP-derived suggestion and WH's documented high-water mark. The counter
   is global so two cutover warehouses cannot issue the same DN number.
5. Create the warehouse's `SIG Warehouse Cutover` document and disable/archive
   WH writing for that warehouse. Select the delivery route through the
   protected cutover action: `ERP_PRINT_AND_WHATSAPP` requires delivery-route
   evidence, while `ERP_PRINT_ONLY` verifies the `SIG Material Issue` print
   format and deliberately makes no WhatsApp claim. Attest the writer and
   delivery gates only after those checks pass.
6. Mark READY, then activate. Only an ACTIVE cutover permits the dispatch
   writer to allocate a `DN26-####` voucher. The dispatch writer must call
   `allocate_dn_voucher()` in its same database transaction.
7. After the first ERP-only dispatch, independently inspect the Stock Entry,
   stock ledger, printed DN and message audit log. Do not re-enable the WH
   writer to fix an exception; use ERP cancellation/amendment controls.

The current package intentionally keeps steps 3, 5 and 6 as explicit,
authenticated cutover actions: they are accountable approvals and route
selection, not arbitrary client-side field edits.

## Jizan pilot evidence (2026-09-16)

`مستودع جازان - SIG` completed the ERP-only path. Reconciliation
`SIG-WH-REC-مستودع جازان - SIG-00162` is `ACCEPTED` with 36 ERP Bin lines,
zero mismatches, and snapshot SHA-256
`81f1644f31df950b5723df889d8c8226f1e930d42c844e1aa3bcce7ec7b3ce1c`.
The cutover is `ACTIVE`, `wh_writer_disabled_confirmed=1`, and
`delivery_route_mode=ERP_PRINT_ONLY`; no stock movement was created by the
cutover run itself.
