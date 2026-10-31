# ERPNext v15 -> v16 migration workspace

Branch: `v16-migration` (this repo) / `sig-v16-phase2` (zatca_integration) / `v16-migration` (sig_whatsapp, sig_qr_design).
`main` and the deployed v15 branches are untouched. Production keeps running v15 until every gate below is green.

## How work is split (so no production secret leaves your PC)

| Lane | Where | Holds | Does |
|---|---|---|---|
| 1. Code and tests | Claude cloud session | no production secrets | edits the v16 branches, runs a throwaway Frappe v16 bench with an empty site, runs tests and browser checks |
| 2. Read-only evidence | your PC | your keys | runs `export_metadata.py` and `reconcile.py`, shares the output files (metadata and totals only, secrets redacted) |
| 3. Trial site (optional) | Frappe Cloud v16 bench | a *separate* trial-only API user | restored copy of a production backup; if you want Claude to test against it, create a read-only or test user on THE TRIAL SITE ONLY and put its key in the cloud environment's secret settings (never in chat) |

Credentials are the owner's call: keys placed in the cloud environment are rotated by the owner after the migration work.

## Deferred (owner decision, 31 Oct)

Trial-copy sanitising (a script that removed secrets and switched off the scheduler, email and ZATCA on a restored copy) was
removed from this branch on request. It is recoverable from commit `46e9248` if it is ever wanted. Until then a restored copy keeps
its live credentials and scheduler, so it can act on real external systems.

## Status (tested on Frappe 16.54 / ERPNext 16.53 / HRMS 16.53, Python 3.14, Node 24)

| Check | Result |
|---|---|
| All four apps install from the branches | pass |
| `bench migrate` | pass after approving ERPNext's new `HR Manager` select row in `permissions.py` (the guard stopped migrate, as designed) |
| Journal Entry hooks on real v16 (Finance, PC reviewer, Finance Viewer, Auditor) | pass; Finance has full access, reviewer scoped, viewer/auditor read-only |
| All 18 custom Pages load in the v16 desk | pass, no script errors |
| App appears in the v16 launcher | pass after `add_to_apps_screen` hook |
| Offline unit tests | 374 pass / 29 fail, identical to `main`, so none introduced by v16 (the 29 are test-isolation problems that already exist) |
| Read-only tools `export_metadata.py`, `reconcile.py` | tested against the local v16 site; redaction and difference detection verified |

## Open items (in order of risk)

1. **Production-only definitions.** These are used by the code but defined only in the production database, so a fresh install cannot reproduce them:
   `SIG Site`, `SIG Site Cycle`, `SIG Field Visit`, `SIG Evidence Event`, `SIG Field Session`, `SIG Field Message`, `SIG PC Transaction`,
   `SIG Project Stream`, `SIG Field Ops Settings`, `SIG TAWAL Contact`, `SIG Field Reporter Map`, `SIG Project PM Assignment`, `SIG Tawal Invoice Link`,
   plus roles, Server Scripts, Workspaces and Number Cards created by patches or by hand. Run `export_metadata.py` against production and commit the reviewed output, so the system can be rebuilt and reviewed from git.
