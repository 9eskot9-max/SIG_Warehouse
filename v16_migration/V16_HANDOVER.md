# SIG ERP: v15 vs v16 handover (1 Nov 2026)

## Current deployment clarification — 1 November 2026

The Cloud API confirmed `neosys.frappe.cloud` is still Active on Frappe Version 15, and `neosys-v16-trial.frappe.cloud` is Active on Version 16. The v16 GitHub branches and trial do not themselves upgrade the main site. The proposed alternative to the name-swap described below is Frappe Cloud's Version Upgrade of the existing production site, preserving its hostname and current production database. Rehearse the exact upgrade path and complete the access, backup, integration and rollback gates before using it. Trial-only settings and its newly onboarded ZATCA device do not automatically transfer to an in-place upgrade. See [production upgrade open fixes](PRODUCTION_UPGRADE_OPEN_FIXES_20261101.md).

For an in-place upgrade, existing user accounts and hashed login passwords are expected to remain; verify representative users can sign in and avoid blanket password resets. Preserve the site encryption key for encrypted integration credentials, and verify each integration after cutover. RV80 deployed BAS currently targets `neosys.frappe.cloud`; the hostname need not change for an in-place upgrade, but the installed workbook and write workflows are not yet verified. The owner deferred the small live ZATCA invoice test until after cutover; no historical invoice import is planned.


## Where things are
| | Site | Version | State |
|---|---|---|---|
| Live today | `neosys.frappe.cloud` | v15 | Still running, scheduler on. Backup taken 1 Nov ~03:14 Riyadh. |
| New ERP | `neosys-v16-trial.frappe.cloud` | v16 (Frappe 16.54 / ERPNext 16.53 / HRMS 16.53) | Holds a full copy of production data from that backup. Scheduler OFF. |

**Why the trial hostname remains:** the trial is a separate restored site and is not the production cutover target. The selected direction is an in-place Frappe Cloud Version Upgrade of the existing production site, preserving neosys.frappe.cloud and its production database. Do not rename sites, restore the trial over production, or change external callers as part of this path. See DEPLOYMENT_READINESS_COMPARISON_20261101.md.

## Branches (GitHub 9eskot9-max/sig_warehouse, also sig_whatsapp, sig_qr_design, zatca_integration)
- `main` = v15 code (unchanged, still what the live v15 site runs).
- `v16-migration` = v16 code (zatca_integration: `sig-v16-phase2`). The v16 bench builds from these.
- Keep the v15 production source and v16 migration source distinct until the in-place Version Upgrade is planned. Use the exact branch/revisions configured on the target bench; a GitHub branch rename is not required to preserve the production hostname.
- Local work: develop on v16-migration and do not merge it into main while v15 is live. Compare any shared bug fix to both branches and carry it to the intended release explicitly.

## What changed in the code for v16 (all on `v16-migration`)
- `pyproject.toml`: `frappe >=16,<17` (all three SIG apps).
- Permissions guard: `HR Manager` added as an optional approved role (it stopped migrate).
- Asset tool: v16 needs an existing target asset for Asset Capitalization; `asset_ops.py` creates a draft composite asset first.
- `rollup.py`: removed `frappe.db.commit()` (no longer allowed in document hooks).
- Page `project-progress` record realigned (patch). Redirect JS handles `/desk/` URLs (v16 uses `/desk`, not `/app`).
- ZATCA (`zatca_integration`): ledger gap fixed (transaction currency on GL entries).
- New: SIG hub page, dock (left rail) with Finance, Petty Cash, Warehouse, Operations, HR, colour icons (`public/icons/sig-icons.svg`), Font Awesome shim (`public/js/fa_icon_shim.js`) because v16 dropped Font Awesome and workbench icons were blank.
- Patches added: HR workspace moved to the SIG HR module (so its rail icon shows); petty-cash workspace opened to Operations roles.

