# TAWAL invoice cycle allocation

Production reference on 8 November 2026: SIG Warehouse `35d8747e753dfbaaae1d380243b01df0e8e6b74b` on `bench-51251-000045-f1f`; PR #110 records that release. The isolated branch starts at the documentation merge `ee382dbabff00a4b8387eba06142806a8a67f423`.

## Observed incident

Submitted Sales Invoice `SIG-SINV-26-149` has one FMJ08 row and two 242-00-000 rows. FMJ08 has no matching Site Cycle or invoice bridge. Both 242-00-000 bridge rows point at the same cycle `242-00-000|NA|20260804`, which was closed manually on 19 October, before this invoice. The existing intake chooses the latest cycle without restricting it to open cycles or excluding one already assigned to another invoice row. The shared evidence resolver rejects FMJ08's no-WO, no-cycle-hint evidence.

## Owner direction

Group rows by site. Allocate distinct open cycles to the rows. If there are more open cycles than rows, choose any sufficient distinct cycles. If there are fewer, create the missing cycles and leave all cycles for that site open; remember that deferral across the draft and submitted phases and retries. Evidence warnings must not prevent the invoice PDF download. Existing conflicting historical links are review cases, not authorization for an automatic rewrite.

## Implementation staged for review

`register_tawal_invoice_evidence` is routed to app-owned code through the existing API name. It takes a Redis lock around allocation and event intake because the generic evidence Server Script commits each accepted event. It reserves one distinct, open, BA- and ERP-Project-matched cycle per unique invoice source row, creates missing temporary cycles, and records a persistent `defer_cycle_closure` flag on each bridge row whenever the batch is short. Existing closed or conflicting bridge links are reported for review and are not rewritten. This handler does not close cycles; invoice PDF generation/download remains on the separate workbook path.

The five offline planner tests cover shortage, excess cycles, retry deferral, conflicting historical reservations and the single missing-cycle case. They do not yet prove the live Frappe safe-exec integration, concurrency, retry recovery after a partial event commit, PDF download, or persona access. Record those as NOT TESTED until exercised.

## Required before a release candidate

- Re-read the live API method override and script settings after migration. Exercise persistent reservations/deferral across partial failures, repeated draft/submission calls and concurrent invoice calls.
- Handle zero, insufficient and excess open cycles without reuse. Confirm any later closure policy separately; this release leaves allocated cycles open.
- Preserve the existing authentication, invoice read checks and other permission boundaries. Review effective Sales Invoice, Site, Site Cycle, Evidence Event and bridge access, role profiles, field restrictions and runtime hooks. No new grants are declared.
- Exercise the actual Frappe v16 safe-exec path, migration repeatability, concurrent calls, duplicate/retry recovery, rollback boundaries, already closed cycles, and the existing workbook PDF flow. Capture representative Finance and Operations access acceptance; report unperformed tests as NOT TESTED.
- Review the entire installed-to-target diff and declared permission layers before merging. No production deployment or historic data repair has occurred.