2. **ZATCA.** Branch `sig-v16-phase2` is the vendor's `version-16` plus your one delivery-date commit. It is a large vendor rewrite (about 63 commits). Needs a full ZATCA sandbox run (compliance, clearance, credit note, QR). The vendor's error handler calls `frappe.db.commit()` inside a document hook, which v16 ignores: a rejected invoice may lose its saved error details. Verify in the sandbox.
3. **`sig_capitalize_tool` (asset_ops.py).** v16 Asset Capitalization no longer creates the asset; it needs an existing composite target asset, and the fields `target_qty`, `target_asset_location`, `capitalization_method` are gone. The button used by the Material Request list must be redesigned and tested.
4. **Permissions.** The v16 upgrade adds up to 316 Custom DocPerm rows to customised doctypes and checks User Permissions on more linked records (v16.36 / v16.50). Take before/after snapshots; expect additions, review each one; retest the Employee-link and Company User Permission cases.
5. **Fresh install is not production.** Patches are marked done, not run, on a new site, so roles and custom fields created by patches are missing there. Always test the upgrade path from a restored backup.
6. **Interface.** v16 has a new sidebar and `/desk` routes (`/app/...` links redirect). Check the SIG theme and the custom workspaces on the trial site; standard-workspace edits are reset by v16. Plan a short retraining.
7. **Other apps and callers.** HRMS and Drive need v16 versions (Drive's repository has only `main`; confirm or drop). RV80/WH VBA, TX Manager and the other external callers should be tried against the trial site.

## Gates before production cutover

- [ ] `reconcile.py compare` prod vs trial: IDENTICAL (trial balance, stock, receivable/payable, assets, counts)
- [ ] ZATCA sandbox: compliance + clearance + credit note + QR pass
- [ ] Each role completes its core workflows on the trial site: Journal Entry submit, SNB draft, PC confirm, dispatch/return, PR/PO, RFQ, attendance, collections
- [ ] Permission snapshot diff reviewed (additions explained)
- [ ] Items 1-3 above resolved
- [ ] Written rollback: keep the v15 site and bench untouched until the v16 site has run for an agreed period

## Running the read-only tools (on your PC)

```bash
export ERP_URL=https://your-site.frappe.cloud ERP_API_KEY=... ERP_API_SECRET=...   # a read-only user
python3 v16_migration/export_metadata.py --out erp_metadata_export
# skim erp_metadata_export/_redactions.txt and a few Server Script files, then share the folder

python3 v16_migration/reconcile.py snapshot --company "<Company>" --fiscal-year <FY> --out prod.json
# point ERP_URL at the trial site (restored from a backup taken at the same time)
python3 v16_migration/reconcile.py snapshot --company "<Company>" --fiscal-year <FY> --out trial.json
python3 v16_migration/reconcile.py compare prod.json trial.json
```

Both tools send GET requests only. Validate `reconcile.py`'s Trial Balance section on the first real run: it was exercised here only on an empty ledger.

---

# Level 2 runbook: trial copy on Frappe Cloud

Production (`neosys.frappe.cloud`, v15) is never touched. Everything below happens on a separate trial site.

## Two ways to get a v16 copy (Frappe Cloud's restore code has no version check, but a v15 backup on a v16 bench is not documented as supported)

1. **Try first:** create a private v16 bench group (frappe, erpnext, hrms and the four SIG apps from the branches above), create a new site on it and restore the latest production backup.
2. **Cloud-supported fallback (and the real cutover rehearsal):** create a private *v15* bench group with the same apps and commits as production, restore the backup there as the copy, then run **Site -> Actions -> Version Upgrade** on the COPY, selecting the v16 bench group and the SIG branches. Cloud's Version Upgrade is the feature the real cutover would use, so rehearsing it on a copy is the most faithful test.

Cloud's Version Upgrade needs a bench group that already contains every app installed on the site; a missing app is the usual failure.

## Order of operations on the copy

1. Restore finishes.
2. Read the restore/migrate job log; send it for review.
3. `export_metadata.py` and `reconcile.py` against production and the copy (see above).
4. Onboard the copy to the ZATCA sandbox/simulation environment .
5. Role walkthroughs, then the permission before/after diff.

## What access Claude needs (and what it does not)

| Access | Needed? | Notes |
|---|---|---|
| Trial-site API key (a Frappe user on the COPY) | yes, if you want Claude to test the copy directly | Create it on the copy. It cannot reach Cloud or production. |
| Frappe Cloud team API key | optional | It is team-wide: it can create, upgrade, restore and **archive (delete) any site in the team, including production**. If used, prefer a separate Cloud user restricted by a Cloud Role (beta) to the trial resources only. The safest alternative is that you click the Cloud steps yourself. |
| Production site keys | no | Only the read-only exporter/reconcile scripts, run on your PC. |

Add any key as an environment secret (cloud environment menu -> Edit -> secrets), never in chat. A new session picks secrets up, so
continue from this runbook in a new session on this repository.

---

# Level 2 results (31 Oct 2026, trial copy on Frappe Cloud)

Setup: private bench group `bench-51214` ("neoweb-v16-trial", Version 16, Falkenstein-3) built from the branches above
(frappe/erpnext/hrms 16, drive `main`, insights `version-3`, telephony `develop`, sheets `main`, ZATCA `sig-v16-phase2`, SIG apps `v16-migration`).
Trial site `neosys-v16-trial.frappe.cloud` restored from the 31 Oct offsite production backup (Frappe 16.54, ERPNext/HRMS 16.53).
Production was only read (admin login, GET requests); nothing on it was changed.

| Check | Result |
|---|---|
| Cloud build of all 11 apps on v16 | pass (about 6.5 min) |
| Restore + `Migrate Site` on real data | pass, 142 patches, no traceback; `after_migrate` guards passed |
| Record counts vs production (created up to the backup time), 17 doctypes | identical |
| GL Entry: 40,086 rows, 175 accounts, debit/credit per account | identical; total SAR 506,603,294.85 each side |
| Stock Ledger Entry: 7,684 rows, 485 items, qty and value | identical; stock value SAR 6,017,358.53 |
| Permission rows (Custom DocPerm) | 612 -> 624: 12 added (Email Account, Currency, Project, Role, Task), 0 removed, 0 changed |
| 18 custom Pages in a headless browser | 17 clean; `project-progress` raised 500 (fixed by patch `realign_project_progress_page`, commit 6957f6a) |
| 15 read-only server methods on real data | 10 ok, 3 need arguments, 2 petty-cash endpoints return 403 for Administrator exactly as on production |

Findings:
- `project-progress`: the database Page record pointed at ERPNext's Projects module; v16's page loader lists that folder unguarded. Patch added.
- Cloud's restore enables the scheduler automatically. The trial's scheduler was paused (`pause_scheduler = 1`).
- Production runs ZATCA from `sig-v15-phase2-base`, which lacks the 26 Aug delivery-date commit that `sig-v16-phase2` includes: decide whether production should have it.
- Frappe Cloud `bench.deploy_and_update` (release pipeline) needs each site as the exact record from `deploy_information`; the plain `bench.deploy` path worked. A second bench was left "Initialize Bench"-pending on Cloud's side.

Still open: ZATCA sandbox run, role walkthroughs by real users, the asset-capitalisation tool, staff retraining on the v16 interface, a written rollback.

---

# Readiness pass (31 Oct, later)

| Item | State |
|---|---|
| Asset capitalisation tool (`sig_capitalize_tool`) | Rebuilt for v16 (draft composite asset, then capitalise). Verified on a v16 bench: submitted asset at stock cost, stock consumed, replay returns duplicate. v15 path unchanged. |
| `project-progress` Page | Realigned by patch; live on the trial, all 18 pages load without errors. |
| Material Request hooks | Removed `frappe.db.commit()` (ignored by v16). |
| ZATCA ledger posting (`zatca_integration` branch `sig-v16-phase2`, commit 47d65c8) | The vendor's `CustomSalesInvoice.get_gl_entries` omitted v16's `set_transaction_currency_and_rate_in_gl_map`, so GL entries had no transaction currency and rate 0. Fixed; verified SAR / 1.0 on a v16 bench. |
| ZATCA data on the trial copy | 2 Production CSIDs, 3 Compliance CSIDs, CSR settings, 3 environments (Fatoora, Simulation, Sandbox), 56 transactions, Company set to Phase 2. |
| Trial deployment | Pipeline `bench.deploy_and_update` works when `sites` is the exact record from `deploy_information`; plain `bench.deploy` rebuilds the current pinned release and does not pick up new commits. |

Do not post invoices on the trial copy: ZATCA is enabled there with production credentials.
Still open: ZATCA sandbox clearance (needs a Fatoora OTP), real-user walkthroughs, the vendor error handler's commit inside `before_submit`, a written rollback, and the production cutover decision.

---

# ZATCA on v16: simulation result (1 Nov 2026, trial site only)

| Step | Result |
|---|---|
| Simulation CSR (new device, Simulation Portal) | generated |
| Compliance CSID (OTP from the Fatoora Simulation Portal) | ISSUED |
| ZATCA compliance checks: standard and simplified invoice, credit note, debit note | all 6 PASS, no errors |
| Simulation Production CSID | ISSUED, active, expires 2027-10-31 |
| Standard (B2B) VAT invoice via normal submit | CLEARED, status PASS, 0 warnings |
| Simplified (B2C) VAT invoice via normal submit | REPORTED, status PASS, 0 warnings |

Findings:
- ZATCA compares the invoice issue date with the current date in **UTC**. The site runs on Riyadh time, so invoices posted between 00:00 and 03:00 Riyadh are dated "tomorrow" in ZATCA's eyes and are rejected (BR-KSA-04). The v16 bench server clock is UTC (Frappe Cloud has no setting for it). Fix options: ask Frappe Cloud support to set the bench server time zone, or avoid submitting invoices in that window. Production v15 has the same exposure.
- A standard (B2B) invoice needs a delivery date **before** the invoice date; a simplified invoice also needs a delivery date, or submit fails.
- The trial company was pointed at the simulation Production CSID (the production CSID `SIG ERPNext Production CSID 2026-08-28` was not used). Before real use on production, the company must reference the real production CSID, which already exists in the database.
- ZATCA-cleared invoices cannot be cancelled or deleted (credit note only), so the two test invoices remain on the trial.

---

# ZATCA live device onboarding on v16 (1 Nov 2026, owner approved)

A NEW device (EGS unit) was onboarded on ZATCA's production portal from the v16 trial site, using one new-CSID OTP:
Compliance CSID ISSUED, all six compliance checks PASS, Production CSID ISSUED (active, expires 2027-10-31).
No real invoice was submitted. The renewal OTPs were not used (the existing production CSID is not due until Aug 2027).

IMPORTANT for the final cutover: restoring a fresh production backup over the v16 site replaces its database, which erases these
three records (CSR settings, Compliance CSID, Production CSID, including the private key). Choose one before cutover:
(a) keep the existing production device: after the final restore the company already points at the old CSID, whose invoice counter
and hash chain continue unbroken (the old v15 site must be closed first, never two systems signing on one device); or
(b) onboard the new device AFTER the final restore, with fresh OTPs (about 10 minutes).
Never keep the private key in GitHub.

# SIG rail entries on v16 (1 Nov 2026)
SIG Finance, SIG HR, SIG Operations and SIG Warehouse appear on ERPNext's left rail through
`sig_warehouse/dock/sig_warehouse/sig_warehouse.json` (a Dock with `mount_on: erpnext`). Verified on the
trial: each opens its workbench (`/desk/accounts/finance-workbench`, `/desk/sig-hr/hr-workbench`,
`/desk/sig-warehouse/operations-workbench`, `/desk/sig-warehouse/warehouse-workspace`).
Two things were needed:
* Frappe Cloud applied the code change as "Update Site Pull" **without migrating**, so the Dock row was not
  created until a Migrate was run. After the cutover restore, always run Migrate.
* A dock pin takes its shell from the module of the workspace it opens. The `SIG HR` workspace sat in the
  HRMS-owned "HR" module and was dropped; patch `move_sig_hr_workspace_to_sig_module` moves it to "SIG HR".
The rail clips icons at short window heights, so on a small screen scroll the rail.

# Pending before cutover (ordered)
1. Staff walkthrough on the trial by real users (planner, PC clearance, purchasing, finance workbench).
2. Decide the final site name / domain; update external callers (Maytapi webhook, Todoist OAuth redirect,
   RV80-WH VBA, TX Manager URLs).
3. Freeze v15 (nobody working), take a fresh offsite backup, restore it onto the v16 site, run **Migrate**
   (patches, Dock sync), keep the scheduler off until reconcile passes, then enable it.
4. `reconcile.py snapshot` on v15 and on v16 (same backup moment), `compare` must say IDENTICAL.
5. ZATCA (Option A): the restored company keeps its production CSID; verify with one real invoice after
   cutover. Ask Frappe support to set the bench timezone to Asia/Riyadh (UTC 00:00-03:00 invoice-date rule).
6. Written rollback: v15 stays untouched and restorable for 2 weeks; if v16 fails, point users back.
7. After cutover: rename branches (main -> version-15, v16-migration -> main), change the Cloud bench
   branch, rotate the Frappe Cloud API key/secret that was pasted in chat.
8. Production definitions export (1,739 records) is kept local, not committed (repo is public).