## v15 vs v16 behaviour to remember
- URLs: `/desk/...` (old `/app/...` redirects). Default list sort is by creation, not modified.
- Left bar: one icon per app is replaced by a rail ("dock"). Only SIG icons + Setup are shown on this site (site layer saved for erpnext). Each user can re-add vanilla icons via Manage Dock.
- Custom icon names are SVG symbols from `app_include_icons`; Font Awesome `fa fa-x` no longer exists.
- `has_permission` hooks must return True/False (None now means deny). `frappe.db.commit` in doc events is a no-op/forbidden.
- Frappe Cloud applies code-only pushes as "Update Site Pull" without migrating. After pushing anything that adds a doctype, patch, dock or workspace, run **Migrate** on the site.
- Deploy recipe that works: build with `press.api.bench.deploy` (not the combined deploy-and-update, which failed pre-checks), then Site -> Update (skip backups) which migrates.
- Removed in v16 (expected diffs): Agriculture roles, Dropbox/Google Drive/S3 backup jobs, energy points, Leaderboard and user-profile pages, v15 HR/Payables/Receivables workspaces (replaced).
- For an in-place Version Upgrade, the production site's database and configuration remain with that site, subject to Cloud's documented upgrade behavior. Preserve the production encryption key and inventory integrations before the upgrade; verify their operation afterward. Trial-specific settings or credentials are not a source to copy over production.

## Verified (v15 live vs v16 copy)
The trial was restored from a production backup dated 1 Nov around 03:14 Riyadh time. At that snapshot, counts matched for MRs (484 / 428 submitted), invoices, payments, journals, stock, items, employees, projects, files, SIG site/cycle/visit/PC/evidence. Users (68), roles per user, role/module profiles, user permissions, custom permissions, custom doctypes (26), server (72) and client (21) scripts, print formats, reports, workflows, templates and settings were reported identical. All 19 SIG pages loaded. These are snapshot comparisons only: production remained active, so do not treat them as current equality or as the production cutover data. An in-place upgrade keeps the live production database; no historical invoice import is planned.

## Remaining release gates before production Version Upgrade

1. **Source comparison:** use DEPLOYMENT_READINESS_COMPARISON_20261101.md for the current installed revision matrix. SIG Warehouse v16 descends from current production Warehouse; the coordinated fixes are staged in draft PR #68 only. ZATCA source is diverged and still needs behavior-equivalence review, especially legacy invoice exclusion, B2B clearance and error handling.
2. **Unresolved trial defects:** the empty Sales Invoice shows SAR NaN after VAT defaults load. Dispatch field access and HR export are staged but not accepted. The ready-MR fix must first have an approved audience and record scope because the existing method uses frappe.get_all.
3. **Permissions and migrations:** review all permission writers and complete matrices, preserve role and record scope, extend snapshots, rehearse the migration path twice on a recoverable production copy, and record real-user acceptance. See the local deployment permission guide and learning-loop gate. Administrator success is insufficient.
4. **Recovery:** take a fresh pre-upgrade production database, files and configuration backup and record its restore reference. Verify a practical rollback path and preserve the production encryption key. Recent dashboard backups do not prove recoverability.
5. **Integrations:** inventory current production writers (scheduler, WhatsApp/Maytapi, Todoist, ZATCA, RV80 and other clients). Ensure only the upgraded production site acts on shared external services during cutover; verify credentials, callbacks, scheduled tasks and actual callers after the upgrade. The hostname stays neosys.frappe.cloud, so RV80 URL changes are not expected.
6. **PM reconciliation:** ERP Project and active TAWAL assignment last read as Jawad; RV80 holds a temporary PO-specific Hazem override for WO-2026-0037 / PO 10001274. Deploy the repaired Excel Setup path, explicitly reconcile both ERP defaults to Hazem and read them back before RV80 Sync From ERP.
7. **Post-cutover acceptance:** in fresh sessions, verify login, key Desk routes, linked forms and affected role workflows, then verify integrations and RV80 read-only sync. Record every audience as PASS / FAIL / NOT TESTED. The owner will run the small live ZATCA invoice test after deployment; no historical invoice import or resend is planned.
8. **Cutover choice:** perform Frappe Cloud's in-place Version Upgrade of the existing active production site only after the above gates. Do not swap hostnames or restore the trial database over production.

The versioned code, trial behavior, and backups are preparation evidence; they do not by themselves make production ready. Keep v15 rollback available according to the agreed recovery window and confirm final cutover steps in the Cloud dashboard before action.

The master white paper is in docs/MASTER-ERP-INTEGRATION.md.
