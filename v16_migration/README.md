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
