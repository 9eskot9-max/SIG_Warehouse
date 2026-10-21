# Mapping Master receipt and Quotation QR release

## Scope

- `Update Mapping` sends a small receipt to ERP when SIGPC refreshes the Mapping Master. ERP records the master key, source workbook/sheet, fingerprint, row/site counts, timestamp and authenticated user. It does not upload mapping rows or create a cycle event.
- A repeated master key and fingerprint returns the existing receipt. Changed fingerprints create a new immutable receipt.
- On Quotation submit, the app issues the existing hidden verification token and QR attachment. The existing `/verify` page is repointed from its Server Script endpoint to the app-owned guest method.
- The current Quotation verifier already exposes the same verification facts: quotation number, status, transaction/expiry dates, company, total and currency. The new app method preserves that public response scope.

## Permission intent

`SIG Mapping Master Revision` is read-only to System Manager, Operations Manager, Operations User, Projects Manager and SIG Excel Setup Editor. Report/export are limited to System Manager, Operations Manager and Projects Manager. Receipt creation is through an authenticated POST method restricted to those same roles; no audience receives DocType create, write, delete or submit rights. No User Permission, Role Profile, Page or Workspace changes are included.

Quotation permissions are not changed. The `custom_verify_token` field is hidden, read-only, no-copy, and allowed on submit; the public verifier is token-gated and rate-limited. The submit hook logs failures without blocking submission.

## Evidence and limitations

The fingerprint is supplied by SIGPC as a checksum for change detection and idempotency; it is not a cryptographic proof of workbook integrity. ERP stores receipt metadata only. BAS deployment and live role acceptance are separate release steps.

Focused local tests cover the Mapping Master receiver, QR token/registry/hook wiring and image decode. Staging repeatability, post-migration permission snapshots, guest probes against a live submitted Quotation, and actual-user acceptance must be recorded during deployment before calling the release verified.
