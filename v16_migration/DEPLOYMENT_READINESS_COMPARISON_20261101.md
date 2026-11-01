# V16 deployment readiness comparison — 1 November 2026

**Decision: NOT READY for production cutover.** The installed v15 and trial v16 app sources are now compared at their current Cloud-reported commits. This is a preparation record; no production change, site update, or migration was run.

## Current Cloud state and installed apps

Read from the signed-in Frappe Cloud dashboards. Both sites showed **Active** at the time checked. Production is neosys.frappe.cloud on bench-38491; trial is neosys-v16-trial.frappe.cloud on bench-51214.

| App | Production v15 | Trial v16 | Comparison |
|---|---|---|---|
| Frappe | 15.125.0, e7458ff | 16.54.0, 2fcb939 | Major-version upgrade |
| ERPNext | 15.124.1, 4e0dce9 | 16.53.0, 9cd11b1 | Major-version upgrade |
| HRMS | 15.64.6, 3fae97a | 16.53.0, b12d935 | Major-version upgrade; v16 permission-writer effects are under review |
| Drive | 0.4.3, 959172c | 0.4.4, 7ed084b | Trial has a newer patch |
| Insights | v3.15.1, c7dc954 | v3.15.1, c7dc954 | Same |
| Telephony | 9447577 | 9447577 | Same |
| SIG Warehouse | main 59c7ce3 | v16-migration 1229f4f | Trial source descends from production head; 19 commits ahead, 0 behind |
| SIG WhatsApp | main 271df4f | v16-migration 9bfd1bd | One commit ahead; only the Frappe version dependency pin differs |
| SIG QR Design | main 0089b0b | v16-migration 39ecff6 | One commit ahead; only the Frappe version dependency pin differs |
| ZATCA Integration | sig-v15-phase2-base 25454a7 | sig-v16-phase2 cbc271a | **Diverged:** 18 production-side and 71 v16-side commits |

The SIG Warehouse ancestry is favorable: the installed production head 59c7ce3 is the v16 branch's merge base. The trial's installed 1229f4f predates the currently staged fixes. PR [#68](https://github.com/9eskot9-max/SIG_Warehouse/pull/68) includes the Excel Setup PM repair, dispatch field access, ready-MR feed correction and HR export review. It is a draft staging candidate, overlaps PRs #64–#67, and must be integrated once—not combined with those PRs unchanged.

## Cutover blockers

1. **ZATCA source equivalence is unresolved.** Production contains a legacy-invoice guard that prevents historical invoices entering generate/resend paths and protects the classification from change. That safeguard has not been found in the v16 source. The production B2B-clearance hook and other production-only error/fallback changes also need a behavior-level comparison against v16. Do not port or deploy based only on commit counts. Historical invoices already reside in ERP; no historical invoice import is planned. The owner's small live invoice test is deliberately deferred until after cutover. Before then, preserve the historical-invoice exclusion and check the non-production test boundaries without contacting the live authority.
2. **Warehouse ready-MR scope is not approved.** The staged feed removes stale status predicates, which makes additional submitted unsent MIRs visible. The existing server method uses frappe.get_all; confirm every caller and record-level scope before widening results. The thirteen viewer-only users remain outside the proposed field-level dispatch grant unless the owner approves that audience.
3. **Permissions and HR export remain open.** Trial testing exposed Hamid's dispatch field denial. PR #68 has a scoped candidate grant, but the required audience, complete before/after matrices, later permission writers, migration repeatability and user acceptance still need review. HRMS v16 creates nine HR Custom DocPerm rows with default export permission; the staged removal has not been accepted against HR's real export needs. Follow the site's permission guide and learning-loop access gate.
4. **Excel Setup PM correction is staged only.** The live Project default and active TAWAL assignment were last read as Jawad. RV80 has a temporary PO-specific Hazem override. After the v16 repair is deployed, explicitly reconcile the affected Project and active assignment to Hazem, read both back, then run RV80 **Sync From ERP** and verify the PO-specific row. Syncing earlier can overwrite the temporary workbook value.
5. **Sales Invoice form has a reproducible display defect.** A fresh empty v16 invoice shows SAR NaN after VAT defaults load. A populated unsaved example calculated SAR 15 VAT and SAR 115 total, but the empty-form defect is not fixed.
6. **Upgrade and recovery path have not been rehearsed.** The intended path is an in-place Version Upgrade of the existing production site so the main hostname and current production database remain. The Cloud dashboard state alone does not prove that the production site's full patch/fixture migration succeeds on v16. Rehearse the exact upgrade using a recoverable copy of the existing site's database, files and site configuration; inspect migration order and the whole active app bundle. Confirm the rollback procedure before scheduling.
7. **Integration and site configuration acceptance remains pending.** Keep the existing hostname because RV80 and other callers already target neosys.frappe.cloud. Inventory active production writers and integrations, preserve the production encryption key, coordinate scheduler/external writers to avoid duplicates, and check credentials and hooks in fresh sessions. Trial-only settings and its newly enrolled ZATCA device do not automatically replace production configuration.

## Preparation state

- PR #68 is draft and not deployed. It reports 29 focused local tests passing; this does not prove the whole-bench upgrade, migrations, access acceptance or live workflows.
- Trial/production backups previously appeared successful, but there is no recorded restore rehearsal or verified recovery.
- The production site's real user acceptance, full permissions diff, repeat migration, integration cutover, and post-cutover invoice test are **NOT TESTED**.
- Cloud API site read returned HTTP 403 on a fresh attempt; no Cloud permissions were changed. The versions above were verified through the signed-in dashboard.
- Do not declare this ready to cut over until blockers 1–6 are closed or the owner explicitly accepts a documented risk with a rollback plan. The actual-user and post-cutover acceptance results must be recorded as PASS/FAIL/NOT TESTED, not inferred from Administrator or API reads.

## Planned sequence once blockers are cleared

1. Pin and review the exact app revisions and merge one coordinated Warehouse release; reconcile the ZATCA source differences.
2. Complete permission-writer/matrix review, scope decision, rehearsal and repeatability evidence.
3. Capture a fresh production backup with an identified restore path; record pre-upgrade app/config/access baseline.
4. Schedule Frappe Cloud's in-place Version Upgrade on neosys.frappe.cloud; monitor the site update through completion.
5. Verify the actual Desk routes and core user roles, linked records, integrations and RV80 read-only connection. Reconcile the PM in ERP before syncing the temporary Hazem value.
6. Only after the owner-approved post-cutover checks, perform the small live ZATCA invoice test and cancel it as directed; record the result and preserve evidence.
