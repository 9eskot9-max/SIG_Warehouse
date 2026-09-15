# Stage 4 — ERP-only cutover runbook

This is a controlled, per-warehouse change. Do not activate the cutover merely
because the app is installed.

1. Freeze a WH stock snapshot for the warehouse and preserve it as CSV with
   `item_code,warehouse,qty` in stock UOM. Export an ERP Bin snapshot using
   those same columns and the same cutoff time.
2. Run `tools/build_cutover_reconciliation.py`. Attach both the WH snapshot
   and the output/exception register to a new `SIG Warehouse Reconciliation`.
   Record the measured totals using `apply_reconciliation_summary`; an
   exception register is mandatory when any line differs.
3. Have the Stock/Finance owner accept the reconciliation. This is the point
   at which an accepted mismatch becomes an explicit business decision.
4. Seed the single company-wide DN counter. Its seed must be greater than both
   the ERP-derived suggestion and WH's documented high-water mark. The counter
   is global so two cutover warehouses cannot issue the same DN number.
5. Create the warehouse's `SIG Warehouse Cutover` document. Attach proof that
   the ERP print format and WhatsApp recipient route have been sent successfully.
   Disable and archive WH writing for that warehouse, then attest both gates.
6. Mark READY, then activate. Only an ACTIVE cutover permits the dispatch
   writer to allocate a `DN26-####` voucher. The dispatch writer must call
   `allocate_dn_voucher()` in its same database transaction.
7. After the first ERP-only dispatch, independently inspect the Stock Entry,
   stock ledger, printed DN and message audit log. Do not re-enable the WH
   writer to fix an exception; use ERP cancellation/amendment controls.

The current package intentionally does not perform steps 3, 5 or 6 by itself:
those are accountable human approvals and external WH/WhatsApp actions.
