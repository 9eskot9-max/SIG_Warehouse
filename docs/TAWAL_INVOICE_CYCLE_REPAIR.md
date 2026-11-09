# TAWAL invoice cycle allocation

Production reference on 8 November 2026: SIG Warehouse `35d8747e753dfbaaae1d380243b01df0e8e6b74b` on `bench-51251-000045-f1f`; PR #110 records that release. The isolated branch starts at the documentation merge `ee382dbabff00a4b8387eba06142806a8a67f423`.

## Observed incident

Submitted Sales Invoice `SIG-SINV-26-149` has one FMJ08 row and two 242-00-000 rows. FMJ08 has no matching Site Cycle or invoice bridge. Both 242-00-000 bridge rows point at the same cycle `242-00-000|NA|20260804`, which was closed manually on 19 October, before this invoice. The existing intake chooses the latest cycle without restricting it to open cycles or excluding one already assigned to another invoice row. The shared evidence resolver rejects FMJ08's no-WO, no-cycle-hint evidence.

## Owner direction

Group rows by site. Allocate distinct open cycles to the rows. If there are more open cycles than rows, choose any sufficient distinct cycles. If there are fewer, create the missing cycles and leave all cycles for that site open; remember that deferral across the draft and submitted phases and retries. Evidence warnings must not prevent the invoice PDF download. Existing conflicting historical links are review cases, not authorization for an automatic rewrite.

## Implementation and production release

`register_tawal_invoice_evidence` is routed to app-owned code through the existing API name. It takes a Redis lock around allocation and event intake because the generic evidence Server Script commits each accepted event. It reserves one distinct, open, BA- and ERP-Project-matched cycle per unique invoice source row, creates missing temporary cycles, and records a persistent `defer_cycle_closure` flag on each bridge row whenever the batch is short. Existing closed or conflicting bridge links are reported for review and are not rewritten. This handler does not close cycles; invoice PDF generation/download remains on the separate workbook path.

PR #111 (`1a8b1fea1eb4f4b287b4fbc6cc2ca817fa71f11c`) is deployed to `neosys.frappe.cloud` on bench `bench-51251-000046-f1f`. The pre-release backup `bekaq3q6gh` and scoped SIG Warehouse build `2gcoksh522` succeeded. Site Update `dmqqhld9ln` succeeded with backup enabled; the site is Active on the target bench, the installed app hash matches, and Cloud reports no pending updates. Frappe, ERPNext and HRMS were not updated. A first update request returned HTTP 417 before a suitable destination bench was provisioned; it was retried only after the exact target bench was Active.

The migration Patch Log contains `add_tawal_invoice_deferred_closure`; the field `SIG Tawal Invoice Link.defer_cycle_closure` is present as a hidden, read-only Check field. A safe authenticated API dispatch check returned the expected missing-phase validation response without accessing or changing invoice data. Focused permission-row comparison found no additions or removals on Sales Invoice, SIG Site, SIG Site Cycle and SIG Evidence Event. The five-role SIG Tawal Invoice Link permission matrix matches the pre-release focused snapshot. The full snapshot diff was unavailable because the pre-release focused snapshot and post-release full snapshot use different schemas; direct API reads verified the new field and affected DocType permissions.

The five offline planner tests cover shortage, excess cycles, retry deferral, conflicting historical reservations and the single missing-cycle case. Live invoice-cycle behavior, partial-commit retry recovery, concurrent calls, migration repeatability, actual-user/persona access, browser workflow, and workbook PDF download remain NOT TESTED. No invoice, evidence event, bridge row or cycle was changed during deployment. See `docs/DEPLOY_LOG.md` and local evidence under `ERPNext/backups/permission_release_tawal_invoice_cycle_20261109/`.

## Follow-up acceptance

- Re-read the live API method override and script settings after migration. Exercise persistent reservations/deferral across partial failures, repeated draft/submission calls and concurrent invoice calls.
- Handle zero, insufficient and excess open cycles without reuse. Confirm any later closure policy separately; this release leaves allocated cycles open.
- Preserve the existing authentication, invoice read checks and other permission boundaries. Review effective Sales Invoice, Site, Site Cycle, Evidence Event and bridge access, role profiles, field restrictions and runtime hooks. No new grants are declared.
- Exercise the actual Frappe v16 safe-exec path, migration repeatability, concurrent calls, duplicate/retry recovery, rollback boundaries, already closed cycles, and the existing workbook PDF flow. Capture representative Finance and Operations access acceptance; report unperformed tests as NOT TESTED.
- Exercise the actual production invoice reproducer only through the intended workbook/ERP workflow; confirm row-to-cycle allocation, shortage deferral and retry behavior without closing cycles.
- Verify the independent workbook PDF download path and representative Finance/Operations access in a fresh authenticated session.
- Repeat the migration in a safe staging environment and exercise concurrent calls and recovery after a partial event commit.
