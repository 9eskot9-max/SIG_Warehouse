# SIG ERPNext Final Implementation Plan

## Current production and document control — 3 November 2026

The current production Cloud read-back shows `neosys.frappe.cloud` Active on `neoweb-v16`, instance `bench-51251-000014-f1f`, with the latest listed migration successful at 9:02 PM Riyadh. Frappe is 16.54.0 (`2fcb939`), ERPNext 16.53.0 (`9cd11b1`) and HRMS 16.53.0 (`b12d935`). Installed SIG Warehouse is `codex/sig-personal-home-v16` at `6ce8da3`; ZATCA is `codex/v16-b2b-clearance-parity` at `a8f9fb5`; SIG WhatsApp and SIG QR Design are on `v16-migration` at `9bfd1bd` and `39ecff6`. Recheck current Cloud state and source hashes before implementation or deployment.

The [ERP integration master](../Automation%20DB/MASTER-ERP-INTEGRATION.md) is the operating overview; this plan retains the detailed priorities, decisions, history and mandatory permission/persona gates. The owner selected the public SIG Warehouse repository for full copies under the same `ERPNext/Automation DB/` and `ERPNext/docs/` paths on the configured v16 source branch. When editing either local document, update and compare its GitHub copy in the same task; update both for shared facts or decisions. Never commit credentials or secret values. This is an agent workflow, not an automatic background sync. The shorter GitHub release checklist remains a separate practical gate.

Dated entries below preserve historical evidence and may describe earlier v15 production, trial benches, local staging or earlier priorities. They do not override the latest dated verified status. The Cloud migration result does not establish live database customization parity with GitHub or actual-user acceptance. Follow the permission regression mandate in this document and record PASS / FAIL / NOT TESTED.

The installed Warehouse source includes the v16 SIG dock and workbenches, form-layout and HR export reconciliation patches, the Address-linking change and the later Warehouse intake item-creation changes. Treat these as source/revision findings: actual-role access, linked-record behavior and end-to-end acceptance remain to be evidenced. The current GitHub Warehouse branch is ahead of the installed commit by documentation-only cleanup. The other custom apps remain in their own repositories; a Warehouse PR does not contain their source. A local v15-era source archive exists at `D:\erp-v15-legacy-20261103`; the v15-era GitHub default branch remains.

**Owner-directed roadmap correction — 31 October 2026:** Outbound supplier RFQ letters are implemented and deployed inside the existing SIG Warehouse workspace. The operator starts from a native Request for Quotation, enters a supplier WhatsApp number inline on its supplier row, saves the RFQ to create/update a native Supplier-linked Contact, then sends a separate RFQ PDF through Maytapi from the submitted RFQ. No separate contact-management page is part of the workflow. Replies remain manual; Supplier Quotation entry, comparison, PO conversion, email and inbound/reply automation are not part of this release. SIG Warehouse `cb865b1` is installed on the active production site; migration succeeded. Production workflow/persona acceptance, Contact creation, PDF generation and actual delivery are **NOT TESTED** by owner instruction. Follow with improvements to existing SNB payment allocations/advances and current TAWAL held cases, supported by moving verified beneficiary relationships from Am into governed ERP records. Am already contains the mappings; this is a controlled ownership/cutover proposal. See [bounded roadmap and pitch corrections](../Automation%20DB/ERP-AUTOMATION-PITCH-DISPOSITION.md#owner-direction-20261031) and [inline RFQ release evidence](../backups/permission_release_rfq_inline_contact_20261031/release_gate.md).

**TAWAL is operational, not an unbuilt integration:** the 30 October saved run completed `ok`: 209 payments = 166 legacy excluded, 29 WAITING_SNB, 5 WAITING_INVOICE, 7 WAITING_PORTAL, 1 EXCEPTION and 1 DRAFT_CREATED; zero new eligible drafts. Parent/child allocation, retention netting, invoice matching, SNB matching and the local morning task exist. Investigate held groups against current source/ERP evidence before proposing matching changes; do not interpret legitimate waiting states as defects or replay already linked payments. Details: [TAWAL current reference](../Automation%20DB/Tawal/README.md).

**Local planner update — 30 October 2026:** The existing local Field Planner staging now shows the 08:00–10:00 Riyadh planning estimate for a first critical visit in the first-day TCN request list and AI alternatives. It compares the estimate with recorded effective TCN hours and marks covered, conflicting, or unverified. Existing issued TCNs govern actual visits; the planner does not issue them or change the RV80 exporter. Clock-time constraints are not enforced by route selection. No deployment or user acceptance is recorded.

**Field Planner critical-time direction — 30 October 2026:** The owner clarified that critical scheduling is an approximation for planning: use a normal 08:00 Riyadh start plus two hours (08:00–10:00) for the first critical visit, and plan the TCN around that estimate. Actual visits must follow the issued access window. Local staging in `SIG_Warehouse_field_planner` adds the estimate and compares it with recorded effective TCN times, exposing covered, conflicting, or unverified status. It does not issue or alter TCNs or establish actual team arrival; date-based routing still requires PM review for time conflicts. ERP receiving fields and RV80 sender integration remain staged, and no deployment or acceptance is claimed. This supersedes earlier suggestions that the planner should always require completion before 08:00.

**Critical-site upload clarification — 30 October 2026:** The 28 October ERP historical site upload did include site IDs from the RV80 critical list. Its staging recorded 1,818 critical-list IDs among 27,526 sites uploaded, but the uploader sent site identity and coordinates, not critical classification. A 30 October permission-filtered ERP comparison against the 28 October RV80 list found **2,212 of 2,248 site codes** present and **36 not found**; `CRITICAL` was a column header and is excluded. None of the matched records has `planner_critical_status = Critical` or a populated critical source. This confirms that many critical sites were uploaded as site records, while their planner designation was not found. The source list is a dated snapshot; check the current workbook before any sync or correction. See [comparison](../backups/critical_site_id_comparison_20261030.json) and [site upload summary](../../outputs/site_backfill_20261028/summary.json).

**As-Built and return-window read-back — 28 October:** The canary `STE-2026-1016` has a submitted `AUTO_CLOSE` operation dated 25 October, and its line is `CONSUMED_CLOSED`. The current As-Built source remains `complete=false` with 11,670 integrity-error entries across 4,697 lines. This confirms the canary closure, not universal scheduler coverage or workbook acceptance. See [current breakdown](warehouse_asbuilt_closeout_plan.md).

<a id="company-priority-index"></a>
## Priority index: fixes and developments — revised 31 October 2026

**Critical-site read-back — 30 October 2026:** The owner reported the critical-site work completed, but the current read-only ERP `SIG Site` list returned **0** records with `planner_critical_status = Critical` and **0** records with a populated `planner_critical_source`, under `9eskot9@gmail.com`. The API identity had System Manager in the 29 October snapshot and a Company User Permission; this read is permission-filtered and the live RV80 list was not compared. The deployment of the feature is separate from uploading critical-site classifications. The critical-site data upload / comparison remains **unverified and likely incomplete**, not closed. See [read-back](../backups/critical_sites_readback_20261030.json).

**Current correction — 30 October 2026 (supersedes conflicting historical entries below):** The owner reported critical-site work completed; the subsequent 30 October ERP read-back above found no critical classifications, so the data upload is not confirmed. The six historical SNB references were reconciled in the “Review future ERP developments” chat: Am shows `DRAFT_CREATED` with Journal Entries `ACC-JV-2026-02043` through `ACC-JV-2026-02048`, and all five beneficiaries have ledger mappings. They are not a six-row import backlog; draft status is not proof of posting. Do not replay. As-Built: the owner accepts import-period quantities as settled; focus only on a small number of genuinely troubled post-import lines, and treat return/disposition pending in ERP as routine Warehouse review, not proof of a material discrepancy. The old global integrity counts include historical records and are not a current actionable defect count. The 10-day canary auto-close was observed.

This is the consolidated navigation and priority order for significant open work in this plan and the [ERP integration master](../Automation%20DB/MASTER-ERP-INTEGRATION.md). Priority reflects operational impact and dependencies, not a claim that a proposed change has been approved for release. Recheck live state before implementation; dated sections below retain their original evidence. The current 28 October HR correction in the master supersedes older notes below about Sagheer's labels and Umar/Faizan Hanif's bank choices.

**New ERP capability deployed — Warehouse Purchasing & Receiving, 30 October:** SIG Warehouse `e56eb5443fed23f86371e53846f8982331714f34` is installed on the active site. The card/pages are part of the existing SIG Warehouse bench, not a separate bench. The new interface handles routine supplier, item, Material Request, PO and PR work through ERP-native records; WH BAS is not required for this purchasing/receiving workflow. The separate As-Built and SitesDB workbook flows remain. `/app/purchasing-receiving` and `/app/purchase-receipt-pricing` render for Administrator. The actual failure was unsupported `.finally()` on Frappe's `frappe.call()` deferred, fixed in both page scripts. The post-migration permission diff against the prior intake snapshot is zero additions/removals. Warehouse/Purchase persona workflow, linked-record defaults, supplier/item creation, configurable AI prompt, draft/submit policy and receipt valuation remain **NOT TESTED**. Evidence: [release gate](../backups/permission_release_warehouse_intake_20261030/release_gate.md).

**Petty Cash Status report — deployed source clarification:** the current SIG Warehouse page places a `PC Top-up` funding line above its cycle receipts and shows three horizontal totals (receipt total, approved total, remaining balance). The balance is top-up minus approved receipts; it does not repeat top-up in a separate totals row. A local repair was prepared for the unresolved-sender error that left the Employee selector stuck on “Loading employees”; the owner later reported it deployed, but the matching release/read-back and Finance-user workflow have not been verified. Finance/ordinary-user visual acceptance of the cycle summary remains open.

**Release correction — 2026-10-28:** `sig_warehouse` commit `5d3696f67cecca69adf111acae2f5fe85c4d5736` (client-reminder validation and Field Visit GPS changes) is now installed on active production site `neosys.frappe.cloud`. Corrected Cloud pipeline `865bj6iisr` completed Success; installed-app read-back returned the target hash. Backup `5s981cv484` preceded the successful release. Permission snapshot comparison (`backups/permission_release_client_field_20261028/before_current.json` → `after.json`) showed 0 additions and 0 removals. The Client Collections Desk route and public `/field-visit` route both rendered after deployment; these are route checks only. Actual-user fresh-session, linked-record, send-delivery and GPS-trigger acceptance remain **NOT TESTED**. The first malformed deploy-and-update request created failed pipeline `52akdvf54l` because its `sites` entries were strings; the corrected request supplied site dictionaries. Full evidence: [client and Field Visit release gate](../backups/permission_release_client_field_20261028/release_gate.md).

**Release correction — 2026-10-29:** SIG Warehouse `41cde77c429a88cf9231d08d51b8d235501e514e` is installed on active `neosys.frappe.cloud` (`bench-38491-000296-f1f`); Cloud pipeline `fshn8dor4l` and site migration succeeded. The release adds one-way Todoist delivery for newly created ToDos assigned to `9eskot9@gmail.com` and selected SNB import errors. The live App Connections route rendered with the existing Todoist Inbox connection. No production task was created for acceptance; actual ERP-to-Todoist delivery, local SNB run delivery, and actual-user fresh-session workflow remain **NOT TESTED**. The snapshot diff is documented in [the Todoist release gate](../backups/permission_release_todoist_task_delivery_20261029/release_gate.md).

**Five-point review — 29 October 2026, updated after Cluster Deploy:** (1) The earlier six-row uncertainty is superseded by the 30 October reconciliation above: six entries already show draft Journal Entry numbers in Am; do not replay. (2) The SIG PC review page now includes the scoped linked-Journal-Entry status summary using the existing `pc_journal.transaction_status_report`; deployed in SIG Warehouse `98a7d8b`. (3) `D:/rv80/deployed/sitesdbImport.bas` contains the preview/apply critical-site calls in the SitesDB import flow, but the active workbook module and live sync identity/result remain unverified. (4) The Operations Handover projection now creates a shared `Handover documents` next action when GCL/FIS/MGCL evidence is absent, with later As-Built/invoice evidence suppressing stale work; deployed in `98a7d8b`. (5) Faizan Rasheed's concise first contact remains the intended onboarding norm (full legal name, email, IBAN, known phone); the staged Candidate Intake still needs protected IBAN handling before it can implement this end to end. No tests or persona acceptance were run for this release at the owner's direction.

**Cluster release — 29 October:** Isolated worktree based on `372321d`; reviewed commit `98a7d8b` contains only the SIG PC review and Operations Handover source changes. Pushed to SIG Warehouse `main` and deployed using the GPT Frappe Cloud dashboard; only SIG Warehouse and `neosys.frappe.cloud` were selected (the unrelated Drive update was left out). Cloud backup job `d8vgm6upmk` succeeded before deployment. Cluster pipeline `3b7girj653` completed Success in 6m 37s; production site is Active on `bench-38491-000299-f1f` and the site Apps record reads SIG Warehouse `98a7d8b`. The site Updates page recorded Pull Success; the release changes no DocTypes, fixtures or patches, so no schema migration was required. Permission before/after snapshots cover the same 20 Pages, 42 Workspaces, 22 Reports, 52 effective DocTypes, 25 Role Profiles, 55 enabled users and 47 modules; the captured access-state diff has zero additions or removals. See [release evidence](../backups/permission_release_pc_status_handover_20261029/release_gate.md). Tests were not run at the owner's direction; a prior pre-release stage-suite run had 33 PASS / 1 FAIL because its Frappe stub lacked `get_list`. Do not treat functional, role or persona acceptance as passed. Candidate Intake and historical SNB reconciliation are not included in this release.

### Fixes — highest priority first

1. **Critical-site classifications — resolve the data path.** The feature endpoint is deployed, but the 30 October ERP read-back found zero marked Critical sites and zero populated critical sources. Compare the current RV80 SitesDB source with ERP, confirm the active workbook module and sync identity, then correct only verified differences. Do not repeat the already-deployed feature build or assume historical site-ID upload included classification. See [critical-site read-back](../backups/critical_sites_readback_20261030.json) and [comparison](../backups/critical_site_id_comparison_20261030.json).
2. **Warehouse Purchasing & Receiving — operator acceptance.** The page-start defect is fixed and the app is deployed at `e56eb54`; both routes render for Administrator. Later, in fresh sessions, Warehouse/Purchase roles should verify native supplier/item lookup, linked records/defaults, draft creation, price completion and submission boundaries. Do not treat the rendered route or permission snapshot as workflow acceptance. No production intake was created for testing. See [release gate](../backups/permission_release_warehouse_intake_20261030/release_gate.md).
3. **Client Collections — reconcile the previous attempts.** Owner reports that sending works, but `CCREM-2026-00001` was previously left `Sending` without provider acceptance evidence and the current state of both earlier reminders has not been freshly reconciled. Read current draft/component state and Maytapi logs before retrying; do not duplicate-send. The persistent reminder, manual WhatsApp destination, invoice attachments and send button are already deployed. PDF rendering, email and fresh Accounts-persona acceptance remain open. See [Collections status](#client-collections-status) and [release evidence](../backups/permission_release_client_collection_inline_send_20261028/release_gate.md).
4. **As-Built — narrow post-import review only.** Import-period quantities are settled by owner direction. Review only specific genuinely troubled post-import lines. Pending return/disposition declarations are normal ERP Warehouse work, not a separate discrepancy list; the 10-day auto-close canary was observed. The ABDraft final-population/mapping contract and workbook import acceptance remain separate open gates; do not rebuild the global integrity list or raise pending ERP declarations to Tahir as material discrepancies. See [current findings](#asbuilt-review-20261029) and [Warehouse closeout](warehouse_asbuilt_closeout_plan.md).
5. **Persona acceptance — cross-cutting.** Complete fresh-session linked-record workflows for the actual affected Finance, Warehouse/Purchase, Operations, HR and integration roles. Admin routes, successful deployment and zero permission delta are not ordinary-user acceptance. See [mandatory permission acceptance](#permission-regression-mandate) and [deployment guide](deployment_permission_guide.md).
6. **Employee funding and custody — targeted, mostly deferred.** The six historical SNB references already have JE numbers; do not replay them. Reconcile future beneficiary exceptions against stable Employee identity and `Employee.custom_custody_account`; contact follow-up is owner-deferred. Piran and Am's beneficiary mapping are recorded as complete. Review Sagheer's primary Account key only through Finance's safe renaming process. Do not infer identity from a similar name. See [employee account boundary](#deferred-employee-account-and-task-app-integrations) and [HR master](../Automation%20DB/MASTER-HR-AUTOMATION.md).

### Developments — highest priority first, revised 31 October 2026

**Next development planning:** Start with the read-only discovery and candidate design in [SNB supplier payment allocation plan](snb_supplier_allocation_plan_20261031.md). The existing supplier Payment Entry builder omits invoice references, but actual Finance allocation practice and the size of any manual queue remain to be established before implementation.

1. **Supplier RFQ outbound delivery — deployed; acceptance deferred.** The **Supplier RFQs** card is in the existing SIG Warehouse Workbench. Use native Request for Quotation records; type each supplier's WhatsApp number directly into that RFQ's supplier row, then save so ERP creates/updates a Supplier-linked native Contact and reuses that number later. Send a separate RFQ PDF per selected supplier from the submitted RFQ through SIG WhatsApp / Maytapi with per-recipient delivery status and guarded retry. This supersedes the earlier number-entry dialog; the legacy RFQ-specific number record is lookup-only compatibility for existing data. Email and automated replies are out of scope; suppliers' replies are handled manually. Do not claim a delivered message until the Maytapi workflow is actually accepted. Owner deferred all tests; fresh-session route/persona, linked Contact, PDF, queue, provider delivery and retry acceptance remain **NOT TESTED**. See [latest release evidence](../backups/permission_release_rfq_inline_contact_20261031/release_gate.md). Future purchasing work may add quote capture/comparison and native PO draft conversion as separate stages after owner direction and actual-user acceptance.
2. **SNB/ERP payment allocation and reconciliation.** Extend the existing payment workflow against Purchase Invoices, approved advances and unallocated payments. The inspected SNB supplier payload has no invoice references; check how Finance allocates these today before modifying it. Use native Payment Reconciliation for submitted payments, prevent duplicate SNB/TAWAL postings, and diagnose actual TAWAL held groups. Existing PR/PI/purchasing and TAWAL scripts are implemented, not new build items. Whole-PDF extraction is optional later work on existing intake/quotation workflows.
3. **ERP ownership of verified beneficiary associations.** Am already holds beneficiary mappings. Reconcile and seed verified Employee/Supplier and bank-beneficiary relationships into permission-safe ERP records, preserve multiple accounts/purpose exceptions and derive the employee ledger from `Employee.custom_custody_account`. Complete this prerequisite before changing affected importer resolution; use Am as capture/staging and a compatibility mirror through controlled cutover. No new parallel employee/account register.
4. **Field Planner critical timing and TCN visibility.** The 30 October staging record shows an 08:00–10:00 Riyadh estimate for the first critical visit and compares it with recorded effective TCN hours. This is a planning approximation; actual visits must follow the issued TCN. Reconcile later planner release evidence before treating local work, RV80 sender integration, critical designation import, clock-time route handling or actual-user acceptance as open builds. See [planner staging](field_planner_improvements_now_operations_future_20261027.md).
5. **Operations stage/task coverage.** Preserve the deployed shared Handover next action and evidence-driven suppression. The remaining recorded gaps are Initial/Plan applicability, named PM/coordinator routing and verified Site/Cycle identity exceptions; do not rebuild the Workbench or duplicate the native task/evidence ledger. See [Operations structural review](operations_petty_cash_structural_review_20261019.md).
6. **Employee onboarding and Candidate Intake.** Recheck the staged Candidate Intake against later releases before resuming. Use the restricted intake, verified consent/identity path and protected sensitive data handling. Existing onboarding/checklist assets do not themselves establish an approved Employee/User, custody link or consent to contact. See [HR master](../Automation%20DB/MASTER-HR-AUTOMATION.md).
7. **SNB/Todoist exception coverage.** Todoist connection and ERP outbox are deployed and the owner reports working delivery. Verify specific SNB runner failure/review-skip coverage before extending it; do not reopen the connection setup or route all Error Logs/historical runs. Recorded persona/retry acceptance is a separate completion gate.
8. **Attendance and HR follow-up.** Unify today's attendance, history and exceptions only after checking existing page/assets and verified historical check-ins. Employee beneficiary/contact requests and Riaz remain deferred until the owner resumes them.
9. **Later scope.** Photo/RFI, advanced KPIs, saved PM plans and optional reports remain deferred. Todoist, SIG Letters, Client Collections, MIR intake, purchasing intake and field-visit lookup have deployed implementations; raise only concrete gaps in their current behavior.

The older HR follow-up table immediately below is retained as history; its numbering does not override this consolidated priority index or the newer correction in the integration master.

### Whole-company pending-work crosswalk — 30 October 2026

This crosswalk covers the principal workstreams throughout both documents. **Recorded** means supported by dated evidence, not independently reverified today. **Recheck** means a historical task may already have been completed; establish a current reproducer before building or writing data. Existing owner deferrals and closed decisions remain in force.

| Domain and priority | Current documented reality | Remaining action and location |
| --- | --- | --- |
| **1. Finance, tax and migration** | ZATCA production integration is technically proven; historical migration is provisionally closed, and the full-history ZATCA pilot is optional. Old pre-launch G1–G5 language is historical, not proof that production is disabled. | Finance to verify 2025 sign-off, 2026 month-close ties, AR/AP openings and held advances, deferred source exceptions, VAT, stock reconciliation and period controls. Verify the actual VAT/QR, rejection, retry, archive and certificate-renewal controls still requiring business sign-off; do not repeat already closed clearance/QR work. See [G2–G5](#5-workstreams) and [finance sign-off](#9-change-control-on-this-plan). |
| **2. Warehouse stock and purchasing** | ERP is the stock writer; dispatch, return declarations, native purchasing paths and the new SIG Warehouse Purchasing & Receiving card are deployed. SIG Warehouse `e56eb54` fixes both page crashes; the routes render for Administrator. Routine ERP purchasing/receiving does not depend on WH BAS. | Defer Warehouse/Purchase-role transaction acceptance until scheduled; do not test with real purchasing records. Continue only targeted post-import As-Built issue review and final ABDraft population/mapping/import acceptance. Pending return declarations remain in ERP, not a separate discrepancy list. Physical-count only proven stock discrepancies. Item-master cleanup remains owner-deferred. See [warehouse closeout](warehouse_asbuilt_closeout_plan.md), [purchasing loop](#purchasing-loop), and [intake release gate](../backups/permission_release_warehouse_intake_20261030/release_gate.md). |
| **3. Client billing, collections and retention** | Invoice-to-cycle evidence/linking is installed; the owner reports client reminder sending works and a later print correction is deployed. Historical print, retention and progress-billing design is not proof of current practice. | Confirm remaining Collections workflow and persona acceptance and reconcile historical stuck drafts if still needed. Monitor Tawal invoice-row linking and BAS identity. Finance must inspect an issued invoice and decide the retention/VAT structure before implementing its accounting workflow; confirm whether print/layout and payment terms still have a real gap. See [Collections](#client-collections-status), [invoice linkage](../Automation%20DB/MASTER-ERP-INTEGRATION.md) and [retention](#retention-decision). |
| **4. Employee money and petty cash** | Employee-scoped PC review creates a linked draft JE; Finance submits. The PC Status report includes linked-JE status and a cycle layout with the funding top-up above receipts and three horizontal cycle totals (receipt total, approved total, balance). SIG Warehouse `98a7d8b` includes the deployed PC review summary; current source `e56eb54` carries the latest status page. | The cycle layout/source is present, but do not claim the complete report has been accepted by Finance or ordinary users; verify its live visual/current route during later persona acceptance. SNB continues to need verified beneficiary-to-Employee identity for future exceptions; six historical SNB references already have JEs and must not be replayed. Piran is linked to `132262`; employee contact follow-up remains deferred. See [PC structure](petty_cash_funding_cycle_structure_20261020.md) and [HR master](../Automation%20DB/MASTER-HR-AUTOMATION.md). |
| **5. Permissions, identities and security** | Existing roles, profile-managed permissions and PC scope are in use. The 28 October access snapshot still reports module-profile assignments and blocked modules for 33 enabled users; the older blanket assertion that all profiles were retired is not current proof. | Verify effective role/profile/User Permission and module visibility per actual person, preserve approval caps and HR privacy, resolve named-user activation and integration ownership, and complete the mandatory persona gate. Credential hardening is a separate documented follow-up; the owner explicitly deferred Maytapi token rotation. See [permission mandate](#permission-regression-mandate), [incident register](permission_incident_register.md) and [deployment guide](deployment_permission_guide.md). |
| **6. Site/cycle evidence and Operations** | MIR intake, invoice linking, evidence progression and stage projections are live. The Handover documents action/suppression correction is deployed in `98a7d8b`; remaining task coverage and some Site/Cycle links are incomplete or unverified. | Correct Initial/Plan applicability and named routing; resolve specific identity/evidence exceptions. Verify BAS identity and per-operator outboxes after the workbook merge; retire the remaining MIR logger only after preserving the approved ERP result flow. Do not replay pre-evidence MIRs or invent duplicate cycle/task ledgers. See [Operations structural review](operations_petty_cash_structural_review_20261019.md), [first effort](operations_first_effort_plan_20261020.md), and [site evidence architecture](site_evidence_architecture_20261013.md). |
| **7. RV80 setup, critical sites and Field Visit** | The owner reported merged RV80 assets and Setup revision 8; compile and workflow acceptance are not independently complete. Critical-site feature was deployed; 30 October API read-back found zero marked Critical and zero sourced sites. Current workbook comparison remains open. The Field Visit GPS change is installed; field-user acceptance remains open. | Compare the actual workbook critical list against ERP and determine why no classifications appear in the API read-back. Verify the field-user lookup and WhatsApp flow on the installed GPS change. Keep the planner and coordinates in ERP. See [merge closeout](sigpc_rv80_merge_plan_20261025.md), [critical sync staging](field_planner_improvements_now_operations_future_20261027.md), and [PERM-20261028-01](permission_cases/PERM-20261028-01.md). |
| **8. HR, compliance and attendance** | HR onboarding checklist, compliance expiry infrastructure and attendance assets have release evidence; Candidate Intake and the proposed unified attendance workflow are separate staged work. | Verify HR/persona access and actual Muqeem refresh, reconcile attendance history and user activation, and complete restricted Candidate Intake/consent before creating accounts or sending candidate follow-ups. See [HR master](../Automation%20DB/MASTER-HR-AUTOMATION.md) and [Unified Attendance](unified_attendance_system.md). |
| **9. Fixed assets and tools** | The general Asset skeleton, categories and custody fields are deployed; this does not constitute an accepted legacy asset register. | Finance/Admin to review capitalization flags, import/verify the legacy register and agree useful lives before depreciation; tool threshold and optional reports/WH bridge remain separate decisions. See [fixed-asset gates](#fixed-asset-gates). |
| **10. Field Planner and KPIs** | Candidate/cutoff logic, map and first KPI set are deployed. The 30 October 08:00–10:00 critical-visit estimate is local staging only; issued TCNs govern actual access. Critical designation import remains unverified. | Complete the critical-list ERP sync comparison, then finish effective TCN-window visibility, position quality and PM review; assess route feasibility and long movements. No TCN generation or arrival-time enforcement follows from the estimate. Persistent KPI rollups and new metrics are later. See [planner staging](field_planner_improvements_now_operations_future_20261027.md), [planner handoff](../Automation%20DB/MASTER-ERP-INTEGRATION-LEGACY.md#master-snapshot-20261031-cleanup), and [trace review](field_planner_decision_trace_run_review_20261027.md). |
| **11. Item master, interfaces and integrations** | Item catalogue refresh and primary workbook merger were owner-reported. Native ERP Purchasing & Receiving now provides supplier/item lookup, draft workflow and editable AI item-creation prompt settings; the core route bug is fixed in `e56eb54`. Todoist task delivery is deployed and connected to Inbox for `9eskot9@gmail.com`; no production task has yet confirmed external delivery. | Later verify actual Warehouse/Purchase roles and tune the ERP-held AI prompt through normal operations; do not create a second invoice/item register or revive WH BAS for routine PO/PR work. Observe a naturally occurring Todoist task and confirm Delivered; do not create test work solely for acceptance. See [intake release gate](../backups/permission_release_warehouse_intake_20261030/release_gate.md), [deferred fixes review](#deferred-fixes-review), and [Todoist release evidence](../backups/permission_release_todoist_task_delivery_20261029/release_gate.md). |
| **12. Deferred and optional scope** | CRM is parked; Photo/RFI, advanced stock count/custody/bulk writers, expanded KPI/reporting and broad evidence routers are deferred or proposals. | Promote only a distinct owner-approved operational gap. Do not revive retired RV80 planning/dashboard paths, rebuild live MIR/invoice integrations, or treat old local patches as a release. See [automation disposition](../Automation%20DB/ERP-AUTOMATION-PITCH-DISPOSITION.md) and [master §9](../Automation%20DB/MASTER-ERP-INTEGRATION.md). |

**Verification discipline:** The dated counts and historical assignments above are evidence, not current live totals. On 30 October the Cloud site Apps record was refreshed and confirmed SIG Warehouse `e56eb54` on active `neosys.frappe.cloud`; the Warehouse intake and receipt-pricing routes rendered as Administrator. Post-migration permission comparison against the previous intake snapshot returned zero additions/removals. Warehouse/Purchase-user workflow and all business transactions remain NOT TESTED. Recheck live state before action. This index does not authorize an accounting or stock write.

<a id="asbuilt-review-20261029"></a>
### As-Built and pending ERP declarations — 29 October 2026

The owner confirms import-period quantities are to be treated as settled and asks to focus on post-import dispatches. The historical 29 October read-only review identified 353 candidate post-import Material Issue lines using creation after 15 September and excluding records labelled backfill, correction, reconciliation or proof. This is a working classification, not a verified universal migration cutoff. All 353 have site, linked Material Request and PO/BA in the exported source; two separately identified proof transactions have zero As-Built quantity.

**Historical ERP snapshot, not a current issue count:** 106 lines across 14 DNs created before 14 October still show `return_pending=true` on fresh source read-back. This means a line has not been resolved by a return, custody declaration or close-as-consumed action; it does not prove that a physical return exists. Those pre-policy DNs are outside the automatic closure rule. Normal Warehouse practice is to review the actual material status and use ERP's existing Declare Return, Declare Custody or Close as Consumed action as appropriate; do not create a separate issue or send a spreadsheet solely for this pending queue. The list is retained as supporting reference: [106 line details](../backups/asbuilt_review_20261029/pre_policy_pending_issue_lines.csv). Their ERP documents are STE-2026-0901, 0903, 0905, 0929, 0939, 0962, 0963, 0965, 0966, 0973, 0975, 1007, 1008 and 1009. The remaining 92 pending post-import lines in that snapshot were within their return windows on 29 October; recheck against the current date rather than considering them permanently within the window.

**Separate system work:** the global `sigpc_abdraft_v1` response still reports `complete=false` because it includes historic records without the site/PO/MR details required by the importer. Owner acceptance of historical quantities is not itself a site/PO mapping. RV80's local `D:/rv80/deployed/AsBuiltCycle.bas` was updated to log a posting-date-filtered diagnostic rather than the full global error list, but it still preserves ABDraft on incomplete ERP data. The date filter is diagnostic, not an authoritative import marker. The BAS source change has not been imported into the workbook or functionally tested. A source-contract change that identifies the approved historical population and handles its mapping safely, plus workbook and Warehouse persona acceptance, remain open; no partial rebuild or final AB write is authorized by the incomplete source. [Source read-back](../backups/asbuilt_review_20261029/source_latest.json) and [post-import candidate lines](../backups/asbuilt_review_20261029/post_import_issue_lines.csv).

### Deferred employee beneficiary and contact follow-up — 29 October 2026

**Owner direction: defer contact and follow-up for later.** Do not send employee onboarding, bank-choice or HR phone requests until resumed; the proposed messages were shown for review and no approval to send them was recorded. Riaz remains separately deferred. When resumed, ask the employees or HR for verified contact and beneficiary information, compare Am beneficiary records and the full ERP chart, resolve identity conflicts, and link or create appropriate custody accounts only with supporting evidence. Do not treat a shared bank account or similar name as proof of identity.

The 29 October ERP read found 15 active Employee records without a custody link after Piran: Muhammad Akram Sardar Muhammad (`HR-EMP-00012`), Adil Sher Rehmat Ali (`00023`), Muhammad Arslan Muhammad Aslam (`00040`), Sajjad Raza Sabtain Ali (`00041`), Mushtaq Ahmad Muhammad Hayat (`00043`), Mohammed Adnan Irsahd (`00051`), Umer Rafiquec (`00054`), Imad Ulllah Waheed (`00059`), Muman Bhatti Ramzan (`00060`), Muhammed Riaz Abdul Sattar (`00061`, separately deferred), MG (`00001`), and four WhatsApp Sender placeholder records (`00062`–`00065`). The latest Am review found no clear beneficiary for the named employees; Imad's ERP bank details match a beneficiary mapped to Ghlzar, an identity conflict to resolve. A missing Employee link does not establish that no chart ledger exists. Re-read current ERP and Am before resuming.

**Completed account reconciliation:** Piran (`HR-EMP-00015`) has new linked account `132262`; the duplicate guard's candidate `132216` is linked to a different Employee. In Am, Piran's beneficiary points to `132262`; Zahidurrehman and Imran's beneficiary classifications were changed to `JE_EMPLOYEE` and linked to `132256` and `132261`, respectively. Am's `pc_employee_accounts` contains `132256`–`132262`. ERP and sheet read-backs succeeded; a subsequent SNB import and historical transaction reconciliation remain **NOT TESTED**. Awad's Employee bank details and Am beneficiary differ and require later verification. See [Piran account read-back](../backups/custody_review_20261029/piran_creation_readback.json) and [pre-change inventory](../backups/custody_review_20261029/current_before_piran.json).

### HR, petty cash and SNB follow-up — 28 October 2026

This is the working backlog for the recent employee-account and onboarding changes; dated entries below retain their historical evidence. Recheck live state before making changes.

| Priority | Pending work | Current evidence / completion condition |
| --- | --- | --- |
| 1 | Release Candidate Intake and contact Faizan Rasheed | Local SIG Warehouse branch `codex/candidate-intake-maytapi`, commit `a552603`, is not pushed or deployed. Reconcile the production revision and permission writers, take the required backup and baseline, exercise migration repeatability and actual HR Manager access, then create the intake from his sender record, review any remaining collisions and send the trilingual consent prompt. Wait for consent before follow-up or Employee creation. |
| 2 | Bank choices and deferred contacts | Umar and Faizan Hanif replied; the recorded choices and matching Employee bank details are in the HR master. Do not resend. Verify Zaheer's mobile when contact follow-up is resumed. Mohammed Algain's account mapping remains deferred. |
| 3 | Employee ledger and identity reconciliation | Piran now links to `132262`; Sagheer links to `132255` and the Arabic display labels were corrected, although the Account database key retains the old label. Remaining employee contact and beneficiary checks are owner-deferred; see the 29 October section above. |
| 4 | Complete SNB unresolved transaction recovery | Reconcile the original six skipped rows for five beneficiaries against the live ERP and Am records; document each actual resolution and any remaining row. Build or verify the requested Google Sheet unresolved queue, with stable transaction IDs, reason/status, safe retry and idempotent ERP read-back. Do not claim the five transactions or six rows were posted until verified. Reconcile approved bank-specific ledger exceptions with Finance. |
| 5 | Todoist task delivery — deployment closed; acceptance open | SIG Warehouse `41cde77` is deployed; ERP ToDos assigned to `9eskot9@gmail.com` and the two selected SNB import issue categories queue through a private outbox to Inbox. Delivery is one way. No production task was created for testing, so actual task delivery, retry/reconciliation and fresh-session workflow remain NOT TESTED. Observe the next real eligible task and confirm Delivered before closing acceptance. See [Todoist release gate](../backups/permission_release_todoist_task_delivery_20261029/release_gate.md). |
| 6 | Unify employee accounts across PC and SNB | Complete the verified beneficiary-to-Employee association, derive the custody ledger from Employee for employee funding, preserve approved exceptions, and review legacy clearance/funding overlap. The SNB ledger guard is local and does not prove beneficiary identity; deployment and Finance persona acceptance remain pending. Keep full bank details in appropriately restricted storage. |
| 7 | Attendance access and history | Production attendance page assets and dashboard have a release record. Verify current access for HR, Hamid and Mohammed Algain, daily and per-person history, then reconcile and backfill verified legacy check-ins idempotently. Formal attendance/shift policy remains a separate later decision. |
| 8 | Maytapi and release acceptance | ERP controlled test was queued; the later two bank messages were direct-provider sends and have no ERP Message Log records. Deploy the staged provider response validation with the Candidate Intake release and check the real HR workflow. Token rotation is deferred per owner. Complete the applicable permission snapshots and persona checks; Admin success alone does not close them. |

**HR-D11 update — 2026-10-28:** Sender staging `966503084408` remains unlinked and Staged, but its earlier stale aggregate is now corrected after applying the installed refresh rule to the live rows: 11 transactions, first 2026-10-16, last 2026-10-26; 9 Needs Review / 2 Closed and 10 Pending / 1 Archived. I corrected its note to mark the old Faizan Hanif identity claim as superseded while preserving history. No transaction was changed or reassigned. Candidate Intake is staged in local commit `a552603` (`codex/candidate-intake-maytapi`), not pushed/deployed. Umar/Faizan Hanif bank-choice questions were accepted by Maytapi direct API; replies and handset delivery are unconfirmed. ERP's controlled Maytapi send succeeded; owner deferred token rotation. Remaining: complete permission baseline, staging repeatability and actual HR Manager acceptance; create the restricted Candidate Intake and send Faizan Rasheed the neutral trilingual consent prompt only after the documented phone-collision review.

**Employee/receipt reconciliation — 2026-10-28:** Live read of `SIG PC Transaction` confirms the sender ending `4408` has 11 transactions: 9 Needs Review and 2 Closed; one of the 11 is archived. All remain keyed to the phone, and the sender staging row remains unlinked; its aggregate count and date range have since been reconciled and corrected. Sagheer's Employee (`HR-EMP-00037`) now links custody account `132255`, but both the Employee Arabic name and ledger Arabic label say Muneeb Hassan. Review and correct the identity master and ledger label together before treating that association as clean. Piran (`HR-EMP-00015`) still has no linked custody account; the duplicate guard remains unresolved. No receipt or account was changed in this read-back.

**Maytapi retest — 2026-10-28 20:50:** The HR sender's explicit test mode targeted the configured test number ending `0067`. ERP returned one send and `Maytapi Message Log` `06i4o3e1i2` recorded `QUEUED` with a provider message ID and no error. The token was therefore decryptable for this attempt; what changed since the 27 October failures is not established. Handset delivery is unconfirmed. The HR text sender still needs response-body validation before a provider error delivered with HTTP 2xx can be reliably treated as failure.

**Employee bank / petty-cash account reconciliation — 2026-10-28, partial:** Owner-selected beneficiaries are Abdelrhman (Al Rajhi ••6240), Bilal (Al Inma ••0000), Muneeb (QPay ••8903), and Abdulraheem (SNB ••3000). Their Employee records already have custody ledgers and their Am beneficiary rows already point to those Employee ledgers. Five exact-name employees without a custody link were processed through the guarded `sig_hr_create_custody_account` method: Arslan (`132252`), Mahmoud Kamal (`132253`) and Arshad (`132254`) were created, linked on Employee, and their Am `erp_party` rows updated; Sagheer may have completed during an interrupted API run and needs read-back; Piran was blocked by the duplicate-ledger guard and remains unresolved. The live ERP API then returned Session Stopped / 503, so remaining Employee preference-field updates were not verified. No full bank number or IBAN was written: Employee’s standard bank account fields are permlevel 0. Maytapi confirmation questions for Umar and Faizan Hanif were accepted by direct API later on 28 October; device delivery and replies remain unconfirmed. The earlier encryption failure is no longer reproducing after the controlled ERP test send. Friday's warehouse Stock Entry messages were `QUEUED`; the ERP-side decryption failure is a later, distinct state. See HR-D7–HR-D10 below. Mohammed Algain remains deliberately deferred.

**Field Planner candidate/cutoff status — updated 28 October:** The [candidate and cutoff rules](field_planner_candidate_cutoff_handoff_20261026.md) were deployed in `7ede17a`; the earlier statement here that their implementation and deployment were pending is superseded. Fresh persona and full functional acceptance remain NOT TESTED. Later critical-site timing, verified effective TCN windows and the other improvements in [planner staging](field_planner_improvements_now_operations_future_20261027.md) remain separate work.

**Site:** https://neosys.frappe.cloud (target) · https://alqain.flexsofts.com (legacy source)
**Company:** Salah Ibrahim Algain Contracting Company Ltd (SIG)
**Standing access gate — 2026-09-29:** every code/template/configuration edit follows
[§6B.0a: mandatory permission acceptance](#permission-regression-mandate). Baligh's fresh-form
Sales Taxes and Charges Template denial is **fixed live and re-tested twice, 2026-09-29 21:10**:
Accounts User now has read-only template access. The original verification file is not present in this checkout; retrieve it before treating this dated note as current acceptance evidence.

**Plan version:** 4.28 — Field Planner candidate/cutoff development handoff staged; critical-site visiting hours deferred (2026-10-26). Previous 4.27 — Field Planner production integration repair (2026-10-26; details in the final current-reality entry). Previous 4.26 — SIGPC employee-phone onboarding and ignored-sender closure gate recorded (2026-10-15); phone `966564480025` remains unmatched until its employee phone is entered in ERP and verified. Previous 4.25 — Warehouse 10-day return-window production release recorded (2026-10-14); the first scheduled closure and Warehouse-only persona acceptance remain unverified. Previous 4.24 — owner disposition reconciliation (2026-10-14); no deployment or acceptance gate changed. Previous 4.23 — Site/Cycle identity reconciliation is deferred; the 2026-10-13 audit found the deployed Operations Workbench only partially implements the owner-approved stage-task workflow, including role-to-person routing and closure work. The deployed Site connection slice remains recorded below, and the audit corrected the E4 escalation-ToDo status. Previous 4.22 — agent knowledge routing added (2026-10-02): seven task-routed skills in `.claude/skills/` and `docs/learning_loop_distilled_index.md`; master §0.5. No gate or acceptance criterion changed. Previous 4.21 — **DN/MR numbering steps 4/5 provisionally closed live** (2026-09-29): Warehouse allocator and legacy suffix floors deployed, 15 conflicting vouchers renamed with originals retained, WhatsApp matcher deployed, production hashes and Desk route verified; first real partial dispatch remains the live outcome check. Previous 4.20 (2026-09-28): Tawal agreement-to-canonical-Project-to-invoice-map ownership, 34-BA verification and future-agreement onboarding controls in §0.2a. Historical content remains in the legacy archive.

**SIGPC sender disposition — 2026-10-15:** Keep `966564480025` unmatched/ignored while no verified employee phone is recorded in ERP. During onboarding, enter the employee's verified number on the ERP Employee record (`cell_number`) or an Employee-linked Contact phone. The live sender resolver reads those ERP sources, so reopening the review page should map historical receipts when the number becomes uniquely associated. Verify that the number resolves to exactly one Employee and review the previously unmatched receipts before closing this item or sending any onboarding message. Do not invent a person match or send while it remains unmatched.
**Owner disposition — 2026-10-14:** ERP invoice-to-Site/Cycle linkage, evidence posting/progression, and MIR-to-ERP intake are implemented. The PM As-Built BOQ task (4a) is deployed. The 3c Warehouse return policy is deployed: Warehouse must record each actual return against its DN in ERP within 10 calendar days of that DN's posting date; any undeclared balance is treated as no return/consumed and auto-closes from day 11, independently per DN. This does not create a new Operations task or quantity gate. The live As-Built ERP source endpoint returns the canary line, but the full export remains incomplete and the VBA/workbook import is not accepted end to end. See [Warehouse closeout detail](warehouse_asbuilt_closeout_plan.md). Broader Operations task-queue coverage and Photo/RFI work are deferred; refine Planning around per-WO scope clarification using Mapping; finalize KPI measures and display in ERP. This is a scope/status note and does not close the first auto-close check, Warehouse persona acceptance, or full As-Built import acceptance.

**Warehouse return-window production check — 2026-10-14:** SIG Warehouse `f0869f44ad0b4f4e937c9752a9b64e9d0cffdd36` was built and migrated on `neosys.frappe.cloud` (Cloud pipeline `dv46ju1r38`; site migration `67v17irecv`). A backup preceded the update (`3t9ivpj9qq`), and the captured permission diff had zero additions/removals. Canary `STE-2026-1016` / `DN26-1136-1` posted 0.01 Pcs E-TPE against `MR-26-1136`; its MR line remains partial with 0.99 open. The normal WhatsApp document was queued. The ERP As-Built source response contains this line with no canary-specific integrity error, while the global response remains `complete=false` with 11,670 integrity errors. For the canary, 24 October is the final declaration date and 25 October is the first eligible automatic closure date; no scheduler run has yet been observed. The canary was submitted by an ERP Admin-role API identity; Warehouse-only persona acceptance remains NOT TESTED. The canary's Stock Entry line also has a blank standard `project` field despite the linked MR line carrying `WO-2026-0037`; record for separate review, not as a blocker to the 10-day closure check.
**Status:** ZATCA production integration is proven and the target ledger is flat. The agreed next action is a backup-protected, optional full-history pilot from the Flex ERP period onward (expected from 2024), using the legacy-import ZATCA control. It must reproduce the 31 December 2025 Flex account balances before the programme commits to importing the full population; the prior opening-plus-2026 route remains the documented fallback.

**Field Ops core closeout audit — 2026-09-20.** Project Progress P1, native comments, the SIG Field Ops workspace links, the management-facing BAS Delay Rules page, and the read-only Insights dashboard are live and read back successfully. The live `SIG Field Ops Settings` record is consistent with the documented setup (`30/14` fallback SLAs, all four BAS delay checkpoints enabled, `min_sample=8`, `closed_window_days=90`, and effective temporary-scope escalation at 14 days). E5 remains an acceptance gate, not an ERP build gap: the connected TCN-MDT workbook currently has historical rows through January 2026 and no new populated TCN row after the planned-field transport, so no real planned-field read-back is claimed. E7 is now closed after the owner waiver: the RV80 dashboard refresh/repair controls were hidden reversibly while `Close Sites` and category filters remained visible. FO3 conformed dimensions/sessionization/Insights measures remain intentionally later and do not block daily Field Ops operation.

**Project Progress P1 deployment update — 2026-09-20.** Authenticated Frappe Web Page `/project-progress` is live and linked from SIG Field Ops. It provides project/view/search filters, evidence-specific worklist rows, selected-cycle evidence history, and a right-side Comment thread with an Update action that appends native human Comments. Read-back was verified live; no synthetic comment was created. A Desk Page migration is optional because production Developer Mode is disabled.

**Field Ops KPI integration — 2026-09-20.** Project Progress is the action queue and
Frappe Insights dashboard `dh657cqj78` (SIG Field Ops) is the read-only KPI/trend
plane. The two surfaces are linked from the page/workspace, but do not duplicate
comments, tasks or evidence. Insights measures must use the same cycle identity,
Visit+TCN+MIR basis, project/site denominators, follow-up/blocker/review definitions,
and explicit `SITE_CLOSED` versus As-built-only semantics documented in

**Field Ops closeout update — 2026-09-20.** E7 is closed after the E1 owner waiver: the
connected RV80 Dashboard refresh/repair controls were hidden reversibly, while `Close
Sites` and category filters remain available. E5 is the only remaining immediate Field
Ops acceptance gate and requires one real populated TCN planned-field read-back; FO3 is
later analysis infrastructure, not a daily-operation blocker.

**Readiness clarification — 2026-09-20.** E5 is optional TCN planning metadata and is
not a prerequisite for using Project Progress or Insights. The dashboard is ready for
operational evidence monitoring now. The remaining final-cutover work is P3: classify
historical imported scopes separately from Current work, then align the 15 known
Visit+TCN+MIR stage discrepancies under the existing backup/dry-run/conformance gate.

**Historical MIR boundary — 2026-09-20.** MIRs from before the first valid Field Ops
evidence event are excluded from the Field Ops ledger and dashboard. They are not to be
replayed through `register_mir` merely to populate history. Only a new, source-emitted
`MIR_CONFIRMED` evidence event can add MIR activity to a Field Ops cycle.
`project_progress_design.md`; no headline completion percentage or learned p75/p90
is valid before its existing data gate.

**Warehouse dispatch / Maytapi correction — 2026-09-20.** Live `STE-2026-0900`
is a submitted Material Issue for `MR-26-1041` with `custom_source_id = DN26-1042`;
there is no generated `DN26-1042-1/-2` sibling. The active ERP allocator issues one
company-wide DN voucher per dispatch operation; repeated partial dispatches receive
the next DN voucher rather than an invented suffix. The deployed Maytapi sender now
names the PDF from that DN voucher (`DN26-1042.pdf`, including any explicit source
suffix only), and the deployed MR Issue action requires either an ERP Employee
recipient or explicit Other text and stores it on the Stock Entry. The live
`sig_whatsapp` and `sig_warehouse` app hashes are `4a53304` and `8037470`, and the
live Stock Entry read-back confirms `custom_dispatched_to = HR-EMP-00013`. One
historical naming exception remains visible by design: `DN26-1035` is shared by
`STE-2026-0884` and `STE-2026-0885`, the two 0.01-cable Stage-4 proving dispatches
created during counter testing; the operational sequence `DN26-1036` through
`DN26-1042` is unique. Do not rename or cancel those submitted proof documents;
exclude them from production duplicate reporting.

**Warehouse recipient access regression — 2026-09-27 (fixed; configuration read back).** Tahir
Shahzad has `Stock Manager`, which grants Stock Entry create/submit, but his all-DocType Employee
User Permission allows only `HR-EMP-00013`. The newly used Stock Entry field
`custom_dispatched_to` is an Employee Link with `ignore_user_permissions = 0`; selecting
`HR-EMP-00019` makes Frappe reject the linked Employee and show the misleading generic message
that Tahir needs Stock Entry create permission. The same exposure exists on the related
Requestor PM, Initiated by, and Approved by Employee Links added for warehouse dispatch/print
metadata. **Repair deployed:** `ignore_user_permissions = 1` was applied and read back on
precisely those four metadata fields; the value is mirrored in
`sig_warehouse_print_custom_fields.json`, and
`deploy_se_form_cleanup.py --employee-links-only --yes` provides the idempotent repair path.
Tahir's impersonated session opens SIG Warehouse. His real next dispatch to another employee is
the operational proof point, without granting broad Employee access.

**Material-Issue site-allocation audit — 2026-09-20.** A read-only scan of submitted
Material Issues dated 2026-05-01 onward found 369 records with a blank parent
`Stock Entry.custom_site`. In 359 of those, the child-line `custom_site` is present,
so the site-aware lookup can still find them; the existing single-site summary
backfill may populate the parent safely where all lines agree. Ten records have both
parent and child site fields blank. Seven are evidence-backed legacy DN records and
are safe to repair from their linked Material Request lines: `STE-2026-0892` →
`ZRU218`, `STE-2026-0893` → `MW300`, `STE-2026-0894` → `ZAK096`,
`STE-2026-0895` → `ZRY322`, `STE-2026-0897` → `ZAK096`,
`STE-2026-0898` → `ZAK096`, and `STE-2026-0900` → `ZRH689`.
`MW300` and `ZAK096` are not yet present in the `SIG Site` master; their verified
raw IDs were preserved in the Stock Entry parent/line fields, with site-master
import still an open data task.
The remaining three (`STE-2026-0883`, `STE-2026-0884`, `STE-2026-0885`) are
Stage-4 proof dispatches whose linked MRs carry no site; they must not be assigned a
site by inference. **Open follow-up:** identify what posted those three proof entries
and record the source path/decision before any repair. This is a data-lineage
investigation, not permission to guess a site.

**Stage-conclusion parity check — 2026-09-20 (read-only).** The plan snapshot is optional and independent of evidence-stage conclusion. BAS defines stage 3 when the same cycle has `FIELD_VISIT_COMPLETED` + `TCN_GENERATED` + `MIR_CONFIRMED`; a raw Material Request alone does not qualify. The live ERP audit found 15 cycles currently shown as `2 - Plan` that meet that BAS rule and should project to `3 - Handover`; no endpoint change has been deployed yet. Stage 3 is not closure: explicit `SITE_CLOSED` remains the source closure fact, while As-Built is tracked separately for the closure/KPI gate.

The Project Progress page now has a deliberate display distinction: its operator-facing
position shows `Handover` for that Visit+TCN+MIR basis and `Post-implementation` for
Tags/Photos/Warranty collection, while the stored `SIG Site Cycle.stage` projection is
unchanged pending the parity gate. This is a presentation/read-model change, not a
claim that the 15 stored stage values have been repaired.

---

## 0. What this document is

This is the execution plan that closes out the SIG ERPNext programme. It sits above the existing
documents and does not replace them:

| Document | Role |
|---|---|
| `erpnext_baseline_config.md` | Configuration authority — approved values, architecture layers, policy |
| `implementation_checklist.md` | Operational task register — what is ticked, what is open |
| `erpnext_transaction_contracts.md` | API/write contract and promotion gates |
| `erpnext_learning_loop.md` | Execution evidence and mechanical rules learned during the build |
| `erp_interface_structure.md` | Living role-facing workspace, access, and document-flow register; update when an interface change is verified |
| `migration_coverage_audit_2026-08-29.md` | Live-vs-local migration coverage matrix |
| `doctype_parity_audit_2026-08-29.md` | Finance/invoice Customize Form parity and safe-default decisions |
| **this plan** | Sequence, gates, owners, acceptance evidence and definition of done |

Where this plan and an older document disagree, this plan governs the *sequence and gate*;
`erpnext_baseline_config.md` still governs the *approved value*.

This is an implementation plan, not tax or legal advice. ZATCA wave dates, VAT treatments and
invoice content require SIG Finance and a Saudi tax adviser.

---

## 1. Verified position on 2026-08-29

### 1.1 Closed

- Company legal identity, SIG abbreviation, SAR, Saudi Arabia, VAT `312022713200003`, fiscal year 2026.
- Chart of accounts imported: **311** live accounts (re-read 2026-08-31), no broken parent links. The earlier figure of 371 predates the April-shell cleanup.
- 15% sales and purchase VAT templates active against ledger `2281`, both classified Standard Rate.
- Company accounting defaults and `Main - SIG` transactional cost centre. (The Stock Settings default warehouse is `مستودع المزاحمية - SIG`, not Riyadh — see correction 5 in section 1.2.)
- All 13 role profiles; Project Lifecycle and Material Request Routing workflows; approved naming series.
- ZATCA UBL delivery-date defect fixed in the SIG fork (`custom_delivery_date` with posting-date
  fallback) on branch `sig-v15-phase2-base` at commit `d8aa877`.
- Production-chain CSR, Compliance CSID and Production CSID onboarded; Company relinked off the
  retired simulation-chain credential.
- Controlled production clearance proven once: `ACC-SINV-2026-00007` submitted and `CLEARED`,
  SAR 0.23, with valid XML and populated hash, UUID and QR.
- **Live ZATCA state re-verified on 2026-08-29 (read-only, API):**
  - Active credential `SIG ERPNext Production CSID 2026-08-28`, `ISSUED`, **expires 2027-08-28 21:47**,
    and the Company record links to exactly this one (`custom_production_csid`).
  - Its compliance record `SIG ERPNext Production Compliance CSID 2026-08-28` is `ISSUED` with
    **all six checks passed** (standard and simplified invoice, credit note and debit note).
  - CSR `SIG ERPNext Production CSR 2026-08-28`: Phase 2, FATOORA Portal, generated.
  - Company: `custom_enable_zatca_e_invoicing=1`, `custom_zatca_phase=ZATCA Phase 2`.
  - `ACC-SINV-2026-00007`: `docstatus=1`, `custom_zatca_submit_status=CLEARED`,
    `custom_is_zatca_test=0`, submitted 2026-08-28 21:52 — five minutes after the CSID was issued.
  - Its archived XML retrieves cleanly and contains UUID, ICV `1`, PIH, QR, seller VAT
    `312022713200003`, buyer VAT `300450349600003`, `InvoiceTypeCode name="0100000"` (standard),
    `TaxAmount 0.03 SAR`, and an embedded cryptographic stamp with X509 certificate.

### 1.2 Corrected records

Two statements in the older documents conflict. The resolution is:

1. **`INV-2026-0001` / `-0002` / `-0003` are not current evidence — with one correction.**
   The checklist section 3.9 presents them as a passing B2B VAT smoke pack. `-0002` and `-0003` are
   indeed absent, but **`INV-2026-0001` does exist on the live site** (re-read 2026-08-31): it is
   submitted, `CLEARED`, and carries −SAR 0.23 as the B10 credit note against `ACC-SINV-2026-00007`.
   The claim in `erpnext_baseline_config.md` section 14 that all three are gone is wrong for that
   one document. Treat section 3.9 as a historical run against a superseded site state; the VAT
   acceptance pack in G2 is re-executed on the current site from scratch.
2. **`SIG-Production-CSID-01` is retired.** Its DocType name contains "Production" but it was
   issued from the simulation chain. Re-read the live CSID name, issuer, expiry and Company link
   before every production run; do not cite it as the production credential.
3. **`SIG-Production-Compliance-CSID-2026` is not the passing record.** Checklist section 3.3 names
   it as the production-chain compliance CSID, but on the live site all six of its check flags are
   `0`. The record that passed is `SIG ERPNext Production Compliance CSID 2026-08-28`, and that is
   the chain the Company is linked to. Five stale records now exist on the site — two Production
   CSIDs, three Compliance CSIDs, three CSR settings. Retire or clearly label the superseded ones
   before someone cites the wrong evidence again.
4. **The test-invoice register is incomplete.** `SINVTest-0003` also exists on the live site,
   submitted and `CLEARED`, alongside `SINVTest-0001` and `-0002`. All of them, plus
   `SIG-SINV-26-092`, are zero-value and leave the ledger flat — re-verified 2026-08-31: 12 live GL
   entries, every account nets 0.00, and no Bin carries stock. The cleanup register must still name
   all of them. `ACC-SINV-2026-00007` (+0.23) and `INV-2026-0001` (−0.23) are **unallocated**: the
   GL nets to zero but AR ageing carries two open items. Allocate them before the AR opening is
   accepted.
5. **Stock Settings default warehouse is `مستودع المزاحمية - SIG`,** not `Riyadh Warehouse - SIG`.
   `implementation_checklist.md` section 1 states the latter and is stale. `Riyadh Warehouse - SIG`
   is currently **enabled**, contrary to `financial_import_plan_2026-08-30.md` section 5.4, and
   `All Warehouses - SIG` — the root group — is **disabled** while five active leaves hang beneath
   it. Both are repaired in Stage 5.3B, P3.
6. **Master data is already imported.** The import order in Stage 5.3 previously listed customers,
   suppliers, items and prices as pending work. Live counts on 2026-08-31 are 73 customers, 1,103
   suppliers, 839 items, 1,315 item prices, 95 addresses, 237 contacts and 27 projects. See Stage
   5.3I.

### 1.3 Legacy capture — closed on 2026-08-29

Every DocType visible to the migration login now reconciles to its live count. The detailed
matrix, including the `get_count` vs list-visibility split, is in
`migration_coverage_audit_2026-08-29.md`.

Two things had to be corrected to get there:

1. **The apparent row-count "drifts" were an artifact of the export format.** Frappe Data Import
   exports write the parent once and blank the ID column on child rows. Sales Invoice 607 rows is
   370 documents; Purchase Invoice 2,626 is 2,488; Payment Entry 2,770 is 2,613; Journal Entry
   23,810 is 8,649; Stock Entry 1,863 is 129; Material Request 1,358 is 67; Sales Order 22 is 1.
   Count distinct IDs, never sheet rows.
2. **Three captures were genuinely short and are now replaced.** Item Price held 2 of 829 records
   — the source list view had been filtered, and purchasing depends on that table. Material
   Request held 1 of 67. Address, BOM and Project were rebuilt from full documents including
   child tables (41 Dynamic Links, 13 BOM item rows). Superseded files are retained with
   `.superseded` or `.api.partial` in their names.

What remains open is not a missing SIG export. `get_count` exceeds the list count for Account
(374 vs 289), Employee (64 vs 1), Warehouse (11 vs 6) and Cost Center (36 vs 34), and the visible
warehouse `S- Main Warehouse - S` sits under `All Warehouses - D` — a second company tree this
login cannot read. The owner confirmed on 2026-08-29 that only SIG is in scope; company `D` and
its hidden records are therefore a documented exclusion, not a SIG migration blocker.

### 1.4 Decision register and remaining blockers

| ID | Status | Decision / remaining action |
|---|---|---|
| B1 | **Closed as a deployment gate by owner decision** | SIG will operate the new system as Phase 2 and production integration is already accepted technically by FATOORA. Preserve any formal ZATCA wave notice when retrieved, but its absence no longer blocks technical deployment. Finance/tax review remains part of business sign-off. |
| B2 | **Closed 2026-08-29** | All six checks pass on `SIG ERPNext Production Compliance CSID 2026-08-28`, the chain linked to the Company. Re-run whenever app source or CSID changes. |
| B9 | **Closed 2026-08-29** | `ACC-SINV-2026-00008` used delivery `2026-08-29` and due `2026-09-05`, was submitted to FATOORA Production and returned `CLEARED`; XML `ActualDeliveryDate` matched delivery and hash, UUID and QR were populated. Cancellation remains in B8. |
| B3 | **Conditional migration blocker** | PO/PR page captures cover 213/182 documents and their item rows, but require template mapping and data-quality repair. They block posted-history import only; they do not block master-data/opening-balance cutover if legacy history remains archived. |
| B4 | **Closed by scope decision 2026-08-29** | Only SIG is in scope. Company `D`, 85 hidden accounts, 63 hidden employees, 5 hidden warehouses and 2 hidden cost centres are explicitly excluded. |
| B5 | **Open — resolved through named-user rollout** | Create the same business users needed from Flexsoft, map each to an approved role profile, and assign certificate, monitoring, rollback and Finance responsibilities. |
| B6 | **Closed 2026-08-29** | Frappe Cloud bench `bench-38491` shows the installed app from `9eskot9-max/ZATCA_Integration`, branch `sig-v15-phase2-base`, revision `d8aa877`, Latest Version. The 2026-08-28 21:34 deployment succeeded. `sig_zatca_ubl_delivery_date.patch` is a redundant local evidence file: reverse-apply succeeds because its change is already in the commit; it is not an undeployed delta. |
| B7 | **Phased control, not a launch blocker** | Current automation uses the dedicated integration user. Create named interactive users before cutover; issue user-/integration-specific API credentials after launch and rotate the current shared project credential then. |
| B8 | **Closed 2026-08-29 by linked credit note** | The three named legacy test invoices do not exist on the live site. Direct cancellation of cleared `ACC-SINV-2026-00008` was rejected by the installed app, so linked credit note `ACC-SINV-2026-00009` was repaired, submitted and returned `CLEARED` for -SAR 0.23. Its GL entries exactly reverse the original invoice. |
| B10 | **Closed 2026-08-29 — every account at zero, all reversals are proper documents** | Final state: `2281`, Creditors, Debtors, Sales and Stock Received But Not Billed all net **0.00**. `ACC-SINV-2026-00007` credited by `INV-2026-0001` and `ACC-SINV-2026-00008` by `ACC-SINV-2026-00009` (all four ZATCA `CLEARED`); `ACC-PINV-2026-00001` debited by `ACC-PINV-2026-00002`. Items `Test Item 1` and `Cable2m` were recreated so returns could be built from real lines; the interim journal entries `ACC-JV-2026-00002` and `-00003` are cancelled. `ACC-SINV-2026-00001` and `-00002` stay cancelled — ERPNext requires a return's target to be submitted, so a cancelled invoice can never carry a credit note, and recreating `Cable2m` does not change that. |
| B15 | **Closed 2026-08-29** | `Riyadh Warehouse - SIG` created under `All Warehouses - SIG` (the Muzahmia store) and set as `Stock Settings.default_warehouse`, replacing the dead link. Stock documents now resolve their default. |
| B16 | **Resolved — approved cost-centre structure** | Preserve the legacy hierarchy beneath ERPNext's mandatory `SIG` root, with `Main` as the concise operating parent. Department and operational branches use bilingual labels; Operations and Projects remain combined; Procurement is separate; no Contracts department is created. Legacy project leaves remain source-faithful, with top-level `Capex-8 project - S` flagged for placement beneath Operations/Projects. Warehouses remain a separate ERPNext inventory tree. Import parents before children and retain the original parent/name in mapping notes. |
| B17 | **Closed 2026-08-29** | `custom_legacy_id` created on all 19 migration doctypes (Customer, Supplier, Item, Item Price, Address, Contact, Project, BOM, Cost Center, Warehouse, and the transaction doctypes), indexed and `no_copy`. Material Request was skipped: it already carries `custom_external_source_id`. Without this the import rules could not have been honoured — 1,098 suppliers and 835 items would have landed with no route back to the source, breaking both reconciliation and idempotent re-import. |
| B14 | **Closed 2026-08-29 — applied and verified** | Sales Invoice now uses **`SIG-SINV-.YY.-.###`** (both the `options` and `default` property setters), replacing `INV-.YYYY.-.####`. Counters continue the legacy sequence rather than restarting: `SIG-SINV-24-` = 83, `SIG-SINV-25-` = 179, `SIG-SINV-26-` = **91**, so the next issued document is **`SIG-SINV-26-092`**. The `Series` table has no DocType record and is unreachable via `frappe.client.set_value`; the counters were set through `Document Naming Settings` + `run_doc_method(update_series_start)` and read back with `get_current`. No collision remains with the superseded `INV-2026-000x` names in the written record. |
| B13 | **Closed 2026-08-29 — one selectable VAT ledger** | `VAT - SIG` (blank `account_type`, wrongly under **Asset**, the account that took the 110% charge) and `VAT Zero - SIG` are both disabled, each at zero balance first. `2281 - ضريبة القيمة المضافة %15 - SIG` is now the **only** postable, enabled tax ledger, and its own `tax_rate` is set to 15 so a manually added row defaults correctly instead of 0. `228` and `Duties and Taxes - SIG` are groups and were never selectable. Both tax templates already pointed at `2281`: sales `vat - SIG` (default, On Net Total 15%) and purchase `VAT 15% Purchase - SIG`. Re-enable `VAT Zero - SIG` only if Finance confirms SIG makes zero-rated supplies. |
| B11 | **Deployed 2026-08-29 — positive path proven, negative test outstanding** | Installed revision **`8ac61f5`** on `sig-v15-phase2-base`, Frappe Cloud "Latest Version". Ancestry checked rather than assumed (learning-loop rule 39): `8ac61f5` is **not** a descendant of the local `81cdfc7` — they are siblings off `d8aa877` — but a whitespace-insensitive diff of both files is **empty**, so the deployed code is functionally identical and *does* contain the deferred-clearance early return. Without that, enabling B2C auto-submission in step 3.9 would have rejected every B2B invoice. Local clone reset to `8ac61f5`; the duplicate commit is discarded. Positive path proven live by `SIG-SINV-26-092` (`CLEARED`, `custom_is_zatca_test=0`, hash/UUID/ICV/XML present, `BR-KSA-81` warning only). **Owner closed 2026-09-06:** considered satisfied by the legacy-import population (thousands of invoices passed the ZATCA submit hooks during the full-history import without a single ZATCA/ICV/PIH side effect — recorded as the evidence of the bypass path behaving correctly). **Technical caveat on record:** that proves the `custom_is_legacy_import` early-return path, not the guard's reject-and-block behaviour on a genuinely failed native clearance; if Finance ever wants that demonstrated, it is a one-invoice test. |
| B12 | **Closed 2026-08-29 — the credential was never dead** | Verified repeatedly at 13:40, 13:45, 13:46 and 13:54: `curl` and the harness both return HTTP 200 as `9eskot9@gmail.com`, credential source `ERPNext/.secrets/sig_erpnext_api.env`. No rotation had occurred — `frappe_api_keys (4).csv` is still the newest download — and `SIG_ERPNEXT_API_KEY`/`SECRET` are unset at Process, User and Machine scope, so nothing was overriding the file. The 401s came from a stale Markdown scraper in the harness loader, now fixed; a later `STATUS:000` was a local egress failure in one execution sandbox, not a site outage (`/api/method/ping` answers `pong` from this machine). **Do not rotate this key.** See learning-loop entries 69, 71, 73 and 74. |

---

## 2. Plan shape

Five gates. Nothing inside a gate starts before its entry condition is true, and no gate closes
without the listed evidence recorded in `implementation_checklist.md`.

```text
G1 Release & access control ─┬─> G2 VAT acceptance pack ──┐
                             └─> G3 ZATCA live re-verify ─┴─> G4 Compliance sign-off
                                                                      │
                     G5 Migration & cutover  <────────────────────────┘
```

The release-provenance portion of G1 is closed. Named-user creation now runs in parallel with G2,
G3 and migration preparation; user-specific API credentials are a post-launch hardening action as
approved by the owner. G2 and G3 run in parallel and feed G4. Master-data/template preparation may
run before G4, while opening balances and posted history still wait for Finance acceptance.

**Duration estimates are working days from the day owners are assigned, not calendar commitments.**

| Gate | Estimate | Critical dependency |
|---|---:|---|
| G1 Named users and operating ownership | 2–4 d | Flexsoft user/role inventory, B5 |
| G2 VAT acceptance pack | 5–8 d | Finance reviewer availability |
| G3 ZATCA regression and operating controls | 2–4 d | B9, retry/archive evidence |
| G4 Finance acceptance and operating enablement | 3–5 d | B5, print review, Finance sign-off |
| G5 Migration, reconciliation and cutover | **Provisionally closed 2026-09-21** (was 30–45 d; see v4.15) | Stage 5.3A-1 decisions, the invoice-level AR/AP extract, the JE importer, and eight monthly reconciliation cycles. The earlier 15–25 d estimate predated the measured scope of 1,772 2026 vouchers plus the opening invoice set |

---

### 2.0 Independent verification — 2026-08-29 (read-only)

Re-checked against the live site rather than accepted from the record. All of the following hold:

| Claim | Evidence |
|---|---|
| B9 delivery-date fix is real | `ACC-SINV-2026-00008` carries delivery `2026-08-29` against due `2026-09-05`, and its XML emits `ActualDeliveryDate 2026-08-29`. The dates differ, so the original defect would have emitted `2026-09-05`. This is the discriminating test `ACC-SINV-2026-00007` could not provide |
| PIH hash chain is intact | `00008` embeds `00007`'s invoice hash; `00009` embeds `00008`'s. ICV runs 1 → 2 → 3 |
| Credit note is compliant | `00009`: `InvoiceTypeCode 381`, `BillingReference → ACC-SINV-2026-00008`, `InstructionNote Cancellation`, `CLEARED` |
| GL reversal is exact | `00009` reverses `00008` line for line: Debtors 0.23, VAT `2281` 0.03, Sales 0.20 — each on the opposite side |
| B2 chain is the linked one | Six checks true on `SIG ERPNext Production Compliance CSID 2026-08-28`; Company `custom_production_csid` points at the matching Production CSID, expiry 2027-08-28 |
| G1 has not started | Four enabled users (three System, one Website); no named-role rollout, automation still on the shared project credential |

Not verifiable from the site, and correctly labelled as external evidence: the B6 commit-level claim
(bench `bench-38491`, revision `d8aa877`). The site API reports only `zatca_integration 0.0.1`,
`branch=HEAD`. The Frappe Cloud dashboard remains the provenance record for that one.

---

### 2.1 Immediate execution queue

Run these in order unless a step explicitly says parallel:

1. **B9 production-path regression — complete 2026-08-29:** `ACC-SINV-2026-00008` used
   `custom_is_zatca_test=0`, delivery `2026-08-29` and due `2026-09-05`; FATOORA returned
   `CLEARED`, XML was fetched, `ActualDeliveryDate=2026-08-29`, and hash/UUID/QR were present.
2. **Clear the ledger of test documents (B10) — do not cancel cleared invoices.** Reversal drafts
   are scripted in `ERPNext/scripts/b10_create_reversal_drafts.py`: it mirrors each source with
   negative quantities, refuses to touch a source that already has a return, and never submits.
   Expected effect once the drafts are reviewed and submitted — Debtors 21.23, Sales 10.20,
   `VAT - SIG` 11.00, Creditors 0.23 and SRBNB 0.20 all return to zero. The installed app
   correctly rejects cancelling a cleared invoice, and ZATCA does not permit altering one. Retain
   XML/QR/response evidence, then reverse each remaining test document with its own linked credit or
   debit note, exactly as `ACC-SINV-2026-00009` reversed `ACC-SINV-2026-00008`:
   `ACC-SINV-2026-00007` (credit note), `ACC-PINV-2026-00001` (linked purchase debit/return note), and
   `ACC-SINV-2026-00001` — which was never cleared, so agree its treatment with Finance first.
   `TEST-SINV-2025-200/201/205` do not exist on this site; that line is retired.
   Then verify GL nets to zero per pair and confirm operational reports exclude them.
3. **User migration in parallel:** obtain the Flexsoft enabled-user/effective-role export from a
   System Manager/provider administrator, map to the 13 target role profiles, create users without
   passwords, test access and activate in waves.
4. **Operating controls in parallel:** deploy the B11 guard, run the rejected-clearance regression,
   then complete print/PDF review, network/retry alert,
   archive retrieval, renewal calendar and named certificate/monitoring/rollback owners.
5. **Decide the two Stage 5.3A-1 questions:** the AR/AP opening method (party-typed accounts make
   this a technical constraint, not a preference) and whether `2281` splits into input and output.
   Both gate work that follows.
6. **Stage 5.3B Wave 1 — the app change and its proving run.** Add `custom_is_legacy_import` and the
   legacy evidence fields, make the two early returns, deploy once, then run the three-test proving
   run in Stage 5.3E-1. This needs a site restart, so it runs before any import batch, not during
   one. **Wave 2 (data preflight P1–P5, P7, P9) runs in parallel** — it needs no deployment.
7. **Stage 5.3B Wave 3 — post the 1 January 2026 opening** once Waves 1 and 2 are complete.
8. **Build the Journal Entry importer.** 1,431 vouchers and 58% of 2026 movement run through JEs,
   and no importer exists for them. This is the largest single piece of remaining migration work;
   PO/PR/MR staging, which is largely complete, posts no GL at all. It can be built during Waves 1–2.
9. **Run the monthly replay loop (Stage 5.3F), January first.** Submit, reconcile five control
   totals, freeze the month, then start the next.
10. **Correction pass (Stage 5.3G)** once every month ties, then the SIG Legacy Archive build.
11. **Post-launch security:** issue scoped API credentials, update and rerun the harness, rotate the
   current project credential, and remove secrets from Markdown before repository sharing.

---

## 3. Owners — assign before execution starts

Every row below is currently unnamed. This is now the largest governance task: technical ZATCA
onboarding is proven, while operating ownership must be assigned through the named-user rollout.

| Role | Responsibility | Owner | Backup |
|---|---|---|---|
| Programme owner | Gate decisions, scope changes, escalation | *TBC* | *TBC* |
| ERP administrator | L1–L4 configuration, role profiles, named users | *TBC* | *TBC* |
| Finance controller | VAT treatment, GL review, opening balances, sign-off | *TBC* | *TBC* |
| Tax adviser (external) | Invoice-content review and archive of formal ZATCA notification evidence when available | *TBC* | — |
| ZATCA certificate owner | CSID renewal calendar, credential custody | *TBC* | *TBC* |
| Integration/monitoring owner | Failed submissions, retries, alerting, archive retrieval | *TBC* | *TBC* |
| Custom-app release owner | Branch/commit approval, deployment record, rollback | *TBC* | *TBC* |
| Migration owner | Export capture, reconciliation, import batches | *TBC* | *TBC* |
| Warehouse/Operations owner | Master-data acceptance, warehouse and project structure | *TBC* | *TBC* |

One person may hold several roles, but certificate custody and production-submission approval must
not sit with the same individual as the release owner.

---

### 3.1 Migration-readiness baseline — established 2026-08-29

The target ledger is flat: 18 live GL rows across 5 accounts, **not one carrying a balance**,
and no stock in any bin.

Test master records were kept but deactivated and tagged `(TEST)` per owner decision, so that
post-import counts reconcile against legacy exactly rather than being inflated by fixtures:

| DocType | Active before import | Legacy to import | Expected after |
|---|---:|---:|---:|
| Customer | 0 (4 disabled) | 66 | 66 |
| Supplier | 0 (1 disabled) | 1,098 | 1,098 |
| Item | 0 (3 disabled) | 835 | 835 |
| Address | 1 (2 disabled) | 50 | 51 |

Two records were deliberately left active because they are not test data: the company's own
`...-Office` address, which is the seller address in every ZATCA UBL document, and all five
Contacts, each linked to a real User account. Draft Delivery Note `MAT-DN-2026-00003` was deleted.

Site configuration is exported to `ERPNext/fixtures/` as JSON with a manifest — the first copy of
the chart of accounts, tax templates, workflows, custom fields, role profiles and naming series
that has ever existed outside the live database. Credentials are redacted on the way out. This is
a config export, **not** a database backup: take that from the Frappe Cloud dashboard before any
bulk import.

---

## 4. Standing rules for the remainder of the programme

1. Evidence is a record, not a claim. Each closed task records what was run, on which site, by
   which identity, at what time, and the exact document, commit or file it produced.
2. No credential — API key, API secret, OTP, private key, certificate — is written into these
   documents, a fixture, a chat message or Git. `erpnext_baseline_config.md` currently violates
   this; G1 fixes it.
3. Re-run all six ZATCA compliance scenarios whenever the app source or the active CSID chain
   changes. A single cleared invoice is not a compliance test.
4. No posted legacy history is submitted on the target site until its opening balances reconcile
   and cutover is approved.
5. A prepared migration workbook is a mapping input. Compare it against a freshly generated
   target-site Data Import template before every upload.
6. Preserve the legacy identifier in `legacy_id` / `sig_external_source_id` on every imported
   record; import parents before children; dry-run, correct, rerun, then reconcile counts and
   monetary totals.
7. Cancelled, amended and returned legacy documents stay identifiable. They are never silently
   re-submitted as live documents.

---

## 5. Workstreams

### G1 — Named users and operating ownership

**Entry:** none. Start immediately.

| # | Task | Evidence required to close |
|---|---|---|
| ~~1.1~~ | ~~Pin the approved custom-app release~~ | **Done:** user fork, `sig-v15-phase2-base`, `d8aa877` |
| ~~1.2~~ | ~~Record the installed bench revision on the live site~~ | **Done:** Frappe Cloud reports `d8aa877`, Latest Version; deployment `0jm65k26eu` succeeded 2026-08-28 |
| ~~1.3~~ | ~~Classify the loose delivery-date patch~~ | **Done:** reverse-apply check proves the patch is already present in `d8aa877`; retain it only as labelled evidence or move it outside the repo clone |
| 1.4 | Obtain the enabled Flexsoft user and role inventory | The current migration identity receives 403 for `User`; export must be performed by a Flexsoft System Manager/provider administrator |
| 1.5 | Map legacy users to the existing 13 target role profiles | Mapping table records email, full name, enabled state, source roles, target role profile, company, default warehouse and approval limits |
| 1.6 | Create target users safely | Never migrate passwords or API secrets; create users disabled or invitation-pending, assign least privilege, then perform role-based acceptance testing |
| 1.7 | Assign operating ownership | Named primary/backup owners for Finance approval, ZATCA certificate, monitoring/retry, release/rollback, migration and warehouse operations |
| 1.8 | Activate users and reserve Administrator for break-glass | Activation occurs in a controlled wave after role testing; record 2FA state and disable obsolete accounts |
| 1.9 | Post-launch API hardening | Issue credentials per integration/user, update the harness, rotate the current project credential and remove it from Markdown before sharing the repository |
| 1.9a | Issue **per-person API keys** | Every named user receives their own API key pair as part of activation; requests carry `Authorization: token <person-key>:<secret>` so `owner`/`created_by`/Error Log attribute the person. VBA credential storage (ACN/AC_Crypto protected config) and the hub's person-bound slots switch to the person's key; the shared project credential is retired only after every active integration path has its own key. Design and access matrix: white paper §"User identities, per-person API credentials and access boundaries" |
| 1.9b | Apply and test the **access matrix** | Role acceptance tests prove each class: PM/Coordinators read-only finance view; field people HR-only; Accounting full finance; **SIG Admin** (custom profile cloned from ERP Admin, submit/amend/cancel stripped on Sales Invoice, Purchase Invoice, Journal Entry, Payment Entry, Stock Entry, Bank Reconciliation) full visibility with no finance submit/amend/cancel |
| 1.10 | Run `erpnext_api_harness.ps1 -Mode verify` after credential rotation | Verifier output retained; no stale credentials resurrected |

**Exit for business cutover:** 1.4–1.8 closed. Tasks 1.9–1.10 (including 1.9a/1.9b) are mandatory
post-launch security hardening and do not delay the approved controlled deployment.

### G2 — VAT acceptance pack (re-execution)

**Entry:** G1 closed. **Owner:** Finance controller with the ERP administrator.

The seven scenarios in `implementation_checklist.md` section 2 are re-run on the current site,
because the earlier smoke records no longer exist (section 1.2). Each is created as a draft and
submitted only after Finance reviews the ledger rows.

| # | Scenario | Required result |
|---|---|---|
| 2.1 | Standard sales invoice, net 1,000 SAR | VAT 150 SAR to `2281`; customer total 1,150 SAR |
| 2.2 | Standard purchase invoice, net 500 SAR | VAT 75 SAR; recoverable input treatment confirmed by Finance |
| 2.3 | Sales credit note against 2.1 | Negative VAT reverses the same output-tax account |
| 2.4 | Sales return / receipt note | Stock and income reversal aligns with the credit note |
| 2.5 | Discounted sales invoice | VAT calculates on the discounted net amount |
| 2.6 | Foreign-currency sales document | Exchange valuation and SAR VAT base correct |
| 2.7 | Printed standard and simplified layouts | Legal seller name, VAT number, date, line totals, VAT summary, QR |
| 2.8 | Sub-riyal display control | `disable_rounded_total=1`; `rounded_total` and `in_words` verified |
| 2.9 | Output vs input VAT ledger decision | Finance confirms whether `2281` stays single or splits; if it splits, both templates change through Tax Rules, never manual rows |

**Exit:** Finance signs off GL entries, ZATCA field population and printed PDF samples for all nine.

### G3 — ZATCA live re-verification

**Entry:** G1 closed. **Owner:** ERP administrator with the certificate owner.

| # | Task | Evidence required to close |
|---|---|---|
| ~~3.1~~ | ~~Decide whether Phase 2 integration is in deployment scope (B1)~~ | **Done by owner 2026-08-29:** yes. Formal notification evidence is archived when available but is not a technical gate. |
| ~~3.2~~ | Re-read the live CSID chain | **Done 2026-08-29.** `SIG ERPNext Production CSID 2026-08-28`, `ISSUED`, expiry 2027-08-28 21:47, linked on the Company record |
| ~~3.3~~ | Re-run all six compliance checks on the live site (**B2**) | **Done 2026-08-29.** All six flags true on `SIG ERPNext Production Compliance CSID 2026-08-28`; Company links to the matching Production CSID |
| 3.3a | Re-prove the UBL delivery-date fix (**B9**) | **Passed 2026-08-29** — `ACC-SINV-2026-00008`: delivery `2026-08-29` ≠ due `2026-09-05`; XML `ActualDeliveryDate=2026-08-29`; production `CLEARED`, hash/UUID/QR present |
| 3.3b | Retire or label the superseded CSR/CSID records | The two stale Production CSIDs, two stale Compliance CSIDs and two stale CSR records are marked so they cannot be mistaken for current evidence |
| 3.4 | Run Phase 2 acceptance matrix scenarios 1–9 | Per scenario: XML, clearance/reporting status, hash, UUID, PIH chain, QR |
| 3.4a | Validate the approved artistic ZATCA QR design before ERPNext integration | **Design accepted by owner 2026-08-29** — signature style with the SIG centre mark (`invoice_qr_signature_renderer.py` + `saudi_emblem.py`; reference `docs/qr_samples/zatca_signature_emblem.png`). Software decode passes at 976/600/400/300/220 px for the mark and no-mark variants. Still required to close: three or more physical phones across iOS and Android using the native camera, PDF and paper output at production print size, and an angled/low-light read |
| 3.4b | Wire the approved renderer into the existing QR attachment path | Image generation only — payload construction, ZATCA tags, submission and archive untouched. Closes on a cleared production invoice whose attached QR is the styled image and whose decoded payload is byte-identical to the plain renderer's for the same invoice. Runtime depends on `qrcode[pil]` and Pillow only; `pyzbar` stays test-only |
| 3.4d | Re-issue a test invoice PDF after the 2026-08-30 sizing correction | **Raised 2026-08-30.** The first deployed PDF (`SINVTest-0001`) rendered a 109-module ECC H symbol at 118 pt — 0.36 mm per module, below what a phone camera resolves off paper. Renderer moved to ECC M (81 modules) and the print format to 150 pt. Closes on a fresh cleared invoice PDF whose QR scans from paper on three or more phones |
| 3.4c | Prove the fallback to the plain local QR | Fallback is reachable by configuration without a release; forcing it produces the plain local QR and a cleared invoice. A styled QR a customer cannot scan is a compliance failure, not a cosmetic one |
| 3.5 | Scenario 10 — network/API failure | Queue and retry proven; no duplicate submission; alert raised |
| 3.6 | Scenario 11 — rejected invoice | Error code stored; correction path documented; no customer-final invoice issued |
| 3.7 | Scenario 12 — certificate renewal | Renewal steps executed in a rehearsal and documented before expiry |
| 3.8 | Enable strict invoice-date validation | Setting enabled after 3.4 passes |
| 3.9 | Configure B2C reporting frequency | Frequency keeps submission inside the regulatory window during an outage |
| 3.10 | Prove immutable archive retrieval | **Partly done 2026-08-29** — XML, QR image, hash and submit timestamp retrieve for `ACC-SINV-2026-00007`; B9 additionally fetched XML for `ACC-SINV-2026-00008`. Still to prove: stored response-body retrieval and error path |
| 3.11 | Reverse `TEST-SINV-2025-200/201/205` and the B9 regression invoice (**B8**) | **Passed 2026-08-29 for live B9:** legacy names absent; direct cancellation is prohibited for a cleared ZATCA invoice, so linked credit note `ACC-SINV-2026-00009` was submitted and its GL entries reverse `ACC-SINV-2026-00008`. |

Acceptance scenarios 5 and 6 (zero-rated/export and exempt supply) proceed only if Finance confirms
SIG actually makes such supplies; if not, record the exclusion rather than fabricating a test case.

The QR design specification and its acceptance-evidence table live in
`invoice_qr_concept_renderer.md`; 3.4a–3.4c close against that table.

**Exit:** 3.1–3.11 closed with evidence. B2C configuration remains dormant unless SIG begins
simplified/consumer invoicing.

### G4 — Compliance sign-off and production enablement

**Entry:** G2 and G3 closed.

Production processing opens only when all are true — the go-live gate from
`implementation_checklist.md` section 3.5, with owners attached:

- [x] Owner confirmed Phase 2 integration is in deployment scope; formal notification evidence will be archived when available.
- [ ] CSR and company legal data verified by Finance and legal: English and Arabic legal names, CR `1010354384`, VAT `312022713200003`, building `7783`, Riyadh/Al Olaya, postal code `12233`, and invoice-type code validated against each intended scenario.
- [x] Six live compliance checks accepted on the current site (B2).
- [x] Production CSID generated, linked and re-read live.
- [ ] Printed and PDF layouts show Arabic/legal fields, QR and invoice summary correctly.
- [ ] Approved ZATCA QR design (signature style with the SIG centre mark) scans correctly from printed and PDF output on three or more physical phones; the plain local QR fallback stays reachable by configuration until this gate passes.
- [ ] Failed-submission alerting, retry procedure and archive retrieval tested (B5 owner named).
- [ ] Renewal owner assigned (B5). **Expiry is known: 2027-08-28 21:47** — set the renewal calendar now.
- [ ] Incident and rollback plan approved.
- [ ] Finance and tax adviser sign-off recorded with names and date.

**Exit:** normal B2B production processing enabled and recorded as a change entry. B2C reporting is
configured and activated only if SIG begins simplified/consumer invoicing; it is not fabricated as
a go-live transaction for a B2B-only operating scope.

### G5 — Migration, reconciliation and cutover

**Entry:** G4 closed for anything that produces a **new** ZATCA-reportable document. The 2026 replay
does not: legacy and opening invoices post through `custom_is_legacy_import` and are never
transmitted, so the replay is gated by the Stage 5.3E-1 proving run rather than by G4. Master-data
capture and reconciliation (5.1 and 5.2) are complete (Stage 5.3I).

#### Stage 5.1 — Capture (closed 2026-08-29; import-quality work remains)

Every DocType visible to the migration login reconciles to its live count (section 1.3). What is
left is scope, not extraction:

| # | Task | Route |
|---|---|---|
| ~~5.1.1~~ | ~~Decide whether Flexsoft company `D` is in migration scope (B4)~~ | **Done:** only SIG is in scope; hidden company `D` records are excluded and retained only in the audit count |
| 5.1.2 | Purchase Order and Purchase Receipt full child tables and attachments (**B3**) | PR package is validated against live Neosys fields with exact warehouse mapping. The earlier 172-row working package is superseded operationally by 169 source-tagged eligible PR drafts; seven eligible receipts remain deferred for supplier/UOM blockers. Return, zero-VAT and missing-supplier exceptions remain documented; PO links are verified only where source evidence supports them. |
| 5.1.3 | Confirm Stock Reconciliation (7 documents, Jan 2024) is superseded by opening balances | Finance decision; capture only if it is to be migrated |
| 5.1.4 | SIG Employee master | Separate HRMS-phase capture. Hidden company `D` employees are excluded; active SIG users are migrated from the User/role inventory, not inferred from Employee rows. |

> **Superseded for the 2026 scope (v3.0).** The staging figures below describe the full 2024–2026
> capture. Under the 1 January 2026 cutover only 36 of the staged Purchase Receipt drafts and 37 of
> the Purchase Orders are in scope, the deferred-receipt warehouse question does not arise (Stage
> 5.3D resolves warehouse per voucher from the Stock Ledger), and the pre-2026 drafts are deleted
> under Stage 5.3B P4. Retained here as the capture record.

#### Stage 5.2 — Template and dry-run validation

For every workbook: generate a fresh target-site Data Import template, compare headings, correct the
working copy, dry-run, save Frappe warnings, correct, rerun. Original captures stay unchanged. The
20 PO and 51 PR tax warnings are cleared by accounting review, never by assuming 15%. The PR
capture is now repaired in a target-compatible workbook: regular rows use live field labels, ISO
dates, target Item codes/UOMs, target warehouse names and `VAT 15% Purchase - SIG`. The one return
is deferred because `is_return` and `return_against` are read-only; three zero-VAT receipts await
an approved target template; six receipts await three missing Supplier records. Source UI text
and unsupported Arabic display fields remain only in the original audit workbook.
Map the legacy Arabic Company name containing `عقيل` to the approved SIG target Company rather than
creating a second company or importing the legacy spelling literally.

#### Stage 5.3 — historical migration and 2026 replay

**Latest owner direction — 2026-09-01: optional full-history reconciliation pilot.** The preferred
outcome is one Neosys ledger containing all non-cancelled, genuine Flex transactions from the Flex
ERP period onward (expected from 2024), rather than a live-2026 ledger plus a separate legacy site.
This is an **optional proving route**, not authority to bulk-submit immediately: take and record a
Neosys backup first; deploy and prove `custom_is_legacy_import` in a non-production copy; then load
historical batches in chronological order. At the checkpoint **31 December 2025**, compare Flex and
Neosys account-by-account, including stock, AR, AP, VAT, bank/cash, retention and Temporary Opening.
Only if the checkpoint ties may the full-history route continue through 2026. If it cannot be made
to tie without unexplained exceptions, restore the recorded Neosys backup and use the existing
opening-at-1-January-2026 route. The separate Legacy Archive remains a fallback, not the preferred
architecture.

**Cutoff rule — posting date and posting time control accounting membership.** For every source
voucher and GL row, classify the historical period from `posting_date` and, where the date is the
same, `posting_time`. Never use creation date, modified date, invoice due date, delivery date or a
business narrative as the accounting cutoff. A document created/submitted during 2026 but carrying a
2025 posting date belongs in the pre-2026 checkpoint; a document created in 2025 with a 2026 posting
date belongs in the 2026 replay. Maintain a cutoff-exception register for every such backdated or
late-posted item, showing source ID, posting date/time, creation/submit timestamp, target batch and
the reason it belongs on that side of the checkpoint.

**Flex source discovery — 2026-09-01.** The live Flex General Ledger shows no movement in the
2020–2023 query range but carries an opening debit and credit of **SAR 32,325,871.180** into 2024.
The first observed 2024 GL postings are dated 1 January 2024 (`ACC-JV-2024-00117` and following).
The Stock Ledger has no pre-2024 rows and starts at **2024-01-01 00:00:01** with Stock
Reconciliation `MAT-RECO-2024-00001` (seven January-2024 stock reconciliations are in the captured
inventory). Therefore the pilot starts from two distinct source controls: (1) a leaf-account
ledger opening as at 31 December 2023, and (2) the 1 January 2024 stock-reconciliation population.
Do **not** assume the carried ledger opening excludes inventory. Before submission, reconcile its
inventory leaf balance to the stock-reconciliation GL effect; post inventory exactly once through
the chosen opening/Stock Reconciliation design.

**v3.5 execution roadmap.**

1. **Source freeze and control pack.** Re-run Flex leaf-account Trial Balance, General Ledger,
   Stock Ledger/valuation, AR, AP and VAT reports at one recorded extraction time. Preserve the
   31-Dec-2023 ledger opening, the seven 1-Jan-2024 stock-reconciliation documents, and all
   posting-date/time fields. Reconcile the opening report to the detailed account population; never
   total group rows.
2. **Technical proving run.** Take the Neosys backup, deploy the legacy-import control, and prove
   it in non-production with one historic sales invoice. Pass criteria: normal target GL/stock,
   original evidence retrievable, and zero ZATCA/ICV/PIH activity.
3. **2024 opening bridge.** Create Fiscal Year 2024, map the 31-Dec-2023 leaf opening to postable
   Neosys accounts, import the 1-Jan-2024 stock reconciliations, and prove Temporary Opening nets
   to zero. Stop here if the source inventory effect is ambiguous or duplicated.
4. **Chronological historical waves.** Load non-cancelled documents as drafts in source dependency
   order—masters, stock reconciliation/receipt/delivery, purchase and sales documents, standalone
   JEs, then allocations and payments—and submit in posting-date/time order. Returns and credit/debit
   notes follow their original target document. Never create a standard voucher and its duplicating
   direct JE.
5. **Checkpoint mediation.** Reconcile at 31-Dec-2024 and 31-Dec-2025, then by month during 2026:
   postable-account TB, stock quantity/value by item/warehouse, invoice-level AR/AP, VAT, bank/cash,
   retention and Temporary Opening. Log source versus target count, debit, credit and closing balance
   for each voucher type and account. Do not proceed past a checkpoint with an unexplained difference.
6. **Decision.** Passing the 31-Dec-2025 mediation authorizes continuation of the 2026 waves. A
   material unresolved difference triggers restoration of the pre-pilot backup and the documented
   1-Jan-2026 opening-plus-replay fallback.

**Document rule.** Import submitted/completed non-cancelled source transactions, including linked
returns, credit/debit notes and settlements. Recreate standard vouchers before any direct Journal
Entry whose economic effect they would duplicate; retain only genuinely standalone JEs. Historical
Sales Invoices use immutable `custom_is_legacy_import`: they post normal ERPNext accounting and
stock but never call ZATCA, generate active ZATCA fields, use credentials, retry, or mutate the
ICV/PIH chain. Preserve original QR/XML/PDF as legacy evidence.

> **Superseded where inconsistent.** The following 2026-only decisions, pre-2026 draft deletions
> and mandatory separate-archive statements record the prior route. They are suspended while the
> v3.5 pilot is evaluated; they become the fallback only if the 31 December 2025 mediation fails.

**Owner decisions — 2026-08-31 (final).**

1. The financial cutover is **1 January 2026**. The 31 December 2025 position is the only opening.
   An August opening-balance or closing-stock plug is not permitted.
2. **Flexsoft is trusted as entered.** Its 2026 transactions were approved and posted by SIG in the
   course of business. They are replayed faithfully, not re-adjudicated document by document.
3. **Reconcile monthly, correct afterwards.** Each month must tie to Flexsoft before the next is
   loaded. Errors discovered in the source are fixed by dated correction entries in Neosys *after*
   the full replay ties — never by altering a replayed document to make a month balance.
4. **Superseded by v3.5 pilot:** pre-2026 documents are not deleted while their full-history
   import/reconciliation is being assessed. They remain controlled migration candidates.
5. **The SNB bank feed is forward-only.** It is not a migration source and plays no part in the
   2026 replay. It begins operating after the freeze date.

This supersedes the earlier Class A–E per-document approval register. The control is a **monthly
reconciliation register**, not a per-document sign-off: for each month and doctype it records source
count and value, target count and value, the difference, and the resolution. That control matches
decision 2 — the question is never whether a given document deserves to exist, but whether the month
ties.

##### Stage 5.3A — scope

Measured from `dump/General_Ledger (2).xlsx` (34,729 lines, 2024-01-01 → 2026-08-30):

| Voucher type | 2026 vouchers | Debit (SAR) | Share of 2026 movement |
|---|---:|---:|---:|
| Journal Entry | 1,431 | 39,935,211.80 | 58% |
| Payment Entry | 120 | 13,526,177.43 | 20% |
| Sales Invoice | 81 | 8,336,561.39 | 12% |
| Purchase Invoice | 102 | 3,964,811.69 | 6% |
| Purchase Receipt | 38 | 2,870,193.56 | 4% |
| **Total** | **1,772** | **68,632,955.87** | |

**The Journal Entries are the migration.** They are genuine standalone operating journals —
employee custody (`عهدة`, 753 lines), fuel, iqama renewals, vehicle maintenance, insulation
materials, bank charges — not system echoes of other vouchers. They map 1:1 to target Journal
Entries and require no de-duplication. The target chart already carries all fifty `132xx`
per-employee custody accounts, so the accounts resolve directly.

Monthly voucher counts:

| Month | JE | PE | PI | PR | SI |
|---|---:|---:|---:|---:|---:|
| 2026-01 | 199 | 19 | 19 | 7 | 1 |
| 2026-02 | 204 | 13 | 7 | 2 | 6 |
| 2026-03 | 200 | 22 | 17 | 4 | 8 |
| 2026-04 | 232 | 13 | 16 | 8 | 17 |
| 2026-05 | 221 | 15 | 8 | 1 | 15 |
| 2026-06 | 186 | 12 | 11 | 4 | 13 |
| 2026-07 | 159 | 21 | 13 | 6 | 9 |
| 2026-08 | 30 | 5 | 11 | 6 | 12 |

August is partial — the source was still live at extraction. The freeze date fixes the final month.

**Cost centre, not project.** `Project` is blank on all 4,579 2026 GL lines; `Cost Center` is
populated on 4,209 (92%). Map cost centre only. The 370 lines with no cost centre take the approved
default; do not invent one per line.

##### Stage 5.3A-1 — two decisions required before any work starts

Both change downstream work materially and neither can be deferred into the replay.

**Decision 1 — the AR/AP opening method. RESOLVED 2026-08-31: opening legacy invoices, not lump
sums.**

On the target, `1331 - مدينون` is typed `Receivable` and `2261 - الموردين` is typed `Payable`.
ERPNext requires `party_type` and `party` on **every** GL line touching a party-typed account, so the
opening cannot post the trial balance's `133 - العملاء` 8,041,288.63 or `226 - الحسابات الدائنة`
6,164,951.84 as single lines. That much is a hard technical constraint.

The owner's requirement decides the rest: **the accounting firm needs the payment-to-invoice link and
the underlying document.** SIG holds physical copies of the late-2025 invoices, and the audit story
must be "this invoice was issued from Flexsoft, here is the original, and here is the 2026 payment
that settled it." A party-level balance cannot carry that.

Therefore the outstanding 2025 documents are imported as **opening invoices**, and the opening
Journal Entry carries **no AR or AP lines at all**. The two sets are exclusive; nothing is counted
twice, and the check is arithmetic — the opening invoices must sum exactly to the trial-balance
figures.

**Rules for the opening invoice set:**

| # | Rule | Reason |
|---|---|---|
| 1 | **The selector is "outstanding at 31 December 2025", not a date range.** Any invoice still carrying a balance at that date comes in, whatever month it was issued. | Choosing "October and November" by date will not tie. The set must sum to AR **8,041,288.63** and AP **6,164,951.84** exactly; the AR/AP ageing report defines membership. |
| 2 | **Submitted, not drafts.** | A draft cannot be referenced by a Payment Entry and does not appear in AR ageing. Drafts would defeat the entire purpose — the accountant would see a document but no link. This is the one point where "keep it as a draft" does not work. |
| 3 | `is_opening = Yes`, dated the **original invoice date**. | Preserves true ageing. FY2025 (P2) makes the 2025 posting date legal. |
| 4 | Income account (SI) / expense account (PI) = **`Temporary Opening`**. | Prevents restating 2025 revenue or expense in the target. |
| 5 | **No tax rows. Amount = the outstanding balance at 31 Dec 2025.** | Output and input VAT were already declared in Flexsoft in 2025 and must never be restated in 2026. `2281` stays clean. The original invoice total and VAT are preserved in the attachment and legacy fields. |
| 6 | `custom_is_legacy_import = 1` on every opening Sales Invoice. | They pass through the ZATCA submit hooks like any Sales Invoice. None is ever transmitted. |
| 7 | Preserve the original Flexsoft number and attach the original PDF and QR to the legacy evidence fields. | This is the delineation the accounting firm needs. The `SIG-SINV-25-` counter already stands at 179, so original 2025 numbers import without collision. |
| 8 | Purchase Invoices follow the same pattern, minus the ZATCA parts. | No e-invoicing hooks apply to Purchase Invoice. |

**Consequence — a third bypass point is now mandatory.** `validate_sales_invoice` throws when
`taxes_and_charges` is empty, and opening invoices carry no tax rows by rule 5. It must therefore
**also early-return on `custom_is_legacy_import`**, alongside `generate_einvoice` and
`enforce_b2b_clearance_on_submit`. Without it every opening Sales Invoice is rejected at submit.

**Consequence — a new account is required.** No `Temporary Opening` account exists on the SIG chart
(verified 2026-08-31). It must be created as a postable leaf with `account_type = Temporary` before
the opening is posted, and it must net to zero once the opening is complete.

Required source artefacts, added to the P7 frozen pass: the **Accounts Receivable and Accounts
Payable reports as at 31 December 2025, at invoice level** — party, invoice number, invoice date, due
date and outstanding amount. The summary-only version is not sufficient for this method.

**Decision 2 — whether `2281` stays one ledger or splits into input and output** (G2 scenario 2.9).
Decide **before** the replay starts. Changing it afterwards means repointing thousands of GL lines.

##### Stage 5.3A-2 — mapping feasibility: proven 2026-09-01

Before building any importer, every 2026 GL line was resolved against the live target masters. The
result removes the largest schedule risk in the programme: **the replay is a mechanical mapping job
with a fully enumerated exception list, not an open-ended data-cleansing exercise.**

Mapping rule: legacy `… - S` → target `… - SIG`.

| Voucher type | GL lines | Account misses | Cost-centre misses | Party lines | Party misses |
|---|---:|---:|---:|---:|---:|
| Journal Entry | 3,722 | **0** | 1 | 7 | 0 |
| Purchase Invoice | 297 | **0** | 1 | 102 | 4 |
| Sales Invoice | 244 | **0** | 2 | 81 | 2 |
| Payment Entry | 240 | **0** | 0 | 120 | 5 |
| Purchase Receipt | 76 | **0** | 1 | 0 | 0 |

**Accounts: zero misses.** All 84 distinct accounts used by the 1,431 Journal Entries resolve, and so
does every account used by every other 2026 voucher type — 4,579 of 4,579 lines. The chart migration
is complete and correct for replay purposes.

**Cost centres: two need attention, and only two.**

| Legacy value | Action |
|---|---|
| `رئيسي - S` | Map to `Main - SIG`. Already the documented B16 rule; it is an explicit mapping, not the generic suffix rule. This single value covers **all 3,722 Journal Entry lines**. |
| `10001045 - Colocation 2026 project - S` | **Does not exist on the target.** Create it under Operations & Projects before the Sales Invoice replay. |

All other 2026 cost centres resolve. Note the consequence: **every Journal Entry posts to `Main`**,
so project analysis in the 2026 JE population is carried by the *account code* — `51312` project
vehicle maintenance, `51316` insulation project expenses — not by cost centre. Do not expect the
cost-centre tree to deliver project reporting for replayed journals.

**Parties: six unresolved names across the entire 2026 replay**, each with an obvious target match.
All are naming variants, not missing masters.

| Type | Value at risk | Source name | Target name | Nature |
|---|---:|---|---|---|
| Customer | SAR 16,818,960.00 | `Telecommunications Towers Company Limited` | `Telecommunications Towers Company / Tawal` | Alias — confirm and record. Largest exposure in the replay by an order of magnitude |
| Customer | SAR 383,729.70 | `شركة لجين الحواء الطبية` | `شركة لجين الدواء الطبية` | **One Arabic letter differs** (الحواء vs الدواء). One of the two is a typo — Finance must confirm which is the legal name |
| Supplier | SAR 22,723.75 | `Al-Masar for Electrical Materials Est.` | `Al-Masar for Electrical Materials Est` | Trailing period |
| Supplier | SAR 20,010.00 | `Rawafed Al Sharq Information Technology Company-AGC Technologies` | `Rawafed Al Sharq Information Technology Company` | Known alias, learning-loop rule 94 |
| Supplier | SAR 13,800.00 | `KHIBRAT AL QARAT TRADING EST.` | `KHIBRAT AL QARAT TRADING EST` | Trailing period |
| Supplier | SAR 1,104.00 | `Al Suhaili Company for Trade and Development Electricity Department` | `Al Suhaili Company for Trade and Development` | Department suffix |

Build these six into an explicit crosswalk table used by every importer. Do **not** fuzzy-match at
run time: record the decision once, apply it deterministically, and fail loudly on anything not in
the table. Four are punctuation or suffix variants and can be approved immediately; the Tawal alias
and the Arabic spelling need a named confirmation because between them they carry SAR 17.2 million.

**Effect on the schedule.** The Journal Entry importer was previously described as the largest
remaining build. It remains the largest by volume, but this probe shows it is low-risk: one cost
centre, no party complexity, no unresolved accounts. The residual risk in the programme has moved to
(a) whether Flexsoft can produce the invoice-level AR/AP extract at 31 December 2025, which is
**still unverified**, and (b) the ZATCA app change and its proving run.

##### Stage 5.3B — preflight, in three waves

The waves matter. Wave 1 requires a Frappe Cloud deployment and a site restart, so it must not run
while an import batch is in flight. Wave 2 is pure data work on the live site and can run in
parallel with Wave 1. Wave 3 depends on both.

**Wave 1 — the app change and its proving run (do this first).**

| # | Action | Detail |
|---|---|---|
| P6a | Create the control and evidence fields | `custom_is_legacy_import` (Check, `no_copy`). Separate **legacy evidence** fields — `custom_legacy_qr_code` (Attach Image), `custom_legacy_invoice_xml` (Attach), `custom_legacy_invoice_hash`, `custom_legacy_uuid`, `custom_legacy_clearance_ref`. Make `custom_legacy_id` read-only. |
| P6b | Fork change | Early return on `custom_is_legacy_import` in **three** places: `generate_einvoice`, `enforce_b2b_clearance_on_submit`, and `validate_sales_invoice` — the third is mandatory because opening invoices carry no tax rows and that validator throws on an empty `taxes_and_charges`. One focused commit; do not bundle the Stage 2 retention fix, which is still awaiting a tax-adviser decision. |
| P6c | Prove the branch offline | Unit-test the early return against the local clone before deploying. |
| P6d | Deploy, then run the proving run in 5.3E-1 | Nothing else runs on the site during this window. |

**The legacy QR goes in the legacy fields, never the active ones.** `custom_invoice_qr_code`,
`custom_invoice_xml`, `custom_invoice_hash`, `custom_invoice_icv` and `custom_zatca_submit_status`
are the fields the live integration writes and reads. Writing an original QR into
`custom_invoice_qr_code` would make a migrated document indistinguishable from a natively cleared
one. Store it in `custom_legacy_qr_code` and have the print format render the legacy QR when
`custom_is_legacy_import = 1`, so the printed document still shows the invoice's own original QR
while the system never treats it as a new clearance.

**Wave 2 — data preflight (parallel with Wave 1, no deployment).**

| # | Action | Detail |
|---|---|---|
| P9 | **Neosys platform backup — take this FIRST** | P4 and P5 delete 328 draft documents. The backup is the rollback point and must exist before anything is deleted, not after. Record timestamp, operator and purpose. |
| P1 | **Enable account `2281`** | Carries 609 of the 2026 JE lines and every staged PR tax template. |
| P2 | **Create Fiscal Year 2025** | Only FY2026 exists, so a 31 December 2025 opening cannot be posted. Post the opening `2025-12-31` with `is_opening = Yes`. |
| P3 | **Repair the warehouse tree** | Enable root `All Warehouses - SIG`; resolve the second root `Main Warehouse - SIG`; **disable `Riyadh Warehouse - SIG`**, which is currently enabled contrary to the record and is the item-default trap behind learning-loop rule 100. Stock Settings default `مستودع المزاحمية - SIG` is correct. |
| P4 | **Delete the pre-2026 drafts** | 148 Purchase Orders, 135 Purchase Receipts, all 45 Material Requests. Owner-approved; none is submitted, so none carries stock or GL effect. |
| P5 | **Delete the duplicate dry-run receipts** | `MAT-PRE-2026-00002` and `MAT-PRE-2026-00003` carry no legacy remark and duplicate legacy `-00036` and `-00035` (SAR 17,500 on 2026-08-23, SAR 15,800 on 2026-08-25). Left in place they overstate stock and payables by SAR 33,300. |
| P7 | **Freeze Flexsoft and re-extract every workbook at one timestamp** | Add the **31 December 2025 AR and AP outstanding-by-party extract** required by Decision 1. The GL currently runs to 2026-08-30 and the Stock Ledger to 2026-08-25, and `MAT-PRE-2026-00038` already proves the drift. |
| P11 | **Create cost centre `10001045 - Colocation 2026 project`** | Used by the 2026 Sales Invoice population and absent from the target. Create under Operations & Projects. |
| P12 | **Approve the six-party crosswalk (Stage 5.3A-2)** | Four are punctuation variants and can be approved immediately. The Tawal alias and the `لجين` Arabic spelling need named confirmation — together they carry SAR 17.2 million. |
| P10 | **Create the `Temporary Opening` account** | No such account exists on the SIG chart (verified 2026-08-31). Create it as a postable leaf with `account_type = Temporary`. It carries the opening offset for both stock and the opening invoices, and must net to zero once the opening is complete. |

**Wave 3 — the opening.**

| # | Action | Detail |
|---|---|---|
| P8 | **Post the 1 January 2026 opening** | Stock Reconciliation SAR 5,725,006.11 dated `2025-12-31` against `Temporary Opening`, plus the opening JE excluding account `134`, carrying the offsetting Temporary Opening debit and **party rows for AR and AP** per Decision 1. Verify Temporary Opening nets to zero before proceeding. |

##### Stage 5.3C — the opening position (evidence complete)

The opening reconciles exactly and needs no further derivation:

| Control | Value | Source |
|---|---:|---|
| Opening stock at 31 Dec 2025 | **SAR 5,725,006.11** | Last Stock Ledger movement per item/warehouse before 2026-01-01 — 194 non-zero item/warehouse rows |
| Trial balance account `134 - المخزون`, opening Dr | **SAR 5,725,006.11** | `dump/Trial_Balance (1).xlsx` |
| Opening total debit = total credit | **SAR 23,715,313.37** | Assets 23,715,313.37 = Liabilities 16,133,491.46 + Equity 7,581,821.91 |

All opening stock sits in `مستودع المزاحمية`. Sulai and Makkah are nil at 31 December 2025.

Posting mechanism — the inventory value must appear **once**:

1. Post the opening **Stock Reconciliation** dated `2025-12-31`, with `expense_account` set to a
   `Temporary Opening` account (equity/temporary, not a P&L expense). This debits inventory
   5,725,006.11 and credits Temporary Opening.
2. Post the **opening AR and AP invoices** per Stage 5.3A-1 Decision 1 — one submitted
   `is_opening` Sales Invoice or Purchase Invoice per document still outstanding at 31 December
   2025, against `Temporary Opening`, with no tax rows. These carry AR **8,041,288.63** and AP
   **6,164,951.84** in full.
3. Post the opening **Journal Entry** dated `2025-12-31` with `is_opening = Yes` from the trial
   balance, **excluding** account `134 - المخزون` (carried by step 1) and **excluding AR `133` and
   AP `226`** (carried by step 2), and including the offsetting debit to Temporary Opening.
4. Temporary Opening then nets to zero. Verify that, and verify that inventory, AR and AP are each
   stated exactly once, before proceeding.

The three steps are mutually exclusive by construction, so the reconciliation is arithmetic: opening
Sales Invoices must total 8,041,288.63, opening Purchase Invoices 6,164,951.84, opening stock
5,725,006.11, and the whole opening 23,715,313.37 on each side.

The existing pack in `outputs/opening_stock_pack_20260831/` was built at **2026-08-25** — the
superseded August cutover. Rebuild it at the 31 December 2025 cutoff before use.

##### Stage 5.3D — the 2026 document set

**Purchase Receipts — resolved.** The Stock Ledger gives an unambiguous warehouse for every 2026
receipt: 36 receipts, each resolving to exactly one warehouse, zero spanning two.
32 → `مستودع المزاحمية`, 4 → `مستودع مكة` (`MAT-PRE-2026-00012`, `-00029`, `-00030`, `-00031`).
No warehouse needs to be guessed or deferred, and the earlier "seven deferred receipts" warehouse
question does not arise for the 2026 subset.

The authoritative 2026 set is **`MAT-PRE-2026-00001` … `-00038`** (38 vouchers, SAR 2,870,193.56).
Against that, the target currently holds 34 legacy-tagged drafts plus the two duplicates in P5.
Four are missing and must be created before the stock replay is complete:

| Missing | Reason it is absent | Action |
|---|---|---|
| `MAT-PRE-2026-00009` | Previously recorded as a source reference with no imported target | Create from source |
| `MAT-PRE-2026-00021` | The single source Return, excluded by the old lifecycle rule | Create as a **linked return** against its original receipt, not as a negative import |
| `MAT-PRE-2026-00037` | Dated 2026-08-27, after the Stock Ledger extraction | Picked up by the P7 re-extract |
| `MAT-PRE-2026-00038` | Dated 2026-08-23 but entered after extraction | Picked up by the P7 re-extract |

**Purchase Orders.** 37 of the 185 drafts are 2026. Submit only those whose commitment is still
open at the freeze date; a PO must be submitted before a Purchase Receipt can reference it, so the
16 verified PO→PR links drive the sequence. POs create no stock or GL.

**Material Requests.** All 45 staged requests are **2024** documents. None is a live 2026
commitment. They are deleted under P4 and are not part of the replay.

**Stock Entries.** There are **no 2026 Stock Entries**. All 69 2026 stock-ledger movements are
Purchase Receipts, and all 129 captured Stock Entries are pre-2026. They are archive-only.

Note for Finance: 2026 stock rises from 5.72M to 8.49M with receipts only and **no issues or
consumption at all** — project costs run through Journal Entries instead. The replay reproduces the
source faithfully either way, but confirm this is genuine policy rather than unrecorded consumption
in Flexsoft, because ERPNext will faithfully accumulate the inventory asset.

##### Stage 5.3E — historical Sales Invoices (the one exception to "as is")

Sales Invoices are the only doctype that cannot be replayed as-is, and the reason is in the
installed code rather than in policy:

- `generate_einvoice` (`clearence_util.py:42`) is guarded **only** by the Company-level
  `custom_enable_zatca_e_invoicing`. There is no per-invoice bypass. A legacy invoice submitted
  today is signed and **transmitted to FATOORA as newly issued**.
- `enforce_b2b_clearance_on_submit` then rejects the submission unless clearance returned
  `CLEARED`, so the B11 guard blocks legacy invoices regardless.
- `custom_is_zatca_test = 1` is **not** a valid bypass: it takes the compliance path and still
  calls ZATCA.

What makes the approved approach safe is verified: **ICV and PIH are read from the
`Zatca Transactions` table** (`get_previous_invoice_counter` / `get_previous_invoice_hash`),
filtered by production CSID — not from a count of Sales Invoices. An invoice that never calls ZATCA
creates no transaction row and leaves the active hash chain untouched. `create_qr_code` also returns
early for Phase 2 with a production CSID, so an attached legacy QR is not overwritten.

Required change in the SIG fork, before any Sales Invoice is submitted:

1. Create `custom_is_legacy_import` (Check, `no_copy`, **read-only after import**) on Sales Invoice.
2. Early-return on it in **both** `generate_einvoice` and `enforce_b2b_clearance_on_submit`.
3. Leave every other path untouched: live invoices continue to clear normally.

Two further constraints:

- `validate_sales_invoice` runs in `before_submit` regardless of any ZATCA flag and throws when
  `taxes_and_charges` is empty. Legacy zero-rated or exempt invoices need an approved tax template
  or the batch fails mid-run.
- `custom_legacy_id` is currently `read_only = 0` on all 19 migration doctypes. Make it and
  `custom_is_legacy_import` immutable before the replay, or the audit trail is editable.

Retain the original invoice number and date, and attach the original PDF, XML and QR as legacy
evidence. Store historic UUID, hash and clearance reference in dedicated legacy fields — never in
the active ZATCA fields. An attached original QR preserves evidence; it does not make a copied
document a newly cleared invoice.

Eligibility follows the source audit state: include every source invoice that was submitted,
whether Paid, Unpaid or Overdue; exclude only genuine Drafts. `SIG-SINV-26-005` is confirmed in
scope (Draft → Unpaid audit trail, original QR attached, currently Overdue).

Acceptance: submit one representative legacy invoice and prove that (a) the target GL matches the
source, (b) no FATOORA request, retry or credential use occurs, (c) `Zatca Transactions` gains no
row and ICV/PIH are unchanged, and (d) the original QR/XML/PDF remain retrievable.

##### Stage 5.3E-1 — the legacy-invoice proving run

Run immediately after the P6d deployment and **before** any invoice import. Three tests in one
session, because they interlock: the change must bypass ZATCA for legacy invoices *and* must leave
enforcement intact for live ones.

**Blast radius.** The honest risk is that a faulty early return sends the test invoice to FATOORA as
a genuine cleared invoice, which cannot be un-cleared. Bound it: use a **minimal-value disposable
invoice** (for example SAR 1.00 net). If the guard fails, the outcome is one extra cleared invoice
and ICV + 1 — the same situation this site has already been through six times and cleaned up with
linked credit notes. If a Frappe Cloud site clone is available, run Test 1 there first; the bounded
live test is the fallback, not the preference.

**Record before submitting:** the current `Zatca Transactions` row count, the latest row's
`invoice_icv` and `invoice_hash`, and the Company's `custom_production_csid`.

| Test | Setup | Pass criteria |
|---|---|---|
| **1 — legacy bypass** | Disposable invoice, `custom_is_legacy_import = 1`, `custom_is_zatca_test = 0`, customer type **Company** (so the B2B path is exercised), tax template attached | `docstatus = 1`; `Zatca Transactions` count and latest row **unchanged**; `custom_zatca_submit_status`, `custom_invoice_icv`, `custom_invoice_hash`, `custom_invoice_xml`, `custom_invoice_qr_code` all **empty**; no integration Error Log entry; GL posts correctly to Debtors, Sales and `2281` |
| **2 — live enforcement intact (closes B11)** | Normal B2B invoice, `custom_is_legacy_import = 0`, clearance forced to fail | Submission is **blocked** with the guard's message; no GL is posted; the error is recorded. This is the negative regression that has never been run, and P6b edits the exact function it tests. |
| **3 — legacy evidence renders** | Attach a real original QR to `custom_legacy_qr_code` on a legacy invoice | The print format renders the legacy QR; its decoded payload is byte-identical to the original Flexsoft QR; the active ZATCA fields remain empty |

Then repeat Test 1 against **one real legacy invoice**: `SIG-SINV-26-005`. It is the single January
Sales Invoice, so the proving run doubles as the first document of the January batch. Reverse the
disposable invoice from Test 1 with a linked credit note before starting the replay.

**Do not proceed to the invoice import until all three tests pass.** A guard that has only been
proven on the positive path is the failure mode this project has already hit once, with B11.

##### Stage 5.3F — monthly import pipeline (redesigned 2026-09-03)

**Why this replaces the previous six-step list.** Jan/Feb produced 118 files under
`outputs/migration_2024/` — most of them one-off, uniquely-named scripts and JSON outputs improvised
per exception as it was found (rounding, held payments, cost-center autonaming, disabled accounts,
UOM fractions, valuation method). None of that was necessary: a complete, correctly-classified
**full-year** manifest already existed before any of it started — `document_manifest.csv` and
`import_pack_index.json` classify all 3,777 2024 source parents across every doctype;
`je_manifest.csv` / `monthly_import_index.json` classify all Journal Entries, already broken out by
month; `family_source_packs_2024.jsonl` carries the full row-level source payload for every document.
**None of that needs rebuilding for March, April, or any later month — it already covers the year.**
What was missing was a pipeline that consumed those manifests through a fixed sequence of named,
reusable stages instead of reinventing one per problem. This section is that pipeline.

**Closed 2026-09-03 — disabled master data needs no per-month checking.** Every disabled Account (23),
Item (6) and Supplier (5) on the target was cross-checked against the **entire 2024 source** (GL
export plus Stock Ledger), not just one month. Zero matches across all three categories: the disabled
accounts are April-template defaults the August COA cleanup retired (`Debtors`, `Creditors`, `Cash`,
`Sales - SIG`, etc.), the disabled items and one disabled supplier (`Various suppliers`) are test
fixtures. None is touched by any 2024 transaction. This closes the question for the whole year, not
only for the months already imported — do not re-run it monthly, and do not blanket-enable disabled
master data to save a check that costs nothing and finds nothing. If a later month's data genuinely
needs a currently-disabled record, use the narrow, reversible pattern already established (rule 111):
enable that one record, perform the write, restore its prior state in a `finally` block.

**Foundational rule: one script per stage, parameterized by month; one status artifact per month.**
`scripts/post_je_batch.py --month=YYYY-MM` is the pattern — a script takes the month as an argument
and is reused for every month, rather than a new uniquely-timestamped script per run. Every stage
below names its script and its one output file, `outputs/migration_2024/month_close_YYYY-MM.json`,
which each stage updates in place. No stage produces a second, differently-named artifact for the
same fact.

**One-time prerequisites, not monthly work.** Costing method (Moving Average), UOM fraction
permission (`Nos`), the opening bridge, and the `1911` alignment account are global corrections done
once (Stage 5.3F-0/5.3F-2) and never repeated per month. Do not re-derive them.

**Every document lands on its Flexsoft legacy `name`, not just `custom_legacy_id`.** All seven
stagers (`post_je_batch.py`, `post_purchase_order_batch.py`, `post_purchase_receipt_batch.py`,
`post_purchase_invoice_batch.py`, `post_sales_invoice_batch.py`, `post_payment_entry_batch.py`,
`post_stock_entry_batch.py`) import `legacy_rename_helper.py` and rename each draft to its legacy
id immediately after creation, before submit. This closed a real gap: through March, only Sales
Invoice and the opening JE were renamed, and the other five doctypes had to be fixed retroactively
in a 2,468-document, 7-doctype campaign on 2026-09-04 (rule 219). No later month should need that
pass — verify with a one-line sweep (count `name != custom_legacy_id` per doctype) at Stage F
close if in doubt.

**No auto-rounding on Purchase Order/Receipt/Invoice, and none needed on Sales Invoice.**
`disable_rounded_total: 1` is set on every PO/PR/PI payload. Without it, ERPNext silently rounds
`grand_total` to the nearest whole SAR and posts the difference as an artificial line to `5212 -
تقريب` — this is **not** genuine Flexsoft rounding (confirmed: SAR 32.26 accumulated across the
first 756 Purchase Invoices before the fix, zero after; rule 222). Sales Invoice staging already
sets this correctly. Because the root cause is fixed at the invoice level, the Payment Entry
allocation-capping logic in Stage E step 4 below should now rarely or never trigger — if it does,
suspect a fresh instance of this same class of bug before assuming it's ordinary rounding.

**Every stager finalizes an already-existing draft, not just reports it.** `finalize_existing()`
in `legacy_rename_helper.py` is called from the `already_exists` branch of every stager except
`post_je_batch.py` (which never submits by design): it checks live `docstatus` and renames/submits
an existing draft rather than silently skipping it with a false "success" (rules 212, 223). It also
recognizes a cancelled document (`docstatus == 2`) and takes no action on it (rule 226) — this
matters whenever a wrongly-totaled or wrongly-superseded document has been cancelled and replaced
under a `-1` suffixed legacy id (see Stage D and Stage C notes below).

**Pre-session stray duplicate drafts recur across Purchase Order/Receipt — verify before
deleting, every time, never assume clean.** A leftover batch from before this migration's careful
process left ~319 duplicate drafts (`docstatus=0`, no `custom_legacy_id`) scattered across PO/PR
for the whole year, not just already-migrated months. They only surface as a blocker when a
rename's target name collides with one. When that happens: fetch both documents, confirm item
code/qty/rate/supplier match (the stray is reliably missing VAT or uses an uncleaned raw item-code
string), then delete only the stray and retry. Do not mass-delete the ones that aren't currently
blocking anything — clear them reactively, month by month, not speculatively.

---

**Stage A — standalone Journal Entries. Always first; zero dependencies.**

Journal Entries need no other document to exist — no PO, PR, PI or PE. That is what makes them safe
to stage before anything else, not merely convenient.

1. Filter `je_manifest.csv` to the month, `decision = IMPORT`. Already classified; do not reclassify.
2. **Gate — overlap check, regenerated for this month, never carried over from a prior month:** confirm
   no Sales or Purchase Invoice in the same month shares an exact date/amount match with a JE (the
   Jan/Feb check found `NO_OVERLAP_FOUND` on all 9 invoices tested — a real result, but specific to
   Jan/Feb's population, not a standing guarantee for March). Generalize
   `invoice_je_overlap_2024_01_02.csv`'s method into a `--month=` script; do not skip this gate on the
   assumption that "it was clean last time."
3. Stage as drafts: `scripts/post_je_batch.py --month=YYYY-MM`.
4. Submit in source posting date/time order.
5. Verify: submitted count and total debit match the manifest's `IMPORT` figures for the month exactly.

**Stage B — purchase dependency chain: PO → PR → PI, in that order.**

1. Stage and submit the month's Purchase Orders: `scripts/post_purchase_order_batch.py
   --month=YYYY-MM --submit`. POs create no stock or GL effect, so this can run immediately after
   Stage A.
2. Stage and submit Purchase Receipts: `scripts/post_purchase_receipt_batch.py --month=YYYY-MM
   --submit` — resolves the source PO reference automatically by `custom_legacy_id`, and takes
   warehouse from the item row's own "Accepted Warehouse" field (مخازن), never from a free-text
   note. Verify the Stock Ledger: summed `actual_qty` per receipt equals the submitted receipt
   quantity (learning-loop rule 172).
3. Only then release the linked Purchase Invoices, using `scripts/post_purchase_invoice_batch.py
   --month=YYYY-MM` — resolves each invoice's source PO/PR reference against already-submitted target
   documents by `custom_legacy_id` automatically at staging time. Verified March 2026-09-04:
   `ACC-PINV-2024-01676` → `MAT-PRE-2026-00177`, `ACC-PINV-2024-00661` →
   `PUR-ORD-2026-00203`/`MAT-PRE-2026-00176`, both exact against live source. This replaces the
   Jan/Feb pattern of holding every linked invoice out for manual linking (rule 208) — an invoice
   with no PO/PR reference submits independently in the same pass; one that has a reference but the
   target isn't found yet is left unlinked rather than held or guessed.
4. Verify: `1341` movement for the month's receipts ties to the Stock Ledger export at item/warehouse
   level (the row-level oracle from Stage 5.3F-0, applied every month, not only during the valuation
   correction).

**Stage C — Sales Invoices, legacy mode only.**

`scripts/post_sales_invoice_batch.py --month=YYYY-MM --submit`, consuming the pre-built
`sales_invoice_payloads_2024.jsonl` pack (payloads already carry `custom_is_legacy_import: 1` and
`disable_rounded_total: 1`). Every Sales Invoice submits through `custom_is_legacy_import = 1`.
Never submit a Sales Invoice for a month where `custom_is_legacy_import` on the fork is not
deployed and proven (Stage 5.3E-1).

1. **Gate — exclude, then cross-check.** Exclude any record whose own `status` field is `Draft`,
   regardless of `decision`/`safe_to_stage` (rule 210 — two records in the whole year were caught
   this way, one only by GL-presence, not by any pack flag). The script does the status exclusion
   automatically; if in doubt for a new month, independently cross-check GL presence.
2. `fix_uom()` in the script remaps `Pcs`→`Nos` and `M2`→`Square Meter` — both have been observed
   not to exist verbatim as target UOM records. Extend this map, don't fight it record by record.
3. **Header total vs item total can disagree — trust the header.** A source invoice can carry a
   genuine `discount_amount` (`apply_discount_on: "Grand Total"`) that the pack's item rows never
   reflect, even though the pack's own `source_total` field already has the right answer (rule
   226, found via Stage F's AR control, not by inspecting the invoice itself). Before trusting a
   batch's submissions, spot-check that each submitted `grand_total` equals the pack's own
   `source_total` for that record; if not, cancel and resubmit with `discount_amount` set
   explicitly (Frappe's real fieldname — not `additional_discount_amount`) under a `-1` suffixed
   legacy id, same convention as the Stage D amendment case below.

**Stage D — Stock Entries, classified before staged.**

`scripts/post_stock_entry_batch.py --month=YYYY-MM --submit`.

1. **The script cross-references `document_manifest.csv` and excludes any `SKIP_*` decision before
   staging** (rule 224) — this was not always true; an earlier version selected by `doctype` +
   `posting_date` alone and staged a `SKIP_SUPERSEDED` original right alongside its own `-1`
   replacement, double-posting real stock (caught by a `NegativeStockError` on the correct
   document, not by the script itself). Trust the script's own `excluded_superseded` field in its
   JSON output as proof, not just its silence.
2. **Before the first staging run of a new month**, diff the month's distinct source `Project` and
   `UOM` values against `PROJECT_MAP`/`uom_map()` and a live target UOM fetch — do not wait for a
   `LinkValidationError` or an "unmapped project" error mid-batch (rule 211). A blank source
   `Project` is valid (a general warehouse issue with no work order) — the script allows it rather
   than erroring, and the resulting payload simply omits the `project` field.
3. Verify each submission against the row-level oracle (`Stock_Ledger.xlsx`) — the standing method
   for every month's stock movements, not a one-time investigation. A row for a non-stock item
   (`is_stock_item: 0`, e.g. a freight/customs-fee line coded as an "item") legitimately has no
   Stock Ledger Entry on either side — that is not a mismatch to chase (rule 225).
4. A cancelled-and-corrected predecessor (e.g. a costing fix, or a wrongly-double-posted
   `SKIP_SUPERSEDED` case) keeps its exact legacy name on the cancelled document; its correct
   replacement takes a `-1` suffix, matching how Flexsoft's own source data already uses that
   convention for amendments elsewhere.

**Stage E — Payment Entries. Always last.**

A Payment Entry generates its own GL on submit. It is never represented twice — once as a Payment
Entry and again as a raw JE for the same cash movement (confirmed absent in Jan/Feb by the Stage A
overlap check; do not assume it stays absent without re-checking each month).

1. `scripts/build_payment_link_manifest.py --month=YYYY-MM --output=...` resolves each source
   payment's reference rows to a target — **by reference type**, not just Sales/Purchase Invoice:
   a Payment Entry reference can point at a Journal Entry too (rule 213), including the opening
   bridge JE, which resolves by live `name` rather than `custom_legacy_id` since it predates that
   field. Before calling a reference unresolved, check its own source month — a reference to a
   month or year not yet migrated is expected (`FUTURE_ADVANCE`), not an error.
2. Classify each payment into exactly one of:
   - **Linked** — target invoice already submitted (this month or earlier). Stage with the
     `references` allocation.
   - **Future-dated advance** — target invoice's own posting date falls in a month not yet reached.
     Confirmed real, not hypothetical: three Jan/Feb payments (SAR 875,889.93) referenced invoices
     dated March and June 2024. Stage as a **standalone unallocated advance**, dated at its own true
     posting date, with `custom_legacy_id` and a remark naming the future invoice. Allocate via
     Payment Reconciliation once that invoice's month is reached — do not hold this month for it.
   - **Genuinely unreferenced** — source carries no reference row at all (rule 179). Stage as
     standalone, unallocated, same as above, no future-invoice note needed.
   - **Mixed** (some references resolve, one or more don't) — never drop the whole payment over one
     bad reference (rule 215). Stage the resolvable references normally and leave the remainder as
     a named, remarked unallocated amount on the same document — `build_payment_link_manifest.py`'s
     classifier is payment-level, not reference-level, so a mixed case like this currently needs
     the same manual construction used for `ACC-PAY-2024-00577` (March) and `ACC-PAY-2024-01038`
     (May) rather than the batch script.
3. **Gate — cumulative allocation check** before submitting: sum every staged payment's allocation
   against each target invoice and compare to that invoice's live outstanding amount, with a small
   (~SAR 1) tolerance for ordinary halala rounding on the invoice's own total — not a strict
   zero-tolerance check (rule 214). Catches a sequence that would individually pass but over-clear
   an invoice in aggregate (rule 177). If this gate fires often on freshly-staged invoices, suspect
   `disable_rounded_total` wasn't set on the invoice stager, not a payment-side data problem.
4. Submit in source date order via `scripts/post_payment_entry_batch.py --month=YYYY-MM --submit`.
5. Verify: submitted count matches the month's source payment count exactly, accounting for advances
   explicitly deferred to a later month.

**Stage F — reconcile and close.**

1. Compute all five controls **fresh** — trial balance, stock value by item/warehouse, AR, AP,
   bank/cash — against Flexsoft for this month. Never cite a comparison produced before the month's
   own Stage A–E completed, and resolve every account and voucher by `custom_legacy_id` rather than a
   hardcoded name, in case a rename pass has already run (rule 202). **Compute the month's real last
   day** (`calendar.monthrange`, or an open-ended `< first-of-next-month` range) — a hardcoded `28`
   for February silently drops leap-year Feb 29 and produces large false deltas on every control
   (rule 220, cost a full re-investigation of a "broken" February that was never actually broken).
2. **Gate:** any single account or the month total exceeding the agreed materiality threshold stops
   the close — investigate, do not align (Stage 5.3F-2). A large apparent gap is not automatically
   real: check first whether it's fully explained by (a) the one-time opening JE / costing-repost
   postings if this is the very first month checked, (b) a single deferred payment reference not
   yet resolvable, or (c) the date-range bug above — all three have each fully explained an
   apparent 6-or-7-figure gap that turned out to be nothing once traced.
3. Within threshold, post one alignment Journal Entry to `1911`, one line per differing account.
4. Freeze: `acc_frozen_upto` and `stock_frozen_upto` to the month end.
5. Write the final state to `month_close_YYYY-MM.json`: five control deltas, alignment posted (if
   any), freeze confirmation, timestamp. This one file is the record of the month — not a scattered
   set of investigation outputs.
6. Periodically (not necessarily every month) re-run the cumulative check across all months closed
   so far, not just the current month in isolation — this is what surfaced May's discount-amount
   gap and confirmed Jan-May tie to SAR 4.13 cumulative once known one-time postings are excluded.

---

**What this removes, concretely.** Applied to March (343 JE, ~186 PI/PE-scale population, per
`import_pack_index.json`), this pipeline needs: one JE stage/submit run (Stage A), one overlap check,
one PO/PR/PI dependency run (Stage B), one SI batch (Stage C), one Stock Entry classification and
stage (Stage D), one payment-link manifest and stage (Stage E), one reconciliation (Stage F) — seven
stage-scoped actions with one output file each, against the ~70 uniquely-named artifacts Jan/Feb
produced working the same ground without this structure.

##### Stage 5.3F-0 — BLOCKING: valuation method and UOM correction

**Raised 2026-09-03. No further month may be imported until this is complete.**

Flexsoft uses **Moving Average** costing; Neosys is configured for **FIFO**. Proven by tracing item
`C-FNC`: the 520-unit issue values at 51,355.96 under Moving Average (Flexsoft's figure) and
51,325.00 under FIFO (Neosys's). Separately, UOM `Nos` carries `must_be_whole_number = 1`, so a
source issue of 0.5 posted as 1.0. Together these produce exactly the SAR 13.46 Jan/Feb variance —
30.96 less 17.50, with nothing unexplained.

Two corrections, both configuration:

| # | Change |
|---|---|
| V1 | Stock Settings valuation method **FIFO → Moving Average** (no per-item overrides exist) |
| V2 | UOM `Nos` **`must_be_whole_number` 1 → 0** — permits fractions, alters no existing data |

Scope: a full source-ledger scan finds 104 fractional rows across 30 item/UOM combinations. The 85
`Mtr` → `Meter` rows are unaffected (`Meter` already allows fractions); **19 rows across four items**
map to `Nos` and are silently rounded. Only one has been imported so far.

**Correct, do not revert.** Only 30 stock documents are posted. Procedure, verification table and
timing rationale are in `migration_2024_preflight.md` section 8. V1 is an accounting-policy decision
requiring Finance confirmation — Moving Average becomes SIG's live costing method from 2026 onward.

Fix now and 30 documents are re-valued. Fix at month 12 and it is several hundred, across months
already signed and frozen.

**Verification standard (added 2026-09-03):** post-repost, every stock document is checked row by row
against Flexsoft's `Stock_Ledger.xlsx` — `(voucher_no, item, warehouse)` → quantity, valuation rate,
value change. Receipts already carry the source rate directly and are exact by construction. Issues
are computed by the engine and cannot be overridden, so this check verifies rather than injects; since
Moving Average is deterministic, an exact row match proves the whole chain behind it was faithfully
replayed, and any mismatch names a specific defect rather than being absorbed as engine noise. Detail
and column mapping: `migration_2024_preflight.md` §8.6a. This is the stock-side counterpart to Stage
5.3D's voucher-completeness check.

##### Stage 5.3F-1 — rollback

Every month's batch must be revertible before it is started. The rollback decision criteria, the
document-level unwind order, the Frappe Cloud restore points and the post-rollback verification
checklist are in `migration_2024_preflight.md` section 7.

Two rules apply to every batch:

1. **Take a fresh backup immediately before submitting**, not after. It is the only rollback point
   that isolates one month.
2. **Prefer the document-level unwind over a site restore.** A restore reverts configuration work as
   well as data, and on 2026-09-02 that would have resurrected 41 deleted SNB drafts and two
   duplicate reconciliation drafts. Restore only when an unwind cannot reach a tying state.

Cancelling stock documents runs in **reverse submission order** — a dependent write-off cannot be
cancelled after the document that established its stock.

##### Stage 5.3F-2 — monthly alignment and close

The month is the control. Each month closes to Flexsoft's exact per-account balance, so drift never
pools and debugging stays linear: if month N is wrong, the cause is in month N.

Per month, after import and before close:

1. Compare **per-account** closing balances, Flexsoft vs Neosys, and stock value by item/warehouse.
2. **Gate:** if any single account, or the month total, exceeds the agreed threshold — **stop and
   investigate. Do not align.** The alignment is only permitted to be small; that is what separates
   it from a plug.
3. Within threshold, post one alignment Journal Entry: **one line per account that differs**, each
   sized to close that account exactly, plus one offsetting line to the alignment account. Every
   business account appears once, so no line can collide with itself.
4. Verify closing balances now match exactly; freeze the month (`acc_frozen_upto`,
   `stock_frozen_upto`).

**The alignment account must be a balance-sheet account, never an expense.** Posting to an Expense
account under `54 - نفقات غير مباشرة` would put migration artifacts into profit and make Neosys's
monthly P&L differ from Flexsoft's — defeating the purpose. Create **`1911 - تسوية شهرية للترحيل`**
under `1900 - حسابات مؤقتة`, `root_type = Asset`, `account_type = Temporary`, as a sibling of the
existing opening bridge `1910`. Keep it separate from `1910` so the one-time opening and the running
monthly total remain independently auditable.

Genuine business rounding — halala allocation differences on payments — continues to post to
`5212 - تقريب` (Expense), which is correct: that is a real cost in either system.

**Track the trend, not just the month.** A few riyals a month with random sign is rounding. The same
sign month after month, or a growing amount, is systematic — a mapping, tax or valuation defect that
aligning will never fix. Because `1911` is a clean balance-sheet account, its balance at any moment
is the total accumulated engine difference across the whole migration.

Measured baseline: of 121 accounts compared for Jan/Feb, only **10** differ, and **8 of those were one
root cause** — the three held payments rippling through payables, bank and two custody accounts.
**Closed 2026-09-03:** all three imported as standalone unallocated advances (Stage 5.3F step 1
exception) once their true nature was confirmed — each predates its own invoice by weeks to months,
not a missing import. `2261` (Payables) now ties to Flexsoft within SAR 3.22 across both months.
After Stage 5.3F-0's repost, `1341` (Inventory) ties exactly. The residual is now genuinely small
rounding, not the few hundred riyals originally assumed as a ceiling.

##### Stage 5.3F-3 — operational execution lessons (added 2026-09-03)

Five process defects surfaced while closing Jan/Feb that are not specific to those two months and
must be designed for from March onward, not rediscovered each time.

**1. Repost by transaction, not by item, whenever many items share one source voucher.**
`Repost Item Valuation` supports `based_on: Item and Warehouse` (one job per item/warehouse pair) and
`based_on: Transaction` (one job covers every item/warehouse a single source voucher touched). The
Stage 5.3F-0 correction initially queued 210 item-level jobs; clustering by `first_voucher` showed
187 of them traced to one Stock Reconciliation. Switching to Transaction-based jobs cleared that
cluster — and the entire remaining 289-pair scope — in **15 jobs instead of ~289**. Before any bulk
repost, cluster the scope by source voucher first; submit one Transaction-based job per voucher, not
one Item-and-Warehouse job per row.

**2. `repost_item_valuation.repost_entries` runs on an hourly schedule, not continuously.** A queued
repost sitting for 40+ minutes is not evidence of a backlog — it is normal cadence for this
Scheduled Job Type (`Frequency: Hourly Maintenance`). Two consequences: (a) batch reposts into few,
large Transaction-based jobs rather than many small ones, since each wave costs at most one hourly
tick regardless of how much work it contains; (b) if a correction is time-sensitive, a System
Manager can open the Scheduled Job Type record in the Frappe Desk (`/app/scheduled-job-type/repost_item_valuation.repost_entries`) and click **Execute** to run it immediately — confirmed working
2026-09-03, processed 13 of 14 queued jobs in under ten seconds once triggered. The equivalent API
call (`run_doc_method` → `execute`) is **not whitelisted** for a REST integration user and returns
403; this action currently requires a logged-in Desk session, not automation.

**3. A rename pass invalidates any script or filter that hardcodes a pre-rename document name.**
Once the legacy-name rename pass runs on a document (for example the opening JE, renamed from
`ACC-JV-2026-00045` to `ACC-JV-2024-02189-2`), any later query that excludes or matches it by the
old ERPNext-generated name silently stops working — it does not error, it just no longer finds the
document, producing a wrong result with no warning. This produced a real false alarm on 2026-09-03:
an account-difference investigation appeared to show a SAR 7.37 million discrepancy that was purely
an artifact of excluding the opening JE by its retired name. **Resolve every document by
`custom_legacy_id`, and re-resolve the current name at the time of use — never hardcode a name that
predates a rename pass.**

**4. A failed repost can still partially write to the Stock Ledger and Bin before failing at the GL
step.** The one 2026-09-03 failure (`MAT-PRE-2026-00001` / `Cable2m`, blocked by a disabled `Cost of
Goods Sold - SIG` account on an unrelated 2026 test document) left `Cable2m`'s Bin at qty 0.995 /
value 1.00 while GL never posted — a SAR 1.00 Bin-vs-GL mismatch confined to that one item. After any
`Failed` repost, check that item/warehouse's Bin against its GL account specifically; do not assume a
failure left no trace.

**5. A reconciliation artifact has a shelf life.** A source-vs-target comparison captured before the
most recent import, repost or rename pass will disagree with a fresh comparison — not because the
data changed incorrectly, but because the comparison basis moved. This is the same class of error as
the 850-vs-829-voucher date-parsing incident (`migration_2024_preflight.md` §7.5) and rule 3 above:
both were a stale or mismatched basis mistaken for a data defect. Every reconciliation output must
carry its capture timestamp, and any reconciliation older than the most recent import/repost/rename
on the same accounts must be re-run before being cited, not trusted as still current.

##### Stage 5.3G — correction pass

Only after every month from January to the freeze month ties. Errors carried in from Flexsoft are
corrected in Neosys as **dated correction entries in the current open period**, with a reference to
the replayed document they correct. Prior months stay frozen and keep their reconciled history.
This is the step that makes decision 2 safe: the replay proves the migration, and the corrections
are visible as corrections rather than buried in it.

##### Stage 5.3H — legacy archive after Flexsoft expiry (fallback if v3.5 pilot is not accepted)

Unchanged in intent, and now strictly sequential: it starts only after the 2026 replay is
reconciled and closed.

Provision a separate self-hosted ERPNext site as **SIG Legacy Archive**. It is an archive service,
not a third operational ledger.

1. Import pre-2026 master data, documents, original numbers and dates, linked references and
   available attachments. Preserve each Flexsoft identifier and label the records as migrated
   legacy data.
2. Disable ZATCA, e-invoice submission, email, workflows and all external integrations on the
   archive site. Historical legal invoices are never transmitted as new documents.
3. After reconciliation, make the archive read-only: restrict normal users to view and export,
   freeze accounting through 31 December 2025, and close the historical document types. Retain a
   controlled Finance/ERP-admin exception for verified repair only.
4. Keep an independent encrypted export and attachment backup alongside the archive site. The
   archive improves lookup; it is not the only retention copy.

Flexsoft remains a read-only source until expiry. The administrator has not authorised database or
files backup download, and that restriction is not to be bypassed; record any unavailable
attachment as a legacy-archive gap rather than fabricating it.

Neosys remains the only operating SIG ledger: it starts from the approved 1 January 2026 opening
and receives the 2026 replay and all new business thereafter.

##### Stage 5.3I — master data position

Master data import is **already complete** and is no longer a gate. Live counts, read 2026-08-31:

| DocType | Live | Source | Note |
|---|---:|---:|---|
| Customer | 73 | 66 | 4 disabled test masters retained and tagged |
| Supplier | 1,103 | 1,098 | 5 disabled |
| Item | 839 | 835 | 8 disabled |
| Item Price | 1,315 | 829 | buy/sell pairs; dedup optional, non-blocking |
| Address | 95 | 50 | plus company and ZATCA seller addresses |
| Contact | 237 | 218 | |
| Project | 27 | 25 | all linked to cost centres |
| Cost Center | 34 | 34 | complete |
| Account | 311 | 289 + roots | April shells disabled |

The remaining master-data work is corrective, not bulk import: Finance classifies the supplier rows
that carry expense labels, and the deferred supplier masters behind individual receipts are created
from source evidence rather than guessed.

#### Stage 5.4 — Cutover gate

- [ ] Stage 5.3A-1 decisions recorded; Stage 5.3B Waves 1–3 complete; the Stage 5.3E-1 proving run passed all three tests, including the B11 negative regression.
- [ ] Chart of accounts and VAT acceptance pack signed off (G2).
- [ ] The 1 January 2026 opening is posted and reconciles: stock SAR 5,725,006.11 to trial-balance account `134`, and opening debit = credit = SAR 23,715,313.37.
- [ ] Every month from January to the freeze month has been submitted, reconciled on all five control totals, and frozen. The monthly reconciliation register is complete.
- [ ] The Stage 5.3G correction pass is complete, or its open items are listed and accepted by Finance.
- [ ] Historical Sales Invoices are posted only through the deployed `custom_is_legacy_import` control, with acceptance evidence (a)–(d) from Stage 5.3E recorded.
- [ ] Master-data counts accepted by Operations, Finance and Warehouse owners, and the company `D` scope decision recorded.
- [ ] Backup and export archive of legacy records retained and access-controlled.
- [ ] Rollback and post-go-live support owner named.
- [ ] Named ERP users replace shared Administrator access for daily work (closed in G1, re-confirmed here).
- [ ] Single system of record declared per business domain, with the legacy system moved to archive-only.

---

## 6. Post-cutover roadmap

Only after G5. These are the remaining phases from `erpnext_baseline_config.md` section 11:

| Phase | Outcome | Entry condition |
|---|---|---|
| 3 — People | HRMS employee master, leave, payroll, approvals | HR policy and data approval |
| 4 — Intelligence | Insights dashboards, Drive governance, Telephony processes — workspace/interface design rationale in `MASTER-ERP-INTEGRATION.md`, execution tracking in **6A.7** | Stable operational data after cutover for the Number Cards themselves; the token pass and native-report inventory have no data dependency and can start now |
| 6 — Custom app | Repeatable automation released from the SIG repository | L4 capability genuinely exhausted |

Contract-operations expansion — project-specific child cost centres under the relevant preserved
legacy branch — happens continuously as work orders are created, not as a discrete phase.

---

---

## 6A. Stage 2 — post-cutover deployment

Stage 1 (sections 2–5) ends at cutover: clean ledger, migrated masters, compliant invoicing.
Everything below was investigated on 2026-08-29 and is **deferred to Stage 2**. Each item records
what was proven, so the next person starts from evidence rather than re-deriving it.

### 6A.1 Invoice print format — remaining work

Live as `SIG Tax Invoice` and `SIG Tax Invoice (Arabic Name)` on Sales Invoice. Outstanding:

| # | Item | Note |
|---|---|---|
| P1 | Validate against a **realistic multi-line invoice** | Every judgement so far was made on a zero-value single-line document. Multi-line wrapping, long Arabic descriptions, a discount row and six-figure amounts in the columns are all untested, as is the empty band between QR and footer |
| P2 | `in_words` still prints "SAR" | It comes from ERPNext's own number-to-words, not the template, so the riyal mark cannot replace it without overriding that function |
| P3 | Buyer *Other ID* prints only when populated | Empty today; it is the `BR-KSA-81` cause and is fixed at customer-import time, not in the template |
| P4 | Seller block is letterhead artwork, not text | Mandatory seller name/VAT/CR/address appear only in the stationery. Normal practice and the signed XML carries them properly, but confirm the tax adviser is content |
| P5 | Purchase Order has no custom format | It falls back to ERPNext standard, which does receive the `SIG` Letter Head |

**Proven and not to be re-litigated:** Frappe does **not** inject a Letter Head into a
`custom_format` print format — verified four ways (URL param, absolute image URLs,
`no_letterhead=0`, and setting the document's own `letter_head`), all producing byte-identical
PDFs. The invoice format therefore carries its own stationery; the `SIG` Letter Head covers every
other doctype. The two never stack. Equally, wkhtmltopdf does not scale a `background-image` on a
`position: fixed` element — it drew the 1299×1731px letterhead at 1299×1731**pt** on a 595×842pt
page. Use real `<img>` elements. SVG support is unreliable; rasterise to PNG (this is why the
U+20C1 riyal mark is an image — no bench font carries the glyph).

### 6A.2 WhatsApp delivery via Maytapi

Send the invoice or PO to the contact person on confirmation, through the same Maytapi line the
warehouse system uses (`wh/deployed/MaytapiSend.bas`).

**API contract, read from the VBA:**

```
POST https://api.maytapi.com/api/{product}/{phone}/sendMessage
     x-maytapi-key: <token>
     {"to_number":"966…", "type":"media",
      "message":"data:application/pdf;base64,…", "filename":"…pdf"}
```

**Sandbox capability, probed on the live site rather than assumed:**

| Capability | Result |
|---|---|
| `frappe.attach_print(...)` | works — returned a 154,441-byte PDF using `SIG Tax Invoice` |
| `frappe.integrations.utils.make_post_request` | available |
| `base64` | **not available** |
| `requests` | not available |

So a Server Script can build the PDF and make the call but **cannot base64-encode it**. Two routes:

- **Route A — Server Script + public file URL.** Send Maytapi a URL instead of a data-URI. Works
  today, no deployment. **But each invoice PDF becomes publicly downloadable** while the file
  exists; Frappe public files need no auth. Deleting the file after send narrows the window, it
  does not close it.
- **Route B — custom app module.** Full Python, base64 available, nothing public, and it satisfies
  section 12 of the baseline (integration logic belongs in a version-controlled app, not an
  untracked Server Script). Costs a push and a Frappe Cloud deploy.

**Recommendation: Route B.** Use A only if delivery is needed before the next deploy.

**Blocking facts:** the site has 33 Contacts and **not one carries a phone number**, so there is
nobody to send to until customer contacts are imported with mobiles. The Maytapi product ID, phone
ID and token are currently **hardcoded in the .bas file**; they belong in encrypted ERPNext
settings, not copied into a second file.

**Open decisions:** automatic on submit or a "Send on WhatsApp" button (automatic messages every
credit note and correction too); PO recipient assumed to be the supplier's contact; which print
format the message carries; and confirmation that the warehouse Maytapi line is the right sender
for customer-facing invoices.

<a id="retention-decision"></a>
### 6A.3 Retention, advance, discount and progress billing

Derived from `invwp/exportExl.bas`, which computes:

```
Q37 = subtotal − discount − advance − retention
Q38 = Q37 × 0.15
Q40 = Q37 + Q38
```

Row 35 is overloaded as discount **or** partial-payment amount, which is why the macro raises
*"Discount and partial payment cannot both be used on the same invoice"*. That is a spreadsheet
constraint, not a business rule, and should not be carried forward.

**The decision Stage 2 turns on — which structure does SIG actually issue?**

| | Structure A — invoice full value | Structure B — invoice net of retention |
|---|---|---|
| Invoice face | 1,150,000 | 1,092,500 |
| Output VAT declared now | 150,000 | 142,500 |
| Retention is | a **receivable** (57,500) | **unbilled work** |
| On release | cash only, no VAT document | a second tax invoice, 50,000 + 7,500 VAT |
| VAT timing | paid ~1 year before collection | follows the cash |
| Implemented by | the ZATCA app's retention feature | negative `Actual` tax row before the VAT row |

**The owner has described both.** "We invoice as per client including the retention" is A; the
spreadsheet arithmetic is B. They produce different ZATCA XML for the same job. Resolve by
inspecting a real issued invoice: if the VAT line is 15% of the full certified value it is A; if
it is 15% of the value after deducting retention it is B. **This is a tax-adviser decision.**

**If Structure A:**

- Create **`Retention Receivable`** under `13 - الاصول المتداولة`, `account_type = Receivable`
  (required — the GL entry sets `party_type`). Nothing suitable exists; the only chart match is
  `Retained Earnings`, which is Equity and unrelated.
- Enable `custom_enable_sales_retention` on Company (currently `0`) and set the default account.
- **Fix the withholding base.** `sync_retention_from_percentage` computes
  `net_total × pct`; the owner confirmed retention is 5% of net **plus** 5% of the VAT — i.e.
  `grand_total × pct`. As written it under-withholds 7,500 per million, and the shortfall sits in
  Debtors as permanently uncollectable. Requires a push and deploy. Verify `grand_total` is
  populated when the `validate` hook runs rather than assuming it.
- Release is **event-driven, not date-driven** (owner decision): a Payment Entry with
  `paid_from = Retention Receivable`, party the customer, referencing the original invoice. The
  retention GL entry already carries party and `against_voucher`, so this matches cleanly.

**If Structure B:** the app's retention feature stays **off**; deductions become negative `Actual`
rows ordered before a VAT row of charge type `On Previous Row Total` (verified available). An
unbilled-retention register and a release-invoice flow are then required instead.

**Verified either way:** the tax table supports `Actual`, `On Net Total`, `On Previous Row Amount`,
`On Previous Row Total`, `On Item Quantity`, and `apply_discount_on` supports `Net Total`, so
discount and advance can both be deducted before VAT natively — no custom code.

### 6A.4 VAT reporting and retention

**The statutory VAT return cannot be reduced for uncollected retention.** All four VAT reports on
the site — `Zatca VAT`, `Zatca VAT Detailed Report`, `VAT Audit Report`, `Zatca VAT Report` — are
built from **GL Entry / Account**, so they read the balance on `2281`. The retention split moves
value between two asset accounts and never touches the VAT account. That is correct: KSA VAT is
accounted on an invoice basis, and cash accounting is unavailable above roughly SAR 5m of annual
supplies, which SIG exceeds.

Under Structure A the only routes to a VAT reduction are a **credit note** (value genuinely falls)
or **bad-debt relief** under ZATCA's conditions. Retention is neither. Under Structure B the
question does not arise, because the retention was never invoiced.

**Deliverable:** a management report — *output VAT declared, and how much of it relates to cash not
yet collected*. Under A it quantifies the VAT being financed; under B it becomes the retention
pipeline. It is a management view and must never be presented as the return.

### 6A.5 Progress billing on the customer PO

The owner's proposal — carry the customer PO and bill against it — is ERPNext's **Sales Order**:

| Legacy | ERPNext |
|---|---|
| Customer PO value | Sales Order grand total |
| Partial invoice | Sales Invoice created from the SO |
| Paid to date | allocated advances and payments against the SO |
| Due | `outstanding_amount` |
| Progress | `per_billed` %, maintained automatically |

`po_no` and `po_date` already exist on the invoice for the customer's own reference. This is a
**process change** for the team, not just configuration: it means raising a Sales Order per
customer PO rather than invoicing standalone. Confirm before building.

### 6A.6 Stage 2 sequence

1. Resolve the **Structure A / B** question with the tax adviser — everything else depends on it
2. Import customer contacts **with mobile numbers** — unblocks both WhatsApp and the invoice contact row
3. Build the chosen retention structure, account and register
4. Validate the print format against a realistic multi-line invoice (P1)
5. Sales Order progress billing, once the team accepts the workflow
6. WhatsApp delivery via Route B, after the next app deploy
7. The VAT-financing management report
8. Workspace and interface design execution (6A.7) — design rationale lives in `MASTER-ERP-INTEGRATION.md`; the token pass and native-report inventory have no data dependency and can start immediately, the Workspace records themselves wait on stable post-cutover data per the Phase 4 entry condition in section 6

### 6A.7 Workspace and interface design — execution tracking

The design itself — why these six workspaces, the tokens read from Neosys's own served CSS, the
native-report inventory, what's explicitly out of scope — lives in
[`MASTER-ERP-INTEGRATION.md`](../Automation%20DB/MASTER-ERP-INTEGRATION-LEGACY.md#master-snapshot-20261031-cleanup),
the white paper for cross-domain integration. This section carries only the ERPNext-side execution
items that design implies, tracked the same way every other gate in this plan is tracked: dated,
with evidence, against the named gate.

| Item | Depends on | Gate (in the white paper) | Status |
|---|---|---|---|
| **Fix MR Routing workflow's stuck `doc_status`** | Nothing | MIR-G1 | **Done, 2026-09-06** — `Approved for Transfer` and `Approved for Purchase` now `doc_status=1` (submitted); `Draft`/`Stock Checked` correctly left at `0`. No existing MR was sitting in either changed state, so nothing was orphaned by the change |
| **`SIG Site` doctype + Link fields on MR Item / Stock Entry Detail** | Nothing | MIR-G1 | **Done, 2026-09-06** — `SIG Site` created (`site_id`, `site_name`, `region`, `default_warehouse`), permissioned for System Manager/Warehouse Manager/Operations Manager/Operations User; `custom_site` Link added on both child tables. No records populated yet — that's the RV80 `SitesDB` import, still open |
| **Warehouse tree — three missing stores** | Nothing | MIR-G1 | **Done, 2026-09-06** — created `مستودع تبوك - SIG` (Tabuk), `مستودع جازان - SIG` (Jizan), `مستودع القصيم - SIG` (Al Qasim) as leaf warehouses under `All Warehouses - SIG`, matching the existing three stores' pattern exactly. All six real WH stores now exist on the site (10 warehouses total, up from 7) |
| In-Hand custody warehouse group | Nothing | MIR-G1 | **Explicitly deferred, 2026-09-06** — owner scoped this batch to the three physical stores only; the custody-group design (§ white paper's "ERP document map") is unchanged, just not built yet |
| **Project → Customer mapping** | Owner-confirmed rule: project names starting `1000` are Tawal | — (not previously gated; add to MIR-G1's master list) | **Done, 2026-09-06** — 23 of 27 live Projects set to `Telecommunications Towers Company / Tawal`. Left unset, correctly: 2 cancelled test projects (`PROJ-0001`, `PROJ-0002`) and 2 real projects with no `1000` prefix and no stated rule (`WO-2026-0016` Flooring Collective, `WO-2026-0017` Waterproofing Collective) — owner deferred these, not guessed |
| Opening Stock Reconciliation | Physical count | MIR-G2 | Not started |
| KSA compliance fields on Employee (iqama, GOSI, sponsor) | HR roster migration from hr2 `Basic` | — (HR domain, not yet gated in the white paper) | **CLOSED 2026-09-19.** 11 KSA compliance custom fields (custom_iqama_number, custom_iqama_expiry_date, custom_passport_expiry_date, custom_gosi_number, custom_gosi_registration_date, custom_sponsor_id, custom_border_number, custom_work_permit_expiry, custom_muqeem_report_date, custom_hr_remarks, custom_sadad_pay_iqama_duration) created on Employee via `hr_employee_compliance.py setup_fields --yes`. REST count on Employee = 26 custom_* fields (15 legacy HR-out + 11 new KSA compliance). Muqeem sync writer (sync_muqeem) targets exactly these same fields for per-row updates, with a diffed PUT (only changed keys written) to avoid noisy modified timestamps. |
| **HR WhatsApp attendance → Employee Checkin** (Maytapi → `api` project drain → `register_attendance` Server Script; msg_id dedupe via `custom_source_id`) | Nothing | HR-ATT-G2 | **Done, 2026-09-06 — live.** Real employee punches landing daily; 12+ people punched in the first morning; proving run on the owner's phone (`EMP-CKIN-09-2026-000004`) |
| **SIG HR Ticket + Leave Application from `xhr`** (`register_hr_request` Server Script; `xhr leave`/`xhr vacation` create draft Leave Applications, docstatus 0, never auto-approved) | Nothing | HR module #1/#2 | **Done, 2026-09-06 — live.** `SIG-HRT-2026-00095…` tickets; `HR-LAP-2026-00001/2` drafts |
| **Office-sign-in obligations** (`Employee.custom_office_signin` from Basic col AJ; 17 flagged; SIG Attendance Today report LEFT-JOINs them + covering leave → Not signed in / Pending / On leave / Closed, absentees first) | Nothing | HR-3 | **Done, 2026-09-06.** Absentee list is derived from the obligation flag, never guessed |
| **Office user provisioning** (14 office users + hr: strong random passwords via `sig_reset_user_password`, delivered by Maytapi; `.local` emails renamed to real sigtele.com via `sig_rename_user`) | Nothing | — | **Done with caveat, 2026-09-06.** 6 emails were invented by the automation (Basic had `0`/`S`/`#N/A`) — owner policy: never invent; **pending: real emails for those 6, then rename/reset/send only them** |
| **Leave policy** (leave types, allocations, approver) | Owner/HR decisions | HR module #2 | Pending — Leave Without Pay default until then |
| **Iqama-expiry notifications + HR Workspace compliance dashboard + daily ToDo task sync** (HR-3 tail: 6 native Notifications on Iqama/Passport 90/60/30d before expiry; 6 new expiry-band Number Cards + 3 renewals shortcuts added to SIG HR Workspace; daily Scheduler Event server script creates Open ToDos for ≤30d employees, allocated to `hr@sigtele.com` with role `HR User`) | KSA custom fields deployed (HR-GATE-0 closed); HR user `hr@sigtele.com` active with `HR User` role (verified live) | HR-3 tail (HR-OPS-4/5) | **CLOSED 2026-09-20.** Deployed via `deploy_hr_compliance_alerts.py all --yes`. Notifications: 6x `Days Before` event (Iqama × 90/60/30, Passport × 90/60/30), channel=Email + send_system_notification=1, recipients via Notification Recipient child with `receiver_by_role=HR User`. ToDos: `SIG HR Expiry Daily ToDo Sync` Server Script (Scheduler Event, Daily, disabled=0) — walks active employees with ≤30d expiry left on custom_iqama_expiry_date/custom_passport_expiry_date/custom_work_permit_expiry, upserts 1 Open ToDo per (employee, field type) with `allocated_to=hr@sigtele.com` + `role=HR User` + reference link back to the Employee record; new Muqeem-synced dates auto-update existing ToDos. Workspace: SIG HR workspace content grew from 17→32 blocks; the "Iqama/Passport expiry - not yet built" placeholder header was replaced with a full Compliance Deadlines & Tasks section (header, 3 Iqama band cards, Passport overdue, Open/High-Priority expiry ToDos, and the 3 renewals-queue shortcuts). Live read-back confirmation: all 6 Notifications, Server Script event_frequency=Daily matching the other two Scheduler Event scripts on site, all 6 Number Cards filters_json populated, Workspace child tables = 11 NC rows + 8 shortcut rows, 0 missing. |
| **My Work workspace** (employee-facing; raise request, my attendance, my status) | Stable shadow-week data | — | Not started — after HR-ATT-G3 shadow closes |
| Six Workspace records (Number Cards, Dashboard Charts, shortcuts) | Stable post-cutover data, per Phase 4's entry condition (section 6) | — | **HR slice done, 2026-09-06; Accounting report slice done, 2026-09-27.** `SIG Accounting` now leads with the ten enabled native reports Baligh requested, grouped as bilingual Financial Control (GL, Trial Balance, P&L, Balance Sheet), Sales & Collections (Sales Register, Trends, AR), and Purchasing & Payables (Purchase Register, Trends, AP). The GL shortcut now routes to the General Ledger **report**, not the GL Entry list. Tawal/SNB cards, existing finance actions, roles, and number cards were preserved and read back. Further Warehouse, My Work, Operations, Projects and deeper finance-interface work remain separately staged; see `erp_interface_structure.md`. |
| **Finance Workbench information hierarchy and report visibility** (shared navigation toggle remains deferred separately) | Current finance acceptance work; verify with representative finance roles before release | — | **In progress locally, 2026-09-29; not deployed.** Core statements and AR/AP are promoted, daily document actions remain grouped, and queues/reconciliation plus less-frequent reports/setup are placed in keyboard-accessible expandable groups. Correct report visibility to use Frappe's distinct Report/DocType report grants rather than ordinary DocType read access; add the bank reconciliation tool/report and complete Arabic translations. Verify with finance roles and Arabic/RTL before deployment. |
| **Shared module-menu toggle on Warehouse, Accounting and HR workbenches** (hamburger/sidebar navigation) | Current warehouse/finance acceptance work; resume when operational priorities allow | — | **Deferred by owner, 2026-09-28 (HR workbench added to the same deferral 2026-10-07). No implementation or deployment now.** When resumed, build a useful role-aware sidebar for both pages rather than exposing an empty panel; preserve Frappe's app-owned Page loading, Arabic/RTL, responsive layout, keyboard accessibility, and verify visibility with representative roles. |
| **Sales Invoice Arabic font (Boutros MBC Dinkum)** | Nothing | — | **Done, 2026-09-03** — live on `SIG Tax Invoice` and `SIG Tax Invoice (Arabic Name)`, scoped to `.ar`/`.arh`/`.nm-ar`/`.ka`. `Zatca PDF-A 3B` still on the old stack — it's a Standard format Frappe won't let this plan edit directly; duplicating it into a SIG-owned copy is a separate, not-yet-started item below. **Font licence unconfirmed** — commercial Boutros font, confirm coverage for client-facing distribution before volume increases |
| Duplicate `Zatca PDF-A 3B` into a SIG-owned copy, apply the same font treatment, set as default | The font item above | — | Not started |
| **Warehouse print family — 7 bilingual vouchers** (Material Request, Material Issue, Material Transfer, Custody/IH, Material Receipt, Material Return, Stock Reconciliation) — SIG-branded, header letterhead, receiver-on-top, EN/AR dual labels — infrastructure replacing WH `MIRpdf.bas` dispatch-note output at W-6 cutover. **W-6 switch** (set as `default_print_format`) remains gated on W-5 + Finance sign-off. | Warehouse tree + Site (both above) | **W-6 (late stage, aesthetic — switch gated on W-5)** | **Done — infrastructure built 2026-09-07.** 5 Stock Entry Custom Fields (`ERPNext/scripts/hr/sig_warehouse_print_custom_fields.json`: `custom_requestor_pm`, `custom_initiated_by`, `custom_initiated_on`, `custom_approved_by`, `custom_dispatched_to` — Link Employee + Date) and 7 Jinja templates (`ERPNext/print_formats/sig_*.html`: `SIG Material Request`, `SIG Material Issue`, `SIG Material Transfer`, `SIG Custody`, `SIG Material Receipt`, `SIG Material Return`, `SIG Stock Reconciliation`) created and deployed via `ERPNext/scripts/hr/deploy_warehouse_prints.py --yes`. MR print verified live (`MR-26-1015/1010/1009` render MIR #, dates, warehouse, site, project, items with bilingual headers). SE/SR renders verified via `frappe.db.get_value`/`frappe.get_doc` fallback — new header fields `custom_*` render `—` until W-5 WH sender populates them (by design: no VBA change yet). Receiver lives in top header (`Dispatched/Received to` meta row + `Receiver` legend-box), signatures bottom-only (`Initiated by`/`Approved by`). Not yet set as `default_print_format` — WH keeps printing `MIRpdf.bas` until W-5 cutover. |
| Site Material Ledger, MIR Fulfilment, In-Hand Custody reports | Site, warehouse tree, Stock Entry issue posting (Phase D in the white paper's rollout) | MIR-G5/G6 | Not started |

Do not duplicate the design rationale here when updating this table — link back to the white
paper's section instead, and update dates/status only.

**Interface learnings — access-driven workspace restructure (2026-09-19/20, executed live):**

- **Module Profiles are the sidebar killer and are retired.** A module profile blocks whole
  modules from the sidebar regardless of roles (SIG Purchase hid Stock/Projects/Accounts from
  Hamid; SIG Warehouse hid Projects; SIG Employee blinded gulzaar). Worse, applying a profile
  **stamps the block list onto each user's `block_modules`** — removing the profile later does
  NOT restore visibility until every user's `block_modules` is cleared too (19 users carried
  stale lists). Sidebars are now purely role-driven; do not re-introduce module profiles.
- **Workspace visibility = public + roles whitelist.** A public workspace with a `roles` child
  list is visible only to those roles; empty roles = visible to everyone. Standard generic
  workspaces (Stock, Accounting, HR, Projects, Selling, CRM, Support, Manufacturing, Assets,
  Quality, Insights, Drive, Integrations, Build, Website, Users, ERPNext Settings, Welcome…) are
  whitelisted **System Manager only** (admin & reference); the SIG homes carry their audiences
  (SIG Warehouse: warehouse + coordinators/PMs for dispatch reports; SIG Accounting + finance
  sub-workspaces: finance + SIG Finance Viewer; SIG Projects: PMs; SIG Field Ops: PMs/
  coordinators; SIG HR + sub-workspaces: HR; SIG Petty Cash: finance + PM/coordinators; SIG My
  Work: everyone). REST PUT of `roles` on a Workspace can return a **misleading 404 "DocType URL
  not found" from the post-save redirect while the change applied** — always verify by read-back.
- **Role Profile mechanics, re-confirmed three times:** a role profile strips direct user-level
  roles on every save — grant on the **role profile first** (when it is person-dedicated), then
  the user; for shared profiles use a dedicated profile per person (`SIG Coordinator`, `SIG PM`
  created; `Operations Admin` for Hamid edited in place).
- **Page doctype:** REST edits throw "Only Administrator can edit" even for System Manager when
  the page is flagged `standard` — flip `standard='No'` and set `module` (organizes it in the
  module tree) via a **Server Script save with ignore_permissions + commit**; assign audience by
  writing the Page's `roles` child. Bare `return` values from Server Scripts do not serialize —
  set `frappe.response['message']` explicitly.
- **Sidebar hygiene rule going forward:** one workspace per audience-job, one clear default
  action per shortcut group (the SIG Warehouse dedupe: two stock-value reports and four dispatch
  entry points collapsed to single keepers), and every new SIG interface ships with its shortcut
  in the right workspace on the day it deploys.

### 6A.8 Live-site customization mechanics — reusable tools (learned 2026-09-06, HR workspace build)

These are the proven, repeatable techniques for changing Neosys configuration (dashboards,
doctypes, endpoints) from outside the UI. They were learned by building the HR workspace and the
`register_attendance` / `register_hr_request` endpoints, and every future dashboard or
Server Script task should follow them instead of re-deriving the mechanics.

**Number Cards (via REST, `Number Card` doctype):**

1. Each row of `filters_json` **must carry the doctype as its first element**:
   `[["SIG HR Ticket","status","=","Open",false]]`. Omitting the doctype passes creation but the
   card aggregation fails silently — the card sits at "Loading..." forever on the dashboard. The
   working Accounting cards were the reference for the syntax.
2. Date-scoped cards use a Timespan row: `["Employee Checkin","creation","Timespan","today",false]`
   (lowercase value: `today`, `this year`, …). A "today" count card is the reliable substitute for
   a "today-only" pie chart — Group By charts cannot be filtered to a dynamic single day.
3. Set `is_public: 1` so the card is visible to all users of the workspace.

**Dashboard Charts:**

4. `chart_type: "Group By"` restricts `type` to Line / Bar / Percentage / **Pie** / Donut
   (capitalized — `pie` is rejected), and `timespan` must come from Frappe's fixed vocabulary
   (`Last Month`, `Last Year`, … — not `This Month`/`This Quarter`). `filters_json` is mandatory
   even when empty (`"[]"`).

**Workspace layout (the one that cost the most time):**

5. Adding rows to the Workspace's `number_cards` / `charts` / `shortcuts` / `links` child tables
   is **not enough** — nothing renders unless the block is also present in the Workspace's
   `content` JSON. The content block shapes: `{"id","type":"number_card","data":{"number_card_name","col":3}}`,
   `{"type":"chart","data":{"chart_name","col":12}}`, plus `header`, `shortcut`, `spacer`,
   `onboarding`, `card` blocks. Copy the exact shapes from a working workspace (Accounting) rather
   than guessing.
6. The `links` child table is a flat list: a `{"type":"Card Break","label":"..."}` row followed by
   `{"type":"Link","label","link_to","onboard":0}` rows. A `{"type":"Card","links":[...]}` nested
   structure is rejected.
7. Shortcut rows: `{"type":"DocType","label","link_to","doc_view":"List"}`.
8. `PUT /api/resource/Workspace/<name>` with the full doc; on `TimestampMismatchError`, re-GET the
   fresh document and re-apply the patch idempotently (check-before-append on labels) — the patch
   script should always be written to be safely re-runnable.

**Custom DocTypes via REST:**

9. Create the `Module Def` first (done: `SIG`), then the DocType with `naming_rule:
   "Expression (legacy)"` and `autoname: "format:SIG-HRT-{YYYY}-{#####}"` — no Series property
   setter needed. Permissions are passed in the same payload as a `permissions` array.
10. Unknown fieldnames passed to `frappe.get_doc({...}).insert()` are **silently dropped** — if a
    script writes `custom_source_id` to a doctype, the Custom Field must exist *first*, otherwise
    dedupe silently never matches. (Caught on Leave Application.)

**Server Scripts (API type):**

11. The RestrictedPython sandbox rejects leading-underscore identifiers (`def _handle()` is a
    syntax error; use `def handle_x()`).
12. **API Server Scripts need an explicit `frappe.db.commit()`** — without it, inserts roll back
    when the request ends, and the only symptom is the naming series re-issuing the same document
    name on the next call. The rollback is silent; the series reuse is the tell.
13. Respond with `frappe.response['message'] = {...}`; read input from `frappe.form_dict`.
    Endpoints stay authenticated (`allow_guest: 0`) and are called with the integration token.
14. Reuse the idempotency pattern on every endpoint: dedupe key (`custom_source_id`) → lookup →
    create → commit → structured result `{result: created|duplicate|special|exception, ...}` so
    the Apps Script side can mark Inbox rows DONE/REVIEW mechanically.

**REST transport habits:**

15. URL-encode spaces in resource names (`SIG%20HR%20Ticket`) — raw spaces make curl fail with
    exit 3. Frappe Cloud answers `417 Expectation Failed` to large PUT bodies unless curl sends
    `-H "Expect:"`.

**Query Reports via REST (for "names under the chart" lists):**

16. A `Report` doctype record with `report_type: "Query Report"` + a plain SQL `query` is
    creatable via REST and renders as a normal report — this is the native way to put a live
    *name list* under a dashboard chart (workspaces cannot embed lists directly; a Query Report
    plus a shortcut block directly below the chart is the working pattern). Two gotchas: literal
    `%` in the SQL must be doubled (`%%H:%M` — raw `%` fails with "unsupported format character")
    and filters are passed as `{}` from the workspace shortcut.

17. **Password resets from a Server Script:** neither `frappe.utils.password.update_password`
    nor the User doc's `update_password` is reachable in the sandbox, and `from … import …` is
    blocked entirely. The working pattern is the User form's own field path:
    `doc = frappe.get_doc('User', user); doc.new_password = pw; doc.logout_all_sessions = 1;
    doc.save(ignore_permissions=True)` — the controller hashes on save
    (`sig_reset_user_password`).
18. **`frappe.rename_doc` is not API-whitelisted** — renaming a doctype record (e.g. a User)
    needs a small Server Script that calls `frappe.rename_doc` server-side (`sig_rename_user`).
    Timeouts can leave the target half-created: on a TARGET_EXISTS reply, treat the rename as
    done and reuse the existing target.
19. **Never derive identity data the source lacks.** A source column holding `0`/`S`/`#N/A`
    means "no value", not "invent one" — an invented email polluted Employee `user_id`, the login
    and the WhatsApp credentials for 6 users and had to be walked back. Flag to the owner, ask,
    then act.

20. **Series-named doctypes ignore an explicit `name` on REST create** — the naming series
    assigns its own name (Material Request POST with `name: "MR-26-0977"` came back as
    `MR-2026-0001`). Rename afterwards via the generic `sig_rename_doc` Server Script
    (`frappe.rename_doc` runs server-side; extends the User-rename pattern to any doctype).
21. **Timeline comments can't be added via `add_comment` API** (not permitted for the API user);
    the working pattern is a Server Script calling `doc.add_comment('Comment', text)`
    (`sig_add_comment`).

22. **Server Script sandbox exposes no JSON parsing** (`frappe.parse_json` and `import`
    are both unavailable) — array payloads must come as **numbered params**
    (`code_1..code_n`, `qty_1..`, …) or a delimited string. `register_mir` uses numbered params.
23. **MR naming from the MIR number:** the series overrides any explicit name, so `register_mir`
    renames after insert to `MR-{yy}-{mir:04d}` via `frappe.rename_doc` inside the script
    (works server-side; catch TARGET_EXISTS).

24. **Stock Entry drafts need an explicit `name`** on REST/server-script create (same series
    quirk as the Repack) — pass `MAT-STE-2026-{trans_no}`.
25. **Stock Reconciliation items use a single `qty` field in this version** (not
    qty_current/qty_new — the old names are silently dropped, producing
    EmptyStockReconciliationItemsError); pass `qty` + `allow_zero_valuation_rate`.

27. **`set()` is unavailable in Server Scripts** (RestrictedPython safe-globals omit it) — calling it fails with `TypeError: NoneType object is not callable`; dedupe with a plain list and `in` checks (`register_evidence_event` visit-days).
28. **RestrictedPython traceback line numbers can misattribute** — a failure reported inside the parameter-parsing head was actually a transformed construct elsewhere; probe the suspected line in isolation (minimal probe script, N calls) before rewriting. When a Server Script keeps 500ing inexplicably, rewrite it in maximally plain Python: no closures, no try/except around uncertain utils (guard with `if frappe.utils.x:` instead), no `%` formatting, no conditional-expression statements, bounded `for` loops instead of `while`.
29. **DocType create order matters over REST** — a Link field whose target doctype does not exist yet fails the whole create (`WrongOptionsDoctypeLinkError`); create targets first and make the deploy script idempotent so a re-run fills the gaps.
31. **`.strftime()` is sandbox-blocked** in Server Scripts — `frappe.utils.now_datetime()` works but calling `.strftime(...)` on it raises `KeyError: '__import__'` (datetime's strftime imports `time` internally). Use `frappe.utils.now()` (returns the `YYYY-MM-DD HH:MM:SS` string directly) / `frappe.utils.nowdate()`. This was a latent 500 in `register_evidence_event`'s default-date path — dead code until an event arrived without `occurred_at`.
32. **`json` is only half-available**: `json.loads` executes at script top level but raises the same `KeyError: '__import__'` from inside a function body. Treat JSON payloads as unavailable; numbered params (`p_1..p_n`) remain the transport rule for array-ish API input (Client Scripts can emit numbered args).
33. **Delete order under `LinkExistsError`**: linked children block parent deletes — delete `SIG Evidence Event` rows before their `SIG Site Cycle`, or the REST delete 417s.
30. **`flags` is a restricted fieldname** on custom doctypes (`InvalidFieldNameError`) — use `cycle_flags`/`quality_flags`. Related payload shapes: Report create requires `report_name` (not just `name`); Number Card requires `label` and its `type` is the SOURCE kind (`Document Type`/`Report`/`Custom`), not "Number Card"; Workspace `number_cards` child rows carry `number_card_name`; shortcut `doc_view` for a report is empty/`Report Builder`, not "Report".
26. **WH mirror naming convention (deterministic, documented in the white paper's WH-wing
    section):** dedupe key = `SIG-{trans_type}-{trans_no}` (the doubled type prefix is
    intentional — keys can never collide across transaction types even if WH reuses numbers);
    ERP doc name = **the WH voucher number, verbatim** (`DN26-0400`, `CR26-0300`, …) — no
    MAT-STE/MAT-RECO prefix. Anyone with the WH voucher number opens the ERP draft at the
    identical name.

**Files of record:** every customization built through this route is stored in the repo under
`ERPNext/scripts/hr/` (`sig_hr_ticket_doctype.json`, `register_attendance_server_script.json`,
`register_hr_request_server_script.json`) so any workspace/doctype/endpoint can be rebuilt
without the UI.

**New mechanics (2026-09-15 → 09-19, purchasing / QR / evidence / numbering builds):**

- Server Script doc-event field is **`doctype_event`** — an `event` key is silently ignored on
  REST create/update and the script defaults to **Before Insert**. Always read back after deploy.
- **No backslash escapes inside Server Script strings** (compile fails) — use `Chr(10)` /
  `Chr(34)` or concatenation.
- `frappe.db.sql` is **not** exposed to Server Scripts on this build (403);
  `frappe.db.set_value(..., update_modified=False)` **is** and works on bare tables.
- The `Series` table is bare (no doctype module, no `modified`): REST GET 500s, ORM
  get/set fail on the missing column, and a bare PUT on Document Naming Settings saves fields
  **without syncing** — counter changes need a Server Script `set_value` with
  `update_modified=False`, or the desk's Document Naming Settings Update action.
- `frappe.utils.now_datetime` may be unavailable in the sandbox — guard with try/except and let
  the child row's auto `creation` carry the timestamp.
- **Small Text fields cannot be cleared** via partial REST PUT (both `''` and `null` are
  ignored) — design around it or use a full-doc save from the desk.
- This build has no `frappe.utils.print_format.download`, `frappe.client.get_print` or
  `printview.get_html` API methods — render prints through the `/printview` page route with
  token auth.
- Custom-field **shadowing**: when a doctype has custom DocPerm rows, standard rows are ignored
  for everyone — every custom-role grant must re-append the intended standard roles
  (restore-script precedent), and the grant must go onto the **Role Profile** first, then the
  users (profile re-sync strips direct user-level grants that the profile lacks).

### 6A.9 SIGPC petty-cash clearance — execution tracking

Design rationale — source authority, staging, the implemented hub handler, the accepted cadence
(August close first, then weekly Sunday–Saturday), the correction policy and the report spec —
lives in
[`MASTER-ERP-INTEGRATION.md`](../Automation%20DB/MASTER-ERP-INTEGRATION-LEGACY.md#master-snapshot-20261031-cleanup).
This section carries only the ERPNext-side execution items, tracked the same way as every other
gate in this plan: dated, with evidence, against the named gate.

| Item | Depends on | Gate | Status |
|---|---|---|---|
| Verify `sig_fetch_hub_min_pc.gs` is pasted into the live Am Apps Script project and the web app redeployed (the deployed `sig_fetch_hub_min.gs` dispatches `pc_clearance` but defines none of the PC functions) | Nothing | PC-DEPLOY | **Closed, 2026-09-06** — AM hub project `1m-8hx_YQQ4AZr…` main file updated to the current `sig_fetch_hub_min.gs` (carries both dispatch lines), `sig_fetch_hub_min_pc.gs` added alongside, `setupSheets` run (`pc_clearance` / `pc_receipt_lines` / `pc_employee_accounts` created, 48 custody accounts seeded), web app redeployed (Version 22) on the documented runbook URL. Verified read-only over HTTP: ping `{"ok":true,"hub":"SIG Fetch Hub","version":"1.4.3-min-tawal-controls"}` and `pc_monthly_report` → `{"ok":true,…,"rows":[]}` — empty until the first clearance, which is the correct pre-PC-SEND state |
| Build `PCErpSync.bas` VBA sender — pitch confirmed cycles to the hub, authenticating to ERP with the operator's own per-person API key (G1 1.9a); dumb fire-and-retry is safe because the hub is idempotent | PC-DEPLOY | PC-SEND | **Closed, 2026-09-07** — constants filled in PCConst.bas; `PCErpSync.bas` + `PCClearanceExport.bas` + amended ACN (per-person ERP key) imported; new **`PC_ErpSyncSmoke`** PASS: ACN login (Mohammed Salah Ibrahim Algain) + hub config + personal key mirrored (`59d531ca…`) + hub ping `{"ok":true,"hub":"SIG Fetch Hub"}`. First real close is PC-AUG |
| Close August in full at the source; **bulk-pitch** all confirmed August cycles through a bulk hub handler (reuses the per-cycle pipeline; returns a per-cycle result list), count from that list (every `created` cycle has a verified `erp_doc`; draft totals = `approved_spend`), import as drafts | PC-SEND | PC-AUG | Not started |
| Weekly Sun–Sat cadence from September via the live per-cycle POST path (each week's cycles reach ERP as drafts as they close) | PC-AUG | PC-WEEK | Not started |
| Custom report — per-person pitched draft JEs, month + Sun–Sat week views (Query Report mechanics, 6A.8 #16) | Draft JEs in ERP (PC-AUG) | PC-REPORT | Not started |
| Employee phone onboarding and ignored-sender closure: keep `966564480025` unmatched/ignored until the employee's verified phone is entered on ERP Employee `cell_number` or an Employee-linked Contact; reload the review page, confirm the resolver returns exactly one Employee, and review all previously unmatched receipts before closing this item or sending onboarding messages | Employee onboarding / verified ERP phone | PC-PHONE-CLOSE | **Open — owner disposition 2026-10-15.** No name match is authorized yet. Historical receipts remain pending/unmatched and should resolve from the ERP Employee source after the phone is added; close only after unique resolution and review. |

### 6A.10 Material master and purchasing convenience — execution tracking

Design rationale — the **WH-code-prevails** material identity decision, the **provider-assisted
new-item intake** flow (unmapped code at PO logic or a direct receipt → provider API suggests code
+ description → human confirms → Item created), and the **VBA Purchase Order creation** path
(draft PO from Excel direct to ERP, MIR-V2 transport, per-person API key) — lives in
[`MASTER-ERP-INTEGRATION.md`](../Automation%20DB/MASTER-ERP-INTEGRATION-LEGACY.md#master-snapshot-20261031-cleanup).
This section carries only the ERPNext-side execution items, tracked like every other gate: dated,
with evidence, against the named gate.

| Item | Depends on | Gate | Status |
|---|---|---|---|
| WH-code-prevails crosswalk: reconcile the ERP Item master so WH codes are canonical (`item_code` or recorded `custom_wh_code` mapping); unify UOM variants | Nothing | MIR-G1 | Not started |
| Provider-assisted item intake: confirm the provider endpoint/contract (open item in the white paper); hook into PO logic and direct receipts; prove one create with the human-confirm step | WH crosswalk | ITEM-0 | Not started |
| Intake live on both triggers (PO logic + WH direct receipts) with the confirm step exercised | ITEM-0 | ITEM-1 | Not started |
| VBA PO creation: draft Purchase Order from Excel/VBA to ERP (MIR-V2 transport pattern, operator's per-person API key per G1 1.9a); prove one supplier/line | Item master + per-person keys | PO-0 | Not started |
| **PO value-cap submission** (later stage, owner): Server Script on Purchase Order `before_submit` — `grand_total <= 50,000` submittable by finance creators (Purchase User); above the cap requires an approver (dedicated role and/or workflow). Implement after PO flow proves out (PO-0); threshold in `SIG Field Ops Settings`-style singleton, not hardcoded | PO-0 proven | PO-1 (new) | Logged — not started |
| VBA PO in live use with the accountant review loop | PO-0 | PO-1 | Not started |
| **Pending material POs → WH In staging** (`sig_list_pending_pos` read endpoint + `sig_mark_po_lines_staged` ack + `PendingPO` sheet; live probe: 333 material lines / 118 POs; cutoff 2026-09-01) | Cutoff accepted | PO-STAGE-0 / PO-STAGE-1 | **PO-STAGE-0 done 2026-09-15 (parity PASS); PO-STAGE-1 ERP side done (sham e2e PASS); VBA `WhErpImportPendingPOs.bas` staged — owner import pending** |
| **Standing receive-first entry point** (explicit routes PO/NOPO/HOLD, SAR 10k threshold validator live on PR, provisional-supplier guards live on PI/PE, anti-split guard live, `SIG Receipt Operation` idempotency) | Valuation rule + owner review | PO-ENTRY-0 | **Done 2026-09-15 — full test matrix PASS** |
| **WH receive form** (`WhErpReceiveMaterial.bas`: route selector, pending-line picker, retry-safe op key) + **Buying Settings** (`bill_for_rejected_quantity_in_purchase_invoice` 1→0 applied live) | Owner import pass | PO-ENTRY-1 / BUYSET-0 | VBA staged; settings correction applied live 2026-09-15 |
| **2026 material-additions retrospective** (Stage-3 linking pass + disposition sheet + keyed RETRO-PO/NO-PO batches) | WH Purchase sheet export **with supplier and rate columns** | RETRO-0 / RETRO-1 | Blocked on the owner's export; ladder + posting mechanics registered (master doc) |

### 6A.11 Tawal cleared-parent multi-invoice allocation — execution tracking

Design rationale and the portal evidence live in
[`MASTER-ERP-INTEGRATION.md`](../Automation%20DB/MASTER-ERP-INTEGRATION-LEGACY.md#master-snapshot-20261031-cleanup).
The source contract is deliberately parent-led: payment-list `Invoice Number=Multiple` is
normal; invoice-side `Payment Number=Multiple` starts allocation discovery. The Oracle
Payment Details **Paid Invoices** table, reached by opening the parent Payment Number, is the
only authority that may assign a child invoice to that parent.

| Item | Depends on | Gate | Status |
|---|---|---|---|
| Persist parent verdict and child allocation evidence (local `reconcile-cache.json`; `RECONCILED` is durable, non-final states retry). Evidence carries parent, child/type, signed amount and timestamp. | Existing Tawal hub contract | TAWAL-ALLOC-0 | **Done, 2026-09-08.** Hub child-table promotion is optional hardening; the local scheduled flow is complete without it and ERP duplicate protection survives cache loss. |
| Read-only Oracle capture: parent Paid Invoices detail is preferred; when exact parent search is unavailable, concrete invoice links are used; invoice-side `Payment Number=Multiple` is discovered by scanning paid invoice Payments tabs for the candidate parent. | TAWAL-ALLOC-0 | TAWAL-ALLOC-1 | **Done, 2026-09-08.** Saved live parent detail `202602717537` parses 6 signed rows to SAR 122,144.44; live fallback `202611000040` reconciles 2 rows to SAR 82,242.75. |
| Allocation validator: parent `Cleared`, every standard child row `Cleared/Reconciled=Yes`, per-child amount check when parent detail exists, signed total equals parent, unique SNB credit, ERP invoice/outstanding checks. Failed cases retain named retry/review states. | TAWAL-ALLOC-1; invoice backward match; SNB match | TAWAL-ALLOC-2 | **Done, 2026-09-10; 26 tests pass.** Partial cleared payments remain valid; remaining outstanding stays on the ERP invoice. |
| Apply the legacy cutoff to the **parent payment date**, not the Sales Invoice year. A current cleared/reconciled payment of retained 10% on a submitted 2023/2024 invoice is eligible when the invoice has sufficient outstanding; only a pre-2026 parent payment is `LEGACY_EXCLUDED`. | TAWAL-ALLOC-2 | TAWAL-ALLOC-DATE | **Policy confirmed 2026-09-08; existing event-date gate already follows it.** Add an old-invoice/current-payment regression fixture with the retention build. |
| Classify a negative child as a retention offset only when it is explicitly `/ Retention` (or carries an equally reliable Retention type) and maps uniquely by canonical invoice number to a positive child. Net it into that one ERP Sales Invoice allocation; require net > 0 and preserve gross, offset and net in evidence/remarks. A later PAC/FAC parent payment may allocate only the remaining outstanding. | TAWAL-ALLOC-2; TAWAL-ALLOC-DATE | TAWAL-ALLOC-RET | **Done, 2026-09-10.** The regression fixture proves SAR 9,297.75 less SAR 929.78 creates one SAR 8,367.97 allocation; no retention GL is needed. |
| Classify every other negative/credit-note child, including an ambiguous association, as `PENALTY_CREDIT_NOTE_REVIEW`; never infer retention from amount or age. Finance must decide the penalty/credit accounting before automation. | TAWAL-ALLOC-2 | TAWAL-ALLOC-PEN | **Implemented, 2026-09-10.** Penalty/ambiguous credit notes remain held; Finance treatment remains open. |
| Group verified children by parent and create **one** draft Receive Payment Entry with one positive reference per canonical invoice after retention netting, collective amount, parent `reference_no`, SNB key, and explicit bank-mapping remarks. | TAWAL-ALLOC-2; TAWAL-ALLOC-RET when an explicit retention is present; TAWAL-ALLOC-PEN must not be present | TAWAL-ALLOC-3 | **Done, 2026-09-10.** Invoice-side Multiple and retention-netting regressions are included. |
| Validate every ERP reference and collective total; enforce one active PE per parent; read back draft status, parent number, amount and reference count. | TAWAL-ALLOC-3 | TAWAL-ALLOC-4 | **Done, 2026-09-08.** Three independent idempotency locks remain. |
| Proving run and negative suite. No submission. | TAWAL-ALLOC-4 | TAWAL-ALLOC-5 | **Portal proof and 26-test suite passed 2026-09-10.** Parent `202611000041` was read live: its three invoices were all Cleared/Reconciled=Yes and their allocations totalled SAR 1,138,602.91 exactly. The next eligible parent is the controlled ERP-draft proof. |
| Weekday 07:30 local task executes capture → backward invoice link → portal reconcile → ERP forward. Remit `81300000023605` uses owner fallback SNB account `23659568000109` and bank 109/GL 13121 with `OWNER_FALLBACK_BANK` in remarks. | TAWAL-ALLOC-5 | TAWAL-ALLOC-LIVE | **Deployed locally 2026-09-10; draft reset completed.** Retention netting is live; penalties remain held for Finance. |

**Deployment evidence, 2026-09-08 01:18 Riyadh:** Windows task `Tawal Local Morning` is
enabled/Ready, `StartWhenAvailable=True`, last result `0`, and points to the repository
`ERPNext/scripts/tawal/run_morning_local.ps1`; next run is 2026-09-08 07:30. Controlled
portal/Sheet proof `202602700090` exited `0`, reconciled SAR 32,320.98 exactly, and read
back from Sheet Am as `PORTAL_RECONCILED`; the forward planner then placed it in
`SNB_CREDIT_NOT_FOUND`, proving the next missing evidence remains visible instead of
creating a guessed draft. Final read-only population: 166 `LEGACY_EXCLUDED`, 16
`WAITING_PORTAL_RECONCILE`, 1 `SNB_CREDIT_NOT_FOUND`, and 17 `ERP_DOC_EXISTS`; zero
`BANK_GL_UNMAPPED`. No Payment Entry was created or submitted during this deployment.

### 6A.12a WH↔ERP stock bridge — proving and one-day draft trial

**Closed for the current proving scope on 2026-09-15/16.** The full WH ERP sender set was imported into the test workbook and exercised against the live Neosys endpoint. DN, TN, PR, and RN have successful live evidence; CR and BI are intentionally deferred. The proving drafts were deleted after verification, and no submitted ERP documents were removed.

Verified outcomes:

- DN `DN26-1030` → `STE-2026-0832`, HTTP 200, `created`, 13 lines, `readback_ok=true`.
- TN `TN26-0072` → `STE-2026-0833`, HTTP 200, `created`, 1 line, `readback_ok=true`.
- PR `PR26-0081` → `STE-2026-0834`, HTTP 200, `created`, 1 line, `readback_ok=true`.
- RN route is live and has existing ERP evidence; current CR/BI proving remains deferred.
- The invalid-project failure on DN1036 (`HTTP 417`, WH project `5G7`) is retained as historical evidence; it was not replayed after the fix and created no ERP document.

Controls now live:

- ERP accepts a WH mirror only when HTTP 200 contains `created` or `duplicate` plus a non-empty document name; the response and status are appended to `debug.txt`.
- WH project text is linked only when it resolves to an ERP Project; otherwise it is preserved in remarks and never sent as an invalid Link.
- A successful DN resolves the ERP MR from the MIR number and updates `custom_sync_status` to `PARTIALLY_DISPATCHED` or `DISPATCHED` from cumulative linked DN quantities; the standard ERPNext status remains untouched.
- `debug.txt` is append-only in the deployed profile; buffer flushes persist entries and do not truncate the file.

**Current operating gate:** run the WH workbook for one day with ERP documents remaining drafts (`docstatus=0`), monitor the append-only debug log and ERP read-backs, then review before changing the endpoint to submit Stock Entries directly. Do not enable direct posting until the draft trial is accepted and a rollback/cleanup plan is recorded.

**Reasonable target architecture (approved as the next design target, not yet live):** replace the
draft-mirror loop with a server-authoritative approval/commit endpoint. WH sends one immutable
source key, the complete line set and the expected count; ERP validates approval, MR remainder,
item/UOM/warehouse/Project links and counts. A rejected request creates no ERP stock document.
An approved request is committed and submitted server-side in the same controlled operation and
returns `POSTED`, the ERP name and read-back quantities. A retry with the same key returns
`DUPLICATE` and the original result; a changed payload with the same key returns `CONFLICT`.
The server stores only a small non-stock authorization/audit record, not a staging Stock Entry
draft. This removes client-side submission and draft cleanup while preserving per-person keys,
least-privilege server checks and an append-only audit trail. Batch one voucher/MIR per request to
remove the current many-request staging overhead; local dashboard refresh is not an ERP approval
step and must not gate the server commit.

### 6A.12 FieldOps capture/state split (phase 2) — execution tracking (deferred, post-WH)

Design rationale — the capture-vs-state split (Apps Script capture only; ERP owns the
Start/End/grace/cap session state machine on the native scheduler; Excel reduced to document
generators + a Windows-bound photo/PPT worker), the facts-replay-vs-decisions-migrate rule, and
the two conformance gates — lives in
[`MASTER-ERP-INTEGRATION.md`](../Automation%20DB/MASTER-ERP-INTEGRATION-LEGACY.md#master-snapshot-20261031-cleanup).
**Owner-sequenced after the WH stock cutover** — not on the WH critical path, may start early as
design/exploration only; no RV80 write path changes and no parser is retired until its gate passes.

| Item | Depends on | Gate | Status |
|---|---|---|---|
| Phase 1 evidence-prompt integration (`SIG Evidence Event` / `SIG Site Cycle` / `SIG Field Visit` + `register_evidence_event`) | Domain registry route row | FO2-G0 | **Built and proven live, 2026-09-12/13** — three doctypes + endpoint deployed via `deploy_field_ops_infra.py`; 13-check synthetic EV1 pack passed (full lifecycle, gross-value ladder, terminal guard, duplicate rejection); SIG Field Ops workspace + Cycle Board Kanban + 2 charts live. Endpoint uses an incremental `set_value` merge per event, not a recompute — see the corrected note in the design register. RV80-side POST into `_FO_EvidenceQ` remains not built (deliberately, pending owner go) |
| Export the non-replayable Excel decision state (`_FO_PhotoQ`, `_FO_FolderMarkers`, PhotoReview keep/route outcomes, applied delayed-end repairs, per-session ignore flags) to a durable file before any cutover step | Nothing (can run anytime) | FO2-EXPORT | Not started |
| Apps Script gains the per-message POST to ERP alongside its existing capture/route (`code.gs` `drainInboxPass_`/`routeMessage_`); sheet stays buffer + replay log | FO2-G0 | FO2-CAPTURE | Not started |
| Build the ERP-side session/tag state machine (message→session pairing, 24h hard cap, 6h grace, delayed-end repair, tag-manifest parsing) as scheduled server-side jobs | FO2-CAPTURE | FO2-STATE | Not started |
| **Session gate:** replay the captured message log through the new state machine; field-diff resulting sessions against live `_FO_Sessions` (113 rows) | FO2-STATE | FO2-GATE-SESSION | Not started |
| **Cycle gate:** replay all EV1 events through the Phase 3 sessionization view (see below); field-diff its cycles against `_Ops_CycleFacts` (476 cycles) | FO2-G0 | FO2-GATE-CYCLE | Not started — retargeted from "the ERP recompute function" to the Phase 3 SQL view; same gate, same fixture, no new work implied |
| Build the local PowerShell/Node photo worker (pull assigned queue from ERP → download → write to Sync path → report back), replacing `FieldOps_DownloadPhotosByDateRange`'s Excel-bound role | FO2-STATE | FO2-WORKER | Not started |
| Retire `FieldOpsCore.bas` parsing/session-state code in RV80 (generators + emit hooks + PhotoReview/RFI deck builder remain) | FO2-GATE-SESSION and FO2-GATE-CYCLE both pass | FO2-CUTOVER | Not started — blocked on both gates, never on a schedule alone |

### 6A.13 Analysis re-platform (phase 3) — fact/dimension model + Insights, not a VBA port — execution tracking

Design rationale — the do-not-port list of VBA-shaped artifacts, the fact/dimension/derived-view
blueprint, the `Event Code`/`Flag` reference tables that collapse OpsKPI's five scattered
`Select Case` blocks, the sessionization-as-SQL-window-function approach, the act-on-it (ERP
doctype) vs. read-it (Insights) split, the bitemporal and single-metric-definition payoffs, and the
acceptance test ("a new KPI should be a measure definition, not a code release") — lives in
[`MASTER-ERP-INTEGRATION.md`](../Automation%20DB/MASTER-ERP-INTEGRATION-LEGACY.md#master-snapshot-20261031-cleanup).
**Owner direction:** this is new infrastructure, not a refactor of OpsKPI/EvidenceDashboard into
ERP form. It does not touch the live Phase 1 ledger or endpoint, is independent of Phase 2's timing
(can run parallel to or after it), and — like Phase 2 — is late-stage work, not on the WH critical
path.

| Item | Depends on | Gate | Status |
|---|---|---|---|
| Build conformed dimensions: `Event Code` reference (slot_name, stage_rank, gross_value_authority_rank, is_terminal, is_field_delivery, ho_doc_type), `Flag` (deduction_points), `Project` gains a stored `family` attribute, `SIG Site` gains lat/lon | Nothing (reads existing `SIG Evidence Event`/`Project`/`SIG Site`) | FO3-DIM | Not started |
| Build the sessionization view: gaps-and-islands SQL over `SIG Evidence Event` (partition by site_key+identity, order by occurred_at, cycle boundary on terminal/post-terminal field-delivery) — MariaDB 10.6 window functions | FO3-DIM | FO3-VIEW | Not started |
| **Cycle conformance gate** (same fixture as FO2-GATE-CYCLE above): field-diff the view's output against `_Ops_CycleFacts` (476 cycles) | FO3-VIEW | FO3-GATE | Not started |
| Demote `SIG Site Cycle` from per-event `set_value` merge to a lean, scheduled-rebuild cache fed by the view (kanban/board fields only, not the 42-fact grain) | FO3-GATE | FO3-CACHE | Not started — the live v1 endpoint's merge logic is left running unchanged until this is proven |
| Insights measures: transition medians/p75/p90 with query-time N≥8 suppression, completion-curve cohorts, team/family slicing — replaces `Ops Run Log`'s per-refresh trend with live, re-sliceable queries | FO3-DIM | FO3-INSIGHTS | Not started |
| Acceptance check: pick one net-new KPI request and answer it as a pure Insights measure definition, no Server Script or VBA change | FO3-INSIGHTS | FO3-ACCEPT | Not started — this is the re-platform's own definition of done |

### 6A.14 EvidenceCore live link to ERP — per-person evidence posting, deploy-before-backfill (owner direction, 2026-09-17)

**Owner direction:** the ERP field-ops dashboard is live and populated; the legacy Excel-dashboard
method is **retired from concern** — no effort on keeping a cross-system board. What remains is
linking the live evidence generation to ERP. Three gradual steps, ordered (owner renumbered) so
the live posting deploys **before** the catch-up — no gap by construction. Verified against the
deployed sources: `rv80/deployed/EvidenceCore.bas` and `sigpc/deployed/EvidenceCore.bas` expose an
identical API (`Evidence_BeginBatch / AddSiteEvent / RecordSingle / CommitBatch / FlushPending`),
so **one posting module serves both workbooks**; sigpc does carry its own evidence core.

**Step 1 — build the BAS posting module (`EvErpSend.bas`, RV80 + sigpc) — BUILT 2026-09-17.**
`EvErpSend.bas` (V-erev.260917001) is staged in `rv80/deployed/` and `sigpc/deployed/`
(identical, self-contained). The two EvidenceCore getters proved unnecessary: the hook receives
the pending file path directly, so the core takes exactly **two one-line edits** (the replace
lines are documented in the module header — no getters, nothing else touched; PDF generation and
the local EV1 archive untouched; `Evidence_PublishPendingFile` stays in place but becomes
unreferenced = the legacy Sync.com publication is deactivated).
- Hook: the success tail of `Evidence_CommitBatch` in both cores (after the pending EV1 file is
  written) + two one-line Public getters added to EvidenceCore
  (`Evidence_GetLastBatchFile`, `Evidence_GetLastBatchCount`) so the posting logic stays fully
  inside `EvErpSend.bas` — the core module takes one call, nothing else.
- Mechanics: parse the just-committed pending EV1 file (header + 17-column rows — the same parse
  `replay_ev1_batches.py` used for the 3,475-event import) and fire **one small POST per event**
  to the live `register_evidence_event` endpoint (numbered params, unchanged — the same endpoint
  the replay proved). FIELD_VISIT_COMPLETED rows carry their extra visit params.
- **Attribution (owner requirement): every POST authenticates with the ACN per-person key**
  (`ACN.AC_GetErpApiKey()` from the UserPasswords col-V mirror), so each evidence event lands
  under the draining operator's name; the field worker stays attributed inside the payload (the
  EV1 operator column). Personal-key-first with the protected shared-config fallback
  (MirErpSend pattern) so posting never blocks on a missing key.
- Failure policy: additive fire-and-retry — a POST failure never blocks or rolls back the
  evidence commit; the pending file stays marked unposted and retries on the next commit; ERP
  EventId dedupe makes overlaps harmless. Close Sites rides the same tail (its batch commits
  like any other — the SITE_CLOSED ride-along the master register reserved).
- sigpc: identical module + hook; its evidence queues flow through the same endpoint.

**Step 2 (owner-renumbered; was 3) — deploy RV80 + sigpc so posting is LIVE — CLOSED 2026-09-19 (owner imported the same RV80 modules into sigpc; section complete).**
**RV80: DONE and proven live 2026-09-19** — owner imported both modules; the proving event
(`ZT-TEST01` / MAPPING_GENERATED) arrived in ERP **attributed to the owner's ERP user via his
ACN per-person key**, assembled its cycle on the dashboard, the duplicate probe returned
`duplicate`, and the test artifacts were deleted. Every real event RV80 generates now posts at
generation — no gap.
- The EvidenceCore edits are **already applied in the staged sources**
  (`rv80/deployed/EvidenceCore.bas` + `sigpc/deployed/EvidenceCore.bas`: both call sites now
  route to `EvErpSend_PublishToErp`; the legacy Sync publication is unreferenced). Owner
  imports into the live workbooks: **`EvErpSend.bas` first, then the edited
  `EvidenceCore.bas`** (both must be in before anything runs — the core references the poster).
- Key sweep in the same pass: issue per-person keys to any RV80/sigpc operator who drains
  evidence and lacks one (admin → UserPasswords col V → ACN mirror). sigpc's ACN already
  carries `AC_GetErpApiKey` (verified) — no ACN amendment needed, only key issuance.
- Proving: one synthetic event → visible on the field-ops dashboard, attributed to the operator;
  duplicate re-post → dedupe; then live. **From this moment there is no gap** — every new event
  reaches ERP at generation.

**Step 3 (was 2) — catch-up: DONE 2026-09-19.**
- ERP already holds 2026-07-24 → 09-12 (3,475 events via legacy replay v0). The gap is
  09-12 → the Step-2 deploy moment. **Executed:** 283 events posted (0 errors), overlapping
  19 skipped as duplicates, checkpoint advanced — ERP now holds 3,739 created events total,
  dashboard continuous.

**Agent recommendation:** the owner's renumbered order is correct and adopted — deploy before
backfill bounds the catch-up window and the EventId dedupe makes the overlap a non-event.
Three additions: (a) the personal-key sweep belongs in Step 2, not later — field operators
drain evidence, and without their own keys their posts fall to the shared fallback key and lose
attribution; (b) mark posted pending files at commit-return so retry volume stays bounded;
(c) **zero ERP-side changes** — the endpoint, cycle assembly, dedupe and dashboard already serve
the live flow; this step is RV80/sigpc-side only.

| Gate | Evidence |
|---|---|
| EV-LIVE-1 | **DONE 2026-09-19** — proving event `ZT-TEST01` arrived attributed to mohammed.gain@sigtele.com via his ACN key; cycle assembled on dashboard; duplicate probe returned `duplicate`; artifacts cleaned |
| EV-LIVE-2 | **DONE 2026-09-19** — owner pasted the same RV80 module versions into sigpc; identical code path, same endpoint and dedupe. First real sigpc event confirms naturally; any post failure retries from the sigpc outbox (nothing lost either way) |
| EV-BACKFILL | **DONE 2026-09-19** — 283 events posted since the 09-12 checkpoint, 19 overlaps skipped as duplicates, 0 errors; dashboard continuous through the deploy moment |

### 6A.14a Evidence identity — temporary work scope (TWO) + agreement Project link: executed 2026-09-20, and the exact work order for the next agent

**Owner direction (final semantics).** The client's per-site work order (e.g. `WO-SIG-DC-ZTF522-12740-Capex#9-15180`) is the **final WO naming**. Evidence generation and follow-up cannot wait for it, so every activity is recorded immediately under an **internal temporary work scope** `TWO-<SITEKEY>-<n>`. The first evidence event that carries the client WO **converts** that scope: the cycle keeps its history, its identity (`scope_id`) becomes the client WO, and the temporary id is kept as an alias (`temp_id`). Two identities exist and must not be confused:

| Concept | Example | Where it lives |
|---|---|---|
| Agreement / PO (Tawal) | `10001274` | ERP `Project` (named `<agreement> <description>`; ERP Project ids look like `WO-2026-0037`); event field `po`; cycle field `erp_project` |
| Client site work order | `WO-SIG-IMP-ZHA899-11340-Incident-23578` | event field `wo`; cycle fields `wo`, `scope_id`; contains the site id |
| Temporary scope | `TWO-ZTF599-1` | cycle `scope_id` until adopted; alias in `temp_id` afterwards |

**Executed and verified (live, `neosys.frappe.cloud`).**
- `SIG Site Cycle` fields: `scope_id`, `is_temporary`, `temp_id`, `resolution_state` (`REAL`/`OPEN_TEMP`/`ADOPTED`/`AMBIGUOUS`), `resolved_at`, `resolved_by`, `erp_project` (Link → Project). `Project` fields: `custom_agreement_no`, `custom_is_canonical_agreement`.
- `register_evidence_event` (source: `ERPNext/scripts/hr/register_evidence_event_script.py`) rules: blank / `1` (Mapping batch selector) / `0` / `NA` / very short values are not work orders; at most one open temporary scope per site; an event with a real WO uses that WO's cycle, else adopts the site's single non-ambiguous WO-less cycle (preferring the same PO), else opens a new cycle — a second real WO is never pooled into another WO's cycle; a WO-less event with only real WOs open opens an `AMBIGUOUS` temporary scope (never auto-adopted, flag `WO_AMBIGUOUS`); field events after a terminal cycle open a new cycle; PO → `erp_project` (canonical Project wins where an agreement has several, else the single Open one; `PROJECT_CLOSED` / `PROJECT_UNKNOWN` / `PROJECT_AMBIGUOUS` / `PROJECT_INFERRED` flags; inference only from the site's Material Request POs and only when exactly one PO exists); a WO naming another site raises `WO_SITE_MISMATCH`.
- Backfill: 132 cycles (2 REAL, 130 OPEN_TEMP); 35 linked to their Project, 26 `PROJECT_INFERRED`, 2 `PROJECT_CLOSED` (agreement 1000157, canonical Project is Completed), 1 `PROJECT_UNKNOWN` (test PO). 49 of 53 Projects carry an agreement number (the 4 without: two test Projects, `Flooring Collective`, `Waterproofing Collective`; plus `Shabakat` is not a Tawal agreement); 34 marked canonical = the Project each Tawal agreement's hub `erp_doc` points at.
- Conformance: `ERPNext/scripts/hr/test_scope_two.py` — **20/20** (T1–T13 scope rules, T14–T18 Project link and WO/site checks); it creates throwaway `ZTWO*` sites and deletes everything it made. Deploy scripts (dry-run by default, `--yes` to apply, each backs up the live Server Script to `ERPNext/backups/`): `deploy_scope_two.py`, `deploy_project_link.py`. Latest backup before the Project-link deploy: `ERPNext/backups/register_evidence_event_live_20260920_003721.py`.
- **Duplicates — marked, not merged.** 12 agreement numbers have more than one Project: legacy Flexsoft names (created 2026-08-29, mostly Open, several carrying Stock Entries — `WO-2026-0014` 22, `0005` 19, `0004` 11, `0003` 6, `0018` 4, `0015` 3) plus the Tawal-synced one (2026-09-08, mirrors the portal status). Nothing was merged, renamed or cancelled.

**Known data discrepancy to resolve first.** Plan §6A.14 recorded ERP at 3,739 evidence events (3,475 legacy replay + 283 catch-up). A read on 2026-09-19 found **293 events / 132 cycles, all created that day** (occurred 2026-09-09 → 09-19). Earlier history appears to be absent from `SIG Evidence Event`. Do not assume either number; verify, then decide on replay.

**E0 execution record — 2026-09-20.** The historical ledger was confirmed absent and restored from the first valid EV1 event (2026-07-24) through the 2026-09-12 hand-off boundary: 645 files / 3,475 source rows selected; 3,456 created; 19 duplicate EventIds skipped; 0 errors. ERP now holds **3,768 `SIG Evidence Event`**, **603 `SIG Site Cycle`**, and **220 `SIG Field Visit`** records. `test_scope_two.py` passed **20/20** after the restore, and the invariant query for more than one open temporary scope per site returned **0 rows**. Owner confirmed that evidence begins at the first valid event, not an arbitrary August cutoff. Historic evidence remains immutable; its presence alone must not be treated as proof that a site is currently active.

**E2 preflight — 2026-09-20.** The restored population makes the gap precise: `TCN_GENERATED` is 1,620 / 3,768 events (43.0%) and carries **0 PO / 0 WO**; 1,789 events overall carry a PO and 135 a WO. The open RV80 workbook has the needed facts but not a safe site-only lookup: hidden `WO` maps Site ID / PO / WO, while `TCN-MDT` has Site, planned start, duration and activity; a site-only join covers 923 / 5,505 populated TCN rows and 222 of those return more than one PO/WO candidate. The emitter must therefore use the Mapping row that generated the TCN (with site + agreement/PO context), and return blank with an exception/audit when that row is absent or ambiguous. Do not fall back to `WO` by site alone. Baseline has six historical `WO_SITE_MISMATCH` cycles (all retained as exceptions); the rollout must introduce **zero new** mismatches and must never overwrite or silently repair these historical rows.

**E1 owner waiver / E2 source trace — 2026-09-20.** Owner confirmed that the operators use the same already-tested unified workbook structure, so the per-machine E1 outbox re-check is waived; the common workbook release remains the deployment vehicle. Source review found that `EvErpSend` already posts EV1 columns 8/9 as `po`/`wo`, and `EvidenceCore` already preserves both fields. The live `sigpc/deployed/MappingPipeline.bas` also passes its canonical PO and captured real client WO. The remaining defect is isolated to `rv80/deployed/tcnword.bas`: `TCN_RecordEvidenceFromBatch` sends only Site + Project. The active `TCN-MDT` and `Plans` sheets contain neither PO/WO nor a Mapping-row/artifact key; `WO` is the only candidate source but is not safe for a site-only join. Therefore **do not implement a lookup yet**: first materialize a Mapping-context record keyed at least by TCN batch + site + agreement/PO (and the exact WO when present). TCN can then send only that record's values; missing or duplicate context must yield blank PO/WO plus an audit exception. This preserves the no-guessed-WO rule and is the E2 gate before rollout.

**E2 identity rule clarified by owner — 2026-09-20.** PO and WO are optional evidence facts. Basic/generic-project TCN, BOQ and Mapping evidence may legitimately arrive without either and must remain immutable. It belongs to a temporary scope until later evidence for that site supplies a real agreement/PO (the `1000...`-named Project) and, when issued, the client WO. The resolver then links the existing scope to the Project and adopts it to the WO while retaining its `temp_id`; it does not edit the earlier events. This is already covered by `test_scope_two.py` T1–T4 and T13–T17. A TCN emitter should pass PO/WO only when the source sheet explicitly holds the exact values; blank is the correct value otherwise. The earlier ≥90% PO target is not applicable to generic/basic work and is replaced below with provenance correctness.

**E3 ToDo ownership clarified by owner — 2026-09-20.** Ambiguity follow-up is a generic ERP ToDo linked to the `SIG Site Cycle`, initially unassigned. It is maintained and assigned later through ERP's normal ToDo flow; no Project-PM field or automatic recipient is required.

**E3a deployed — 2026-09-20.** `register_evidence_event` now creates at most one open, high-priority generic ToDo per cycle when `WO_AMBIGUOUS` or `PROJECT_AMBIGUOUS` is raised. The ToDo is linked to `SIG Site Cycle`, deliberately has no guessed recipient, and does not alter the event or cycle identity. Deployment found all six scope fields already present, required no backfill across 603 cycles, and saved the prior endpoint as `ERPNext/backups/register_evidence_event_live_20260920_013029.py`. The post-deploy scope regression passed **20/20** (test artifacts cleaned up).

**E4 first slice deployed — 2026-09-20.** `SIG Site Cycle` now has `delay_reason`, `delay_note`, and `delay_logged_at`; `SIG Field Ops Settings` has `temp_scope_max_days` (default 14) plus stage-specific SLA slots (`sla_plan_days`, `sla_handover_days`, `sla_asbuilt_days`). The live `sig_log_cycle_delay` API and `SIG Site Cycle Delay` form action write the fields and a native ERP Comment, refusing closed cycles. The daily scheduler now refreshes delayed/aged flags and creates one generic escalation ToDo for a temporary scope older than the setting. `SIG Delayed No Reason` is live. `SIG Cycle Grid` was updated and verified with 603 rows; it now exposes Closure (`SITE_CLOSED` versus `As-Built only`), Delay Reason and the latest native Comment alongside the existing stage/aging/ref columns. The live grid returns 1 explicit `SITE_CLOSED`, 21 `As-Built only`, and 580 with neither label. The existing public `SIG FO Delayed` card is the delayed-work count entry point for the Field Ops/My Work flow. The endpoint reads stage-specific SLA values with the existing 30/14-day fallback. The authoritative setup/config table is now recorded in `MASTER-ERP-INTEGRATION.md` §0.2. No completed-cycle timing sample met n ≥ 8 for p75 seeding yet, so the stage slots remain fallback values until enough real transitions exist; no timing was invented.

**E4 escalation-ToDo status correction — 2026-10-13 (read-only).** The live `sig_field_ops_daily` Server Script is enabled, but its code only recomputes `is_delayed` / `is_aged`; it contains no temporary-scope ToDo creation. A read-only scan of the live Server Script inventory found the E3a ambiguity writer and the HR expiry writer, but no E4 escalation writer. `temp_scope_max_days` is currently `0`, so the documented effective fallback remains 14 days; this config value does not itself create tasks. Treat the generic temporary-scope escalation ToDo as **not verified / outstanding**, not as deployed. Reconcile this requirement and the stale statement in `MASTER-ERP-INTEGRATION.md` §0.2 before representing E4 as complete. No escalation ToDos were created or assigned during this audit.

**E4 timing-coverage gate — 2026-09-20.** A read-only audit of all 603 cycles found 22 terminal cycles, but only **7** have both `tcn_at` and `first_visit_at`; the candidate pairs `mapping_at → boq_at`, `boq_at → pimp_at`, `pimp_at → tcn_at`, `first_visit_at → ho_at`, and `ho_at → asbuilt_at` currently have **zero** complete samples. Therefore the n ≥ 8 gate for a project-owned p75 is not met for any transition. Keep the stage SLA slots on the documented 30/14-day fallback, surface the missing timing facts as a data-quality gap, and recompute p75 only after the weekly job sees at least eight complete, same-project transitions. Do not infer or backfill elapsed times from `created_at` or event order.

For diagnostic context only, across all (open and terminal) cycles there are 98 TCN→first-visit pairs; 22 are negative-duration sequence violations. The positive-only raw interpolation is about **16.0 days**, but it is deliberately **not** an SLA/KPI: it mixes incomplete cycles and invalid ordering, and it is not a closure percentile.

**E4 closure/KPI correction — 2026-09-20.** The 22 current `terminal=1` rows are not 22 Excel-closed sites: only **1** has an explicit `SITE_CLOSED` event (`FTR010`); the other **21** were terminalized by `ASBUILT_BOQ_GENERATED` and have no `closed_by`. The legacy rule is explicit that `SITE_CLOSED` is the operator-confirmed closure and that As-Built must not stand in for closure statistics. Consequently, the closure KPI and any completion p75 are **N/A**, not zero and not a computed percentile, until the cycle projection separates explicit source closure from the As-Built milestone. Do not use the 21 derived terminal rows as Excel closure evidence.

**E5 emitter slice — 2026-09-20.** The EV1 row remains backward-compatible: the original 17 columns are unchanged and four optional columns are appended (`PlannedStart`, `PlannedDurationHours`, `PlannedActivity`, `PlannedBatch`). RV80 `tcnword.bas` now reads the actual `TCN-MDT` fields — Planned Start Date/Time, Plan Outage Duration, Remarks, and the selected batch `#` — and passes them through the shared `EvidenceCore`; both RV80 and sigpc `EvErpSend.bas` post those optional values only for `TCN_GENERATED`. `replay_ev1_batches.py` accepts the optional columns while continuing to replay legacy 17-column files. No site-only PO/WO lookup was added and no `SIG TCN Plan` doctype was created.

**E5 acceptance check — 2026-09-20 (read-only).** The live `SIG Site Cycle` metadata exposes `planned_start`, `planned_duration_hours`, `planned_activity`, `planned_batch`, and `planned_week`; the live endpoint source handles all four arguments only on `TCN_GENERATED`. The connected Excel checklist workbook has the source TCN-MDT inputs (`Planned Start Date/Time`, `Plan Outage Duration`, `Remarks`, batch `#`) and `_Ops_CycleFacts` output columns (`PlannedStart`, `PlannedDurationHours`, `PlannedActivity`, `PlannedBatch`). The staged RV80/sigpc modules and replay script carry those values correctly and preserve the 17-column contract. But the latest 100 live ERP TCN cycles currently have **zero** populated plan snapshots, so the operational workbook import has not yet been proven live. E5 is **implementation-ready, acceptance pending**: import the staged modules into the live RV80 and sigpc workbooks, emit one normal populated TCN, and read back the four cycle fields; no broad test suite or new doctype is required.

**E6 duplicate-Project preflight — 2026-09-20 (read-only snapshot before closeout).** The live inventory had 12 duplicated agreement numbers: `10001045`, `10001113`, `1000157`, `1000170`, `1000341`, `1000455` (three Projects), `1000493`, `1000501`, `1000608`, `1000649` (three Projects), `1000657`, and `1000705`. This snapshot preceded the owner-approved archive/delete closeout recorded below; it is retained as the before-state evidence.

**E6 link/cost-center audit — 2026-09-20 (pre-closeout snapshot).** `Project` has no direct `cost_center` foreign key; cost centers are separate masters. The older duplicate Projects `WO-2026-0003`, `0004`, `0005`, `0006`, `0007`, `0014`, `0015`, `0018`, `0019`, and `0026` carried posted GL and/or Stock Entry history and were therefore archived rather than deleted. Four older noncanonical duplicates — `WO-2026-0025`, `WO-2026-0012`, `WO-2026-0002`, and `WO-2026-0001` — passed the zero-link preflight and were deleted in the closeout below.

**E6 owner policy — 2026-09-20.** The owner retired the legacy subproject convention: each agreement/PO now resolves to **one active Project**. The historical `1000341` / `1000376` subproject pattern is not a reason to retain duplicate active Projects (`1000376` itself is not duplicated). Canonical Projects remain active; linked historical duplicates are preserved as `Completed` + inactive so Stock/GL history remains intact; only unreferenced erroneous duplicates are deleted.

**E6 full retirement map — executed 2026-09-20.** The complete one-Project-per-PO cleanup covered **14 noncanonical targets**, not just four: `WO-2026-0026` → canonical `WO-2026-0050` (archived; 4 GL rows); `WO-2026-0025` → `WO-2026-0051` (deleted after zero-link preflight); `WO-2026-0006` → `WO-2026-0040` (archived; 1 Stock Entry / 2 GL); `WO-2026-0007` → `WO-2026-0041` (archived; 1 / 2); `WO-2026-0012` → `WO-2026-0042` (deleted after zero-link preflight); `WO-2026-0003` and `WO-2026-0004` → `WO-2026-0043` (archived; 6 / 12 and 11 / 24); `WO-2026-0002` → `WO-2026-0044` (deleted after zero-link preflight); `WO-2026-0001` → `WO-2026-0045` (deleted after zero-link preflight); `WO-2026-0014` → `WO-2026-0046` (archived; 22 / 46, including a second named cost center in GL); `WO-2026-0015` and `WO-2026-0018` → `WO-2026-0047` (archived; 3 / 6 and 4 / 8); `WO-2026-0005` → `WO-2026-0048` (archived; 19 / 40); and `WO-2026-0019` → `WO-2026-0049` (archived; 2 / 6). All ten linked historical Projects read back `Completed` + inactive; all four zero-link Projects read back 404 after deletion.

**E6 cost-center and Journal Entry audit — 2026-09-20 (pre-closeout snapshot).** The live site had 36 Cost Centers; 15 carried one of the duplicate-agreement numbers (including the separate `1000376` cost center). Most agreements had one cost center, but `1000455` had two active leaves and `1000649` had two. The GL audit found **zero** rows with `voucher_type = Journal Entry` for either the duplicate Project IDs or these duplicate-agreement Cost Centers; all Project-linked GL rows were Stock Entry rows, and the seven draft Journal Entries had no matching Project or Cost Center account row. The owner-approved canonical mapping and leaf disabling are recorded below; no Journal Entry rewrite was required.

**E6 canonical Cost Center mapping — 2026-09-20 (applied, reversible).** The owner chose one future-mapping Cost Center per agreement, retaining the leaf with existing ledger history; for `1000455`, the higher-use `1000455 Colocation 5G5 2023 - SIG` was retained over `ITC`, and for `1000649`, `1000649 Colocation 2024 - SIG` was retained over `Mobily`. The canonical replacement Projects were linked live and read back successfully: `WO-2026-0050` → `10001045 - Colocation 2026 project - SIG`; `0051` → `10001113 Capex-9 - SIG`; `0040` → `1000157 5G2 - SIG`; `0041` → `1000170 Mobily - Salah Ibrahim Algain - SIG`; `0042` → `1000341 Colocation and Upgrade project 2022 Early start - SIG`; `0043` → `1000455 Colocation 5G5 2023 - SIG`; `0044` → `1000493 Incident recovery 2023 - SIG`; `0045` → `1000501 Capex 6 2023 - SIG`; `0046` → `1000608 Incident recovery 2024 - SIG`; `0047` → `1000649 Colocation 2024 - SIG`; `0048` → `1000657 Capex 6 2024 - SIG`; and `0049` → `1000705 Colocation and Upgrade project 2024 - SIG`. The two noncanonical leaves are now disabled for future use (history preserved, not deleted): `1000455 Colocation ITC 2023 - SIG` (8 GL rows) and `1000649 Mobily 2024 - SIG` (0 GL rows). `1000376 Colocation and Upgrade project 2022 - SIG` remains enabled because it is a single, non-duplicated agreement cost center. This does not rewrite submitted ledger rows or delete Projects.

**E6 deletion preflight and closeout — 2026-09-20.** All 12 canonical Projects have the selected Cost Center and remain active. The four direct-delete candidates (`WO-2026-0025`, `WO-2026-0012`, `WO-2026-0002`, `WO-2026-0001`) had zero links in the checked cycle, stock, GL, purchasing, invoicing, timesheet, task, update, issue, attachment, and ToDo tables; no posted or draft Journal Entry account row matched them; they were deleted and read back as 404. The ten history-bearing duplicate Projects were not deleted; they were archived as `Completed` + inactive, preserving Stock/GL history. Final read-back is 49 Projects total, 37 active, and every agreement group in scope has exactly one active Project. The cost-center side is clean for future writes; the two disabled leaves intentionally retain historical GL (`ITC`: 8; `Mobily`: 0) and are not deleted.

**Project Progress design finalized — 2026-09-20; P1 infrastructure deployed.**
The owner requested a reasoned progress-monitoring system grounded in the master and
evidence, not a copy of the Excel dashboard. The finalized recommendation is in
[project_progress_design.md](project_progress_design.md) and master §0.3: a native
ERP page with project summary, expandable site table, and evidence/comments/actions
panel. Each milestone displays only its own evidence; monitoring eligibility is
separate from evidence position and source closure; historic imports do not become
active work. Human notes are directly visible and writable; WO is shown only when
needed to disambiguate scopes, with no mandatory PM.

Delivery gates are Progress P0 (shared definitions and baseline), P1 (page/read model),
P2 (native comments/ToDos and audited monitoring decisions), P3 (stage alignment and
default-page cutover). This refines E3 presentation and E4 acceptance: do not tune an
SLA merely to reduce a delayed percentage; distinguish explicit overdue follow-ups,
reported blockers and default-threshold review age. Existing E3 temporary-scope
escalations remain linked generic ToDos, not automatic evidence of project delay.
It also replaces E3's always-visible scope column with conditional scope detail.
E5 optional plan transport and E6 cleanup are unaffected. Later cross-domain measures
remain under the master's commercial/material gates.

Read-only audit correction: 853 Comment records linked to Site Cycles are all empty
system entries of type Deleted; there are zero of type Comment at this check. They
must not be advertised as 853 human comments or selected as Latest update.

**Work order for the next agent (do in this order; each step has its gate).**

| # | Work | Gate / acceptance |
|---|---|---|
| E0 | **Verify evidence history.** `frappe.client.get_count` for `SIG Evidence Event`, `SIG Site Cycle`, `SIG Field Visit`. If history is missing, replay `Sync\Dump\_Evidence\Batches` (645 EV1 files, 2026-07-24 → 09-12) with `replay_ev1_batches.py`, chronological, then confirm counts. The endpoint now applies the TWO/Project rules during replay. | Counts explained and recorded here; no duplicate events (EventId dedupe); `test_scope_two.py` still 20/20 afterwards |
| E1 | **Roll out R0 delivery fixes to every operator machine** (import `EvidenceCore`, `EvErpSend`, `ACN` in RV80 and sigpc; `tcnword`, `logs`, `csv`, `EvidenceDashboard` in RV80; `MappingPipeline` in sigpc), then each operator runs `Evidence_ShowOutboxStatus`. Owner's machine already passed (0 pending, credentials resolved). Remaining: Gulzar, Mr. Tahir, mtayy, ASUS. | Each machine reports 0 pending and credentials resolved; ERP shows their events under the ACN name |
| E2 | **Carry PO/WO only when sourced.** Generic/basic TCN, BOQ and Mapping evidence may be PO/WO blank. When a source row explicitly holds an agreement/PO and a real client WO (not Mapping selector `1`), preserve both in EV1; otherwise send blanks and let ERP keep/use the temporary scope until later identifying evidence arrives. Never derive a value from a site-only lookup. | Every emitted PO/WO is source-proven; generic events remain valid without either; a later PO/WO event adopts the prior non-ambiguous temporary scope and links the canonical Project; no new `WO_SITE_MISMATCH` (six historical exceptions retained separately) |
| E3 | **ERP follow-up mechanics.** (a) Generic unassigned ToDo linked to the cycle on `WO_AMBIGUOUS` / `PROJECT_AMBIGUOUS`, then maintained through normal ERP ToDo assignment. (b) Escalation ToDo when a temporary scope is older than `temp_scope_max_days` (new `SIG Field Ops Settings` field, default 14). (c) **Assign WO** action on a temporary cycle (Client Script → server method; sets `wo`, `scope_id`, `resolution_state = ADOPTED`, keeps `temp_id`, `wo_source = MANUAL`; refuses a WO that names another site). (d) Project Progress shows Site/Project by default; expose `scope_id`/WO when needed to distinguish multiple scopes or resolve ambiguity, with full references in details and saved identity-review views. Valid generic work is not blocked by a missing WO. (e) Health cards: % cycles with a real WO, open temporary scopes, median days temp → adopted. (f) Setting for the client WO pattern (`^WO-SIG-`); non-matching WOs flag `WO_NONSTANDARD` instead of being rejected. | Extend `test_scope_two.py` for each; invariant query (more than one open temporary scope per site) returns 0 rows |
| E4 | **Delay tracker and comments.** `delay_reason` (Select from Settings) + `delay_note` on the cycle; **Log delay** dialog posts a native Comment and sets both; grid columns for reason and last comment; filter *Delayed, no reason in 7 days*; per-stage SLA = p75 of the project's own transition times (n ≥ 8, else the constant) recomputed weekly; My Work card *My delayed sites*. The management-facing BAS Delay Rules page controls which stage checkpoints contribute to the derived delayed flag/card, with all four enabled by default. Spec: master legacy archive, "Delay tracker and comments". | Project Progress separates overdue explicit follow-ups, reported blockers and default-threshold review age; exclude unconfirmed historical work from Current counts; comments visible and persistent; valid project-specific n ≥ 8 before learned SLA; owner walkthrough; Delay Rules page read/save and immediate derived-flag recalculation |
| E5 | **TCN plan into ERP.** Source implementation is complete and backward-compatible: the endpoint accepts `planned_start`, `planned_duration_hours`, `planned_activity`, `planned_batch`; RV80/sigpc emitters send them only for `TCN_GENERATED`, while legacy 17-column EV1 rows remain valid. Remaining gate is importing the staged modules into the live RV80 and sigpc workbooks; no new doctype is needed. | A new populated TCN-MDT row read-backs its planned start/activity on the cycle; blank-plan TCNs remain valid |
| E6 | **Duplicate Projects — closed 2026-09-20.** One active canonical Project per agreement; ten linked legacy Projects are Completed/inactive, four zero-link erroneous Projects deleted. Canonical Cost Centers are linked for future mappings; two duplicate leaves are disabled but preserve history. | Read-back confirmed 12 canonical active Projects, 10 archived legacy Projects, 4 deleted targets, and no Journal Entry dependency |
| E7 | **Freeze the RV80 dashboard / OpsKPI** (only after E1 passes on all machines); archive its refresh buttons. This also removes the ~6 s dashboard refresh inside each TCN export. | **Closed 2026-09-20:** owner’s unified-workbook E1 waiver accepted; live Dashboard shapes `EvDashBtn1` (`Refresh All`), `EvDashBtn2` (`Verify All`), and `EvDashBtn3` (`Repair Cache`) were hidden reversibly through the connected Excel session. `Close Sites` and the 5G/Capex/Incident filters remain visible. ERP workspace is the only board. |
| E8 | **Later (designed, not started):** tag-block hand-off (`SIG Tag Block`, list + ack endpoints, `work_key` on the Tags sheet, ERP emits `TAGS_COLLECTED`), FieldOps session parsing and media archive to ERP (stages A–D), petty-cash retirement, ACN replaced by ERP login. Specs: master legacy archive, "RV80 after ERP migration". | Per-stage gates in that section |

**Rules for the next agent.** Events stay immutable (never edit or delete an event to fix identity). Never auto-adopt an `AMBIGUOUS` temporary scope. Never send a WO the sheet does not hold. Run any endpoint change through a dry run, a backup and `test_scope_two.py` before and after. `WO = 1` on Mapping is a batch selector, not a work order. The client WO string contains the site id; a mismatch is a data error to flag, not to fix silently. TCN CSV / MOP Word files remain on the operator PC (`Downloads\TCN-MDT Exports\…`); ERP holds only the evidence record and the artifact path as text. RV80 log settings buffer ~2,000 lines in memory: when diagnosing a hang, rely on the forced-write breadcrumbs in `tcnword.bas`.

<a id="fixed-asset-gates"></a>
### 6A.15 Fixed Assets & Tool Custody — skeleton CLOSED 2026-09-19, Finance/Admin fill-in later

**Scope (owner instruction, 2026-09-19):** Prepare the FA *system skeleton only* (Categories, Locations, tracking custom fields, custody issue/return flows for tools → employee or "other"). Categories must stay GENERAL — no fine per-class depreciation differentiation yet. Finance & Admin fill in legacy register, item flags, useful lives, and run monthly depreciation *later*. No legacy import is blocking this gate.

**Deployed & API-verified (neosys.frappe.cloud):** `ERPNext/scripts/fa_setup_system.py` (idempotent; re-run with `--yes` safe). Live counts exact match target:

| Component | Expected | Actual | Notes |
|---|---|---|---|
| Asset Category | 9 | **9** | Land, Vehicles & Transport, Buildings & Leasehold, HVAC & Fixtures, Furniture & Office, Surveillance & Security, IT Equipment, Software & Intangibles, Tools/Machinery/Heavy Equip |
| Location | 15 | **15** | Riyadh, Jeddah, Dammam, Hail, Abha, Tabuk, Buraidah, Al Muzahimiyah WH, Al Kharj WH, Sulaiyil Site Camp, SIG HQ, On Loan – Subcontractor, Sent for Repair, Disposed / Sold, Scrapped / EOL |
| Asset custom fields (custom_*) | 14 | **14** | legacy_id, legacy_source_system, asset_tag_no, sig_site (Link→SIG Site), project_link (Link→Project), custodian_employee (Link→Employee), issuing_warehouse (Link→Warehouse), custody_status (Select), issue_date, expected_return_date, return_date, handover_ref, asset_condition (Select), remarks_admin |
| Asset Movement custom fields (custom_*) | 14 | **14** | movement_type (Select: Issue→Employee / Issue→Site / Issue→Subcontractor / Return-from-Employee / Return-from-Site / Transfer / Repair-in / Repair-out / Disposal / Scrap), legacy_id, From/To pairs for SIG Site, Project, Employee, Warehouse; condition_check, expected_return, handover_ref, remarks |

**Account mapping:** Per-category FA leaf uses the correct live 11xx SIG CoA leaves (Land 1111, Vehicles 1121, Buildings 1131, HVAC 1141, Furniture/Office 1142, Surveillance 1151, IT 1161, Software 1171, Tools 1181). Shared contra/expense/CWIP/disposal accounts match the Company defaults: Accumulated Depreciation = 1780, Depreciation Expense = 5203, CWIP = 1790, Disposal = 423. Cost center = "Contract Root - SIG". Land is `non_depreciable_category=1` with no default finance_books row (the child-row validator requires `total_number_of_depreciations > 0`; ERPNext still resolves the implicit default book without a row so skip the row for Land only). Default method = Straight Line, useful lives 4–20 yr as placeholders (Finance edits per ZATCA class mapping later).

| Item | Depends on | Gate | Status |
|---|---|---|---|
| FA bootstrap: 9 Asset Categories + 15 Locations + 28 Custom Fields (Asset & Asset Movement), correct 11xx leaf mappings + accounts/finance_books child tables | Live CoA resolved JSON (`fa_accounts_resolved.json` + live DocType probes for Asset Category child-table shape) | FA-GATE-0 | **CLOSED 2026-09-19 — HTTP 200/201 for every write; REST GET counts 9 / 15 / 14 / 14 exact match, no 417s** |
| Item master: flag capital-purchase Items as `Is Fixed Asset` + assign Asset Category (optionally enable `Auto Create Assets From Purchase Receipt` on those items) | FA-GATE-0 closed | FA-GATE-1 | **Pending (Finance / Admin manual) — no code block expected.** Use Item → Data Import if the list is large; no new script required. |
| Legacy asset register import (31 Dec 2025 snapshot): gross cost, accum depr, opening date + populate 14 custom_* fields per asset (legacy_id, tag_no, SIG Site, Project, custodian, custody_status, issue dates, handover_ref, condition) from Flexsoft/Excel physical-inventory | FA-GATE-0 closed, Item FA flags done, legacy mapping agreed | FA-GATE-2 | **Pending (Finance data entry).** Do NOT run depreciation before this import is reviewed; ERPNext creates schedules from the FA opening date. |
| ZATCA-live depreciation class mapping: edit useful life / rate per Asset Category (or per individual Asset overrides); agree Saudi tax class useful-life table; confirm 1780/5203/423/1790 tie to audited 31-Dec-2025 balances | FA-GATE-2 closed, Finance tax-depreciation policy agreed | FA-GATE-3 | **Pending (Finance sign-off, not code).** Placeholder Straight-Line 4-20 yr lives are deliberately wrong per-class; do not rely on them for statutory depreciation. |
| Monthly depreciation run (Assets → Depreciation Schedule → Create Schedules; auto-book GL is already on in Accounts Settings) | FA-GATE-3 closed | FA-OPS-1 | **Pending (Finance ops).** First real run only after FA-GATE-2 reviewed and FA-GATE-3 lives/rates approved. |
| Issue a tool to an employee (or other): New Asset Movement → `custom_movement_type` = "Issue to Employee" → select Asset, `custom_wh_from`, `custom_employee_to`, `custom_expected_return`, `custom_condition_check`, `custom_handover_ref` → Submit. Update the Asset's `custom_custodian_employee`, `custom_custody_status`, `custom_issue_date` manually after submission (or a later optional server script bridges it automatically — not blocking skeleton). | FA-GATE-0 closed, Asset register populated, at least one Asset with Is Existing Asset or purchase-side import done | FA-OPS-2 | **Manual (Admin/Warehouse).** Issue to Site / Subcontractor / Repair / Disposal / Scrap use the other `custom_movement_type` Select values with the matching From/To Link fields. Return flow uses the Return-* types and records `custom_condition_check` + return date. |
| Stage-3 SIG Warehouse custody ↔ FA Asset Movement bridge (keep vocabularies aligned so a later server script can write one from the other without schema changes) | FA-GATE-0 closed, Stage 3 WH custody vocabulary stable | FA-OPS-3 | **Design-only (no code this gate).** `custom_movement_type` Select vocabulary intentionally mirrors the WH custody-event vocabulary so a server-script bridge is low-effort later. Staged as a post-skeleton optimization once Finance's legacy FA-GATE-1/2 are complete. |
| FA Reports: Asset Register (by category / site / custodian / condition), FA Movement History (issue/return/transfer/disposal), Depreciation Schedule (preview vs actual) | FA-GATE-2 closed (data in), report-building toolset (Query Report / Insights / Workspace dashboard) | FA-OPS-4 | **Pending (report builder, optional).** Out-of-scope per original "skeleton only" instruction; add after FA-GATE-2 so the report dimensions exist. |

### 6A.15a Fixed-asset allocation plan and warehouse asset dispatch — PROPOSED 2026-09-21 (read-only assessment; nothing written to ERPNext)

**Live starting point (read-only API, 2026-09-21):** the `11xx` fixed-asset accounts carry **SAR 2,593,489.74** of cost, all from Flexsoft legacy journals (opening `ACC-JV-2024-02189-2` plus monthly replays). **ERPNext has 0 Asset records** (9 Asset Categories exist), so the balances are not yet tied to individual assets.

| Account | Balance (SAR) | GL postings | Asset Category | Allocation unit |
|---|---:|---:|---|---|
| 1121 Project vehicles | 1,158,001.47 | 4 | Vehicles & Transportation | one Asset per vehicle (plate, chassis, registration) |
| 1131 Property / villa | 1,141,250.00 | 1 | Buildings & Leasehold Improve. | one Asset per property (deed / title no.) |
| 1171 Accounting software | 94,325.38 | 1 | Software & Intangible Assets | one Asset per licence |
| 1181 Tools & equipment | 71,050.31 | 3 | Tools, Machinery & Heavy Equip | one Asset per tagged unit above the cost threshold |
| 1161 Screens & computers | 66,904.08 | 10 | IT Equipment | one Asset per device (serial) |
| 1142 Office furniture | 31,682.85 | 4 | Furniture & Office Equipment | per unit if tagged, else per office/site group |
| 1151 Surveillance cameras | 27,080.00 | 1 | Surveillance & Security | per unit if tagged, else per site group |
| 1141 Air conditioners | 3,195.65 | 2 | HVAC & Equipment Fixtures | per unit if tagged, else per site group |

About 89% of the value is vehicles and the villa. Only tools, IT, furniture, cameras and air conditioners (about SAR 200k) fit warehouse dispatch.

**Allocation rules**

1. **The ledger stays the authority.** Allocate each balance to individual Assets; never re-post it. Load the register as **existing assets** (`is_existing_asset`, opening accumulated depreciation) so no GL entry is created. A normally submitted Asset would post the cost a second time.
2. **Reconcile to the halala.** Per account, the sum of Asset gross costs must equal the balance above. Any gap goes to one named "unallocated" Asset per account that Finance clears; nothing is forced.
3. **Threshold.** Items below a Finance-set cost threshold stay ordinary stock tools (Material Issue + custody ledger, `sig_dispatch_tool`). Decision pending: the tool threshold.
4. **Identity and custody at load.** Each unit gets a tag/serial, a Location (stores named after the warehouses) and `custom_custody_status` = In Store. Vehicles and the villa get their responsible person and site at load, and are not dispatched through the warehouse tool.
5. **Depreciation last.** Use each category's useful life from Finance's tax-class table (FA-GATE-3); land is not depreciated. Run no depreciation until the register is reconciled and signed off.

**Load order (preview-first, one category at a time, no writes before approval):** 1181 tools → 1161 IT → 1142 / 1151 / 1141 → 1121 vehicles → 1131 villa and 1171 software. Input: the physical asset list plus the asset-account transactions above.

**Warehouse asset dispatch (built and deployed 2026-09-21, see 6A.15b):** one button, **Dispatch / Return**, on the Dispatch Board. The dialog is keyed on **Item code**: a Fixed Asset Item shows an Asset picker (that Item's submitted Assets) and issues or returns through a native **Asset Movement** (`sig_warehouse/asset_ops.py`); any other Item follows the existing stock path (`custody.sig_dispatch_tool`, Material Issue). ERPNext does not allow a Fixed Asset Item to be a stock Item, so an asset has no warehouse stock balance and needs no Stock Entry; its "warehouse" is its Location. `sig_dispatch_tool` now rejects Fixed Asset Items. Dispatch and return write the Asset's `custom_*` custody fields, are idempotent on operation ID, and are restricted to Stock Manager / System Manager. It is live and proven on one unit (6A.15b); the register load still waits for the physical list.

**Open decisions:** (1) tool cost threshold below which items stay stock; (2) Finance owner who signs off useful lives (FA-GATE-3); (3) the physical asset list for tools and IT.

### 6A.15b Stock-to-asset cycle for tools — DEPLOYED and proven live 2026-09-21

**Why tools:** vehicles, the villa and the other fixed-asset accounts are one-off purchases loaded from the register (6A.15a). Tools are the only class bought repeatedly on small invoices into warehouse stock, so they need a repeatable code-to-asset cycle.

**Live finding (read-only, 2026-09-21):** only **10 tool items** hold stock (item codes `T-*` / `TC-*`), in Mazahmiyah; the highest value is `T-CLM-FL` Clamp Meter Fluke at SAR 1,050 (`T-C-CRAMP` 145, the rest under SAR 30). The `E-*` items (cabinets, DC systems, batteries) are project installation material, not tools, and stay stock. So the cycle is right but its current volume is small, and most tools fall under any sensible capitalization threshold.

**Cycle (native ERPNext, no custom ledger):**
1. Buy as an ordinary stock Item (Purchase Receipt into the warehouse).
2. When a unit qualifies (cost above the Finance threshold, or it needs a tag and one named custodian), capitalize it with **Asset Capitalization**: it consumes 1 unit of the stock Item from the warehouse and creates the Asset at the stock valuation cost. The ledger moves value from stock to the fixed-asset account once, so nothing is double counted.
3. ERPNext forbids one Item being both stock and fixed asset, so each capitalized tool gets a **fixed-asset twin Item** `FA-<stock code>` (category *Tools, Machinery & Heavy Equip*, non-stock), created automatically on first capitalization.
4. The new Asset gets its tag/serial, sits in a store Location with custody status *In Store*, and is issued and returned through the Asset Movement dialog (6A.15a).

**Deployed and proven live (2026-09-21, first unit `S-SHO-RM-42`, Safety Shoes Road Mate size 42):**

| Step | Record | Result |
|---|---|---|
| Capitalize one unit from stock | Asset Capitalization `ACC-ASC-2026-00001` | Consumed 1 unit from Al Muzahimiyah warehouse (stock now 0); Dr `1181 - عدد و أدوات` SAR 130.43 / Cr `1341 - المستودعات` SAR 130.43 |
| Asset created | `ACC-ASS-2026-00001`, twin Item `FA-S-SHO-RM-42`, tag `SIG-TL-0001` | Category *Tools, Machinery & Heavy Equip*; submitted; Location *Al Muzahimiyah Warehouse*; custody *In Store* |
| Issue to a person | Asset Movement `ACC-ASM-2026-00400` (Issue to Employee) | Custodian `HR-EMP-00019` Asif Nawaz; custody *Issued - Employee*; the Movement and the Asset post **no** ledger entries |

**One dialog, driven by the Item code.** The Dispatch Board's single **Dispatch / Return** button asks for the Item first. A Fixed Asset Item shows an Asset picker (that Item's submitted Assets) and issues or returns through a native Asset Movement (`sig_warehouse/asset_ops.py`: `sig_dispatch_asset`, `sig_return_asset`). Any other Item follows the stock path (`custody.sig_dispatch_tool`, Material Issue and the custody ledger), and a stock Item can be converted with the option *Register this unit as an Asset* (`sig_capitalize_tool`). `sig_dispatch_tool` rejects Fixed Asset Items. All three writers are idempotent on operation ID, restricted to Stock Manager / System Manager, and never post a second ledger entry.

**ERPNext v15 facts confirmed on the first run (record so they are not rediscovered):** Asset Capitalization has no `remarks` column (the retry marker is stored in `title`); it needs `capitalization_method = "Create a new composite asset"` and a cost centre; ERPNext leaves the created Asset as a draft, so `sig_capitalize_tool` now submits it (commit `e7261e5`, deployed; the auto-submit itself has not been re-proven on a second unit); no Asset Capitalization or Asset record existed before this run.

**Capitalization rule of thumb:** an ordinary stock tool is capitalized only when it needs a tag and one named custodian, or its cost passes the Finance threshold. Personal protective items such as safety shoes normally stay as issued stock; `S-SHO-RM-42` was used as the proving unit because it was a 1-unit, SAR 130.43 item.

**Below the threshold:** the tool stays an ordinary stock tool on the existing Material Issue and custody ledger route.

**Open decisions:** the capitalization threshold in SAR, and whether new tool purchases above it should skip stock and be bought directly as a fixed-asset Item. The remaining fixed-asset register load (6A.15a) is unchanged and still waits for the physical list.

### 6A.15c SIG Site as the two-way hub — DEPLOYED 2026-09-21/22

**How connections work here (record for reuse):** SIG Site is a custom DocType; its Connections panel is the `links` child table of the DocType (`DocType Link` rows: `link_doctype`, `link_fieldname`, optional `group`, and `is_child_table` + `parent_doctype` + `table_fieldname` for item lines). The opposite direction is a Link field to SIG Site on each document plus a Site group in that document's own dashboard. ERPNext copies same-named fields when a document is created from another, so **one field name, `custom_site`, is used everywhere** (Asset keeps `custom_sig_site`).

**Site to documents (17 entries, four groups):** *Field Ops* (Site Cycle, Field Visit, Evidence Event); *Stock* (Material Request and its item lines, Stock Entry and its detail lines, Delivery Note, Purchase Receipt); *Assets* (Asset, Asset Movement); *Accounts* (Sales Order, Sales Invoice, Purchase Order, Purchase Invoice, Payment Entry, Journal Entry). `ERPNext/scripts/deploy_site_connections.py` (idempotent, dry-run by default) also adds `custom_site` to the six accounts doctypes and makes the existing site fields list filters. For example, site `ZRH689` shows 5 Material Requests and 2 Stock Entries.

**Documents to Site:** `SIG_Warehouse` `dashboards.py` (`override_doctype_dashboards`, commit `2a770f5`) adds a Site group to the connections list of Material Request, Stock Entry, Delivery Note, Purchase Receipt, Sales Order, Sales Invoice, Purchase Order, Purchase Invoice, Payment Entry, Journal Entry and Asset. The Material Request and Stock Entry Site fields were buried at the bottom of the form (after the Connections tab); they now sit under Company and Stock Entry Type. Prompted by MR-26-0628, which had its site (`ZRW783`) but no visible connection.

**Open:** existing invoices, payments and journal entries carry no site yet (backfill only where the link is certain, preview first); SIG IH Event/Position have no site link; the Site master still lacks Project, Customer, status and region; Asset Movement "from site" is not a panel entry.

### 6A.15d Field Ops daily scheduler repaired, visit-feed finding, group-message sheet health — 2026-09-22

**Repair:** the `sig_field_ops_daily` Server Script (Scheduler Event, Daily) recomputes `is_delayed` / `is_aged` on open SIG Site Cycles. It failed every night since at least 2026-09-15 with `ImportError: __import__ not found`, because its first line was `import frappe`; Server Scripts run sandboxed with `frappe` already in scope. The line was removed in the source (`scripts/hr/deploy_field_ops_infra.py`) and in the live script, and a manual run at 2026-09-22 00:49 completed. Rule to keep: **never `import` in a Server Script.**

**Finding: site visits have not updated since 2026-09-13, and no ERP job feeds them.** ERP creates a `SIG Field Visit` only from an accepted `FIELD_VISIT_COMPLETED` evidence event. That event came from RV80's Google/session synchronizer, which was intentionally short-circuited, so nothing has produced one since. The other evidence events keep flowing live (newest TCN 2026-09-21 12:38, as-built 2026-09-21 16:23 UTC), which is why the cycles look active while the newest visit stays 2026-09-13. The daily job never created visits; the earlier belief in a daily sheet-to-visit script is not borne out. Restoring visits is designed in [field_visit_feed_design.md](field_visit_feed_design.md) (gates F0-F3). **F0 (preview), F1 (shadow) and F2 (live) are done and deployed 2026-09-22** (release `3486692`): an ERP-side session engine in `sig_warehouse` reads new Inbox rows by cursor every 15 minutes, applies the FieldOpsCore Start/End rules, keeps proposed sessions in `SIG Field Session` (messages in `SIG Field Message`), and in Live mode posts each completed session through `register_evidence_event`, creating and linking the SIG Site when missing. First Live run: 38 visits posted at 35 sites, 27 SIG Site records created, 0 failed; the newest visit moved from 2026-09-13 to 2026-09-21; a stale-feed ToDo alert is on. Settings: `SIG Field Ops Settings.feed_mode` (Off / Shadow / Live). The PM intake page is planned in [site_visits_page_design.md](site_visits_page_design.md).

**Group-message sheet is healthy:** `Whatsapp to sheet Automation` (`1wgxHyL5…`) is receiving and processing messages. The Inbox holds 27,478 rows; 134 to 259 messages per day over 2026-09-18 to 09-21, latest received 2026-09-21 23:40 and processed a minute later; statuses 26,221 DONE, 1,238 SKIP, 19 REVIEW; recent HR attendance messages create `EMP-CKIN-…` check-ins in ERP. The 5G group tab's newest row is 2026-09-21 19:22. There is no two-day gap on the message side.

### 6A.15d-2 Pre-feed historical backfill (Jul 28 – Sep 10) and review-queue closure — 2026-09-22

**Finding:** visits from before the live feed (6A.15d) started already existed in ERP, but only as a thin `SIG Field Visit` ledger (`EV1|…` batch prefix, source `FieldOps_SyncAll`) — site + timestamp only, no reporter, duration or diagnostics — so the Site Visits PM page (which reads `SIG Field Session`, a different table) never showed them. The richer, reporter-attributed version of the same visits existed only offline, in the legacy Excel pipeline's `Field Sessions` sheet (`SIG Documentation - Task Checklist 2.02.xlsm`, hidden/veryHidden tabs, last computed 2026-09-10): 201 sessions, Jul 28 – Sep 10, cleanly handing off to the live feed's Sep 12 start with no overlap.

**Backfill executed:** a one-off whitelisted endpoint (`field_feed.sig_field_backfill_historical`, System Manager only) inserted all 201 sessions as `SIG Field Session` rows, pre-resolved client-side against current ERP master data (Employee, SIG Site, SIG Site Cycle, SIG Field Reporter Map) and matched by site+time to the existing EV1 evidence records (181/201 matched) — no new evidence event or `SIG Field Visit` was created, so Site Cycle rollups were not touched. This is the boundary the sigpc white paper (`white paper cp.md` §§11.2/11.6) already draws for AI/automation in this ecosystem: a reviewed, one-off historical pass is fine; a live operator-facing guess is not.

**Data-quality fixes applied (mechanical, no judgment):**
- 3 reporter phones that looked unresolved (`966573501903`, `966535650867`, `966536139137`) turned out to be real, already-known employees (Muhammad Bilal Khalid Saeed, Muneeb Hassan Muhammad Munir, Ali Haider Muhammad Ramzan) using a secondary/WhatsApp number different from their HR `cell_number` — added to `SIG Field Reporter Map`.
- 12 site codes had an established `SIG Site Cycle` but no master `SIG Site` record — created the missing records (mirrors the live feed's own `_ensure_site`).
- 1 session flagged `REPAIRED_DELAYED_SYNC_END` was the legacy classifier's own "already fixed this" marker, not an anomaly — un-flagged.

**New PM action — `confirm` (`site_visits.confirm`):** REVIEW items whose only issue is a judgment call about an estimated duration (`HARD_CAP_24H`, `NEW_START_MISSING_END`, `DUPLICATE_START`, `INVALID_NEGATIVE_DURATION`) had no way to be closed out except misusing Void or Fix Site. Confirm clears the flag without changing any data, using the feed's own `ERP_LAST_VISIT` cutover so a confirmed historical session can never become eligible for live (re)posting. **Owner decision 2026-09-22: exact timing doesn't matter, only that the employee and site are known and the visit happened** — so all 17 remaining review items with a resolved employee+site were bulk-confirmed via this action, plus one more (`ZTFA104`, Abid Saeed Shaukat Ali) confirmed with the site code left unresolved.

**Voided (not real visits):** the last 2 review items had no real site at all — the reporter typed `NEED` and `OUTAGE` in the site field instead of a site code (placeholder text, not a typo'd code). Closed via `void` with reason "not a true visit — site field is a placeholder, not a real site code." **Review queue: 21 → 0.**

### 6A.15d-3 Every post owns a site page — analysed 2026-09-24, code written locally, NOT deployed

**Rule (owner):** any post creates its `SIG Site` if missing; a missing site is never an exception or a review item. A site page needs only `site_id` + `site_name`. **No key correction** (ZMK→ZMKA, zero variants): site-code cleanliness is upstream's job (RV80 `tcnword.bas` `OpcoToAVariant` applies it to TCN rows only; ERP does not and will not).

**Who creates a site page today:** WhatsApp feed `post_session` (yes), `register_mir` (stub), `register_stock_entry` (stub), PM Fix-site with "create" (manual). **Gap:** `register_evidence_event` (TCN, PIMP, GCL, photos, warranty, MIR confirmed, all 15 codes) creates a Site Cycle only — no `SIG Site`, no `site` link. `custom_site` on Sales/Purchase Orders/Invoices, Payment Entry and Journal Entry is manual only.

**Bug found:** `post_session` created the site page but never copied it onto the `SIG Field Session` row, and `get_visits` treated `UNRESOLVED_SITE` as a review trigger — so 27 already-posted live visits showed "Needs review" (31 total; the other 4 are 3 real start-without-end + the ZTFA104 leftover).

**Local changes (uncommitted, awaiting a deploy window):** `register_evidence_event_script.py` ensures the SIG Site and sets `site` on cycle, visit and event; `field_sessions.assemble` no longer emits `UNRESOLVED_SITE`; `site_visits.get_visits` no longer treats it as review; `post_session` refreshes `site` and strips the flag; `scripts/hr/repair_session_site_links.py` (dry run by default) repairs existing rows. **Checked 2026-09-24 (browser + source sheet):** the 13 unposted "IN_ERP_WINDOW" sessions dated Sep 12–13 are mostly covered — 11 have an EV1 visit at the same site the same day (the later Sep-13 ledger batch reaches Sep 13), just never linked on the session row; `RIY2185` Sep 13 06:46 has an EV1 at 09:15; only `ZJZ154` (Sep 12 16:45, auto-closed) has no visit. The Sep 10 afternoon Starts (`ZJZ235`, `ZHA180`, `ZRW779`, `ZRW909`) are covered by EV1 and have no session row. **Open check:** (2) composite site pages such as `687-00-000 (Building)` vs the evidence normalizer, which strips spaces/brackets.

### 6A.15d-4 Site identity and historical link reconciliation — DEFERRED 2026-10-13

**Completed slice:** the Cycle Connections Site action and the supported exact-match Cycle-to-Site backfill are recorded as deployed on 2026-10-13; the live baseline after that repair is 2,306 Cycles, 2,110 Sites, 2,298 Cycles with a valid Site Link, and 8 Cycles held unlinked for review (`1`, `A`, `ZJZ464`, `ZJZ472`, `ZJZ473`, `ZT-TEST01`, `ZZZ111`, `ZZZZ1`). Do not reopen the broad resolver project as a prerequisite for using the Site connection action.

**Deferred work:** standardize identity resolution across evidence intake, WhatsApp Field Sessions, stock, and finance; reconcile remaining Cycle/Event/Visit/Session links; and confirm official current Site names against an authoritative, current source. The 2,110 live Site masters have matching `site_id` / `site_name` values, but the available SitesDB snapshot is dated 2026-07-25, so this is internal consistency—not proof of current official names. A read-only audit found 18 of 315 Field Sessions without a Site Link (13 completed, 5 auto-closed); direct API reads of `SIG Evidence Event` and `SIG Field Visit` returned 403, so their row-level link coverage remains unverified. No VBA change is the first step.

**Re-entry design:** retain the existing `sig_warehouse` app and add an app-owned `SIG Core` module for one shared Site resolver; keep operational evidence and Cycle behavior in `SIG Operations`. Key approved aliases by source namespace plus external ID, preserve raw source IDs, and keep Site resolution separate from Project/WO/Cycle resolution. Do not globally insert/remove `A`, trim zeroes, or merge punctuation variants. Before any repair, confirm the current authoritative Site source, dry-run a row-level manifest, separate exact links from ambiguity/test placeholders, preserve names and event history, and use an idempotent reversible migration. Any eventual app/metadata change must pass the existing permission baseline, learning-loop access gate, and affected PM/Coordinator, Operations, Stock, Finance, and Administrator workflow checks. No Site/Cycle/Event/Visit/Session records or VBA were changed in this audit.

<a id="operations-stage-task-gap"></a>

**Stage-task and ToDo audit — 2026-10-13 (read-only).** The owner-approved Operations Workbench process expects one applicable shared task per stage/work item, closed by matching evidence or a recorded manual cycle closure; role ownership is PM, Coordinator, or either. These pipeline tasks are not required to be native ERP ToDo documents. The deployed `/operations-workbench` backend returned 610 open cycles and 1,696 closed cycles, with 1,183 pending role-coded work items (762 Coordinator, 421 PM). This dated audit confirms that stage work exists in the deployed read model; it does not confirm individual assignment or complete task coverage. Closed-cycle counts are audit data only and must not appear as dashboard counters/cards.

For the owner-confirmed Incident scope (Abdulraheem Mohammed and Mohammed Sohail as PMs), the live read model has 26 open cycles and 16 PM-role pending items: 14 As-Built BOQ file tasks and 2 Visit tasks. Five open Incident cycles have no projected task in the current model; classify these before treating them as closure-ready. The live page renders pending-work labels and a personal “My ToDos” list, but it does not resolve PM/Coordinator tasks to named users or show a dedicated, complete task queue. Current pipeline projection covers TCN, MIR, Visit, Tags, Photos, and As-Built BOQ; Mapping/BOQ, RFI, Warranty, handover documents, and explicit cycle closure are not fully implemented as actionable tasks. RFI/Warranty/document applicability and the required evidence contracts must be wired before those tasks can close automatically.

The live site has 6 native Open ToDos: 5 high-priority E3a scope-identity reviews linked to Cycles and intentionally unassigned by policy, plus one unrelated unlinked medium-priority item dated 2026-04-22 (`x dated 2026-04-22`). All 6 are unassigned; the five review items are overdue. The unlinked item is a review candidate, not an instruction to delete it. No task or ToDo was created, assigned, completed, or deleted.

The live `SIG Project PM Assignment` has 17 active/default rows for TAWAL contacts; it is not an internal SIG PM/Coordinator assignment map. The live Project custom fields do not contain a per-project PM/Coordinator map. The owner-confirmed roster supplies family/scope responsibilities, while verified BA/project membership and Employee/User routing remain unconfigured. The workbench must resolve these mappings before claiming that a PM’s personal task queue is complete. Do not treat the absence of native ToDo rows as evidence that stage work is absent, and do not treat role-coded stage items as assigned to a named person.

**Owner-directed first implementation slice — 2026-10-13; DEPLOYED, PARTIAL.** [Operations stage-task execution plan](operations_stage_task_queue_plan.md) records the full target and [the revised local concept](ui_concepts/operations_workbench_concept.html) shows the intended queue. Commit `832a23ac90a802cd18d01c4430d889e70d5c18c6` adds currently available TCN, MIR, Visit, Tags, Photos and As-Built BOQ evidence tasks, confirmed scope-roster routing when the signed-in Employee can be resolved, independent native My ToDos, review items, explicit cycle closure and task-filtered export. Evidence closes its matching task; delay flags the same task. The deployed Workbench does not have a direct Complete button. Manual legacy cycle closure remains deliberate, with reason/actor/time, retained evidence and independent follow-ups preserved. Pipeline `bfolq8of6f` succeeded; the production app hash is `832a23ac90a802cd18d01c4430d889e70d5c18c6`. A fresh authenticated PM session (`abdul.raheem@sigtele.com`) loaded `/app/operations-workbench`; the route/render check passed. Before/after permission snapshots reported zero grant changes. The task projection remains partial: reconcile all current ERP stages and accepted evidence sources to the white-paper catalog, including Mapping/BOQ, RFI, Warranty and handover rules; classify the five reported no-task Incident cycles by row. Do not automatically close them. Full task coverage, Coordinator acceptance, registered-audience permission regression, export and closure acceptance remain NOT TESTED / INCOMPLETE. Coordinator acceptance remains pending by owner direction. No live tasks, assignments or permissions were changed during deployment verification.

**Stage 4 naming correction and repair — deployed 2026-10-14.** The owner-approved cycle `ZNJ104|WO-SIG-IMP-ZNJ104-11340-Incident-23580|20260726` has HO evidence (`2026-07-26 14:57:25`), no `asbuilt_at`, and an open PM-owned As-Built BOQ task due `2026-08-09`. Its stage is `4 - Invoicing`; `Review due` remains the overdue task status, not a stage. Production app hash `452cbcd3` is live on `neosys.frappe.cloud`; Stage 4 options, evidence writer, Workbench, and Kanban agree. All 43 open records moved from the old label because all have HO/invoice evidence; the old-stage count is zero.

The first follow-up migration wrote the delay-checkpoint setting incorrectly and cleared `is_delayed` on 31 records. Post-deploy read-back caught this. The repair release restored the approved four keys (`initial`, `plan`, `handover`, `invoicing`) and the 31 flags from the pre-change manifest. All tracked fields on the 43-row manifest now match their pre-change values apart from the intended stage rename. The target cycle remains delayed and aged, with its original due date and PM As-Built BOQ task. Backups: `32f7h9v2en` (before the defective follow-up) and `2ju3kvcda9` (before repair). Permission snapshots before/after repair show 0 additions and 0 removals; `SIG Field Ops Settings` remains System Manager-only. PM persona acceptance is NOT TESTED; Coordinator acceptance remains pending by owner direction; the live API identity was not used to impersonate either role.

### 6A.15e Navigation / workspace layout — assessed, not executed 2026-09-22

**Owner observation confirmed with data:** SIG-built work has no single sidebar home. `SIG Site Cycle` is a raw-list shortcut in *both* SIG Projects and SIG Field Ops (module `None`); `Material Request` is a shortcut in both SIG Warehouse and SIG Operations; `Project Progress` is a bare URL shortcut duplicated the same way, so there is no breadcrumb back to either. The three field-ops doctypes (`SIG Site Cycle`, `SIG Field Visit`, `SIG Evidence Event`) sit in their own `SIG` module, which has no Workspace at all — they only appear because two unrelated workspaces each separately linked to them. None has a `title_field` or `List View Settings`, so the raw list (`/app/sig-site-cycle/view/list`) dumps 56 undifferentiated columns even though a good Kanban (`SIG Cycle Board`) and four curated reports already exist for the same data. The new Site Visits page (6A.15d/site_visits_page_design.md) would inherit the identical "nowhere to go back to" problem if linked the same way.

Full assessment and proposed consolidation (one SIG workspace, drop the duplicate raw-list shortcuts, title fields + List View Settings on the three doctypes, one shortcut each for Project Progress and Site Visits with a breadcrumb back): [erp_navigation_assessment.md](erp_navigation_assessment.md). **Nothing executed; waiting on owner approval**, since these are visible to every user immediately. `Impersonate User` (System Manager, native to Frappe Cloud) is the confirmed way to verify a role's actual sidebar before and after, without submitting anything.

### 6A.16 KSA HR Compliance — Iqama / GOSI / Muqeem monthly sync

**Owner instruction (2026-09-19):** Muqeem iqama expiry sheet is downloaded once a month from the Saudi Muqeem portal (Gov active-residents xlsx). HR shares the dump file to Downloads (today: deferred — HR supplies tomorrow). Build the reference-file + update-in-ERP pipeline against the dump shape in modMuqeemDashboard.bas/modFindGovDownload.bas. The "HR person name" native field (Employee.employee_name) must be updated from the dump name if the names differ (change should be in the employee HR person name, not a custom-field duplicate). RV80 `SIG Site` import explicitly DEFERRED per owner.

**Deliverable script:** `ERPNext/scripts/hr_employee_compliance.py` (single script, two subcommands + `all` aggregate):
* `setup_fields [--yes]` — 11 KSA compliance custom fields on Employee doctype. Idempotent via `custom_field_exists(dt, fieldname)` pre-check (Custom Field docnames are generated hashes, not `<dt>-<fieldname>` synthetic names, so existence check cannot use ensure_resource-name lookups — same fix used in fa_setup_system.py).
* `sync_muqeem [--yes] [--dump <path>]` — idempotent monthly Muqeem→Employee sync.
  * Dump discovery matches VBA `FindActiveResidentsReportPath`: scans `%USERPROFILE%\Downloads` for newest `.xlsx` whose filename contains BOTH Arabic keywords المقيمين (Residents) AND النشطين (Active). Falls back to explicit `--dump` path if present.
  * Dump column positions match VBA `modMuqeemDashboard.bas` constants exactly: `COL_NAME=2`(B), `COL_PASSPORT=7`(G), `COL_IQAMA=9`(I). Optional extras: IQAMA_NO=8(H), SPONSOR=1(A), BORDER=10(J), GOSI=11(K), PERMIT_EXP=12(L). Single-point edit if the Gov ships a new layout.
  * Matching strategy (priority): (1) case-insensitive trim + collapse-whitespace match against native `Employee.employee_name`; (2) 10-digit Iqama number match against `custom_iqama_number` (kicks in after first successful sync stores iqama numbers, stable across renames); (3) substring contains-match as tiebreaker.
  * Patch semantics: PUT only changed keys (`_diff()` against live doc snapshot) → no spurious `modified` timestamps, no unnecessary last_modified drift.
  * Native field update rule: if dump name differs (case-insensitive trimmed), PUT both the native `employee_name` AND space-split `first_name/middle_name/last_name` when >=3 space-separated tokens (owner explicit: "change should be in the employee hr person name").
  * Reconciliation report footer: rows-in-dump, matched-vs-ERP, missed-list, extra-ERP-not-in-dump list, HR-name-change PUT count, total fields written. Dry-run prints the identical PUT list without touching the ERP.
  * Sync timestamp written per employee to `custom_muqeem_report_date` = dump file ctime (matches VBA PROP_MUQEEM_ASOF contract).

**Custom Fields deployed (2026-09-19, REST verified count = 26 total Employee custom_* fields, 11 NEW of which 1 was already from an earlier run):**

| New field (all 11) | Type | Status | Notes |
|---|---|---|---|
| custom_iqama_number | Data (searchable) | **ALREADY** | 10-digit Saudi iqama id. SADAD Pay Iqama "Iqama ID" column. |
| custom_iqama_expiry_date | Date (searchable) | **CREATED** | Matches Muqeem col 9=I. Hijri→Gregorian preserved by openpyxl. |
| custom_passport_expiry_date | Date (searchable) | **CREATED** | Matches Muqeem col 7=G. |
| custom_gosi_number | Data (searchable) | **CREATED** | Saudi GOSI social insurance membership no. |
| custom_gosi_registration_date | Date | **CREATED** | GOSI start date for the employee. |
| custom_sponsor_id | Data | **CREATED** | Kafeel / Sponsor name or numeric id from Muqeem col 1=A. |
| custom_border_number | Data | **CREATED** | Saudi border entry number (Muqeem col 10=J if present). |
| custom_work_permit_expiry | Date | **CREATED** | MLSD work permit expiry (Muqeem col 12=L if different from iqama expiry). |
| custom_muqeem_report_date | Date | **CREATED** | Download/creation date of the latest Muqeem report that updated the employee (per-row sync timetamp, matches VBA PROP_MUQEEM_ASOF). |
| custom_hr_remarks | Small Text | **CREATED** | Free text: missed matches, name-change notes, leave-without-pay. |
| custom_sadad_pay_iqama_duration | Data | **CREATED** | Months value populated from HR2 Main col-D "Pay Iqama" duration when they queue renewals. Written to the SADAD CSV. |

Pre-existing HR CFs that were ALREADY present (not touched; confirmed listed in 26-count verification):
`custom_arabic_name`, `custom_bank_beneficiary`, `custom_nationality`, `custom_nationality_arabic`, `custom_office_signin`, `custom_out_mudad`, `custom_out_mudad_bank`, `custom_out_mudad_iban`, `custom_source_department`, `custom_source_job_title`, `custom_source_manager`, `custom_iqama_expiry`, `custom_iqama_status`, `custom_muqeem_source_as_of`, `custom_sponsor`.

| Item | Depends on | Gate | Status |
|---|---|---|---|
| Custom Fields (11 KSA compliance on Employee doctype), idempotent, correct VBA-modelled dump column positions already baked in | None | HR-GATE-0 | **CLOSED 2026-09-19 — setup_fields --yes returned 1 ALREADY + 10 CREATED. REST GET count of custom_* on Employee = 26 exact match (15 legacy HR-out + 11 compliance). No 417s.** |
| Muqeem sync writer pipeline: filename discovery (Matches VBA FindActiveResidentsReportPath Arabic keywords), openpyxl sheet-read by absolute VBA constants column position, match-by-name-then-iqama, dry-run reconciliation report, selective PUT only changed keys, native employee_name update rule, --dump path override | HR-GATE-0 closed, openpyxl installed in the Python env the script runs under (pip install openpyxl python-dateutil when HR shares the file if not already present) | HR-GATE-1 | **CLOSED 2026-09-19 — code review complete, dry-run reconciliation report path exercised; HTTP PUT scaffolding validated against fa_setup_system.py REST helpers. Actual execution with real data blocked on HR supplying the Gov dump file (owner said "ask HR tomorrow", not a code blocker).** |
| First real Muqeem sync execution: when HR drops the Gov xlsx into Downloads, run `python hr_employee_compliance.py sync_muqeem` (dry-run preview), verify missed/extra lists with HR, then re-run with `--yes` + `--dump` if the auto-discover path picks the wrong file | HR-GATE-1 closed, dump file actually present in Downloads or explicit path given | HR-OPS-1 | **Pending manual trigger once HR shares the file (owner: "HR will share it tomorrow"). Rerun: `cd erp ; python ERPNext/scripts/hr_employee_compliance.py all --yes`. Expected runtime: 15s for ~600-1200 Muqeem rows vs 64 live ERP employees.** |
| Monthly recurrence: after every new Muqeem dump (~every 4 weeks or after iqama renewal batches) re-run HR-OPS-1 | HR-OPS-1 closed cleanly once | HR-OPS-2 | **Scheduled-Operator (no cron). Command: `python ERPNext/scripts/hr_employee_compliance.py sync_muqeem --yes`.** |
| SADAD Pay Iqama pipeline: on HR2 dashboard, HR fills "Pay Iqama" duration (months) on Main col-D → ExportSadadRenewIqamaFromMainToDownloads emits `SADAD Renew Iqama yyyy-mm-dd.csv` into Downloads → HR uploads csv into SADAD portal for bulk iqama renewal payments. When that csv is produced, optionally back-push those duration values into ERP `custom_sadad_pay_iqama_duration` as well (1-line extra writer script if needed — the field is live so the data slot already exists) | SADAD csv actually produced by HR2 dashboard | HR-OPS-3 | **Not blocking — infrastructure exists (the CF + export-bridge VBA already in hr2). Add the ERP backfill writer only after first manual Pay Iqama run confirms the HR2-side UX works.** |
| Iqama / Passport expiry Email Alerts / Workspace dashboard + Daily ToDo task creation: Notification doctype watches `custom_iqama_expiry_date` / `custom_passport_expiry_date` at 90/60/30 days-before bands (Email + System Notification channel, `receiver_by_role = HR User` → delivers to `hr@sigtele.com`). Scheduler Event Server Script runs daily → upserts 1 Open ToDo per employee × expiry-type (Iqama, Passport, Work Permit) when ≤30 days left; allocated to `hr@sigtele.com` (role `HR User`, ref linked to the Employee doc, priority High for ≤15d or overdue, Medium 16-30d). Workspace `SIG HR` placeholder section replaced with 6 expiry Number Cards + 3 renewals shortcuts. All three pieces re-read the same custom_* fields that the monthly Muqeem sync writes (`sync_muqeem` puts newer dates in, Notifications re-evaluate via the nightly maintenance date loop, ToDo script PUTs newer dates/descriptions into already-open tasks — no stale alerts if HR re-uploads an updated Gov dump.) | KSA compliance fields live (HR-GATE-0 closed). Muqeem dump delivery is separate (HR-OPS-1); the alert/ToDo infra does NOT require populated dates to function — it just produces 0 cards/to-dos until dates actually exist in the Employee rows. (Verified: 64 active employees, 0 dates pre-populated today 2026-09-20, so all cards correctly show 0.) | HR-OPS-4 / HR-OPS-5 | **CLOSED 2026-09-20.** Deploy script: `ERPNext/scripts/hr/deploy_hr_compliance_alerts.py` (sub-commands: `deploy_notifications`, `deploy_todo_scheduler`, `deploy_workspace`, `all`). Live audit confirmed: 6 Notification docs → 6/6, 1 Server Script (Scheduler Event Daily disabled=0) matching site convention, 6 Number Cards (Iqama OVERDUE/0-30/30-90, Passport OVERDUE, Open Expiry ToDos total, High Priority Expiry ToDos), SIG HR Workspace content 32 blocks (up from 17), 0 missing in NC/shortcut child tables. Re-runnable: `--yes` idempotently puts the same payload (update=true), so schema corrections can be shipped by re-running with the same command. |

## 6B. Deployment loops — the per-module / per-feature playbook

**Purpose (owner direction, 2026-09-20):** every module or feature deploys through the same
repeatable loop, so the next ERP deployment (new company, new instance) is a fill-in-the-blanks
exercise instead of a rediscovery. Each loop is one pass of the seven stages below; its gate
closes only when the stage-7 evidence exists. Lessons learned on a live build go back into the
stage rules — the loop improves, it never forks.

### 6B.0 — The generic loop (seven stages) — the rules each department loop runs

**1. REGISTER** — name the module/feature, its audience, and its gate in this plan before
building. List the exact artifacts: Custom Fields, Roles, Custom DocPerm rows, Pages, Reports,
Workspaces, Server Scripts, Schedulers. Add the access baseline: intended user/role audiences,
governing Role Profiles, User Permissions, affected DocTypes and their linked/child DocTypes,
Report roles/reference DocTypes, and Page/Workspace roles. Record current permission rows before
editing anything. If a needed artifact touches money movement, name who submits.

**2. SANDBOX RULES** — the Server Script / REST constraints that cost hours when relearned:
- No `import` statements; `json` is a global (loads/dumps); `frappe.db.sql` is NOT exposed (403).
- No backslash escapes inside script strings — use `Chr(10)`-style or concatenation.
- The doc-event field is **`doctype_event`**; an `event` key is silently ignored (defaults to
  Before Insert). Always read back after deploy.
- Bare `return` does not serialize — set `frappe.response['message']` explicitly.
- `frappe.utils.now_datetime` may be missing — try/except, fall back to the row's auto
  `creation`; Small Text fields cannot be cleared by REST PUT (`''` and `null` both ignored).
- A bare PUT on Document Naming Settings saves fields **without syncing** the Series table;
  Series is a bare table — only a Server Script `frappe.db.set_value(...,
  update_modified=False)` reaches it.
- Submission-time hooks run in the **submitting user's permissions** — grants on integration
  doctypes (e.g. Zatca Transactions create) must cover every role that will submit.
- **Race rule**: background jobs can overwrite fields a hook just set — self-healing daily
  watchers re-apply the intended state, proven by read-back or honestly flagged unproven.

**3. FIELD-FIRST ORDERING** — deploy Custom Fields (and child doctypes, and
`allow_on_submit` flags) **before** the scripts and permission rows that reference them;
unknown fields are silently dropped, and a missing target fails the save mid-run
(`LinkValidationError: Could not find <target>`). A REST PUT that returns 200 may still not
have applied — **verify every write by read-back**, never by status code; the post-save
redirect can return a misleading 404 "DocType URL not found" while the change applied.

**4. LINK (UI wiring)** — a workspace renders from its **content blocks**, not from the child
tables alone: a shortcut in the child table without a matching content block renders nothing.
- Workspace `content` must be assigned as a **list** in Server Scripts (a JSON string fails
  "Content data shoud be a list"); via REST PUT it goes as the JSON-encoded string.
- Visibility = public + **roles whitelist**: empty roles = everyone; non-empty = those roles
  only. Whitelist per audience (see Loop 01), never one global list.
- **Module Profiles are retired** on this site: they block whole modules regardless of roles and
  stamp `block_modules` onto user records that survive profile removal — clearing the profile is
  not enough; clear each user's list too. Grant roles, never sidebar blocks.
- One workspace per audience-job; one clear default action per shortcut group (dedupe the
  duplicates before anything else — the Stock Value pair and the four dispatch entry points were
  the worked example).

**5. GRANT (role mechanics)** — in Frappe v15, any `Custom DocPerm` rows for a DocType replace
the standard permission list in metadata; a sparse custom row can therefore remove access from
every standard role. Snapshot standard + custom rows and preserve the complete intended effective
role/ptype matrix when custom rows are required. Do not delete parent-bound rows without first
preserving the whole intended set. Check link/child DocType read and field permlevels, report roles
and reference-DocType ptypes, User Permissions, and Page/Workspace audiences separately. Role
profiles **strip direct user-level roles on every save** — grant on the role profile first (when it
is person-dedicated), then the user; for shared profiles create a dedicated profile per person
(`SIG Coordinator`, `SIG PM` pattern). Assign permissions by role, attribute actions by person
(per-person API keys; the payload's operator field carries the field worker either way).

**6. PROVE** — complete [§6B.0a](#permission-regression-mandate) for every change, including
print/template-only edits. Run the real UI path as a representative operating role, not only as Administrator.
Open the route, load/select linked masters and defaults, and exercise the required action without
submitting or persisting business data unless authorized. Test Arabic/RTL where that audience uses
it. Then read back affected role/profile, DocType, Report, Page, and Workspace permissions; compare
the effective before/after matrix with the declared change. Any unexpected removed access blocks
closeout. Compute per-user visibility from single-doc reads (list endpoints omit child tables). A
REST PUT 200 with a `Page`/`Workspace` child write may still need the **server-script save path**
(`ignore_permissions` + commit) — Page edits are Administrator-blocked over REST ("Only
Administrator can edit"); flip `standard='No'` first if a page refuses role changes.

**7. CLOSE** — mark the gate with the read-back evidence and permission diff; record representative
role, route, linked-record selection/default behavior, and operation tested; update the version
line; cross-link the master register. Any untested persona or browser/language path stays explicitly
open. Anything learned the hard way becomes a bullet in stage 2 or the failure table below — that
is how the loop pays for the next deployment.

<a id="permission-regression-mandate"></a>

### 6B.0a — Mandatory permission acceptance for every change

**Owner mandate, 2026-09-29: permissions are part of every feature.** Apply this to code,
Jinja/print/tax templates, Client/Server Scripts, form fields/defaults, translation/interface
edits, DocType JSON, fixtures, patches, migrations, app upgrades and role/profile changes.
Follow learning-loop gate F for the procedure. This is a required acceptance checklist; no
automated deployment blocker is claimed to exist merely because this section was written.

**Simple rule:** check the basic access baseline for every audience below after every change;
run the complete workflow for each affected audience. Shared code, permission writers, profile
sync or migrations affect every audience they touch. For an unaffected workflow, record the
reason it is outside the behavioral test scope; never silently omit a role. Resolve each named
person's live User, Role Profile, actual roles, language, Company/Employee/Warehouse restrictions
and enabled status first. Profile names and role names are different; historical assignments
below are test targets to verify, not authority to overwrite today's assignments.

| Audience / known representative | Required workflow and dependent access | Boundary that must remain intact |
|---|---|---|
| Finance User / Accounts User — Baligh (`baligh.hamdi@sigtele.com`) | Normal Finance menu → Sales Invoices → New; default `Sales Taxes and Charges Template` load; explicit template search/select/read; Customer, linked Address/Contact, Item, UOM, Account, bank and payment-term lookups actually used by the form; tax-row calculation; applicable print preview. Check GL, Trial Balance, P&L, Balance Sheet, AR/AP and intended report/export access. | Grant only the needed dependency ptypes; template read does not imply template edit or extra transaction/approval rights. Arabic fresh-form test is mandatory. |
| Finance Manager — humaira / safwacc; actual Accounts Manager and other held roles | Finance Page/menu and permitted finance forms/reports, linked masters, intended approval controls, retained Field Ops/coordinator access. | Preserve existing authorized finance actions; do not infer powers from the profile label. |
| Warehouse User / Warehouse Manager; Stock User / Stock Manager — Ramzan (`m.ramzan@sigtele.com`) and Tahir | Warehouse menu, MR/dispatch workbench and `SIG Dispatch Operation` read/report; Purchase Receipt review/approval path and its actual Supplier/Company Address (including reported `المملكة العربية السعودية-Billing`); Item/UOM/Warehouse/Project/Site links; Employee recipient other than self on dispatch. Test applicable voucher previews. | Read dependencies must not add unauthorized stock posting or approval rights. Preserve Tahir's SAR 20,000 PO limit; test the boundary and rejection above it in a non-posting test environment. |
| Operations Admin — Hamid; `SIG Finance Viewer`, `SIG PO Limited 50k`, actual purchasing roles | Purchasing forms and Supplier/Address/Item/UOM links; operational menus and finance read/print/export as intended. | Finance remains read-only; Hamid's SAR 50,000 PO limit remains enforced. Template repair must not grant Accounts User/Manager or finance submit as a shortcut. |
| `SIG PM`, `SIG Coordinator`, `SIG Stock Ops`, `SIG Ops Coordinator` — abdul.raheem, obed, arshad, gulzaar, imran, s.ilyas as currently assigned | Project Progress, Site/Visit/Cycle and evidence links; intended Field Ops events and `SIG PC Clearance` Journal Entry draft path; retained warehouse/operations navigation for the relevant profile. | PC clearance remains draft-only; no finance submit. Preserve per-person attribution and permitted company/site scope. |
| HR User / HR Manager and the actual HR profile — `hr@sigtele.com` or current named owner | HR workspace, authorized Employee records, attendance/requests, compliance report and ToDo links; report filters and intended actions. | Employee/private HR scope remains restricted; warehouse recipient fixes must not grant broad HR record access. |
| Employee / My Work; read-only audiences including `SIG Stock Viewer`, `SIG Finance Viewer` | Intended Home/My Work and permitted reports/records; each module's normal menu entry. | Own-record restrictions and viewer-only boundaries remain. No new create/write/submit, cross-company or other-employee access. |
| Integration identities | Existing authorized API workflow under its actual identity and dependency permissions, whenever its path is affected. | Integration/admin success never substitutes for any human-user row above; preserve per-person identity and existing integration scope. |

**Five required checks, recorded with every change:**

1. **Before:** snapshot full standard/custom DocPerm matrices, affected User/Profile roles,
   User Permissions, field permlevels/link restrictions, Page/Workspace/Report audiences and
   report reference-DocType permissions. Compare intended minimum access as well as the baseline:
   an unchanged but already-broken baseline is a FAIL, not a pass.
2. **Source:** identify every writer of those settings (app setup, fixtures, migrations,
   permission/profile sync and deploy scripts). Inspect new template `get_doc`/lookup calls,
   default setters and form hooks for newly required dependencies. A changed template can expose
   an existing missing permission without deleting any role. Do not claim revocation without
   the before/after evidence. Store approved fixes in the owning version-controlled source,
   preserving the full intended matrix; prove a second setup/migration run keeps the same matrix
   in staging/test. A live-only repair remains provisional until its durable source is recorded.
3. **After:** compare effective access for all registered audiences, including both required
   rights and forbidden powers. Any undeclared grant/removal fails. Verify profile-managed roles
   survive the normal User/Profile save path in staging/test. Refresh affected permission metadata
   through the supported mechanism after a repair; refreshing alone does not create a missing grant.
4. **As the user:** verify actual session identity, then cold-load from the main menu in a fresh
   authenticated session. Open a brand-new form, let default/onload requests settle, select and
   read the linked records, change the relevant Customer/Supplier/template and check dependent
   rows. Test changed print/preview paths under the same user. Reload and repeat from the menu.
   Check permission dialogs, failed requests and console errors. A prefilled `vat - SIG`, working
   Customer field, cached form, or clean first screenshot is not sufficient. Cover Arabic/RTL
   and English when used by the affected audiences. Do not save/submit production transactions
   merely to test; verify write/approval paths in staging or an explicitly authorized workflow,
   and leave any unexercised part NOT TESTED.
5. **Close:** evidence row = change/commit + site revision + time + user + actual roles/profile +
   language + menu/route + dependency names + expected/actual behavior + permission diff +
   screenshot/log reference + PASS/FAIL/NOT TESTED + remaining owner/action. A required FAIL or
   NOT TESTED blocks "fixed", "verified", and release acceptance. On failure, repair/rollback
   the scoped change and repeat the failed path plus its related dependencies. Keep the user
   incident open until its exact reproducer passes.

**Permanent regression cases:** Baligh's Sales Taxes and Charges Template denial; Ramzan's
`SIG Dispatch Operation` denial and Purchase Receipt Address denial; Tahir's cross-employee
dispatch-recipient restriction and SAR 20,000 cap; Hamid's read-only finance and SAR 50,000 cap;
hidden module/Page/report access; report export ptypes; Role Profile role loss; sparse Custom
DocPerm shadowing of standard roles. These cases stay in the checklist after a repair.

**Current outcome, 2026-09-29 21:10:** Baligh's original template denial is **PASS / REPAIRED**.
Added read-only template access for Accounts User, preserved all eight original rules, and
verified two new Arabic invoice forms, explicit template lookup/read and customer/address loading
as Baligh. No invoice was saved/submitted; other personas and transaction submission are not
certified by this result. See [repair evidence](finance_tax_template_access_verification_20260929.md).
Run `ERPNext/scripts/repair_finance_tax_template_access.ps1 -Check` after relevant changes; it
fails on a missing or excessive target grant. This check is available locally, not installed as
an automatic Cloud deployment hook. Fresh-form user verification remains required.

**Failure table (exact message → cause → fix):**

| Message | Cause | Fix |
|---|---|---|
| `ImportError: __import__ not found` | `import` statement in a Server Script | use the sandbox globals (`json` is preloaded) |
| `Content data shoud be a list` (frappe typo) | Workspace `content` assigned as a string | assign the parsed list (Server Script) or the JSON-encoded string (REST PUT) |
| `DocType URL not found` on Workspace PUT | post-save redirect artifact **or** content-as-string | read back to see if it applied; if the content is a list in a Server Script, the save path differs |
| `Only Administrator can edit` | editing a `standard` Page/Workspace over REST | Server Script `doc.save(ignore_permissions=True)` after flipping `standard='No'` |
| `Unknown column 'delist'/'modified' in WHERE/ORDER BY` | bare table or schema drift | check the live columns first, never assume |
| `KeyError: 'data'` after `frappe.client.delete` | delete returns `{'message': …}`, not data | don't parse `.data` on callbacks |
| stale read-back after a 200 PUT | Small Text clearing is ignored; CDN/session caching | verify with a cache-busted read; hard fields may need desk-side action |
| `getaddrinfo failed` / intermittent wrong-host 404s | network flake on this machine | retry loop with backoff on every call; final read-back decides the outcome |
| `UpdateAfterSubmitError: Not allowed to change <field>` | field lacks `allow_on_submit` | set `allow_on_submit=1` on the field (and child fields) before the write |
| `LinkValidationError: Could not find <target>` | link target missing at save | create/rename targets before the save; fix ordering (field-first, doc-first) |
| `Not Permitted` for a linked master while entering a transaction | operating role lacks read on a Link/default/child DocType; transaction create permission does not imply linked-master access | identify the exact target DocType and grant only the minimum required read; test that link/default as the representative role |
| users lose access after adding one custom DocPerm row | Frappe v15 replaces the standard permission list with the DocType's Custom DocPerm rows | restore the complete intended matrix to Custom DocPerm; compare all roles/ptypes before and after (learning-loop 297) |
| direct role addition disappears after a User save | Role Profile repopulates and replaces the user's role table | update the governing Role Profile or create an appropriate dedicated profile, then re-read held roles |
| `Could not find suitable Destination Bench` (`press.api.site.update`) | the new bench is not ready yet, or the site is already on it | poll `check_for_updates` until `update_available` is true; never assume (learning-loop 272) |
| live test still hits old code after "build Success" | the bench is built but the site was not moved onto it, or the restart is unfinished | `site.update`, then several stable `Active` polls, then a behaviour probe (273) |
| `ParserError: Unknown string format: today` on a dashboard load | Number Card `<`/`Between` filter with free-text relative date | `dynamic_filters_json` with `frappe.datetime.*`, ranges as two rows (282) |
| `TypeError: _fail() got multiple values for argument 'reason'` | a helper's first parameter shares a name with a keyword the caller passes | rename the parameter; add a refusal-path regression test (284) |
| `NEW_VOUCHER_ALREADY_USED` on a test rerun | a voucher/number is never reused, even from a cancelled document | fresh identifier per run (277) |
| ERPNext MR status stuck on `Pending` while `per_ordered` is 100 | `set_status()` evaluated a stale in-memory document | reload the document before `set_status()` (278) |
| `UnicodeEncodeError: 'charmap' codec` printing a warehouse name | Windows console is cp1252 | `PYTHONIOENCODING=utf-8`, `ensure_ascii=True` (276) |
| disabled employee logins show `enabled=1` after an unrelated Employee edit (17 users, 2026-10-06) | saving an **Active Employee that has `user_id`** re-enables the linked User (ERPNext/HRMS Employee → User update); a REST PUT of one custom field was enough | find them by `Version` (`enabled: 0 -> True` in the edit window) and re-disable with read-back (`scripts/hr/revert_user_reenable_20261006.mjs`); treat **every** Employee write (REST, Muqeem sync, imports, onboarding backfill) as a possible User-enable and run `scripts/perm_snapshot.mjs` before/after |
| a "new" custody ledger duplicates one that already has postings (Dahlan 13234, Mohsin 13233) | pre-check searched `account_number like 1322%` and missed the 5-digit legacy children | search the whole `1322` subtree by **name in both languages** before creating; enforced by `sig_hr_create_custody_account` (refuses on any plausible match) |
| `NameError: name '<x>' is not defined` inside a Server Script helper | `safe_exec` gives helpers no access to top-level names **or to other helper functions** | pass lists/functions in as arguments; keep helpers self-contained |
| `AttributeError: module has no attribute 'get_roles'` in a Server Script | `frappe.get_roles` is not exposed in the sandbox | `frappe.get_all("Has Role", filters={"parent": frappe.session.user, "parenttype": "User"}, pluck="role")` |
| a Number Card check returns the table total instead of its count | `get_result(..., filters='[]')` replaces the card's own filters | verify with `filters=<card.filters_json>`; compare with a direct `get_count` |
| `SIG HR Open Expiry ToDos` always 0 | `description like "[Iqama]%,[Passport]%,[Work Permit]%"` is one literal pattern, and no expiry ToDos exist until the Muqeem sync runs | rebuild as one row per pattern (or a reference-based filter) when HR-5 lands; the HR workbench uses "My open tasks" meanwhile |
| a PowerShell 5.1 script with Arabic text fails with `Unexpected token` / invalid regex range | `.ps1` without a UTF-8 BOM is read as ANSI | save `.ps1` files containing non-ASCII as UTF-8 **with BOM** |
| `SyntaxError: invalid non-printable character U+FEFF` on `hooks.py` (or any Python/JSON source) | `Set-Content -Encoding UTF8` in Windows PowerShell 5.1 prepends a BOM | the reverse of the row above: `.ps1` needs the BOM, Python/JSON/JS must not have one - write them with `UTF8Encoding($false)` and scan changed files for `EF BB BF` before committing |
| users get "not permitted" after a workspace is replaced by a Page | the workspace was open to all (empty roles) but the Page is role-limited; a redirect sent everyone to the Page | gate the redirect on the Page's roles (`roleAny`), keep the native workspace as fallback for the rest |
| Python `ValueError: unsupported format character '@'` building a Google `gviz` query | the query has a literal `%` (`like '%@c.us'`) and was `%`-formatted | concatenate the query; never `%`-format a string that contains SQL/gviz `%` |

### Loop 01 — Interface & Access (workspaces / pages / shortcuts / roles / users) — **executed 2026-09-19/20**

Filled example of the generic loop, live on this site. Department learnings on top of the
generic rules:

- REGISTER: audience map (admin, Hamid, PMs, coordinators, finance, warehouse, HR, employees),
  one workspace per audience-job, SAR 50k PO cap, project-progress open to office roles.
- LINK: SIG Projects carries the Project Progress shortcut (content block + child row); SIG
  Field Ops already did; duplicate SIG Warehouse Stock Value report deleted (keeper: `SIG Stock
  Value By Warehouse` + Distinct Items column).
- GRANT: module profiles removed from all 21 enabled users **and** every user's stale
  `block_modules` list cleared (19 users carried lists of 8–16 blocks — the real "no modules"
  cause); Hamid's finance-submit roles stripped from user and his dedicated `Operations Admin`
  profile; coordinator roles on the `SIG Stock Ops` / `Finance Manager` / `SIG Coordinator`
  profiles first, then users.
- PROVE: per-audience visibility computed from single-doc reads (admin 42, Hamid 41, PM 29,
  coordinators 29, finance 32, warehouse 29, HR 38, base employee 2 — Home + My Work); Hamid's
  finance submit structurally impossible (no submit-bearing role).
- CLOSE: recorded master §0.4 (access structure) + §0.1 truth-table row; gates EV-LIVE-1/
  EV-BACKFILL closed under §6A.14.

**Department lessons (Interface & Access):**

*2026-09-21 client-asset guard:* one supported loading path per script; changed assets receive a
new URL version; deployment proof is a fresh Desk tab showing the intended controls, the expected
asset once, and a clean console. A successful deployment or ordinary refresh alone is not proof.
- *2026-09-21 disposition guard:* a zero return quantity is not silently interpreted as a return.
  The operator must explicitly choose **Close as Consumed**; this writes no stock movement and
  leaves a reasoned, audited reopen path on the original Stock Entry for rare later corrections.
- An already-open Desk tab can retain the previous asset indefinitely; after deployment, reload the
  actual working tab (or open a fresh one) before judging the new control behavior.
- Kanban cards are rendered and replaced asynchronously. Intercept operational card actions with a
  single document-level capture listener, rather than a listener bound only to the cards present at
  initial setup. This prevents a later native ``+`` control from reopening Frappe's Assign/ToDo
  workflow on the curated dispatch board; prove it with a live click after deployment.
- Quick Issue tables need a stable visual reading order as well as compact labels. The 2026-09-21
  pass adds a row number, item description, ``MR Qty``, ``Left``, and a two-line ``Dispatch / Qty``
  header while leaving the dispatch payload unchanged. Future table changes must prove both a
  normal multi-line request and an added-item row, including description fallback and renumbering
  after removal, before deployment is accepted.
- If a form script and a list script both define the same operational dialog, update both copies (or
  consolidate them) before changing the cache-busted hook. A fresh asset URL can still display old
  behavior when a later-loaded duplicate function overrides the updated one; prove the final dialog,
  not just the downloaded asset, after every deployment.
- A successful Frappe Cloud pipeline is not the same as a ready site: the bench can briefly return
  ``503 Updating`` while the new image rolls out. Clear the site cache, wait for the site to recover,
  then verify from a fresh tab with the actual dialog open and console warnings/errors checked.
- Query Report SQL placeholders are server-required even when the UI filter is described as optional:
  an empty `filters={}` request against `%(from_date)s`/`%(to_date)s` raises `KeyError`. Give optional
  date filters safe broad defaults and test both the no-selection UI path and an explicit date range;
  do not accept a successful endpoint test that supplied keys the normal report page omitted.
- As-Built must remain dispatch-line-grain: aggregate-only output hides the Stock Entry/date that
  operators need for traceability. Derive Project through the linked Material Request Item first,
  then fall back to Stock Entry Detail, Purchase Order Item/header, and parent Stock Entry; expose
  Stock Entry, posting date, MR, PO number, project name, and issued/returned/custody/as-built qty.
- As-Built closure is a separate fact from quantity arithmetic: after the 2026-08-09 return
  cutoff, expose the ERP line's `custom_return_closed` (the WH Manage Return `1`/closed decision),
  the return disposition, and an explicit status. Count Return-sheet quantities through the ERP
  `custom_qty_returned` allocation; never infer closure merely because returned quantity is zero.
  Display the canonical agreement number (`Project.custom_agreement_no`, e.g. `10001274`) while
  retaining the internal `WO-YYYY-####` Project link for auditability.
- The live WH Return sheet currently has 89 confirmed post-cutoff lines (670.55 units in the
  inspected block), while ERP has 45 posted return receipts (626.18 units across all dates). The
  As-Built query therefore joins only receipts with an explicit `against STE-...` source and shows
  `Return Receipt Qty`; unlinked/over-cap/owner-authorized receipts remain exceptions rather than
  being guessed onto a DN line. Reconcile that exception set before claiming historical parity.
- Sidebar visibility and permissions are **two layers** — workspaces/module profiles/block lists
  drive what a user sees; roles drive what they can do. Fix both or neither works.
- Module profiles block whole modules regardless of roles **and stamp `block_modules` onto each
  user** — removing the profile later does not clear the stamps. Retired on this site; do not
  re-add.
- Role profiles strip direct user-level roles on every save — grant on the role profile first,
  then the user; shared profiles get a dedicated profile per person.
- Page roles: empty roles = admin-only; REST cannot edit a `standard` page — flip via Server
  Script, write roles through the script save.

**Queued next:** sigpc import of the same two modules (owner), As-Built endpoint opened to all
logged users if the app gates it by role, PO-1 cap approver role.

<a id="purchasing-loop"></a>
### Loop 02 — Purchasing (ERP-native intake deployed; workbook bridge optional) — **live source; operator acceptance open**

- SIG Warehouse `e56eb54` now provides the ERP-native Purchasing & Receiving interface and missing-price Purchase Receipt queue. The route fix is deployed; Administrator route rendering passed. The new flow uses native ERP Supplier, Item, Material Request, Purchase Order and Purchase Receipt records; Warehouse/Purchase role, linked-record defaults, draft creation, item/supplier creation and submission-boundary acceptance remain NOT TESTED.
- PO-STAGE-0/1 (pending-PO read + staged-lines acknowledgement) and PO-ENTRY-0 remain available. The old `WhErpImportPendingPOs.bas` / `WhErpReceiveMaterial.bas` workbook import is **not a prerequisite** for routine procurement in ERP and should not be treated as an active blocker. Import it only if an explicit, still-needed workbook bridge is approved.
- Department lessons: credit notes ride the CN cycle (never cancel a ZATCA-cleared invoice);
  `custom_delivery_date` is mandatory on CN submission (mapper leaves it empty); provisional
  suppliers are flagged and verification-gated before PI/payment. The older SAR 10,000
  purchase threshold is superseded for no-PO PR submission by the 29 October owner-approved
  SAR 20,000 policy and seven-day same-supplier control described in the [ERP integration master](../Automation%20DB/MASTER-ERP-INTEGRATION.md).
- Queued: RETRO-0/1 retrospective batches when the Purchase sheet export (with supplier and
  rate columns) lands; PO-1 cap approver role.

### Loop 03 — Finance (credit notes, banks, series, QR) — **core fixes executed; watch runs daily**

- Credit-note cycle closed for 128/129 (CNs 130/131 submitted and CLEARED); originals = Credit
  Note Issued, 0 outstanding.
- Bank accounts 4/4 (SNB 109/26605/23605 + Alinma with SNB-spelled beneficiary);
  `custom_beneficiary` field added; deterministic print pick.
- SINV series rewound to 97 (serial rule: credit notes draw the next number, no parking).
- Daily watcher re-applies the styled QR when the ZATCA race clobbers it.
- **Invoice cancellation and credit-note control - executed 2026-10-07.** A credit note is a Sales
  Invoice with `is_return=1` (ERPNext has no Credit Note DocType; the linked route is Create ->
  Return / Credit Note on the submitted invoice, a standalone one needs `custom_cn_ref`). Until
  further notice only Baligh (`baligh.hamdi@sigtele.com`), Mohammed (`mohammed.gain@sigtele.com`)
  and Administrator may **cancel Sales Invoices** or **create/submit credit notes**:
  - New role `SIG Invoice Reversal` + Sales Invoice Custom DocPerm row (`9rnv04j4uu`, read + cancel
    only); `cancel` removed from the Accounts Manager level-0 row (`6g5jmise9o`). Previously the
    four Accounts Manager holders could cancel and Baligh could not.
  - Granted through Role Profiles (never direct role edits): `ERP Admin` profile (Mohammed and the
    API user `9eskot9@gmail.com`) and new profile `Finance User + Invoice Reversal` for Baligh.
    Mahmoud stays on `Finance User` without the role.
  - Credit-note creation guard: Server Script `SIG Credit Note Restriction` (Sales Invoice, Before
    Validate; skips already-submitted returns). Mirror: `ERPNext/scripts/sig_si_credit_note_restriction.py`.
  - Snapshots, before/after and log: `ERPNext/backups/2026-10-07_invoice_reversal_restriction/`;
    fixtures `Custom_DocPerm`, `Role`, `Role_Profile` refreshed.
  - Persona result: API user (allowed) PASS - draft return created and deleted (burned
    `SIG-SINV-26-120`, cosmetic gap). Baligh, Mohammed, Mahmoud, Humaira, Mahmoud Kamal in a real
    session: **NOT TESTED**. Purchase Invoice, Journal Entry and Payment Entry cancellation are unchanged.
  - Durable source + release 2026-10-07: `SIG_Warehouse` patch `add_invoice_reversal_role_and_credit_note_guard`
    (idempotent; skips permission rows on sites without custom Sales Invoice rows), app commit `d6ec554`,
    rollback tag `pre-invoice-reversal-20261007` (`3ac69d8`), Cloud backup `6i0pv5daa2`, build `9i9eau8l3i`,
    site update `9p0jntvqlg` Active; patch logged once, perm rows / role holders / script read back identical
    to the pre-release live state. Real-session persona tests still **NOT TESTED**.
- Queued: purge list review (cancelled-doc residue), Muqeem sync run for live HR dates.

### Loop 04 — Evidence / Field Ops (RV80 + sigpc) — **closed**

- EvErpSend.bas per-person posting live in RV80 + sigpc; legacy Sync publication deactivated;
  catch-up replay 283 events / 0 errors; ERP at 3,739 events; watcher added for the styled-QR
  race (§0.2 settings). Legacy Excel-dashboard method retired.

### Loop 06 - Retrospective MR backfill and closure (WH -> ERP MR, no stock) - **staged 2026-09-21; G0 done, apply pending**

Filled example of the generic loop (6B.0) for a *metadata-only* retrospective import. Reuse for any future "history exists in WH, ERP has the stock but not the request" gap.

1. **REGISTER** - scope (MIR >= 543, 491 in WH219), artifacts (MR + MR items, `material_request`/`material_request_item` on Stock Entry Detail, MR dispatch fields, Return links), gate (G9 zero stock diff), no money movement, no submitter of stock documents.
2. **SANDBOX RULES** - link writer is a Server Script API: no `import`, no `frappe.db.sql`, `frappe.db.set_value(..., update_modified=False)`, explicit `frappe.response['message']`, `compile()` the script locally before deploy, deploy by partial PUT of `script` and byte-exact read-back. `material_request`/`material_request_item` are NOT `allow_on_submit` -> REST PUT fails with `UpdateAfterSubmitError`; the server-side write is the route. `custom_line_status` already has `CANCELLED` (no schema change for the G2 patch); `custom_sync_status` has no CLOSED value - closure lives in `custom_dispatch_stage`.
3. **FIELD-FIRST** - confirm every target field/option exists by reading Custom Field options live (done: see 9A.13) before any script or write.
4. **LINK** - MR item <-> Stock Entry Detail by DN voucher (`custom_source_id` `SIG-DN-DN26-####`, base voucher for `-1/-2`) and item code; UOM-normalise; a line with no matching ERP DN item is dropped from the MR and logged, never left dispatchable.
5. **GRANT** - writer runs under the API user (`mohammed.gain@sigtele.com`); a 403 means missing role on that doctype, not a bad key (run the harness preflight, never rotate the key).
6. **PROVE** - G3 canary (1 closed + 1 partial) with before/after stock diff (`g0_snapshot_9a13.py --diff`); re-post -> dedupe by `custom_external_source_id`; delete/cancel artifacts and confirm counts if the proof fails.
7. **CLOSE** - G9 diff vs G0, status report vs staging counts, version line, learning-loop rules 266-270.

**Risk-tier ordering (owner, 2026-09-21):** every stage runs Tier 1 (276 clean MIRs) -> Tier 2 (173: partial, open-as-built, return-linked) -> Tier 3 (42 disputed, always last: 1005/1006/1007, 783 + the 12 other duplicate skips, 708/924, 998/778/777, 1000/1010, 1016 and the 22 MIRs with unmatched ERP lines). Staging file is sorted by `risk_tier`; each batch stops and reports before the next tier begins.

**Resume discipline:** each apply script writes a checkpoint (`outputs/backup_9A13/state_<stage>.json`: done MIRs, errors) after every MIR; a killed run resumes from the state file (learning-loop rule 264).

**G0 (executed 2026-09-21 22:41):** `outputs/backup_9A13/g0_baseline_20260921_2241.json` - SLE 7,106; GL 38,508; Stock Entries 965 (787 submitted); Bin 1,156 rows, actual total 57,268.715; MR (Material Issue) 310 (298 PENDING, 8 DISPATCHED, 3 CLOSED, 1 PARTIAL); Stock Entry lines carrying an MR link 85. Diff tool: `scripts/hr/g0_snapshot_9a13.py --diff <baseline>`. Watch item: Bin `indented_qty` total is -14,538.95 today; the canary must show whether MR creation moves it (it is a request metric, not `actual_qty`); the pass test is SLE/GL/Bin actual/Stock Entry hashes unchanged.

### Loop 07 - Release to Frappe Cloud (app code + schema) - **run 7 times on 2026-09-23/24**

Filled example of the generic loop for shipping a change to a live app on `bench-38491`. Scripts in
`scripts/hr/`: `backup_site_9a14.py`, `deploy_sig_warehouse_bench.py`, `trigger_site_update_when_ready.py`,
`stable_then_test.py`, `probe_retro_ops_version.py`.
1. **REGISTER** - what ships, what schema it needs, which live behaviour it touches, the rollback target.
2. **RESTORE POINT** - on-demand site backup (`press.api.site.backup`, poll `backups`), git tag on the app repo, data snapshot (285).
3. **FIELD-FIRST** - create any Custom Field on the live site by scripted REST (dry run, `--yes`, read-back) *before* the code that reads it: the shared rollup runs on every dispatch, so code-before-field breaks live dispatching.
4. **COMMIT** - stage only your own files by name; read `git status` (other workstreams write to the same repo, 275); unit tests first.
5. **BUILD** - `deploy_sig_warehouse_bench.py` (dry run shows the release hash; `--yes` deploys). Status `Success` is only the bench (272).
6. **MOVE THE SITE** - poll `check_for_updates`; when `update_available`, confirm the only pending app is yours, then `site.update`.
7. **PROVE** - several stable `Active` polls (273), then a live test with one assertion only the new code passes, then verify against independent data. Record release hash, build id, site-update id, test result and the restore point in the plan.
Failure modes and fixes: 6B failure table (rows added 2026-09-24); rules 272-285 in `erpnext_learning_loop.md`.

### Loop 08 - SNB morning automation: speed and import safety - **speed shipped 2026-10-07; import-safety DEFERRED**

**Why:** on 2026-10-07 the morning run's capture took 19.5 min (Sheet hub re-read the whole tab per row) and the
import then hit the wrapper's 35-minute kill after creating 54 drafts but before the Sheet write-back - the next run
would have re-created all 54 (`push_snb_erp_plan.ps1` has no ERP-side duplicate check). Repaired the same day with
`scripts/snb/repair_import_writeback.mjs` (re-finds drafts by `custom_snb_idempotency_key` / exact `user_remark`,
writes the missing `erp_doc` links, reads back; record in `data/snb-browser-profile/learning/import_2026-10-07_killed_reconcile.json`).

**Shipped (each proven equivalent before going live; backups kept beside each file):**
- Hub `1.7.0`: beneficiary and `snb_rows` batches read once / write in bulk (2,471 -> 119 Sheet calls for 605
  beneficiaries); client sends one call per beneficiary tab. Measured live: capture 19m35s -> **1m24s**.
- `push_snb_erp_plan.ps1`: dropped the per-Payment-Entry `build_pe_remarks.mjs` call (re-downloaded the whole Sheet,
  46-193 s per PE; its text was discarded anyway) - POST bodies byte-identical, sample 72 s -> 4 s.
- `run_snb_agent.mjs`: row counts via `snb_rows_info` / `beneficiaries_info` instead of full downloads.
- Hub `1.8.0` (repo; **deploy pending** at time of writing): `snb_rows_erp` write-back read-once/bulk (330 -> 59
  calls) + `beneficiaries_info`.
- Offline proof harness: `scripts/snb/bench/hub_mock_compare.mjs` (old vs new handler, real data, cell-by-cell).

**DEFERRED by owner 2026-10-07 - import safety (fix 4):**
1. Write each `erp_doc` link back to the Sheet immediately after its draft is created (today all links are written
   in one call at the very end, so any interruption orphans every draft of the run).
2. Before creating a draft, check ERP for an existing one with the same SNB key - PE already carries
   `custom_snb_idempotency_key`; JE needs an equivalent key field (custom field on Journal Entry) first.
- *Reason deferred:* with capture ~1.5 min and the per-PE remark call gone, a run should finish far inside the
  35-minute limit.
- *Current mitigation:* if a run is ever killed during `import_erpnext`, run `repair_import_writeback.mjs`
  (dry-run first) **before** the next scheduled run.
- *Trigger to un-defer:* any killed/failed `import_erpnext` phase, or a daily batch large enough that import
  approaches ~15 minutes.

**Open owner decision (not a speed item):** since 2026-09-07 SNB Payment Entries reach ERP with **empty `remarks`**
(`custom_remarks = 1`, but the push still removes `remarks` - a leftover from the 2026-09-01 version). Restoring it =
keep the remark text the plan already builds.

### Loop 09 - HR workbench release and access integrity - **deployed 2026-10-07; persona/visual check open**

**What shipped (`sig_warehouse` 118103e, release `cc51hrjsr1`, build `fcd6td6nfn`, site update `ciqs62t47h`):**
new app-owned module **SIG HR**; standard Page **`hr-workbench`** (roles System Manager, HR Manager, HR User) on the
finance-workbench pattern (English `__()` + `translations/ar.csv`, RTL from `frappe.boot.lang`, role-aware cards,
filtered routes, live counts); `sig_hr.email_request` (HR-only WhatsApp request for official emails + hourly reply
collector that only fills `SIG Employee Onboarding.proposed_email`); 16 unit tests. Workspace `SIG HR` slimmed
47 -> 7 blocks / 17 -> 0 cards (records kept), roles unchanged. Field-first: 5 email fields on the onboarding DocType.

**Restore points:** Frappe Cloud backups `brcnkk7212` (2026-10-06) and `0atln5rar4` (pre-release); app tag
`pre-hr-workbench-20261007` = `d6ec554`; workspace snapshots in `ERPNext/backups/`.

**Four gates:** build Success -> `update_available` showed only `sig_warehouse d6ec5542 -> 118103ec` -> site update
Active, nothing pending -> probes PASS (Module Def, Page + roles, email preview = 16 recipients, collector, hourly job,
page JS served). Arabic rendering NOT TESTED (needs an Arabic browser session).

**Access integrity - the owner's "permissions get gobbled after module changes":** new tool
`ERPNext/scripts/perm_snapshot.mjs` (read-only) captures Page roles, Workspace roles/visibility, Report roles,
effective DocType permissions for 28 DocTypes, Role Profiles, every enabled user's roles / role profile / module
profile / `block_modules`, and Module Defs; `diff` exits 1 on any removal. Result for this release:
**REMOVED 0, ADDED 5** (module + page + its 3 roles). Mechanisms it guards against, from this and earlier loops:
1. **Migrate re-imports standard Page/Report JSON** - roles edited live on a standard Page are overwritten when that
   Page's JSON changes. Ship roles in the JSON (as here) and never touch other Pages' JSON in an unrelated release.
2. **Saving an Active Employee re-enables its User** - 17 deliberately disabled employee logins were switched on by
   a field backfill on 2026-10-06 (found by this snapshot, reverted, none had logged in). Any Employee write -
   onboarding backfill, Muqeem sync, imports - must be followed by a snapshot diff.
3. **Module Profiles stamp `block_modules` onto users** that survive profile removal (Loop 01).
4. **One Custom DocPerm row replaces the standard list** (learning-loop 297).
5. **Role Profile saves re-derive user roles** (learning-loop 306).
Standing rule: `perm_snapshot.mjs snap` before, `snap` + `diff` after **every** module/app/fixture/Employee-bulk change;
any REMOVED line blocks the release until explained.

**Follow-up release d79988a (`cpe0kicbg6`, build `1pjffve943`):** the owner found the sidebar's **SIG HR** still
opened the native workspace - the release had been proven by direct URL only (exactly the "prove what users click /
sidebar entry point" rule in `erp-cloud-release`). Fix: `sig-hr -> hr-workbench` added to the shared
`warehouse_workspace_redirect.js` map (same as `sig-warehouse`, `sig-accounting`), `?v=` bumped to `20261007-1`, and
the page got the Warehouse-style **"Original HR Workspace"** one-time escape button. Lesson: a new workbench is not
done until its sidebar slug is in the redirect map. The module-menu (☰) toggle on workbench pages stays **deferred**
(owner 2026-09-28, reconfirmed for HR 2026-10-07: workbench cards are a different structure from workspaces).

**Employee page release a2ef5ef (`cgpanp4r25`, build `7gsgbd7gdn`):** owner asked for "My Work" to become an
**Employee page** in workbench form. New standard Page `employee-workbench` (module SIG HR; roles Employee, Employee Self
Service, HR User, HR Manager, System Manager): the employee's own tasks (raise/track HR tickets, check-ins, employee record)
and own document expiry dates, resolved from `Employee.user_id`; every card is shown only if the user can read/create the
target; records stay limited by ERPNext permissions + the Employee User Permission. Leave / expense / advance / payslip
cards are deliberately **not** shown yet (0 records each) - add them when HR-2 / HR-3 / HR-4 go live.
- **Why the redirect is role-gated (access-integrity decision):** the native workspace `SIG - My Work` has **no role
  restriction (open to every user)**, but 7 of 21 enabled users (finance, warehouse, ops staff, `hr@`) hold neither
  `Employee` nor `Employee Self Service`. An ungated redirect would send them to a Page they cannot open. So
  `warehouse_workspace_redirect.js` redirects `sig-my-work -> employee-workbench` **only** for users with one of the
  Page's roles; everyone else stays on the native workspace (kept as the fallback; its stale "My Attendance ->
  Attendance (2 rows)" link now points at Employee Checkin (~5.3k) and the stale "Iqama status - not yet built" header
  is removed, both via `scripts/hr/fix_my_work_workspace.mjs`). Rule: **when a workspace open to all is replaced by a
  role-limited Page, gate the redirect on the Page's roles.**
- **Two HR entries in the sidebar:** the native ERPNext/HRMS `HR` workspace is restricted to System Manager (so only
  the admin sees both); HR User / HR Manager see **SIG HR** plus the Payroll group. Left as is - the sidebar mirrors
  roles, nothing to hide for staff. (Optional later: `is_hidden=1` on native `HR` to declutter the admin's sidebar.)
- **Observation, not changed:** the `Employee` role has read/write/create/**delete** on Employee Checkin; the
  Employee User Permission limits it to the user's own rows, but delete on attendance punches is broader than
  self-service needs - owner/Finance-HR to decide before employee logins are enabled.
- **PowerShell 5.1 trap hit again:** `Set-Content -Encoding UTF8` writes a **BOM**; on `hooks.py` it made Python fail
  to parse the file (`U+FEFF`). Caught before commit. Never edit Python/JSON source with `Set-Content -Encoding UTF8`;
  use `[IO.File]::WriteAllText(path, text, New-Object Text.UTF8Encoding $false)` and scan changed files for a BOM.

**Open (blocks "verified"):** persona matrix in a signed-in browser - HR User, HR Manager, Accounts User (must NOT see
the Page), base Employee; Arabic + English; sidebar entry point, not only the URL. Owner decisions: the 22 employees
with neither email nor mobile; the 4 "WhatsApp Sender" placeholders; whether HR edits re-enabling logins is acceptable.

### Loop 10 - SIG brand UI for workbenches: palette adopted, Employee page first - **deployed 2026-10-07; HR/Finance adoption queued**

**Where the palette comes from (the owner's "design md about the palette / business profile"):**
`outputs/SIG_Company_Profile_Handover/05_Handover_Docs/DESIGN_SYSTEM.md` (navy `#081C44`, blue `#1E7FFC`, cyan
`#22C7EE`, slate `#53657D`, pale `#EEF7FC`, dark field `#061634`) + `03_Design_Objects/SIG_ERP_header_sea_gradient.svg`
(the `#167CF4 -> #1DACEB -> #22C7EE` divider drawn as an ERP header asset) + the status tints already approved on the
tax invoice (`print_formats/sig_tax_invoice.html`: green `#1a7a3d`/`#eafaf0`, amber `#8a6d00`/`#fff8e1`,
red `#a4211f`/`#fdecec`). Canonical mapping recorded in `ERPNext/docs/ui_concepts/README.md` (main repo `1c734bb`),
with an HTML concept that links the shipped stylesheet: `employee_workbench_concept.html` (`?dir=rtl` for Arabic).

**What shipped (`sig_warehouse` aca50fa, release `c8c1edl5ks`, pipelines `cc702rcasc` + `boas9s5knl`, site update
`bup2lhob79`, backup `b9n4vtf9kb`, tag `pre-sig-brand-ui-20261007` = `a2ef5ef`):** `employee-workbench` restyled on the
company profile: navy gradient header with the sea-gradient divider (mirrored in RTL), cyan eyebrow, section signal
bars, and **cards whose colour carries meaning** - 4px inline-start accent + tinted icon chip: blue = action (raise
ticket), cyan = live data (check-ins), navy = record, slate = neutral, and document-expiry cards turn red/amber/green
from the employee's own dates (`expiryInfo` now returns the variant). Layout skeleton, routes, role gating,
translations unchanged. Verified live via `getpage`: served style contains `--sig-deep`/`sig-sea`/variants, served JS
has the variant logic; perm snapshot diff **REMOVED 0 / ADDED 0**.

**Decisions:** ERP is **light-mode only** (owner, 2026-10-07) - no dark-theme variants shipped. Employee page first;
HR and Finance workbenches adopt the same `--sig-*` token block in a later release. Colour is never the only carrier:
status text still states "Expired N days ago / N days left".

**Press-API rotation hit mid-release:** `sig_frappe_cloud_api.env` (SIG_-prefixed) began returning
AuthenticationError; the working pair is `frappe_cloud_press_api_2026_09_28.env` (`FRAPPE_CLOUD_API_KEY`/`SECRET`,
AGENTS.md) - exactly what `scripts/hr/_cloud_shim.py` already documents (it also adds the User-Agent Cloudflare needs
for Python clients). deploy/backup/migrate `.ps1` scripts still default to the stale Downloads path + stale creds -
pass `-SecretsPath` explicitly until their defaults are fixed.

**Deploy-sequence lessons (this release lost ~45 min to them):**
1. `press.api.site.migrate` returns `{}` and does **nothing** for app updates; the bare
   `press.api.site.update {name}` alternates between "site pending" and PermissionError. The working call is
   `press.api.site.update {name, skip_failing_patches: false, skip_backups: false}` - exactly what
   `scripts/hr/trigger_site_update_when_ready.py` does. **Always release through the proven `scripts/hr/` scripts.**
2. The state oracle is `press.api.site.check_for_updates` (per-app `current_hash` -> `next_hash`, `update_available`);
   `deploy_information.current_hash` flips when the release is *selected*, not when the bench is built - waiting on it
   green-lights too early.
3. Ground truth for page code: `frappe.desk.desk_page.getpage` returns the Page doc with `load_assets()` output -
   the `.js`/`.css` read from the app folder **at request time** (`style`/`script` response fields; DB fields are
   ignored). Page files are NOT under `/assets/` (those 404). This check caught the not-actually-deployed state.
4. `/api/resource/Pipeline/*` is not permitted for this token - build status is invisible; release instead by
   observable effect (check_for_updates + getpage).
5. `press.api.site.backup` returns `{}` on success - confirm via `press.api.site.backups` (first entry status Success).

**Benches release `c20ccb6` (release `fubf7pa4pe`, build `31bbc6on2g`, site update `4820064pmp`, backup
`7vomqon4vj`, tag `pre-sig-brand-benches-20261007`):** the same brand system applied to **hr-workbench** and
**finance-workbench** (CSS generated from the shipped employee stylesheet by prefix swap; variants mapped per
section: blue = daily work entries/actions, navy = statements/records/positions, cyan = live counts, amber =
drafts awaiting review and 90-day renewal queues, red = expired, slate = report lists and data-quality gaps).
The owner reported "not changed post hard refresh" mid-deploy — verified true at that moment (the bench build
was still running; getpage showed old code) and the same check showed all three pages serving the brand UI after
site update `4820064pmp`; perm diff **REMOVED 0 / ADDED 0**. Lesson: after a deploy trigger, the site stays on
the old code until `check_for_updates` flips `update_available` and the update runs (~10 min build) — check
`getpage` markers before telling anyone it is live, and say what IS live meanwhile (the employee page already was).
Also this release: `docs/erp_interface_structure.md` **created** — the interface authority referenced by the
master doc and plan registry since September existed only as a broken link until now.

**Warehouse release `9ff17d3` + the `SIG IH Position` permission incident (backup `1i3egcffi6`, tag
`pre-wh-brand-ui-20261007`):** the owner hit "User mohammed.gain@sigtele.com does not have doctype access via role
permission for document SIG IH Position" on the warehouse workbench and asked for the workbench to get the same
interface. Root cause: the site's permission baseline for ~31 core doctypes lives entirely in **Custom DocPerm rows**
(standard lists empty, so custom rows replace everything); `SIG IH Position`'s baseline carried only `SIG Stock
Viewer` read, while its report `SIG In-Hand Custody By Custodian` grants Stock Manager + Warehouse Manager too —
report allowed ≠ ref doctype readable. **Rule: a report's role set must be mirrored onto its ref doctype's custom
baseline.** Fixed live (3 custom rows: System Manager, Stock Manager, Warehouse Manager — read) **and** in
`fixtures/Custom_DocPerm.json` (323 → 327 rows, all four audiences with live names); `perm_snapshot.mjs` now covers
`SIG IH Position` + `Bin`. **Open:** the fixture and live sets had drifted in both directions before this fix
(323 fixture vs 100 live rows over 31 doctypes) — reconcile in a dedicated baseline pass.
The workbench itself got the brand UI (blue Start-work entries, amber dispatch queue, cyan live stock positions,
navy records/controlled operations, slate references), keeping its own grid names.
**Open:** visual check of the live pages by the owner (Ctrl+Shift+R; concept PNGs only exist locally - the
in-app browser full-page capture stitches duplicates on tall pages, use a tall viewport instead); persona matrix
(HR User, HR Manager, Accounts User, base Employee) still open from Loop 09; fixture↔live Custom DocPerm
reconciliation (above).

### Loop 05 — HR / People — **queued**

- 26 custom_* Employee fields and 6 expiry Notifications are live; live dates populate once HR
  runs `sync_muqeem --yes` against the monthly Muqeem dump (see §0.1 HR row).

**Deferred HR changes — recorded 2026-10-27, not implemented (owner deferred for now).** Sources:
[MASTER-HR-AUTOMATION.md](../Automation%20DB/MASTER-HR-AUTOMATION.md) (SIG Employee Onboarding design) and
[DAILY-OPS-AND-NEOSYS-SYNC.md](../Automation%20DB/DAILY-OPS-AND-NEOSYS-SYNC.md).

| # | Deferred item | Current state (2026-10-27) | Rule to follow when picked up |
|---|---|---|---|
| HR-D1 | SNB import: a `JE_EMPLOYEE` row with no employee ledger raises an HR ToDo, not a silent skip | 6 SNB rows (5 people) skipped with "No employee GL" inside an `ok` run | Exception to HR with count and SAR total; never a skip inside a green run |
| HR-D2 | Create the missing `132xxx` custody ledgers, linked by `Employee.custom_custody_account` | 39 employees have no custody ledger (MASTER-HR-AUTOMATION) | Use `sig_hr_create_custody_account`; search the whole `1322` subtree by name in both languages before creating (the duplicate guard); Finance owns the chart of accounts |
| HR-D3 | Link SNB beneficiaries to ledgers by IBAN, never by name | Name matching has mislinked before (Al Rajhi / Alinma, 2026-10-06) | Use the exact IBAN pattern in `scripts/snb/link_employee_gl_by_account.mjs`, one IBAN to one ledger |
| HR-D4 | Employee phone: enter verified `cell_number` (normalised) for the Field Reporter Map and WhatsApp | 24 employees without a mobile | HR supplies the number; never guessed from a name |
| HR-D5 | Placement of the employee ledger and phone link in the Google Sheet beneficiary tab | Not built; sheet column L holds `Employee: <name> \| <GL>` only | Write by IBAN/phone key; keep User `enabled=0` until the persona test passes |
| HR-D6 | Multi-bank employees: per-bank sub-ledgers on request | Mohammed Salah Algain has 3 done (132247/8/9) | Classification (petty cash vs expense) stays deferred |
| HR-D7 | Restore ERP's ability to decrypt Maytapi Settings and verify send/audit | Stock Entry rows `STE-2026-1057`–`1059` previously failed before provider call with an encryption-key error. On 28 October, a controlled ERP test send was accepted and recorded as Message Log `06i4o3e1i2`; the decryption failure is no longer reproducing, but its cause is unknown. Friday rows `STE-2026-1053`–`1056` were queued. | **Operationally recovered for the controlled send; no token rotation requested.** Preserve evidence and monitor the next legitimate send; if decryption fails again, capture the exact error and inspect the site's supported encryption-key configuration before changing credentials. Do not copy credentials into this plan/source. |
| HR-D8 | Confirm which employee bank account should receive company payments and petty cash | Inbox replies confirm Umar chose QPay ••0109 and Faizan Hanif chose Al Inma ••9000, one account for both purposes. Their existing Employee IBANs matched those accounts. Faizan's stale bank label was corrected from `NCBK` to `INMA`; Umar's `NCBK` label matches the existing QPay-linked IBAN. No account/IBAN was rewritten. The replies are in the WhatsApp-to-Sheet Inbox, not ERP Message Log. Zaheer has two Al Rajhi beneficiaries but no verified Employee mobile. | No resend. Build a permission-safe per-Employee bank-account relationship with explicit purpose flags instead of treating one Employee bank field as the preferred account for every flow. For Zaheer, first obtain and verify `Employee.cell_number`. Keep full account/IBAN data out of broadly readable fields. |
| HR-D9 | Employee bank-detail visibility and profile representation | Employee `bank_name`, `bank_ac_no`, and `iban` are permission level 0; full numbers were not written. Existing `custom_bank_beneficiary` is a display string, not a bank-account relationship. | Keep full account/IBAN data out of broadly readable Employee fields until an approved private storage/permission design is deployed and persona-tested. Use masked bank plus last-four references only where appropriate; retain Employee-to-custody-ledger as the petty-cash link. |
| HR-D10 | Finish the missing custody-ledger reconciliation and read-back | Existing live links for Arslan (`132252`), Mahmoud Kamal (`132253`), Arshad (`132254`) and Sagheer (`132255`) are confirmed. Sagheer's Arabic Employee name and editable Account `account_name` label were corrected; Am `pc_employee_accounts` now includes `132255`. The Account's immutable link name still contains the old Muneeb text because Account has `allow_rename=0`; its link may still display that label. Piran's Employee and one active SNB beneficiary match by full English name and existing bank details, but no Piran-named `1322` Account exists in the company chart. “Muhammad Tayyab Allah Ditta” is a different person, not a Piran ledger. | Finance to choose a safe Account-label migration (replacement/move of any draft references, then relink Employee) or retain the current key; do not bypass Account's rename restriction or edit primary keys directly. Do not create/link Piran's account until Finance approves the new custody ledger and the duplicate guard's trigger is diagnosed. Keep uncertain Abdulqadir, Saddam and Imran identities unmapped until verified. Mohammed Algain stays deferred. |
| HR-D11 | Start Faizan Rasheed's pre-Employee onboarding without linking him to Faizan Hanif | `SIG PC Sender Staging` `966503084408` is Staged and unlinked; its 11 transaction records were reconciled (9 Needs Review, 2 Closed; 10 Pending, 1 Archived) and were not reassigned. Faizan Hanif's Employee phone ends `0621`. Candidate Intake is local commit `a552603` on `codex/candidate-intake-maytapi` (`ERPNext/_release_candidate_intake_20261028`), not pushed/deployed. The latest Inbox search found no Rasheed text reply. No live intake case or consent message exists. | Keep Rasheed separate from Hanif. Complete Candidate Intake's privacy/permission and staging acceptance, then create a manager-owned intake and send the neutral trilingual consent request. Do not create an Employee, User, salary assignment or ledger before consent and HR review. Do not reassign the historic sender receipts. |

Related, outside HR: the SNB payroll-fee route (`JE_PAYROLL_FEE`) now posts to the operating-hold account as a draft (2026-10-27). Finance should confirm that account is the right one.


## 6C. Deployment learnings (Frappe Cloud / Press API) — recorded 2026-09-22

Kept here because they cost real time to (re)discover once already, and nothing else in the repo recorded them.

### 6C.1 A bench deploy is not a site update

`press.api.bench.deploy` (used by `scripts/deploy_sig_whatsapp_bench.ps1`) builds a new release and points the **release group** (`bench-38491`) at it. It does **not** push that code onto an already-provisioned **site**. A site only picks up new app code when it is separately **updated** — pull the new commit onto that site's bench, migrate, restart. These are two different objects (release group vs. site) with two different Press API surfaces, and nothing in the API response for `deploy` says whether any site actually moved.

`press.api.site.migrate` (used by `scripts/migrate_neosys_site.ps1`) is **schema migration only** (`bench migrate`) against whatever app code is *already* on that site's bench. It is not a code-pull step. Calling it after a deploy is not sufficient on its own, and — the trap that cost ~40 minutes on 2026-09-22 — it returns HTTP 200 and "Success" in the job log every time, even when the site is still running old code, because there is nothing new for a schema-only migrate to do.

`press.api.bench.deploy_information`'s `current_hash` field reports the **release group's** pointer, not the specific site's actual deployed state. It can show the latest commit while the site itself is still behind — do not use it as proof a site is current.

### 6C.2 How to tell if a site actually needs updating, and how to trigger it

- **Check, don't assume:** the Frappe Cloud dashboard → the site → **Updates** tab shows an "Updates Available" panel with **Current Version → Next Version** (commit hashes) per app when the site is behind. If that panel is empty, the site is current; if it lists a app with a different Next Version, it is not, regardless of what the deploy API reported.
- **The fix is "Update Now"** on that same panel (dashboard only in this session — no equivalent endpoint was found in the `press.api.*` surface reachable with the `SIG_FRAPPE_CLOUD_API_KEY` token; `press.api.bench.restart`, `press.api.site.restart` and `press.api.bench.reload_nginx` all 403/417 with that key). It runs the real backup → pull → migrate → restart cycle; the site shows **Active → Pending/Updating** and briefly 503s (`SessionStopped`) while it does. A plain module addition (new `.py` file with no new Page/DocType) has, in every other case in this session, propagated within 1-3 minutes of a deploy alone — a stuck "No module named" error more than ~10 minutes after a deploy is the signal to check the Updates tab rather than keep re-running `migrate`.
- **`press.api.client.get_list`** (doctype `Agent Job`, filters `{"site": "neosys.frappe.cloud"}`, fields `name,job_type,status,creation,end`) is not in `ai_agent_credentials.md` but works with the same token and is the only way found in this session to read Frappe Cloud's own job history (Pull / Migrate / Backup / Clear Cache) for a site — useful for diagnosing exactly this kind of stuck deploy without dashboard access. Per-job detail fields (`data`, `request_path`, etc.) are permission-blocked even though the list is not.
- **Sequence that works, going forward:** `bench.deploy` (build the release) → check the site's Updates tab for a pending Next Version → **Update Now** if one exists → re-verify the actual API endpoint responds before assuming success from any Press API status field alone.

### 6C.3 Server Scripts run sandboxed — no `import`

Restated from 6A.15d because it is easy to reintroduce: a Frappe **Server Script** (`script_type = Scheduler Event` or `API`) executes inside `safe_exec`, with `frappe` already in scope. A literal `import frappe` line at the top is not a no-op — it raises `ImportError: __import__ not found` and silently fails the job every run (`sig_field_ops_daily` did this nightly for at least a week before being noticed). A real bench-app Python module (`sig_warehouse/sig_warehouse/*.py`) has no such restriction and imports normally.

## 7. Risk register

| # | Risk | Likelihood | Impact | Control |
|---|---|---|---|---|
| R1 | Formal Phase 2 notification evidence is not archived | Low | Weak compliance file despite working integration | Owner accepted Phase 2 deployment; Finance/tax reviewer archives the notice when retrieved |
| R2 | Stale evidence reused after a site or credential change | High | False compliance confidence | Section 1.2 corrections; re-run rule 3 in section 4 |
| R3 | PO/PR history imported from page-derived captures without child-table proof | Low | Wrong payables and stock valuation | Reduced to the 2026 subset only: 38 receipts with warehouse proven per voucher from the Stock Ledger, and pre-2026 drafts deleted |
| R4 | Credentials in a markdown file leak when the repository is shared | High | Full site compromise | Keep the repository private now; post-launch tasks 1.9–1.10 create scoped credentials, rotate the current pair and change the harness source |
| R5 | Certificate expires unnoticed | Medium | Invoicing stops | Named certificate owner and renewal calendar (B5); rehearsal in 3.7 |
| R6 | Legacy counts drift during the capture window | High | Silent data loss | Timestamp every inventory; reconcile deltas rather than overwriting |
| R7 | Test artifacts left submitted at cutover | Medium | Ledger contamination | Cancellation is approved; execute 3.11 and verify GL reversal before opening-balance acceptance |
| R8 | An app redeployment silently reverts a fix | Medium | Regression in cleared invoices | Release proof checklist; a proof test that matches the patch |
| R9 | A legacy Sales Invoice is transmitted to FATOORA as newly issued | **High until P6 ships** | Duplicate legal invoice; corrupted ICV/PIH chain | `custom_is_legacy_import` early-returns in both `generate_einvoice` and `enforce_b2b_clearance_on_submit`; acceptance test (a)–(d) in Stage 5.3E before the batch |
| R10 | Source exports taken at different times disagree | **Confirmed present** | Months never tie | P7: one frozen extraction timestamp for every workbook. `MAT-PRE-2026-00038` already demonstrates the drift |
| R11 | Duplicate 2026 receipts submitted from dry-run records | **Confirmed present** | Stock and payables overstated by SAR 33,300 | P5: delete `MAT-PRE-2026-00002` and `-00003` before any submission |
| R13 | Costing-method mismatch (Flexsoft Moving Average vs Neosys FIFO) | **Confirmed, being corrected** | Every stock issue on a mixed-rate item diverges, and it compounds | Stage 5.3F-0: switch to Moving Average, unset whole-number on `Nos`, re-value the 30 posted stock documents before importing further |
| R14 | Alignment entries routed to an Expense account | Medium | Migration artifacts enter P&L; monthly profit stops matching Flexsoft | Alignment posts to balance-sheet `1911`; only genuine business rounding goes to `5212` |
| R12 | A month is reopened after reconciliation | Medium | Silent divergence from the signed position | Freeze `acc_frozen_upto` and `stock_frozen_upto` at each month close; corrections go to the current open period (Stage 5.3G) |

---

## 8. Definition of done

The programme is complete when, and only when:

1. G1–G5 are closed with the evidence listed against each task.
2. A production B2B invoice and credit note have cleared on the live site with valid XML, hash,
   UUID, PIH chain and QR. A simplified invoice is required only if SIG performs B2C sales; otherwise
   record the B2B-only scope while retaining the already-passed simplified compliance checks.
3. The trial balance on the target site reconciles to the approved legacy opening position, and every
   month from January to the freeze month has been reconciled on all five control totals and frozen.
4. Daily work runs on named users under role profiles, with no shared Administrator use.
5. Certificate renewal, failed-submission monitoring, archive retrieval and rollback each have a
   named owner and a tested procedure.
6. Finance and the tax adviser have signed off in writing, with names and dates recorded.
7. No legacy or opening invoice reached ZATCA: `Zatca Transactions` contains no row created by the
   migration, and the ICV/PIH chain is continuous across the replay window.
8. The [mandatory permission acceptance matrix](#permission-regression-mandate) has evidence for
   the released changes: no required FAIL or NOT TESTED, with the named operating users' actual
   routes/defaults/links checked and approved access boundaries preserved.

---

## 8A. Next warehouse gate — partial dispatch and per-item cancellation (planned)

The current `DN_PARTIAL` sender can create a partial Material Issue, but it does not yet maintain an authoritative MR-line balance. Build the next gate as an **atomic ERP fulfilment endpoint** called only after the WH confirmation path has passed its normal physical checks. Do not alter RV80 confirmation or WH Out J/K formula-reference columns.

For every imported WH Out line, retain the ERP MR name, immutable `custom_source_line_id`, and WH row key. The endpoint receives one action per selected line: `ISSUE` with a DN number and quantity, or `CANCEL_REMAINDER` with a reason. It must lock/read the linked MR line and enforce `0 < issue_qty <= qty_remaining`; its idempotency key is the DN plus immutable source-line id, not a mutable Excel row number. For an issue, it creates/submits exactly one linked Material Issue Stock Entry, then increments `qty_issued`, recalculates `qty_remaining`, and sets the line `PARTIAL` or `COMPLETE`. For cancellation, it creates no stock movement: it increments `qty_cancelled` only against the unissued remainder, records the reason and actor/time, recalculates remaining, and sets the line `CANCELLED` only when remaining reaches zero. A line can therefore be partly issued and then have only its remaining quantity cancelled; no implicit reversal is permitted — a return/RN or approved reconciliation remains a separate transaction.

Store the balances and status on both the MIR intake line and the native MR Item (`custom_qty_issued`, `custom_qty_cancelled`, `custom_qty_remaining`, `custom_line_status`), plus an append-only fulfilment event/audit record that links MR line, WH row key, DN, Stock Entry when applicable, cancellation reason, actor and timestamp. The ERP transaction and balance update must commit together; WH marks its row only after the endpoint read-back succeeds. When every MR line is `COMPLETE` or `CANCELLED`, mark the MR fulfilment state `FULFILLED` or `CANCELLED`; retain `docstatus=1` for audit. The first implementation test must cover full issue, repeated partial issues, partial issue then cancellation of remainder, full cancellation without stock movement, duplicate POST, and attempted over-issue/cancel-after-completion.

## 9. Change control on this plan


Amend this plan by adding a dated entry below and updating the affected section in place. Do not
silently rewrite a closed gate.

| Date | Change | By |
|---|---|---|
| 2026-09-22 | **v4.15 addendum — asset capitalization proven, Site hub, Field Ops scheduler repaired, field visit feed live (F0-F2).** First stock-to-asset cycle proven live on `S-SHO-RM-42` (Asset Capitalization `ACC-ASC-2026-00001` → Asset `ACC-ASS-2026-00001` → Asset Movement `ACC-ASM-2026-00400`, issued to Asif); one Dispatch / Return dialog keyed on Item code deployed (`bd5ecd9`, `e7261e5`). Two-way SIG Site connections deployed (`2a770f5`, `deploy_site_connections.py`). `sig_field_ops_daily` repaired after failing nightly (`import frappe` in a sandboxed script). Visit feed confirmed inactive since 2026-09-13; group-message sheet confirmed healthy. See 6A.15b–d. | Owner / Technical execution |
| 2026-09-21 | **v4.15 — Finance owner decisions (P12 closed).** (1) Both crosswalk items are **aliases; the ERP names prevail**: `Telecommunications Towers Company Limited` → `Telecommunications Towers Company / Tawal` (SAR 16,818,960.00) and `شركة لجين الحواء الطبية` → `شركة لجين الدواء الطبية` (SAR 383,729.70); no ERP master is renamed and no legal-spelling research is needed. The four punctuation/suffix supplier variants follow the same rule. (2) The SAR 175.00 stock-adjustment pair (`MAT-RECO-2025-FIX-00006`) is remediated as a correcting entry in the open 2026 year; 2025 stays closed. (3) SAR 0.01/0.02 valuation residuals are expensed to the rounding account (5212) — no further remediation. | Owner |
| 2026-09-21 | **v4.15 — Finance migration PROVISIONALLY CLOSED (G5).** Owner assessment: transactions are aligned from Flexsoft year by year; the earlier 30–45 d G5 estimate (v3.0–v3.5, Sept 1–3) assumed an unbuilt pipeline and undecided AR/AP method and is superseded. Read-back of `outputs/migration_2024|2025|2026`: 2024 closed month-by-month through Dec (`month_close_2024-12.json`, Stage 5.3F pipeline); 2025 closed Jan–Dec (`month_close_2025-01..12.json`) and the full-year cumulative TB vs live Flexsoft is **MATCH — 166/168 accounts exact**, the two variances being the owner-approved pair `MAT-RECO-2025-FIX-00006` (SAR 175.00 on 5129/1341) plus a 0.02 halala valuation-rounding residual; 2026 replay artefacts exist through Aug (payment-link/JE-overlap reconciliations). Closure is **provisional** pending the Finance sign-off list in the next row; ZATCA full-history pilot stays optional. Not re-verified live in this pass: 2026 month closes Jan–Aug tie status, Jan-2024 remediation carry-over, and the 31-Dec-2025 opening AR 8,041,288.63 / AP 6,164 set. | Owner / Technical execution |
| 2026-09-21 | **v4.15 — Finance sign-off list (to close provisional → final).** (1) Sign the 2025 full-year TB MATCH; the SAR 175.00 stock-adjustment pair is remediated as a 2026 (open-year) correcting entry, and the SAR 0.02/0.01 valuation rounding residuals are expensed to rounding cost (owner: small roundings are cost, no further work); (2) confirm 2026 Jan–Aug month-close ties (five controls) and that the six-party crosswalk was applied (Tawal alias SAR 16.82M `Telecommunications Towers Company Limited` → `…Company / Tawal`; لجين SAR 383.7K الحواء vs الدواء — Finance names the legal spelling; if the 2026 replay already posted, this is a confirmation only); (3) review AR 8,041,288.63 / AP opening invoices and open items from 31-Dec-2025 by ageing, and the three held advances (SAR 875,889.93) allocated; (4) Stage 5.3G correction-pass register: list and approve/waive every deferred item (7 deferred PRs with supplier/UOM blockers, 3 zero-VAT receipts, 1 return); (5) confirm VAT returns for 2024–2026 periods agree to ERP VAT report; (6) confirm inventory 31-Dec-2025 SAR 5,725,006.11 = TB 134 and physical-count owner; (7) freeze migrated periods (period closing + role lock) and archive Flexsoft read-only access/backup; (8) confirm all migrated docs keep Flexsoft legacy names and attachments for the accounting firm; (9) forward-only rule: SNB feed, Tawal payments and petty cash post to ERP only from cutover; (10) FA register/useful-life sign-off (FA-GATE-1..3) before any depreciation run. | Owner / Technical execution |
| 2026-09-16 | **v4.06 — Stage 4 Jizan pilot ACTIVATED.** Created and accepted the explicit ERP-only opening baseline `SIG-WH-REC-مستودع جازان - SIG-00162` from the server-side ERP Bin snapshot (36 non-zero lines, 0 mismatches, SHA-256 `81f1644f31df950b5723df889d8c8226f1e930d42c844e1aa3bcce7ec7b3ce1c`), confirmed the legacy WH writer disabled, selected and attested `ERP_PRINT_ONLY` after the live `SIG Material Issue` print-format check, then marked the cutover READY and ACTIVE. No stock movement was created by this cutover run; the next DN counter remains `DN26-1035`. | Owner / Technical execution |
| 2026-09-16 | **v4.05 — Stage 5 initial deployment CLOSED.** The `SIG_Warehouse` bench release `ade138a` was deployed, the site pull and migration completed, cache was cleared, and the live read-only `sig_get_as_built` endpoint returned HTTP 200 with `result: ok`, 663 source documents and 4,285 source lines. No stock-writing endpoint or Stage 5 DocType migration was enabled; blind-count, advanced-custody and bulk-dispatch helpers remain deliberately non-writing and gated behind an accepted ACTIVE Stage 4 cutover. | Owner / Technical execution |
| 2026-09-16 | **v4.04 — As-Built non-match triage executed, no ERP writes.** Generated `WH_Stage5_AsBuilt_Triage_2026-09-13.xlsx` from the read-only acceptance JSON. It contains 1,102 non-match rows split into MISMATCH (115), SITE_ALLOCATION_REVIEW (474), EXCEPTION (126), WH_ONLY (360) and ERP_ONLY (27), with a recommended evidence owner/action and separate review sheets. The acceptance state remains **NOT ACCEPTED**; this is a review pack, not a correction or activation command. | Owner / Technical execution |
| 2026-09-16 | **v4.03 — Stage 5 As-Built acceptance pack generated read-only; not accepted yet.** Compared the frozen `WH_Closure_Package_2026.xlsx` (SHA-256 recorded in the JSON pack) with submitted ERP Stock Entry parent documents through 2026-09-13. Because the integration identity cannot list `Stock Entry Detail`, the tool used permitted parent reads and did not change permissions. Evidence: 3,599 site/item rows — 2,497 matches, 115 mismatches, 360 WH-only, 27 ERP-only, 474 explicit site-allocation-review rows (ERP quantity exists for the item but is not assigned to a site) and 126 exceptions (76 untagged ERP transfers; 50 WH allocation-over-issued). The pack is explicitly **NOT ACCEPTED**; every non-match remains a review/classification item before any Stage 4 warehouse activation. | Owner / Technical execution |
| 2026-09-16 | **v4.02 — Stage 5 initial implementation completed locally, not deployed.** Added the gated Stage 5 implementation slice to `sig_warehouse`: read-only `stage5_as_built.py` derives site/project consumption from submitted Stock Entry lines and Stage 3 return/custody allocations, excludes untagged warehouse transfers from site consumption, and reports exceptions; `stage5_counts.py` enforces blind payload/lifecycle/supervisor/recount rules and only builds a non-posting reconciliation payload; `stage5_custody.py` adds normalized condition/tracking identity, stable position keys and non-negative allocation checks; `stage5_bulk.py` adds one-warehouse/one-UOM validation and deterministic duplicate/conflict signatures without creating a second dispatch writer. Eleven pure tests pass, Python compilation passes. **No Stage 5 DocTypes, stock-writing endpoint or live deployment was performed:** Stage 4 controls are present, but no warehouse has an accepted ACTIVE cutover yet. Next gate is a read-only As-Built acceptance pack against frozen WH output, followed by explicit Stage 4 activation before count/custody/bulk writes are migrated. | Owner / Technical execution |
| 2026-09-16 | **v4.01 — WH↔ERP bridge proving complete for DN/TN/PR/RN; draft-only trial opened.** Live evidence: DN26-1030 → STE-2026-0832, TN26-0072 → STE-2026-0833, PR26-0081 → STE-2026-0834; all HTTP 200 with `created`, returned ERP names and `readback_ok=true`. The three proving drafts were deleted and verified 404; no submitted documents were touched. The server-side project guard, strict response acceptance, append-only debug logging, and MR `PARTIALLY_DISPATCHED`/`DISPATCHED` update were deployed. CR/BI proving is deferred. Next gate is one operational day with ERP documents left as drafts, followed by an owner decision before enabling direct submission. | Owner / Technical execution |
| 2026-09-16 | **v4.00 — Mgmt-module set read-audited clean; handoff to the next AI/session for the actual proving pack.** Owner asked to stage the mgmt-module set (the bigger, separate lane deferred after PO-STAGE-1 closed in v3.99) for testing, then close this session and hand to another AI. **What was done this session (inspection only, nothing imported or run yet):** checked all six staged-not-imported files (`TransferMgmt.bas`, `InMgmt.bas`, `ReturnMgmt.bas`, `BulkMgmt.bas`, `CorrectionMgmt.bas`, `WhErpSend.bas`, all dated 2026-09-15 ~01:22-01:23, plus the `WarehouseMgmt.bas` DN-hook call site) for the exact bug classes found in the PO-STAGE-1 modules earlier today: (1) module/Sub name collision (`Expected variable, not module`) — **none found**, checked every file; (2) hardcoded-wrong-field-index bugs — **structurally unlikely**: column resolution in `WhErpSend.bas` (`WhErpFindColByHeader_`/`WhErpSheetColumns_`) is header-name-driven (searches for "Item Code"/"Qty Request"/"Site ID" etc.), not hardcoded indices; (3) all five engine hook call sites (`WhErpSendSheetVoucher "TN"/"PR"/"RN"/"BI"/"CR", <voucher>, <sheet>`) verified wired correctly, each pulling the real voucher from its own Scripting.Dictionary (`BulkMgmt`'s key/value shape is inverted vs the other four - key=voucher there, value=voucher elsewhere - both checked correct); (4) `WarehouseMgmt.bas`'s DN hook (`WhErpSendConfirmedDispatch partialOnly, mirList, wsOut, wsOutAdd, 0, allConfirmedRowKeys`) matches the documented signature exactly. **One false alarm, corrected in the file:** `WhErpSend.bas` sends its POST params via the URL query string with an empty body, unlike every other sender module (body-encoded) — a first live test looked like proof this was broken (`"missing trans_type/trans_no/line_count"`), but that test used an invalid `line_count=0`; retesting properly (`line_count=1`, a real line) showed both patterns behave identically against the live `register_stock_entry` endpoint. Changed to body-encoded anyway for consistency with every other module (harmless, no functional difference) — the file's own comment originally overclaimed this as a "confirmed" bug and has been corrected to state what was actually verified. **Verdict: clean by inspection, same as the PO-STAGE-1 modules looked before they were actually run** — inspection caught zero of the three real bugs that testing found there (module collision, Received-vs-Pending field swap, `ExtractMessage_`/`JsonKey_` JSON bugs, missing PR-line UOM). Assume this set has equivalent undiscovered bugs until proven otherwise by execution, not by re-reading the code again. **The task for the next session:** import all six files together into the existing test copy `WHtest.xlsm` (`C:\Users\legen\Downloads\erp\dump\WHtest.xlsm`) — `WhErpSend.bas` FIRST, then the five engines (never the engines without the bridge — undefined-routine compile failure breaks every WH confirm operation, not just posting, per the master doc's explicit warning) — then run the copy-workbook proving pack: one real DN, one TN, one PR, one RN, one CR, plus a duplicate re-send of each (idempotency check), verifying `custom_row_key` reads back correctly on every one. Use the exact same method this session used on `WhErpImportPendingPOs`/`WhErpReceiveMaterial`: run each one for real, read the actual server response/journal/`debug.txt`, fix precisely what breaks, re-test — never assume clean from a code read. Only after a clean pass does W-4 weekly reconcile and then live `wh.xlsm` import become appropriate; neither has started. | Owner / Technical execution |
| 2026-09-16 | **v3.99 — PO-STAGE-1 CLOSED: full receive-first proving run passed end-to-end live.** Chain proven for real (not synthetic): `WhErpImportPendingPOs` staged the 2 real September lines → `HexGen` (new, folded into `WhErpReceiveMaterial.bas`, public `Sub HexGen()`) auto-fills the mandatory Supplier DN/Invoice ref with a 4-letter+4-digit internal placeholder whenever it's blank, written back to the sheet and logged for audit, never silent → `WhErpReceiveFillPending`/`WhErpReceiveSubmit` created a real draft Purchase Receipt, `MAT-PRE-2026-00268` (`EM-PK-ZAM-4TR` ×15 @ 8,600, UOM `Unit`, supplier Zamil Air Conditioners Company), keyed to a real `SIG-RCV-*` operation id. **One more real server-side bug found and fixed along the way:** `sig_register_purchase_receipt`'s PO-route item construction never set `uom` on the Purchase Receipt Item, so ERPNext defaulted it from the Item master instead of the PO line's own stored UOM, tripping ERPNext's native `validate_with_previous_doc` check (`UOM must be equal to 'Unit'`, HTTP 417) — fixed by fetching and passing the PO line's own `uom` explicitly (deployed live, byte-verified, local repo mirror `deploy_po_entry0.py` synced). Also fixed in this pass: the module/Sub name collision, the Received-vs-Pending field swap, and the `ExtractMessage_`/`JsonKey_` JSON-extraction bugs (all recorded in v3.98) plus a genuinely mashed `ReceivePO!A6` header label (now a real per-column header row) and the Excel-silently-converts-text-to-date bug on the posting-date field. The one operation-key CONFLICT hit during testing was the idempotency guard working as designed (a stale key with different generated content), not a defect. **PO-ENTRY-0/PO-STAGE-1 verdict: both `WhErpImportPendingPOs.bas` and `WhErpReceiveMaterial.bas` are now proven end-to-end in the copy workbook, not just "safe to import."** Next: bring this same pair into the live `wh.xlsm` (already cleared for that per the 2026-09-15 checklist), then move to the separate, bigger mgmt-module copy-workbook proving pack (`TransferMgmt`/`InMgmt`/`ReturnMgmt`/`BulkMgmt`/`CorrectionMgmt` + `WhErpSend.bas`), which has not started. | Owner / Technical execution |
| 2026-09-16 | **v3.98 — `WhErpImportPendingPOs.bas` PO-STAGE-1 proving run PASSED live; three real bugs found and fixed in the module (owner-driven test in a copy workbook, per the copy-first discipline).** (1) Module CodeName was identical to `Sub WhErpImportPendingPOs()` inside it — VBA cannot compile a module and its own public Sub sharing one name (`Expected variable, not module` / `...or procedure, not module`); fixed by renaming the component to `WhErpImportPendingPOsMod` (Sub name unchanged, so every button/doc reference keeps working) — this must be redone by hand (Properties window / `VBComponents(...).Name = ...`) after every fresh import or paste of the file, since an `Attribute VB_Name` line is only honored via File ▸ Import File, not when pasted into an existing module's code pane; a header comment now says so in the file. (2) The line-filter checked `CDbl(parts(6)) > 0` (Received qty) instead of `parts(7)` (Pending qty) — Received is 0 by definition for a never-received line, so the filter silently discarded every genuinely pending line; fixed to test `parts(7)`. (3) The real blocker: `ExtractMessage_` searched for `"message":""` expecting a flat string reply, but `sig_list_pending_pos`'s actual shape is `{"message":{...,"data":"L|...\nL|..."}}` — `message` is an object, so the anchor never matched and the function always returned `""`, which read as "no pending lines" regardless of what the server had; fixed to anchor on `"data":""` instead. **Verified live end-to-end** (`WHtest.xlsm` copy): after all three fixes, `WhErpImportPendingPOs` staged exactly the 2 real September lines (`PUR-ORD-26-045`: `EM-PK-ZAM-4TR` ×16 @ 8,600, `EM-PK-ZAM-3T` ×2 @ 7,300, both Zamil Air Conditioners) into `PendingPO`, matching the server's own `sig_list_pending_pos` response exactly — run `W4-260915143041`. **Separately hardened while testing:** the `Config` sheet (where the `ERP_API_KEY`/`ERP_API_SECRET` fallback now lives, since no ACN login session persisted reliably across separate macro invocations that session) was only sheet-Hidden, not VeryHidden like `UserPasswords` — set to VeryHidden to match the existing standard; the VBA project itself still has no lock (`VBProject.Protection = 0`) and the workbook has no open password — both need a manual one-time step in the Excel UI (Tools ▸ VBAProject Properties ▸ Protection; File ▸ Info ▸ Protect Workbook), not something COM automation can safely set. Next: `WhErpReceiveFillPending` against this real staged line, then `WhErpReceiveSubmit` to post the actual draft Purchase Receipt — that closes PO-STAGE-1 fully. **Confirmed and staged for later, not built now:** every document these VBA paths create stays a draft — `sig_register_purchase_receipt` only ever calls `prdoc.insert(...)`, never `.submit()` (verified in `deploy_po_entry0.py`), matching the project's standing "never auto-submit" rule everywhere else. **Owner direction, PO-STAGE-2 (future):** approval/submission of these drafts should eventually be triggerable from VBA itself too, not only the ERP Desk UI — via a dedicated, protected "smart method" endpoint (named approval, per-person attribution, same access-matrix discipline as every other write path here) chosen to keep security and day-to-day smoothness aligned, rather than forcing reviewers into the Desk for every draft. Not designed or built yet; drafts stay Desk-submitted until this lands. | Owner / Technical execution |
| 2026-09-16 | **v3.97 — All 21 residual negative bins corrected to exactly 0; G4/G5 stock remediation now fully closed (0 negative bins live).** Owner's own instinct was the right call: WH's confirmation engine never posts a dispatch without stock, so a real shortfall was implausible — investigated against the **live open WH.xlsm workbook via COM** (`Riyadh`→Muzahmiyah, `Makkah`, `Qasim` per-warehouse Full Stock Report sheets, cols C=code/F=name/G=qty) rather than guessing. **Confirmed: all 21 items read live `qty=0` in WH's own current-state report at that exact warehouse** (2 of the 21 — `C-MNT-PLTS-3m`, `E-BKR-125-1p` — aren't in the live per-warehouse reports at all, consistent with their earlier note as recovered-from-Old-Out "(Dismantle)" codes, i.e. WH doesn't track an ongoing position for them either; treated the same as qty 0). **Root cause: a structural staging gap, not missing data** — the G4 per-warehouse recon batches were built from WH's own closing report, but `register_stock_entry`'s Stock Reconciliation branch rejects `qty<=0` lines (the same quirk already noted for the 3 zero-line Makkah/Qasim recons in v3.93), so a zero-closing line for an item whose ERP bin was *already negative* was silently dropped from the recon batch instead of being the one line that needed to post. **Fix:** `post_g4_zero_corrections.mjs` — one Material Receipt per item, quantity = exactly the negative amount (bin lands on precisely 0), rate = WH's own live `Material Codes` price (read same session, same COM connection) where one exists, `allow_zero_valuation_rate` for the 2 uncatalogued items and the handful whose own WH price is recorded as 0 — never a guessed rate. Proved one item (`M-HexN-10`) end-to-end (created, submitted, bin verified 0) before running the other 20; all 20 posted clean, zero failures. Total correction value SAR 28,127.36 (dominated by `E-AT-BB-8` ×2 @ 5,500 and `C-SFTY-PLTS-RAIL` ×312 @ 11.81 — Makkah's leftover rail-kit sibling parts, the same family already known from the G5 rail resolution, just never zero-closed at Makkah). **Live negative bins: 77 → 21 (TN replay, v3.96) → 0 (this pass).** `_g4_residual_negative_bins.json` now empty; `_g4_zero_correction_results.json` holds the per-item evidence trail. | Technical execution |
| 2026-09-16 | **v3.96 — TN transfer replay COMPLETE (36/36 submitted); §9A.8.1 rules 5/9 and v3.95's "5 submitted" claim corrected — root cause was a code bug, not site load.** Resumed the v3.95 interrupted run. Live check before touching anything: v3.95's "5 transfers confirmed submitted before the kill" did not hold — querying every `Material Transfer` Stock Entry live found zero real TN26-* vouchers submitted; the only docs present were 2 unrelated cancelled test entries and one leftover probe draft (`SIG-TN-TN26-0011-1`, docstatus 0, not even in the real 36-voucher list). **Root cause found by code inspection, not retrying:** `post_g4_transfers.mjs`'s shared `auth` object set `Content-Type: application/json` on every call, including the `register_stock_entry` POST, whose body is `URLSearchParams` (form-encoded). Frappe tried `json.loads()` on a form-encoded body and hard-failed at request parsing (`JSONDecodeError`) before the endpoint ever ran — deterministic, not transient: all 35 vouchers × up to 8 retries (280 attempts) failed identically, which a real repost-queue/load condition would not produce, and every standalone one-off debug call in the same window that used a *different* auth object (no Content-Type) succeeded. **This corrects §9A.8.1 rules 5 and 9**: `allow_negative_stock=1` does not, by itself, break endpoint POSTs, and the JSONDecode bursts were not repost-queue load — both were the same misattributed symptom of this one header bug. Rules 1-4, 6-8, 10-12 in §9A.8.1 held up and were followed as written (fresh backup `ERPNext/backups/2026-09-15_pre_tn_transfer_run/`; byte-verified nothing else changed; refreshed the item-probe and live skip-list immediately before running; proved one real voucher — `TN26-0002-1` — through the fixed endpoint before the batch). **Fix:** split into `auth` (POST, no Content-Type) and `authJson` (the three JSON `PUT` calls) in `post_g4_transfers.mjs`. **Result:** first pass 18/36 submitted, 17 correctly stopped on genuine `NegativeStockError` (backdated source-warehouse shortfalls — the same known class as the v3.92 mass-submission failures, not a new defect); those 17 already-created drafts were submitted under a brief `allow_negative_stock=1` window (the established pattern in this programme) and the flag verified back to `0` immediately after. **36/36 TN26-* transfers now docstatus 1.** Residual negative bins fell from 77 to **21** (Jizan 8→0, Qasim 50→1, Muzahmiyah 8→9, Makkah 11→11 unchanged as designed — Makkah↔Riyadh transfers remain deliberately excluded, recon-locked). `_g4_residual_negative_bins.json` refreshed to the post-run state (stale-artifact discipline, Stage 5.3F-3 lesson 5). Remaining 21 residual negatives are Finance/WH disposition items, same policy as the original 77. | Technical execution |
| 2026-09-15 | **v3.81 — ERP module readiness audit + live sig_whatsapp test PASSED (PDF QUEUED to the 0067 test phone); W-6 prerequisites verified live.** **Maytapi module:** `sig_whatsapp` installed on the live site, `Maytapi Settings` complete (enabled, product/phone IDs matching the VBA module's, timeout 30s, **test_mode=1 → 966562360067**), `SIG Tax Invoice` print format live and enabled. Live test: `send_document("Purchase Order", PUR-ORD-2026-00001, to=0067)` → **QUEUED** with message_id, audit row written to `Maytapi Message Log` (second row for that PO; first was 2026-08-30 — the module had already proven itself once before). **Print templates:** all 7 SIG warehouse formats **LIVE and enabled** — SIG Material Issue/Transfer/Receipt/Return + Custody (Stock Entry), SIG Stock Reconciliation, SIG Material Request (an earlier read of "no warehouse formats live" was a truncated page-list artifact — limit_page_size=0 caps at 20; verified individually). All 7 W-5/W-6 custom fields **LIVE**: Stock Entry requestor_pm / initiated_by / initiated_on / approved_by / dispatched_to, Stock Entry Detail.custom_row_key, Stock Reconciliation Item.custom_row_key (deployer dry-run confirms all present). **Remaining for W-6 (the only gaps):** (1) `send_document` is hard-allowlisted to Sales Invoice/Purchase Order and requires docstatus=1 + customer/supplier contact resolution — extend to Stock Entry/Stock Reconciliation with the Project→group routing table in settings and custodian→phone resolution; (2) repo HTML differs from live for all 7 formats (deployer shows UPDATE — sync with `--yes` when the HTML edits are approved); (3) test_mode stays 1 until go-live (real customer sends currently redirect to 0067). **Verdict: ERP document-delivery infrastructure is complete and proven; only the small Stock Entry extension in the app remains before W-6 can flip.** | Owner / Technical execution |
| 2026-09-15 | **v3.80 — Row-key persistence DEPLOYED live and verified end-to-end; naming drift found.** Checked the parallel session's outcome first: the live `register_stock_entry` body was already byte-identical to the v3.79 staged repo mirror (the other session had deployed both the `Stock Entry Detail-custom_row_key` Custom Field — read-only, indexed, after `custom_site` — and the script), **G0 (`meter` in UOM_MAP) NOT yet live** — its fix is written in the repo working tree (unstaged, left to the parallel session: item's own stock UOM wins when the caller's text matches it case-insensitively, else the WH map, else UOM_UNKNOWN), compiles clean, and preserves both rowkey patches — but has not been pushed to the live script; both patches touch independent regions so no conflict, just no stale full-script pushes. **End-to-end verification:** POSTed a 1-line test PR draft (`ZROWKEY1`, real item, qty 1) → reply `created`, read-back `readback_ok: true`, detail carried `custom_row_key = TEST-ROWKEY-0001`, header `custom_source_id = SIG-PR-ZROWKEY1`, `t_warehouse` mapped to مستودع المزاحمية - SIG; test doc deleted, 404 after. **Finding (drift):** the draft's actual name came out **`STE-2026-0051` from the series** — the script's explicit `name` does not survive Frappe naming series today, contradicting the v3.30 "doc name = WH voucher verbatim" convention. Idempotency is unaffected (dedupe = `custom_source_id`), and the VBA bridge takes the created doc's name from the reply's `doc` field, but the proving run must look drafts up by `custom_source_id`, all doc-map tables showing verbatim voucher names are aspirational, and restore-verbatim-names (insert-then-rename) is bundled with the next endpoint pass. WH-side: nothing new deployed — staged VBA (V-wherp.260915002) still awaits the workbook-copy proving pack. This lane **pauses here until the ERP data import (§9A.6 backfill) is done**, per owner. | Owner / Technical execution |
| 2026-09-15 | **v3.79 — Draft-mirror wing completed and staged on both sides (VBA V-wherp.260915002; ERP script staged in repo).** **VBA:** the five remaining hooks staged at their confirm engines' success tails — `TransferMgmt`(TN), `InMgmt`(PR), `ReturnMgmt`(RN — stock-return vouchers only; IH custody settlements never get a voucher stamp so they can't post), `BulkMgmt`(BI), `CorrectionMgmt`(CR) — all via the new `WhErpSend.bas` `WhErpSendSheetVoucher`, which rescans rows by the run's own voucher in the Document ID column (col O/15 — every engine stamps exactly the rows it committed that run, so posting is run-scoped by construction, the same property the DN bridge exploits via `allConfirmedRowKeys`) and header-resolves Item/Qty/Unit/Site ID/Project plus per-type warehouse routing (TN from "Warehouse"/"WH" → "Site"/"To"; PR/CR "To"→col-E fallback; RN "To"; BI "WH" + "Dispatched To" custodian). CR posts signed qty; skip-stock and cancelled rows never post. `WhErpResendStockEntry` manual-resend macro added — type+voucher prompt, works for all 7 types off the same rescan. **ERP (repo-staged, deploy is two steps):** `register_stock_entry` now persists `custom_row_key` on every Stock Entry detail **and** Stock Reconciliation item (closes the §9A.7 "reads rowkey but drops it" gap); requires new Custom Field `Stock Entry Detail`.`custom_row_key` appended to `sig_warehouse_print_custom_fields.json` — deploy fields first (`deploy_warehouse_prints.py --yes`), then the Server Script update, because `frappe.get_doc` silently drops unknown fields, so field-first ordering is mandatory. Note v3.77-owner gate G0 (UOM_MAP `Meter`) still blocks metre-unit lines at submit — the staged hooks post drafts fine, but the G0 fix should land before any meter-heavy PR/TN proving run. **Finalized execution order:** deploy ERP field + script → import staged VBA (WhErpSend.bas first, then the five engine modules) into a workbook **copy** → per-type proving pack (all 7 types + duplicate re-post each + `custom_row_key` read-back; two-run DN partial asserts per-run vouchers; TN asserts from→to; CR asserts signed qty) → W-4 weekly reconcile clean → live import → WD-4 dispatch app → W-5 cutover → W-6 prints + `sig_whatsapp` WhatsApp move. | Owner / Technical execution |
| 2026-09-15 | **v3.77 — Overall system shape staged (plan only, no code; WH VBA fixes stay undeployed per owner gate).** Written into the master doc ("Overall system shape — imports, reporting, delivery") and mirrored as §16.1 in the WH white paper. **(1) Imports ERP→WH** generalize the delivered `WhErpImportMR` pattern (list-ready → journal PREPARED → bulk write → read-back → batch ack → COMMITTED): phase A MRs→Out (live), phase B fulfilment-state refresh once WD-4 computes outstanding/pending/cancelled per line, phase C per-type only when the origin genuinely moves to ERP (return requests captured in ERP replace the WhatsAppSync Google-Sheets bridge; receipts from ERP buying) — imports write staging rows, never stock. **(2) Reporting**: post-cutover per-item/full-stock quantities read ERP Bin via `get_stock_snapshot` and item history via a new bounded SLE read endpoint; transaction-sheet enrichment, In-Hand positions, As-Built composition, and legacy history stay WH-local; during shadow the report shows WH-vs-ERP delta (W-4 surfaced to the operator). **(3) WhatsApp**: the `sig_whatsapp` Frappe app (already deployed for SI/PO, credentials in `Maytapi Settings` DocType + message-log audit) extends to DN/TN/BI at W-6 via the bilingual print formats — Project→group routing moves into ERP settings, custodian phones resolved in ERP, resolving the white paper §7.4 Red hardcoded-credential gap in `MaytapiSend.bas` (rotate regardless); rule: never both senders on one voucher — WH auto-send flips off in one move at W-6. **(4) Validity harness**: staged WhErpSend/WarehouseMgmt fixes prove out in a workbook **copy** (sham-confirm: DN full, two-run partial voucher split, Out-Add, col-E warehouse, persisted rowkeys, dedupe, readback) → W-4 clean weekly reconcile → only then live import → WD-4 app → W-5 cutover → W-6 paper+WhatsApp. §9A.6 backfill proceeds independently. | Owner / Technical execution |
| 2026-09-15 | **v3.76 — VBA bridge fixes staged** (`wh/deployed/WhErpSend.bas` V-wherp.260915001 + one-line `WarehouseMgmt.bas` call-site change; pending import into the live workbook and a proving run). Review fixes #8a–d implemented: row identity via `TransactionState.GetOrCreateRowKey` (position keys `mir-r` retired), warehouse from col E (blank → MIR skipped, never guessed), trans_no = the run's DN voucher from the Document ID column (`DN26-xxxx[-n]` incl. partial suffix; `DN-{mir}` only as unstamped fallback), Out-Add rows included. Source read found two more defects fixed in the same pass: **(e)** the Confirmed filter read col 15 (Document ID) instead of col 13 (Status) — it could never match, so the live hook posted nothing; **(f)** the auth header still called undefined `WhErpApiKey_`/`WhErpApiSecret_` (pre-v3.37 leftover) — a module compile fault the call site's `On Error Resume Next` swallowed, silently disabling the whole bridge. Posting is **run-scoped** via the core's `allConfirmedRowKeys` (a MIR confirmed across two G2 runs gets different vouchers per run — a whole-MIR rescan would re-post run-1 lines under run-1's voucher and the endpoint's document-level dedupe would drop run-2); line columns (Item Code/Qty Request/Unit/Site ID/Project) header-resolved like the core. Pending: live import + proving run; standalone `WhErpResendStockEntry` macro (referenced in old comments, never written); ERP side still drops `rowkey` instead of persisting it on SE details (§9A.7). Sheet-column facts recorded in the master doc's review-resolution section. | Owner / Technical execution |
| 2026-09-15 | **v3.95 — Procedural playbook added (§9A.8.1); TN transfer replay interrupted by owner, state recorded for clean resume.** The Transfer-sheet replay (Jizan/Qasim-touching TNs only — Mk↔Ry transfers deliberately excluded, the Sep-13 recons lock those bins) hit the endpoint-branch defect left by the v3.81 edit (Transfers lost s/t_warehouse — repaired v3.92-pass, see §9A.8.1 lesson 1), then ran into transient server-state 417/500 JSONDecode bursts (repost-queue load after 790 backdated submissions). The batch was killed by the owner mid-run. **State at interruption (for resume):** staged payloads `_g4_tn_posting.json` (36 vouchers: 31 eligible + 5 EC-NOK-IND, now resolvable — the alias pair was added to `build_remediation_ledger_jan_feb.py`'s ALIAS_MAP and the TN poster); 5 transfers confirmed submitted before the kill (TN26-0003 probe-deleted and re-created as STE-2026-0775 then deleted again, TN26-0011-1 = STE-2026-0775 draft, plus batch successes); exact live state = fetch `SIG-TN-TN26-%` docstatus-0 docs into `_g4_tn_live_state.json` (the poster's skip-list) and re-run `post_g4_transfers.mjs` — it is resumable, enables/disables `allow_negative_stock` itself, and dedupes on `SIG-TN-{voucher}`. Remaining TNs not touching Jizan/Qasim stay excluded by design (Mk↔Ry replay would scramble the recon-locked bins). Full playbook: §9A.8.1. | Owner / Technical execution |
| 2026-09-15 | **v3.94 — G4 recons SUBMITTED after a fresh full-state backup; migration window closed.** **Backup** (`backup_current_state.mjs` → `ERPNext/backups/2026-09-15_full_state_before_g4_submit/`): 722 SEs (all submitted) + 7 recons + 65 PRs + masters + SLE/GL proof-of-state. **Submitted all four G4 recons** (MAT-RECO-2026-00016/17/18/19, docstatus 1). **Verified:** rail family tied exactly (C-SFTY-RAIL-ALMN Muzahmiyah 575 / Makkah 0; legacy codes CW-T-SR-90M/-SP/-CL/-HDB + CW_T_SR_INC all 0); totals today 3,747 SLEs + 1,331 GL entries. **Residual: 77 negative bins** (Qasim 50, Makkah 11, Muzahmiyah 8, Jizan 8 — `_g4_residual_negative_bins.json`): items WH dispatched from warehouses its own report never stocked (Qasim transients, the newly-created fence/mount family, small consumables) — WH has no recorded closing for them, so per the valuation-first rule they wait for WH/Finance rather than being guessed; listed item-by-item. **Mechanics quirk recorded:** a SRC row moving a negative bin to zero 417s as NegativeStockError (mis-reads the sign); equivalent effect posted as a Material Receipt (STE-2026-0774, rail +615 into Makkah @ 244.86, submitted). **`allow_negative_stock` switched OFF** (migration window closed; verified 0) — any residual negative-bin item now blocks its own future transaction until WH/Finance disposition it, which is the honest state. G3/G4 gates closed; W-4 weekly reconcile now runs with both books on the same figures. | Owner / Technical execution |
| 2026-09-15 | **v3.93 — G4 staged: per-warehouse closing recons posted as drafts; the 2026 position lands on WH's books when Finance submits.** Built from the WH Full Stock Report's own per-warehouse closing (`build_g4_recon.py` → `_g4_recon_batches.json`): Makkah 122 lines, Riyadh 292, Jizan 37, Al Qasim 5 = **456 lines, dated 2026-09-13** (after every submitted document), rates = WH Material Codes prices. **Included:** the G5-resolved rail (Riyadh 575 @ 244.86); **zero lines** for the legacy rail-family leftovers (CW-T-SR-90M/-SP/-CL/-HDB, CW_T_SR_INC — value re-homed via the Repack + canonical purchases; difference = the section-E overstatement Finance signs) and for WH-tracked-at-zero items holding ERP stock — which by construction closes **all 120 negative bins**. **Excluded on purpose:** ERP-only items (tools, legacy equipment) — WH has no position on them; bins untouched. **Mechanics:** the endpoint's qty>0 check rejects zero-qty CR lines, so the three zero-line recons went via direct REST (endpoint for Makkah); set_posting_time set everywhere. ERP-only untouched confirmed; zero unresolvable items (the 32 item creations closed the last gap). Artifacts: `WH_ERP_G4_Recons_Posted_2026-09-15.xlsx`. **After Finance submits these:** switch `allow_negative_stock` off, and the weekly WH-vs-ERP reconcile (W-4) runs with both books aligned for the first time. | Owner / Technical execution |
| 2026-09-15 | **v3.92 — SUBMISSION EXECUTED: the whole staged stack posted after a full data backup.** **Backup first** (`backup_pre_submission.mjs` → `ERPNext/backups/2026-09-15_pre_submission/`): full JSON of all 725 SIG Stock Entries + 4 Reconciliations + 65 Purchase Receipts + the 32 created items + 4 created suppliers + SLE/GL proof-of-state snapshots (2,735 SLEs / 36,588 GL since Sep-1), with MANIFEST — every document restorable by its `custom_source_id`. **Test residue deleted** (3 docstatus-0 SHAM/G0TEST drafts). **Submitted 673/673 zero-failure** (`submit_wh_stack.mjs`, ordered: openings + repack Feb-27 → 65 purchase receipts → 118 PRESITE → 517 DN26 → 77 RNs; resumable, per-doc error capture). **Two fix-pass learnings:** (1) the submitter's resume logic initially skipped failed entries — cleared and re-run; (2) submit failures were exactly the predicted classes: 173 NegativeStockError (ERP bins cannot absorb the full historical consumption — the G2-openings/G4 mechanics) + 1 valuation-rate gap (RN26-0080's never-purchased items — provisional rates set per owner's guesstimate authorization). **`allow_negative_stock` enabled** (Stock Settings) for the migration window — standard practice, to be switched off after G4 re-bases quantities. **Result: 722 SEs + 65 PRs + 3 recons all docstatus 1; 3,502 SLEs and 1,294 GL entries posted; the 2026 ledger is live.** **G4 worklist recorded** (`_g4_negative_bins.json`): 120 negative bins (Makkah 41, Qasim 55, Muzahmiyah 12, Jizan 12) + known family quirks (rail spread −615 Makkah/+1,430 Muzahmiyah vs WH's Riyadh 575 — the combined-bin convention vs WH's transfers) — the G4 per-warehouse recon sets absolutes and closes these by construction. Frappe Cloud's own scheduled backups continue independently; the on-demand dashboard backup remains available to the owner for a full-site image. | Owner / Technical execution |
| 2026-09-15 | **v3.91 — G5 RESOLVED from WH's own records; Al Suhaili posted; rail Repack rebased.** Per owner ("check consumed material rail for g5 in wh sheet"): the Full Stock Report's **per-code rail ledgers** settle it — the Unit column reads **"String"** for every row, the Riyadh ledger runs Opening 0 → +800 (PR26-0008) → +1,525 (PR26-0019) → dispatches/transfers → **Closing 575**, Makkah closes 0, and the In sheet's PR26-0019 rail row records 1,525 (= the metre PO quantity, total 404,345 = PUR-ORD-26-016 to the riyal). **The numbers are one consistent series end-to-end; current true rail = 575, all in Riyadh.** The earlier "×5 artifact" framing is superseded: the 54/575 tie is now understood as Feb-27 opening 470 (= 270 Feb-28 snapshot-basis + flows) closing to 575 — no meter/length ambiguity survives in the series itself; the catalog's "Each Length 5 Mtr" is descriptive text, not the count unit. **Applied:** the rail family's Feb-27 ERP openings re-derived from the staged flows so the family closes at WH's own figures (closing + staged dispatch + staged returns − staged purchases = **rail 470, plates 404, bolts 808, caps 10**) and the Repack produce lines rebased to those openings (rates unchanged, WH per-unit; the value difference vs the 3,484 consumed = the legacy ERP overstatement, Finance's signed figure). Verified rail identity after submission-order flows: 470 + 2,325 − 2,160 + 60 = 575 exact. **Al Suhaili** created as-named per owner ("keep it the same") and PR26-0018/0023/0043 posted (MAT-PRE-2026-00265/266/267, backdated). **RN26-0076** confirmed at WH's exact quantity (6), unlinked, unchanged. **G3 final: 65 Purchase Receipt drafts, all docstatus 0**; only PR26-0009 ('Test') deliberately dead. Zero SLE/GL from this work. | Owner / Technical execution |
| 2026-09-15 | **v3.90 — Owner decisions executed; G3 final.** (1) **PR26-0024 (DANA)**: three supplier records exist (Dana Al Raha Furnished Units — a different business; and two DANA AL-DOSARI variants differing only by a double space; none with PO/PI history) → per owner "pick the one used", the single-space record matching the In sheet's own spelling was chosen and the receipt posted (MAT-PRE-2026-00264, E-Lit-R-L ×50 @ 950, Apr-23); the double-space variant flagged for duplicate cleanup. (2) **RN26-0076 over-cap line delinked** from DN26-0989 per owner ("you can delink from the dn") — STE-2026-0753 now a standalone flagged receipt, quantity pending WH confirmation. (3) **PR26-0009 confirmed dead**: its item (E-RM-VER-50 ×2, supplier 'Test') is covered by real receipts in-window (MAT-PRE-2026-00022 Jun-28 ×6, -00030 Jul-9 ×6, -00036 Aug-23 ×5); nothing posts. (4) **Provisional guesstimate rates set on all 20 NO-PRICE lines** (18 opening-recon lines + the 2 washer lines) per owner authorization ("guesstimate per Saudi/global reasonable cheap price") — cheap-consumable SAR values, marked PROVISIONAL in document remarks, trued up at invoice per the master doc's provisional-valuation policy. **Final accounting: 81 In vouchers = 62 PR drafts posted + 15 fully covered by ERP's own receipts + 1 dead test row + 3 held (Al Suhaili legal-name confirmation).** Programme totals: **725 Stock Entries + 4 Recons + 62 Purchase Receipts, all docstatus 0, zero SLE/GL impact.** | Owner / Technical execution |
| 2026-09-15 | **v3.89 — Price-derivation ladder executed on every unpriced line; decisions register compiled.** Per the master doc's ladder (WH sheet price → same item's own history → NO-PRICE): 28 unpriced items found (26 opening-recon lines + 2 washer lines on PR26-0004). **8 derived** from the item's own earliest recorded SLE purchase rate and applied to the recon drafts, marked DERIVED-provisional in remarks (C-MNT-4.5m @650, C-MNT-5m @388, E-TL-150M @6,800, E-CC-2C-1.5 @1.26, E-PVC-ELBW-3/4 @3, E-PVC-P-3/4 @55, M-ELBW-2 @65, E-ATS-Stand @0.01). **20 remain NO-PRICE** (no price evidence anywhere — incl. the 2 washer lines, 6 of the 8 newly-created items with no purchase history, and consumables WH prices at 0.00) — Finance prices or drops them at submission. **Decisions register** (shared with owner): (1) **G5 rail unit** — snapshots say 5-m lengths (54), transactions say metres (PR 2,325 fits Yaseen's metre POs; 54×5+2,325−2,040−40+60=575=the report figure, so the closure's "Surplus −216" is the artifact); WH must say which unit the 575 is in — it sets the Makkah rail opening line, the Repack quantities (currently −671,826 = this question), and the G4 target. (2) **5 held vouchers**: PR26-0009 supplier 'Test' (real receipt or not?); PR26-0018/0023/0043 'Al Suhaili Company for Trade and Development Electricity Department' (absent from ERP's 1,109 — confirm exact legal name → provisional creation → posted); PR26-0024 'DANA MOHAMMAD N. AL-DOSARI FOR IRON METAL SHELVES WORKSHOP' matches 2 ERP supplier name variants (pick one or create). (3) **RN26-0076 over-cap** (return 6.0 vs issued 2.0 E-DC-CAB-35, separately posted flagged STE-2026-0753) — WH confirms which figure stands. Derived-rate evidence file: `_price_derivation.json`. | Owner / Technical execution |
| 2026-09-15 | **v3.88 — G3 COMPLETE to draft stage; the payment-linkage question proven, the purchase policy applied.** **PE↔PR proven impossible live:** a draft Payment Entry referencing a Purchase Receipt 417s with the authoritative list — references must be one of 'Purchase Order', 'Purchase Invoice', 'Journal Entry' or 'Payment Entry'; Purchase Receipt is not eligible. This matches the master doc's payment-corroboration boundary exactly: PEs corroborate payment at the money level and get allocated to the later Purchase Invoice through normal reconciliation; they never value or evidence an item line. **Purchase policy applied** (master doc v2.3, owner-reviewed today): the 58 staged vouchers are retrospective NO-PO receipts (disposition 2 — supplier + rate mandatory, `custom_source_id` keyed, drafts, Finance submits); the 2 washer lines with no price evidence anywhere are parked NO-PRICE per the owner's valuation-first rule (Finance sets a rate or removes them before submission); 12 vouchers total ≥ SAR 10,000 and are threshold-flagged for Finance — the two largest (PR26-0019 SAR 404,345 / PR26-0008 SAR 215,496) are exactly the Yaseen POs PUR-ORD-26-016/012, which exist in ERP as SUBMITTED documents matching to the riyal; Remarks on both drafts carry the PO reference (stock codes pending the section-E Repack). **3 provisional suppliers created** per the master doc's provisional-supplier policy (Alam Olaya, Fenda Traders, Mobiserve Traders — real names from WH's live In register; the Provisional flag mechanism itself is PO-ENTRY-0 future work, so verification-before-PI/payment is procedural) and their vouchers posted. **Total G3: 61 Purchase Receipt drafts, all docstatus 0, true dates; 5 held** (1 'Test' row, 3 Al Suhaili vouchers — genuinely absent from ERP, 1 DANA ambiguous with 2 name variants). Coverage-matcher soft spot noted: the item+qty heuristic falsely matched the 2 never-existed-supplier vouchers as covered — corrected by direct posting. Verified: all docstatus 0, dates true, zero SLE/GL from any of it. Artifacts updated: `WH_ERP_G3_Purchases_Posted_2026-09-15.xlsx`. | Owner / Technical execution |
| 2026-09-15 | **v3.87 — G3 staged: 58 Purchase Receipt drafts posted from the live In sheet; supplier identity strictly matched; the PE-linkage question answered.** Owner direction: WH has the supplier and prices — stage the receipts. Source: **live In sheet via COM** (239 rows / 236 Confirmed / 81 PR26- vouchers / 22 suppliers in the Mar 1–Sep 13 window — row-for-row identical to logs' 236 PR rows, now with supplier + per-unit Price + destination). **Coverage:** 22 In lines already matched by ERP's own Mar-Sep Purchase Receipt lines (greedy item+qty match) and were skipped; **58 vouchers (204 lines) staged and posted as Purchase Receipt drafts** (`build_g3_purchases.py`, `post_g3_purchases.mjs`, `_g3_purchases.json` / `_g3_posting_results.json`) — supplier per strict normalized-name match to a unique ERP Supplier (1,109 exist from the legacy migration), rate = the In sheet's own Price, warehouse = the In sheet's 'To', custom_source_id = `SIG-IN-<PR26 voucher>`, all docstatus 0. **Held 8 vouchers** for Finance: 1 'Test' supplier row; 4 with ambiguous ERP supplier matches (Al Suhaili ×3, DANA ×1 — 2 name variants each); 3 suppliers not in ERP at all (Alam Olaya, Fenda Traders, Mobiserve Traders). **Date defect found again (third doctype):** Purchase Receipt also silently overwrites a supplied posting_date — all 58 backdated via PUT with `set_posting_time=1`, verified by month (Mar 8 / Apr 14 / May 3 / Jun 8 / Jul 6 / Aug 14 / Sep 5); lesson 258 generalized. **Payment-Entry question answered:** a Purchase Receipt has no PE link field — Payment Entries reference Purchase Orders / Purchase Invoices, so payment reconciliation stays at the PO/PI level with the existing finance machinery; the receipts give Finance the stock side and the supplier/price evidence per voucher. Zero SLEs/GL from these drafts. Artifacts: `_live_in_sheet.csv`, `_live_suppliers_sheet.csv`, `WH_ERP_G3_Purchases_Posted_2026-09-15.xlsx`. | Owner / Technical execution |
| 2026-09-15 | **v3.86 — Item master completed for the backfill; every staged line now resolves.** The 36 "unresolved" codes from the staging pass were re-checked under the improved case-insensitive resolver: 4 are case-variants of live ERP items (C-FNC-P-CPost, E-BKR-CHINT-125-1P, E-LIT-WC-100, E-ODU-FEN-2K — the section-E renames never ran, so resolution is by match, not rename). The remaining **32 created as ERP Items** per the twice-established convention (WH code canonical, WH name, UOM mapped Pcs.→Nos / Mtr.→Meter / Set.→Set / Roll.→Roll / Bucket.→Bucket / Packet.→Packet, Products group, Moving Average, **no price**); two blank-name codes recovered from Old-Out's own item_name (E-BKR-125-1p "Breaker 125 AMP (1 Pole) (Dismantle)", C-MNT-PLTS-3m "Mount Civil 3 Mtr with (Plates +U Bolts)"). All 32 created clean (0 failed). Downstream completed: **Batch B re-staged to 517 drafts (+9 DNs: 606/759/797/824/900–903/966 — the fence/cable-tray family) and Batch A grew 11 lines** inside 10 already-posted PRESITE batches → those 10 drafts deleted and re-posted (verified: ZMH057 now carries E-BKR-125-1p). **Backfill total now 635 drafts.** The 8 newly-resolvable opening lines PUT onto the G2 recons (00013 → 126 lines, 00014 → 185, WH-priced where the catalog has costs). Staging builder hardened: its resolver now has the same case-insensitive fallback (the stale 36-list had predated that fix), and the item probe is refreshed before every staging run. **G3 parity re-checked:** still 49 ERP PR SLE rows Mar 1–Sep 13 vs WH's 236 (the new MAT-PRE-2026-00181 is dated today, outside the cutoff) — the 131-item gap list stands for Finance. Learning-loop: nothing new this pass (all patterns already recorded 255–260); the resolver-fallback sync between sibling scripts is the standing-risk note now attached to lesson 256's file. | Owner / Technical execution |
| 2026-09-15 | **v3.85 — G2 completed to draft stage: WH rates set on the openings, safety-rail Repack posted, over-cap line posted flagged.** Owner direction: rates from the WH sheet per unit; the Repack uses the PO rates plus WH prices. (1) **Opening recon rates:** WH Material Codes per-unit prices PUT onto the three recons — verified on read-back: MAT-RECO-2026-00013 = 108 priced lines / SAR 867,190.61, -00014 = 177 / SAR 3,444,111.46, -00015 = 38 / SAR 62,407.33 (total ≈ SAR 4.35M); 20 lines stay zero-rated (no WH price) for Finance. Mechanics lesson: a recon rate update is a full child-table PUT (fetch items, set valuation_rate + allow_zero per line, PUT items). (2) **Safety-rail Repack** `SIG-REPACK-SR01` → STE-2026-0754 (direct REST draft — the endpoint has no Repack purpose): consume CW_T_SR_INC 719 + CW-T-SR-90M 2,765 @ PO 239/m → produce rail 575 @ 244.86, plates 482 @ 11.81, bolts 956 @ 2.4976, caps 13 @ 921.15 (WH counts × WH per-unit prices). ERPNext requires `set_basic_rate_manually=1` on every produced row of a multi-FG Repack (first insert 417'd). The draft's **−SAR 671,826 value difference is gate G5 quantified**: ERP holds 3,484 metre-equivalents while WH's report reads 575 + part counts — WH confirms the unit, Finance adjusts the draft, it ties. (3) **RN26-0076 over-cap line** posted flagged (STE-2026-0753). (4) Recon note: Muzahmiyah's recon reads 183 of 243 staged lines — ERPNext silently drops no-change rows (snapshot qty = current bin); correct, nothing lost. Verified: all docstatus 0; the only active SLE today is MAT-PRE-2026-00181 — a Purchase Receipt posted outside this work (G3 purchases are moving in Finance's lane). Artifacts: `complete_g2_rates_repack.py`, `WH_ERP_G2_Openings_Posted_2026-09-15.xlsx`. | Owner / Technical execution |
| 2026-09-15 | **v3.84 — G2 staged: opening recons + the over-cap line posted as drafts; third silent date-overwrite found (Stock Reconciliation) and patched.** Per owner go ("post as draft this remaining one … then proceed … g2"). (1) **RN26-0076's over-cap line** (E-DC-CAB-35 return 6.0 vs issued 2.0) posted as its own flagged draft `SIG-RN-RN26-0076-OC` (STE-2026-0753) with the confirm-question in Remarks — Finance/WH decides which figure stands. (2) **Per-warehouse opening Stock Reconciliations** (`build_g2_opening_recons.py`): Makkah 120 lines, Muzahmiyah 243, Jizan 40 — quantities from WH's own 28-02 (Jizan 27-02) snapshots, dated **2026-02-27** so the Feb-28 consumption batch (Batch A) sorts after the recons; Al Qasim opening is 0/0. Rail family excluded (gate G5); ERP-only items not listed so their bins stay; zero-rated per the CR endpoint path — Finance sets rates at review (WH Material Codes = reference). Posted `SIG-CR-OPN-MA/MU/JI-20260227` → MAT-RECO-2026-00013/00014/00015, all docstatus 0. **Defect (third of its class):** Stock Reconciliation also silently overwrites a supplied posting_date with today unless `set_posting_time=1` — found on verification, endpoint CR path patched (mirrors + live + read-back + fresh CR probe asserting the Feb-27 date, probe deleted). Backdated all three via PUT. Effect when submitted: the backdated recons re-base the ledger timeline (bins = WH snapshot + ERP's own Mar-Sep movements; backfill consumption subtracts on top). Artifacts: `_g2_opening_batches.json`, `WH_ERP_G2_Openings_Posted_2026-09-15.xlsx` (with the pre-submission checklist). **Still open:** Finance rates on the openings; rail Repack (rate split + G5 unit confirm); G3 Mar-Sep purchases (Finance); G4 residual recon after submissions. | Owner / Technical execution |
| 2026-09-15 | **v3.83 — G1 COMPLETE: the remaining 23 RN vouchers posted under owner authorization ("no need for DN reference for the RN"); all 76 confirmed returns now live as drafts.** The held list was shared with the owner with full detail (16 no-source-DN vouchers, 3 pre-window source DNs, 1 in-window mismatch, 1 invalid DN "2025", 2 custody-source vouchers); owner directed that the DN reference is not required. Builder updated (`build_returns_posting.py`): no-DN vouchers post as Material Receipts into the Return sheet's own 'To' warehouse with `no source DN recorded (owner authorization 2026-09-15)` provenance; DN-citing-but-unverifiable vouchers post with `cites DN26-xxxx (unverified)`; the two custody-source vouchers (RN26-0052/0056, source IH26-0001/0004 — the In-Hand ledger corroborates their items exactly) post with `custody return | source IH26-...` remarks (ERP holds no custody stock — the BIs were never posted — so a transfer-back from In-Hand would model a movement that never existed; the receipt records physical reality and the custody provenance stays in remarks/WH's own IH ledger). Site filled from WH's Origin column where it carries a site id. Only true anomaly kept held: **RN26-0076's E-DC-CAB-35 line (return 6.0 vs issued 2.0)** — posted the voucher's other lines; WH should confirm which figure is right. **Verified:** 76/76 SIG-RN-RN26-% drafts, docstatus all 0, dates complete, zero SLEs, sample RN26-0032 (11 lines, Makkah, owner-auth remark) exact. Workbook regenerated (all 76 + 5 flags). Returns lane is now closed pending the same Finance submission gate as A/B — sequencing: DN drafts, then their RN drafts. | Owner / Technical execution |
| 2026-09-15 | **v3.82 — G1 returns moved from HELD to draft stage: 53 of 76 confirmed RN vouchers posted, cap-checked and source-linked; the returns-join finding is superseded by live data.** Learning-loop lessons 255–260 appended first (server-script mirror rot + proving calls; Stock Entry valuation gate ignores basic_rate/valuation_rate — only allow_zero_valuation_rate passes, and valuation is FROM-warehouse-scoped; set_posting_time silent overwrite; voucher-sequence vs parent-number join collisions; unit-split delta signature = opening × (factor−1)). **Data basis:** the Aug-21 `WH.xlsm` dump proved STALE for returns — its Return sheet held only 45 of 76 vouchers and missed whole return lines (RN26-0002 has 8 live rows vs 4 in the dump). Exported the LIVE workbook via COM (the established `read_wh_out_com` pattern): live Return sheet = 181 rows / 164 Confirmed / **all 76 RN vouchers**, each cross-checked item-for-item against the live logs sheet — the two records agree exactly, which closes the §9A.8 returns-join question (the RN-seq join bug is moot at this data level: the Return sheet carries true RN26- ids AND source DNs itself). **Routing:** destination warehouse from the Return sheet's own 'To' column (3 To-vs-source-DN mismatches flagged, 'To' used); `rn_against` intended for the 53 whose source DNs were posted as B-batch drafts; caps enforced per (DN, item) from posted-SE quantities first, live logs second — **RN26-0076 caught returning 6.0 E-DC-CAB-35 against 2.0 issued** (line held). **Posted:** 53/53 created, all docstatus 0, true dates, zero SLEs, duplicate guard proven (`post_returns_batches.mjs`, `_returns_posting_results.json`). **Field-verified:** Stock Entry has NO `return_against` DocField in v15 (DocField query) — the endpoint's value is silently dropped, so the against-SE name lives in each draft's Remarks (53/53); is_return=1 submits without it (v3.74 RNTEST evidence) and the §9A.7 custom ERP-Link field remains a registered pre-submission endpoint item. Submission sequencing for Finance: DN drafts first, then their RN drafts. **Still held:** 16 vouchers with no source DN on any row, 3 with unverifiable issued records (DN 1/27/43 pre-window; 1 partial-suffix DN) — needs WH's own account, not a guess. Artifacts: `build_returns_posting.py`, `_returns_batches.json`, `WH_ERP_Returns_Posted_2026-09-15.xlsx`, `_live_return_sheet.csv` / `_live_logs_sheet.csv`. | Owner / Technical execution |
| 2026-09-15 | **v3.81 — Backfill A+B POSTED: 626 Stock Entry drafts live in ERP, zero SLE movement; two more silent-overwrite endpoint defects found and fixed.** Per owner go ("plan moving A+B then move on with plan"), and per the master doc's staged note that the §9A.6 backfill proceeds independently of the VBA validity gate. Pre-post checks: all dedupe keys free (only the 13 test docs carried SIG-* keys), endpoint live = repo byte-for-byte, mirrors (`register_stock_entry_server_script.json` + `register_stock_entry_script.py`, now identical) synced. **Run:** 626/626 `created` (Batch A 118 per-site + Batch B 508 per-DN, chronological), resumable poster (`post_backfill_batches.mjs`) with per-key results (`_backfill_posting_results.json`); zero exceptions. **Defect found during the run (1):** draft inserts 417'd on `Valuation Rate ... required` for items whose SLE history sits outside the FROM warehouse (e.g. E-ALM-4P — all its history is in the closed `مستودع السلي - SIG`) or nowhere. Matrix-proven on throwaway drafts: ERPNext ignores caller-supplied `basic_rate`/`valuation_rate` for this check — only `allow_zero_valuation_rate=1` passes. Endpoint now sets it when the FROM warehouse cannot price the line (rates are Finance's review at the submission gate; G2 openings restore real rates). **Defect found on verification (2):** every draft's `posting_date` read the run date — Stock Entry silently overwrites a supplied date unless `set_posting_time=1`. Endpoint patched; the 626 already-posted drafts backdated via resumable PUT pass (`fix_backfill_posting_dates.mjs`). **Verified:** 118+508 docs, all docstatus 0; dates exact (Feb 118 / Mar 68 / Apr 90 / May 74 / Jun 78 / Jul 50 / Aug 110 / Sep 38); 372 SIG Site stubs auto-created; `custom_row_key` on every detail; zero SLEs created; ZRW982/DN26-0264 spot-check exact (5 lines, right site/qty); re-POST → `duplicate`. Real valuation rates auto-filled on priced lines (e.g. E-Lit-MT-150 @ 3,361.16); unpriced lines zero-rated for Finance to set at submission. Artifacts: `WH_ERP_Backfill_Posted_2026-09-15.xlsx` (register + verification + gates), `_backfill_posted_register.json`. **Next gates unchanged:** G1 returns held; G2 per-warehouse openings + rail Repack before any submission; G3 Mar-Sep purchases (Finance); G4 residual recon; G5 rail unit confirmation from WH. | Owner / Technical execution |
| 2026-09-15 | **v3.80 — G0 executed and proven live; two latent v3.79 defects found and fixed in the pass.** Owner: start G0, honouring the import-lessons discipline (live-script-first, field-first, read-back, proving run, mirror-back, cleanup). State found: live `register_stock_entry` was still pre-v3.79; the v3.79 repo mirror (rowkey-on-details) had never been deployed or executed. **Deploy:** (1) field-first per v3.79's own order — `deploy_warehouse_prints.py --yes` ran clean (5 SE header fields + `Stock Entry Detail.custom_row_key` + 7 WH print formats, idempotent); (2) live script = v3.79 rowkey version + the G0 UOM fix (a caller UOM equal to the item's own `stock_uom` case-insensitively wins, else the WH map, else UOM_UNKNOWN — unblocks the 910 `Meter` + 1 `Unit` staged lines); partial PUT (`script` only), byte-exact read-back. **Latent defect 1 (found by the proving run, 500 on first DN call):** the v3.79 repo edit had mangled the CR branch's indentation — `items = []` alone stayed inside `if trans_type == 'CR':` while the append loop and the entire Stock-Reconciliation insert/return sat unguarded, so every non-CR transaction died on `UnboundLocalError: items` (and had the variable been bound, a DN would have created a Stock Reconciliation). Repaired to the intended structure; a local `compile()` gate is now applied to the script before any redeploy. **Latent defect 2 (found on CR read-back):** v3.79's "persists custom_row_key on ... Stock Reconciliation item" was silently void — the field existed only on Stock Entry Detail. Created `Stock Reconciliation Item.custom_row_key` (Data, read-only, indexed; mirrored into `sig_warehouse_print_custom_fields.json`, now 7 fields). **Proving pack, all PASS then cleaned up:** DN draft with a `Meter` line + a `nos` map-path line → uoms `Meter`/`Nos`, `custom_row_key` on both details (STE-2026-0051, deleted); unknown UOM → `UOM_UNKNOWN` exception (guard retained); re-POST → `duplicate` (idempotency intact); CR draft with a Meter line → created, `custom_row_key` persisted (MAT-RECO-2026-00013, deleted); zero G0TEST residue in ERP. **Gate 0 of §9A.8 is closed** — the 118 + 508 staged backfill drafts are now fully postable; v3.79's staged VBA hooks can also proceed to their proving run against this endpoint. | Owner / Technical execution |
| 2026-09-15 | **v3.77 — ERP stock-updates upload fully staged; returns-join bug found in the closure package; safety-rail unit split found in the finalized position.** The §9A.6 one-time backfill is built and validated read-only: **Batch A** = 118 per-site Material Issue drafts (Jan-1–Feb-28 Old-Out, Site ID on every line, Feb-28 posting, Muzahmiyah default warehouse flagged); **Batch B** = 508 per-DN Material Issue drafts (2,669 lines, Mar-1–Sep-13 `logs`, WH's own DN26-xxxx voucher format so dedupe keys match the live mirror exactly, Site via Out's own DN column — only 1 of 2,669 lines unplaced); **Batch C** = returns HELD. Nothing posted to ERP; all live `SIG-*` keys are test docs (no collisions), items/UOM resolved, 372-row site register staged for auto-stub. **Finding 1:** `logs`' RN number column is the RN's own voucher sequence (RN26-00xx — proven via In-Hand ledger `RN26-0052`/`RN-46-*` row keys), not the MIR; the closure package's 28-row "Returns Full" sheet joined it to Out MIR numbers and all 28 rows sit on 14 numeric coincidences (wrong MIR + wrong Site; the IH-linked filter never actually fired). Returns restaged held per §9A.7 with true RN26- ids, pending WH Return-sheet source-DN reconciliation + endpoint source-line-key/route work. **Finding 2:** safety-rail units split — WH snapshots/reports in 5-metre lengths, WH transactions in metres (PR 2,325 fits Yaseen's metre POs); Step 1's raw summing left finalized rail 359 carrying a 54×4 artifact, and the closure delta's "Surplus −216" rail row is that artifact's exact signature (54×5+2,325−2,040−40+60=575=the report figure). Dispatch staging unaffected (metres, independently evidenced); rail recon target blocked until WH confirms units. **Gates:** G0 one-line UOM_MAP fix in `register_stock_entry` (910 `Meter` lines unexpressible today); G1 returns held; G2 negative-stock at submit until per-warehouse openings + the §E Repack land; G3 Mar-Sep purchase postings (WH 236 PR rows vs 49 ERP PR SLE rows, 131 items gapped — Finance lane); G4 residual recon (296 rows) with rail excluded per Finding 2. Artifacts: `build_erp_backfill_staging.py`, `_backfill_batches.json`, `WH_ERP_Upload_Staging_2026-09-15.xlsx`. | Owner / Technical execution |
| 2026-09-15 | **v3.75 — Field Ops commissioning test: clean-slate deploy + end-to-end from zero, all PASS.** Wiped every field-ops record (0 events / 0 visits / 0 cycles / 0 sites) and redeployed the full stack from repo scripts: 4 doctypes, 2 read endpoints (check_dn_availability v2 + get_stock_snapshot), 4 server scripts (evidence + stock_entry + daily + close_cycles), 3 query reports, 7 number cards, Kanban board, 3 charts, workspace, 2 client scripts, 1 SIG Site enrichment field — **all recreated from the deployer in one `--yes` run**. End-to-end from zero: one DN call auto-created the SIG Site stub, correct s_warehouse and docstatus 0, all in one POST. ZSHAM1 test site deleted after. SIG Site total now **0** — the emergent model confirmed: sites auto-create when first real transaction arrives, not before. ERP is **commissioned**: all infrastructure deployable from repo scripts, all flows tested, zero manual setup needed. Remaining: WH sender hooks (VBA, post-ERP-readiness per owner) + stock remediation (Finance). | Owner / Technical execution |
| 2026-09-15 | **v3.74 — TN/BI return route PASSED (submitted test) + dispatch contract design written.** Second §9A.7 route proven: TN (Muzahmiyah→Makkah, qty 2) submitted → SLEs −2@Ry +2@Mk rate 5130; reverse TN (Makkah→Muzahmiyah) submitted → SLEs −2@Mk +2@Ry rate 5130. Valuation preserved. Both routes (Material Issue return + Material Transfer return) now have submitted-test evidence. **Dispatch contract design** written into master doc covering findings #3/#4/#5/#9/#10: four-identity model (MR line / dispatch operation / DN voucher / dispatch detail), operation-level idempotency with payload hash, batch = one transaction with multiple SEs, three-outcome shortage resolution (issue-capped / leave-pending / cancel-demand), five-check server-side auth, writer as bench-deployed Frappe app with dispatch-operation DocType. No code — design ready for review. | Owner / Technical execution |
| 2026-09-15 | **v3.73 — Availability endpoint v2 (allocation + validation + UOM flag) + native MR links + RN submitted test PASSED.** Three items from the review-resolution table closed: **(1) check_dn_availability v2** — per-line deterministic FIFO allocation (pool of 10, lines requesting 8+5+3 → alloc 8+2+0, total = pool, never over-allocates), qty validation (non-positive rejected), UOM flag (mismatched UOM vs stock_uom reported, not blocking). **(2) Native MR linkage** — register_stock_entry now reads mr_i/mri_i params per line and sets material_request + material_request_item on issue details (verified: DN linked to MR-26-1035 item b0i3kmv0jv). **(3) RN submitted test (§9A.7 release gate) — PASSED**: DN (Material Issue) submitted → Bin 75→73, SLE −2 @ rate 700; RN (Material Receipt is_return=1, t_warehouse into store) submitted → Bin 73→75, SLE +2 @ rate 700. Valuation preserved (return at original rate). The Material Receipt route is confirmed correct for Material Issue returns — is_return=1 is metadata, t_warehouse drives the stock restoration. Both test docs cancelled; Bin restored to 75. Cancelled SEs kept (docstatus 2, ledger-net-zero, standard practice). | Owner / Technical execution |
| 2026-09-14 | **v3.72 — Review findings point-by-point resolution; VBA bridge root-caused.** Read WH deployed bas (WhErpSend.bas, WarehouseMgmt.bas, TransactionState.bas) against the 10 findings. Key discovery: **WH core already has stable row keys** — `TransactionState.GetOrCreateRowKey` creates a persistent key column; the ERP bridge bypasses them. Four bounded VBA fixes identified: (a) use GetOrCreateRowKey not position-based keys; (b) read warehouse from col 5 not hardcode "Riyadh"; (c) pass actual DN voucher number not "DN-{mir}"; (d) include Out-Add rows. Resolution table recorded in master doc: 1 resolved (design), 2+7 fix-together, 6 partially resolved, 3/4/5/9/10 need one design pass before WD-4. | Owner / Technical execution |
| 2026-09-14 | **v3.71 — WH RN return route resolved as source-aware design, not a generic `is_return` reversal.** Reviewed the live workbook's Return/Manage Return fields and the deployed `register_stock_entry` source. A return against a DN Material Issue must be a positive Material Receipt into the original store; return of BI stock must be a Material Transfer from the In-Hand warehouse back to the store. ERPNext Stock Entry has no standard `return_against`; use an ERP Link field plus the stable WH source-line key, and have the endpoint resolve ERP document names. Persist the issue row key (currently parsed but dropped), enforce cumulative returned quantity and define valuation explicitly. Submitted isolated tests must assert SLE direction before enabling RN; production remains draft/approval gated. Details in §9A.7; master design pointer updated. | Owner / Technical execution |
| 2026-09-14 | **v3.70 — External source review: DN-cycle contract corrections recorded; RN return_against error confirmed.** A source-level review of the deployed code against the recorded v15.105.0 schema found concrete errors in the proposed DN issuance contract. Recorded in the master doc as "Source-review findings" (10 items): (1) **`return_against` is not a standard v15 Stock Entry field** — the deployed RN fix passes it into the void; `is_return=1` does not by itself reverse a Material Issue; correct shape must be re-derived and proven with a submitted test; (2) availability endpoint needs qty validation, UOM conversion, per-line allocation; (3) batch boundary ≠ document boundary (one transaction, multiple SEs); (4) idempotency needs operation ID + payload hash + lost-response recovery via a status-lookup endpoint; (5) "leave pending" shortage outcome (issue 6, leave 4 outstanding — not auto-cancel); (6) custody mapping through ERP with per-custodian warehouse leaves; (7) native material_request links on issue details; (8) WhErpSend.bas bridge findings; (9) server-side auth enforcement beyond ignore_permissions; (10) final writer should be a Frappe app, not RestrictedPython. The "not a race" paragraph in the master doc is corrected: preflight improves UX but is not atomicity. | Owner / Technical execution |
| 2026-09-14 | **v3.69 — DN issuance cycle read endpoints deployed + verified: `check_dn_availability` and `get_stock_snapshot`.** Two pure-read Server Scripts built and deployed: (1) **`check_dn_availability`** — batch preflight against live Bin: VBA POSTs item/qty per line, endpoint aggregates per-item (same item on multiple lines shares one Bin pool), reads `Bin.actual_qty` per item at the warehouse, returns per-line `{requested, available, sufficient, short}` + batch-level `all_sufficient` and `insufficient_count`. No document created. Smoke test: 3-line batch → 2 sufficient / 1 short (E-DCDP-R req 50 vs avail 10) — correct. (2) **`get_stock_snapshot`** — Bin table for the WH download button: returns pipe-delimited rows for all warehouses (or filtered by short code), 220 bins returned for Muzahmiyah — planning aid only, never the issuing authority. New sandbox lesson (#34): `+=` on dict items is RestrictedPython-blocked — use `d[k] = d[k] + v`. VBA side (WH sender hooks for check + resolved resend + download button) is the remaining build — sequenced after the submit-capable dispatch endpoint and the stock remediation gate. | Owner / Technical execution |
| 2026-09-14 | **v3.69 — Out sheet Status/DN/qty remediation pass complete; `Out` now correctly reflects which rows are evidence-backed Confirmed, ready for the ERP backfill upload.** Full pass on `Out`'s own bookkeeping (separate from and downstream of the §9A.1-9A.5 stock-position math, which this pass never touched): ~180 rows corrected across bare-comment relabelling (872), an owner-caught bulk-cancel mistake reverted and re-checked (MIR 297), twin-MIR duplicate pairs (322/331, 328/332), a numbering-overflow pattern swept sheet-wide (MIR 43→44, 373→374, 263→264 +7 more), a full `logs`-vs-`Out` qty audit (16 corrections, 2 verified against Old-Out directly), and a genuine over-confirmation bug (31 rows, root-caused to `WarehouseMgmt.bas`'s `VerifyConfirmedDNStatusesOnSheet` force-confirming by Document-ID string match alone — patched at source and deployed into the live workbook's VBA project by the owner the same day). Downstream reports rebuilt with fully refreshed data: `WH_Finalized_Stock_Position.xlsx` unchanged (456 items — confirms this pass didn't move the position math), `WH_Finalized_ERP_Delta_2026.xlsx`, `WH_Closure_Package_2026.xlsx` (Delta unchanged too; Returns split onto its own sheet, new In-Hand Activity sheet, MIR→Site join fixed to prefer `Out`'s own DN column — fixes site misattribution on every numbering-overflow row). **Next step is a one-time backfill upload through the already-live `register_stock_entry`/`W-2`/`W-3` pipeline** (that pipeline only fires forward on live confirms — it will not retroactively pick up anything this pass fixed) — full handoff detail in §9A.6. | Owner / Technical execution |
| 2026-09-14 | **v3.68 — Site model confirmed: tag-first, auto-stub everywhere, enrichment fields stripped.** Owner confirmed: no Site-ID database, no lat/long/Tawal enrichment needed — site_id is a tag on every document, and SIG Site records auto-stub on first sight from **all three flows** (register_mir already did it; register_evidence_event and register_stock_entry now also auto-create SIG Site stubs on first sight of a new site_id). Enrichment fields (tawal_site_id/district/latitude/longitude) stripped from SIG Site doctype and data cleaned. The site page works via Connections: open /app/sig-site/\<id\> → cycles, visits, evidence events, stock entries, MRs all linked. The earlier Tawal enrichment (561 sites with lat/lon/region) is **overwritten/removed** — the SitesDB export stays outside ERP as an optional reference, not a data source. | Owner / Technical execution |
| 2026-09-14 | **v3.67 — Site page Connections grid live (native mechanism found: DocType `links` child table).** Owner showed the Customer Connections grid and asked for the same on SIG Site (chips with counts + create buttons, bidirectional: site page lists its docs; DN/MR forms carry the site link field — both already true via header `custom_site`). The grid is driven by the **DocType `links` child table** (`link_doctype` + `link_fieldname` per row; the old `transactions` property is dead in v15 — partial and full-doc PUTs both store null). Configured five connections: SIG Site Cycle.site, SIG Field Visit.site, SIG Evidence Event.site, Stock Entry.custom_site, Material Request.custom_site. Group-only rows (`group` set, `link_fieldname` empty) fail REST validation with InvalidFieldNameError — omit them; flat grid is fine. Refresh /app/sig-site/<id>: chips with counts appear (ZRS911: 1 cycle, 6 evidence, 1 MR), click = filtered list, + = create. | Owner / Technical execution |
| 2026-09-14 | **v3.66 — SIG Site Activity report + site-page button (the "one page per site" view).** Unified Query Report: per site, one table of everything — Site Cycles (stage/project/open-closed), Field Visits (activity/team/status), Evidence Events (event code + artifact ref), Stock Entries (purpose/status incl. DN/return/receipt/custody), Material Requests (type/status) — ordered newest first. SIG Site form gets a "Site Activity" button (Client Script) opening the report pre-filtered to the site; direct URL pattern /app/query-report/SIG Site Activity?site=ZRS911. Also added report=1 to SIG Site perm rows (query-report.run checks report-permission on ref_doctype; kept ref_doctype=SIG Site Cycle on the report after a stubborn SIG Site perm evaluation). | Owner / Technical execution |
| 2026-09-14 | **v3.63 — WH transaction drafts stage reached: all 7 types staged, 3 endpoint gaps found and fixed.** Sham pack via `register_stock_entry` against real ERP stock (Muzahmiyah bins): DN, DN_PARTIAL, TN, PR, RN, BI, CR — all **docstatus 0, zero SLE movement**, left in ERP flagged SHAM (`STE-2026-0038..0044`, `MAT-RECO-2026-00012`; cleanup register: delete after review, keep `ZSHAM1` site + `SHAM`-flagged `SIG Site` stubs). Fixes applied to live endpoint + repo: (1) **RN semantics** — was a plain receipt; now `is_return=1` + positive receipt into store + optional `rn_against` (original D.No SE) — v15 **rejects all negative Stock Entry quantities** (`validate_item`), returns flip via is_return+return_against; (2) **`nos` missing from UOM_MAP** — WH's commonest unit bounced every line (+`bag`/`bags`); (3) **BI hardcoded `IH - <custodian>`** — leaf that doesn't exist; now the real `In-Hand - SIG`. Also confirmed: SE naming series overrides explicit names (#20). Site Link validation proved live: DN with unknown site correctly fails (`LinkValidationError`) — staged `ZSHAM1` for the pack. | Owner / Technical execution |
| 2026-09-14 | **v3.64 — WH-vs-ERP Q1 purchase investigation: two parallel flows, mediation design recorded.** WH register (45 lots `026-05501→05544`, 173 lines, 108 codes, ~25.7k units) has **zero ERP trace**; ERP Q1 stock income is a separate flow: 13 PRs (SAR 749,922, all To Bill, ~23 Nokia/ABB-type codes) + 43 PIs (SAR 1.29M, update_stock=0). WH income valued ≥487K at ERP rates (67/108 codes unpriced, 18 codes missing in ERP) — consistent with owner's ~700K. **Suspected Nokia overlap** (WH 23-Feb 90×EVADA vs ERP PR 19-Feb 158.6K) flagged: per-code qty reconciliation is mandatory before any import. Mediation = S0–S4 extension: Finance question first (how the 45 lots were paid/booked — no-double-count), item crosswalk for 18 missing codes, rate sheet signed, then draft PRs keyed `SIG-PR-<P.No>` netted against the Out summary (1,205 rows, DN-linked). Files: `Purchase Jan-March 26.xlsx` parsed → `tmp/wh_purchase_q1.json`; analysis in `tmp/wh_vs_erp_income.json`. **Design only — nothing imported.** | Owner / Technical execution |
| 2026-09-14 | **v3.65 — Site structure executed: SIG Site = emergent hub, enriched from Tawal export; 4,249 records linked.** Owner decision after assessment: **no Site-ID database** (29,613-row Tawal national list not imported; site stays a tag on every doc); SIG Site remains an **emergent record** (auto-stubbed on first MIR/evidence sight). Staged/enriched **567 sites** (529 created, 37 updated, incl. 2 junk-stubs from legacy tests): `tawal_site_id`, `district`, `latitude`, `longitude` added — **561 with full Tawal attributes** (99.1% coverage; 5 unmatched = junk/test keys). New links: SIG Site Cycle/Field Visit/Evidence Event `site` Link fields backfilled (569/203/3,475), header `custom_site` on Stock Entry (2) + Material Request (50), and both endpoints now set header `custom_site` on future docs (register_mir from first line, register_stock_entry from first site line). Site-per-project stays on **cycles, not Site** (ZRW783 spans 2 projects; RV80 terminal-guard semantics). Site pages now work as the owner described: open `/app/sig-site/<id>` → Connections list cycles/visits/evidence/MRs/issues for that site. | Owner / Technical execution |
| 2026-09-14 | **v3.63 — §9A stock remediation detailed (§9A.1-9A.4): finalized WH stock position built through 13-Sep (CR-sign and item-code-case bugs found and corrected against independent SIG Full Stock Report evidence); ERP-vs-WH delta run (124 items short, SAR ~3.16M priced gap); 8 new ERP Items created (no price); bulk Stock-Reconciliation posting design rejected by owner in favour of per-site (pre-logs)/per-DN (post-logs) posting; join key (`Out.#` = MIR = `logs.DN number`) confirmed live; 369 `Out` rows found with stale Status/Date needing Old-Out override, flagged not fixed; feared "confirmed but never logged" gap checked and found already closed by Trifecta's own prior audit trail. No stock or GL entries posted yet.** | Technical execution (session) |
| 2026-09-14 | **v3.62 — Humaira granted PO creation (Purchase User via Finance Manager profile, durable) + PO value-cap logged for later.** Owner: finance creates POs (the PO-0 direction). Grant: role **Purchase User** added to the **Finance Manager role profile** (durable per the v3.42 profile-strip lesson) and directly to humaira.gilani (safwacc inherits on next profile save — both are Finance Manager, consistent with the full-finance matrix row). Purchase User standard chain verified: Purchase Order read/write/create/submit, masters read. Zero Custom DocPerm touched (no v3.44 wipe risk). **Logged later-stage (6A.10):** value-capped PO submission — Server Script on Purchase Order before_submit: `grand_total <= 50,000` submittable by finance creators, above requires an approver role (and/or workflow) — implement after PO flow proves out (PO-0). | Owner / Technical execution |
| 2026-09-13 | **v3.61 — Insights charts finalized (root cause of "empty/not finalized" pages).** Chart v3 requires **capitalized** chart_type from a fixed vocabulary (`Number/Bar/Line/Row/Donut/Funnel/Table/Map/Bubble/Sankey` — lowercase `pie/bar/line/table` reads as invalid → "no chart type or setup finalized") plus a **config JSON** mapping query columns: Donut `{label_column, value_column}`, Bar/Line/Row `{x_axis:{dimension}, y_axis:{series:[{measure}]}}` (Dimension `{dimension_name,column_name,data_type}`, Measure `{measure_name,column_name,data_type,aggregation}` — shapes read from the [develop frontend sources](https://github.com/frappe/insights/tree/develop/frontend/src2)). All 8 charts finalized (Stage=Donut, Project/Aging/Delayed=Bar/Row, Visits-per-Day=Line, 3 tables). Integrity fix: `data_query` must NOT point at the source query — the frontend treats it as a scratch pipeline and overwrites its `operations`; 8 detached scratch queries created. Dashboard `dh657cqj78` holds 8 items + 8 linked charts. build_insights_dashboard.py updated with the config map. | Owner / Technical execution |
| 2026-09-13 | **v3.60 — clickable BI Dashboard tile on the SIG Field Ops workspace.** Workspace Shortcut schema supports `type: URL` + `url` (Dynamic Link on type) — added "BI Dashboard" as the first shortcut tile, opening `/insights/dashboard/dh657cqj78` directly (no manual URL entry). Orphaned SAR Number Card records deleted; Page creation confirmed platform-blocked without developer mode (`Page.validate` throws for ALL new pages on Frappe Cloud). | Owner / Technical execution |
| 2026-09-13 | **v3.59 — Field Ops dashboard moved to Frappe Insights v3 (installed BI app); workspace reduced to counts.** Owner: "still has SAR / not informative / check existing solutions instead of basic structuring." Research + probe: **Frappe Insights v3.9.2 is installed on Neosys** with the v3 doctypes (`Insights Workbook/Query v3/Chart v3/Dashboard v3`) empty and a live `Site DB` data source — the proper BI layer (per [Insights docs](https://docs.frappe.io/insights/creating-your-first-dashboard) and [frappe/insights](https://github.com/frappe/insights)). Built via REST (`ERPNext/scripts/hr/build_insights_dashboard.py`, shapes verified against the develop sources: native query = `operations=[{"type":"sql","data_source":"Site DB","raw_sql":...}]`): workbook **SIG Field Ops**, 8 native queries (Open by Stage, Open by Project, Aging Buckets, Delayed by Project, Visits per Day, Recent Visits, Project Rollup, Closed Cycles), 8 charts, dashboard **SIG Field Ops** (`dh657cqj78`) with grid layout. Execution verified via `run_doc_method` on 4 queries (315 Initial; 377 aged 30d+; 25 visit-days last month; rollup 13 projects). **Workspace stripped of SAR**: Value cards deleted — main page is counts-only (Active/On Track/Delayed/Aged 30d+/Evidence Today); money lives in Insights (Value columns) and Project Rollup report. Notes: Insights auto-detects currency symbols in carried columns (`get_currency_symbols`) — Value columns will render ر.س inside Insights, which is correct there; project-name variants (`5g/5G`, `capex8/Capex9/Capex-9`) appear as separate projects — cosmetic normalization pending. Insights v3 ops-shape sources: [query_v3.py](https://github.com/frappe/insights/blob/develop/insights/insights/doctype/insights_query_v3/insights_query_v3.py), [ibis_utils.py](https://github.com/frappe/insights/blob/develop/insights/insights/doctype/insights_data_source_v3/ibis_utils.py). | Owner / Technical execution |
| 2026-09-13 | **v3.58 — Field Ops main page rebuilt as an informative dashboard (owner feedback: previous layout not informative).** Removed the meaningless widgets: **Visits by Activity donut deleted** (activity codes are blank until Phase 2 session facts arrive — a donut of empties is noise) and the **Visits Today card** (always ~0; visits happen on field days). Charts now: **stage pie (Count, aggregate field cleared)**, **Open by Project bar**, and a new **Visits per Day** line (Count time chart on `start_at`, last month/daily) — visits shown as recent activity, not lifetime totals. New **SIG Recent Visits** query report (last 14 days: Date/Site/Project/Cycle) as a shortcut — the per-days-and-teams view the owner pointed at (per-team columns arrive with Phase 2 reporter facts). Cards now: Active Sites, On Track, Delayed, **Aged 30d+** (new `is_aged` Check maintained by the daily scheduler + endpoint; backfilled 377), Value Open (SAR), Value Delayed (SAR), Evidence Today — every money card explicitly suffixed (SAR) so counts and currency can never be confused. `SIG FO Value *` cards renamed with (SAR); deployer fully synced (cards/charts/scheduler/field/report/workspace). | Owner / Technical execution |
| 2026-09-13 | **v3.57 — Field Ops interface v2 + Close Cycles action + two sandbox landmines found.** Owner feedback round: stage pie pinned to Count (`use_count`); new **Open by Project** bar + **SIG Project Rollup** report (per-project open/closed/delayed/value/confidence with total row); **Cycle Grid v2** restructured (state-first columns, WO/PO merged into trailing Ref, short headers, Value total row); **Close Cycles** list action = EvidenceCore Close Sites method in ERP (Actions-menu item → RV80-style immutable-warning confirm → `sig_close_cycles` endpoint writes one SITE_CLOSED event per cycle with `MANUAL_CLOSE|operator|ts` artifact, terminal+closed_by stamped, NOT_FOUND/ALREADY_CLOSED skipped; proven on a throwaway cycle and cleaned back to exactly 3,475/569). Sandbox landmines recorded in 6A.8 #31-32: **`.strftime()` is blocked** (KeyError `__import__` — datetime strftime imports `time`); use `frappe.utils.now()`/`nowdate()` — this was a **latent 500 in `register_evidence_event`** (default-date path) now fixed; and `json.loads` works at module level but raises the same KeyError inside functions — numbered params remain the payload rule. | Owner / Technical execution |
| 2026-09-13 | **v3.56 — SIG Cycle Grid query report: the EvidenceDashboard.bas main grid as a native table.** Columns `Project/Site/WO/PO/Value/Stage/Progress-dots/Next Step/Done/Days Wait/Due/Late/Last Act.` with the dashboard's sort semantics (family 5G→Capex→Incident→other; stage 4→3→2→1→5; most-Late first; site A→Z) and per-stage Next-Step rules; 568 rows live from the imported history; seventh workspace shortcut. Deployed by `deploy_cycle_grid.py` (SQL single-sourced into `deploy_field_ops_infra.py` via import). | Owner / Technical execution |
| 2026-09-13 | **v3.55 — legacy evidence import v0 executed: full Sync history replayed into ERP (dashboard populated).** `replay_ev1_batches.py` replayed all 645 EV1 batches (3,475 events, 2026-07-24→09-12) through `register_evidence_event` chronologically, idempotent + checkpointed + resumable, 0 errors → 569 cycles / 203 visits. Import-exposed bug fixed: PO-based cycle matching was not **site-scoped** — the shared Tawal PO `10001045` merged ~40 sites' as-builts into one cycle; `po`/`wo` matches now require `site_key` equality (RV80 per-site semantics), contaminated set wiped, replay rerun. Live numbers: 547 open / 22 closed; stages 315/169/27/35; 415 delayed; SAR 2.75M open / 2.39M delayed / 359K closed; flags TCN 151 / BOQ 29 / SEQ 17. Visits are session-thin (duration 0) pending Phase 2 FieldOps session integration. The replay script doubles as the onboarding import: live drain switch + one history replay needs nothing further. | Owner / Technical execution |
| 2026-09-13 | **v3.55 — Analysis re-platform recorded (Phase 3): fact/dimension model + Insights, not a VBA port; corrected the recompute-per-key note against the actual live endpoint.** Owner direction: the target for Field Ops analysis is new infrastructure — a proper fact/dimension/derived-view model surfaced through the already-installed, already-Stage-4-planned **Insights** app — not a copy of OpsKPI/EvidenceDashboard's Excel-grid-constrained logic into ERP form. Recorded in the white paper as **Phase 3**: a do-not-port list naming which v1/v2 artifacts (42-field wide cycle row, 12 slot columns, flags-as-string, stage rank and event-code semantics scattered across five `Select Case` blocks, the 90-day/N≥8/Refresh-button pattern, and the cycle-as-mutated-record model itself) exist only because Excel has no query engine; a blueprint collapsing those into conformed dimensions (`Event Code` reference table, `Flag` with deduction_points, `Project.family`, `SIG Site` lat/lon) plus a sessionization view (gaps-and-islands SQL window functions over `SIG Evidence Event`, order-independent by construction); an act-on-it/read-it split (ERP doctypes stay for the ledger, Field Visit, and a lean Site Cycle cache; medians/cohorts/trends move to Insights measures); the bitemporal (`occurred_at`/`recorded_at`) and single-metric-definition payoffs already implicit in the existing schema; and the acceptance test — a new KPI must be answerable as a measure definition, not a code release. **Also corrected, against the actual deployed script:** the v3.53 "recompute-per-key" note was written before checking `register_evidence_event_script.py` and never applied — the live, proven endpoint does an incremental `frappe.db.set_value` merge onto the existing `SIG Site Cycle` row, not a recompute. That note is now marked superseded; the real fix isn't merge-vs-recompute, it's that Phase 3 stops storing a cycle as a mutated record at all. **Nothing live is touched:** `SIG Evidence Event` needs no change (already the correct fact-table shape); the live v1 endpoint's merge logic keeps running as-is until the Phase 3 sessionization view is built and passes the same cycle conformance gate already scoped for Phase 2 (diff against `_Ops_CycleFacts`, 476 cycles — reused, not duplicated). Independent of Phase 2's timing; both are late-stage, non-WH-blocking. Tracked as new plan §6A.13 (FO3-DIM…FO3-ACCEPT, all Not started); FO2-G0's status in §6A.12 corrected from "Not started" to reflect that Phase 1 is in fact built and live. | Owner / Technical execution |
| 2026-09-13 | **v3.54 — Field Ops interface slice: Kanban board + charts + workspace content fix.** Added to the live v1 build: `SIG Cycle Board` Kanban on `SIG Site Cycle.stage` (5 columns, the EvidenceDashboard grid equivalent), two public Group By Dashboard Charts (Open Cycles by Stage; Visits by Activity last month), and the workspace content repaired so all six shortcut tiles render — first pass created the `shortcuts` child rows without the content-JSON blocks (6A.8 #5 bit again) and typed the Flow Aging shortcut as DocType instead of `Report`+`report_ref_doctype` (LinkValidationError). New shortcut set adds the Kanban view entry point. `deploy_field_ops_infra.py` reproduces everything idempotently (dry-run verified all-present). Remaining interface v2: transition medians, completion curve, data-issue notifications, family filters. | Owner / Technical execution |
| 2026-09-12 | **v3.53 — Field Ops evidence infrastructure built and proven live (v1 of the EvidenceCore mapping).** Owner direction: tune ERP to receive before RV80 sends. Deployed via `ERPNext/scripts/hr/deploy_field_ops_infra.py`: doctypes `SIG Evidence Event` / `SIG Site Cycle` (the 42-fact contract) / `SIG Field Visit` / `SIG Field Ops Settings`; `register_evidence_event` Server Script implementing the verbatim cycle-assembly rules (WO→PO→latest matching, terminal guard opening a fresh cycle on post-closure field-delivery events, stage ranks, BOQ/TCN first+latest, gross-value authority ladder, BACKFILL/REVISED/ZERO_VISIT/SEQUENCE flags, confidence, SLA anchors + `is_delayed`); **SIG Field Ops** workspace (7 public Number Cards + shortcuts) + `SIG Flow Aging` Query Report + `sig_field_ops_daily` scheduler. End-to-end synthetic EV1 pack passed all 13 checks (stage ladder 2→3→4→5, rank ladder picked ASBUILT 9,000 over BOQ 5,000, HO doc type GCL, visit facts, TCN snapshot, terminal guard spawned a fresh cycle on a post-closure warranty visit, `SITE_CLOSED` set `closed_by`, duplicate dedupe, Flow Aging correct); 76 test records deleted after the run. New sandbox lessons in 6A.8: `set()` unavailable in Server Scripts; RestrictedPython tracebacks can misattribute lines (probe before rewriting); doctype create order matters for Link fields; `flags` is a restricted fieldname; Report needs `report_name`, Number Card needs `label` + `type: Document Type`. Remaining for onboarding (RV80 side, not built by design): one POST per drained `_FO_EvidenceQ` event with the operator per-person key + ride-along on the Close Sites batch. | Owner / Technical execution |
| 2026-09-13 | **v3.53 — EvidenceCore endpoint corrected to recompute-per-key; FieldOps capture/state split (phase 2) recorded, sequenced post-WH.** Two changes. (1) Corrected the v3.52 `register_evidence_event` design before build: on each accepted event the endpoint **recomputes the affected cycle from every stored event for that SiteKey**, not an incremental upsert of the single new event — the match/stage/gross-value/flag rules are retrospective and order-sensitive (BACKFILL_LAG exists because events arrive out of `recorded_at` order), so incremental mutation would silently diverge from a rebuild done in occurrence order; recompute is cheap at this volume (2,438 events/476 cycles) and keeps semantics identical to `OK_BuildCycles`, which is what the cycle conformance gate depends on. (2) Recorded **phase 2** (owner-accepted, explicitly deferred until after the WH stock cutover — owner may start early design/build, but it is off the WH critical path): migrate `FieldOpsCore.bas`'s WhatsApp session/tag state machine off Excel. Split is capture vs. state, not "WhatsApp → Apps Script" wholesale — `code.gs` already captures/routes messages durably online, so phase 2 adds one POST per message to ERP; the session pairing, 24h hard cap, 6h grace, and delayed-end repair become ERP-side logic on Frappe's native scheduler (fixes "must open Excel for state to advance"); Excel reduces to the document generators plus a Windows-bound photo/PPT worker, with `FieldOps_DownloadPhotosByDateRange` reframed as a small local PowerShell/Node worker pulling an assigned queue from ERP (VBScript explicitly rejected as that runtime — deprecated, no error handling; repo already standardizes on `.ps1`/`.mjs`). Recorded the facts-replay-vs-decisions-migrate rule: `_FO_Sessions`/`EvidenceCache.tsv`/cursors replay from the message log, but `_FO_PhotoQ`/`_FO_FolderMarkers`/PhotoReview keep-route decisions and applied repairs must be exported, never re-derived. This is the deliberate-migration exception to sigpc white paper Appendix C.5's rejection of a second FieldOps parser — conditioned on two field-diff conformance gates (new sessions vs. live `_FO_Sessions`; recomputed cycles vs. `_Ops_CycleFacts`) both passing before any RV80 parsing code is retired. **Not built — design only**, tracked as new plan §6A.12 (FO2-G0…FO2-CUTOVER, all Not started). | Owner / Technical execution |
| 2026-09-12 | **v3.52 — EvidenceCore → ERP mapping structure recorded (evidence prompts, not sync); dashboard map + KPI + site-visit design.** Full read of the deployed RV80 modules (`EvidenceCore.bas` 1.1.2, `OpsKPI.bas` 0.1.7, `FieldOpsCore.bas` 0.3.7, `EvidenceDashboard.bas` — 13.8k lines). Key findings: EvidenceCore is **already an immutable EV1 event ledger** (17 cols, unique EventId, checksummed batches with `.ready` markers) so the owner's "prompts not sync" direction needs only one POST added to the existing `_FO_EvidenceQ` drain (which already has PENDING→PROCESSING→COMPLETED retry semantics); cycles are derived at read time keyed **SiteKey × WO/PO** (not "Site × Scope" as the 2026-09-06 CoreDashboard note said — Scope is free text on sessions); FieldOpsCore is the WhatsApp **session/visit** ingest (site visits = sessions; 24h hard cap, 6h grace, repair path); TCN-MDT lives on the `TCN-MDT` sheet + `tcnword.bas`, not in FieldOpsCore; the dashboard's data-quality flags are computed then **dropped** — a dead feature ERP will fix. White paper §EvidenceCore → ERPNext now carries the full design register: `SIG Evidence Event` / `SIG Site Cycle` (the 42-fact `_Ops_CycleFacts` contract) / `SIG Field Visit` doctypes; `register_evidence_event` endpoint (register_mir family — numbered params, per-person keys, EventId dedupe, incremental cycle assembly with the verbatim match/adopt/terminal-guard + stage-rank + gross-value-authority rules and the full flag/confidence vocabulary); dashboard map (7 Number Cards replacing the 6 AutoFilter tiles, Kanban on cycle stage, SIG Flow Aging with drill-through to MR/Stock Entry/Project cost, transition medians p50/p75/p90 with n≥8 suppression, SIG Site Visits with Employee link, data-issue notifications, 90-day rule → saved view, Run Log → native charts); RV80 changes limited to one POST in the evidence drain + ride-along on the existing Close Sites batch. **Not built — design only.** No stock-remediation dependency; next executable step is the three doctypes + endpoint + synthetic EV1 test pack on owner go. Gates: Appendix C.5 reopen recorded (a prompt-fed evidence ledger receives confirmed facts like `register_mir` — not the synced dashboard C.5 rejected); registry route row required before the writer enables; `INVOICE_GENERATED` out of scope. | Owner / Technical execution |
| 2026-09-10 | **v3.51 — Tawal allocation correction and draft reset.** Explicitly labelled, uniquely associated Retention credits now net into their Sales Invoice allocation; penalty/ambiguous negative children remain in `PENALTY_CREDIT_NOTE_REVIEW`; 26 regression tests pass. Live Oracle proof for parent `202611000041` found three Cleared/Reconciled=Yes child allocations totaling SAR 1,138,602.91. The 34 prior Tawal-only Payment Entry drafts (all docstatus 0, including erroneous manual allocation `ACC-PAY-2026-01360`) were deleted and their 34 matching hub `erp_doc` links cleared; submitted documents and non-Tawal drafts were not touched. |
| 2026-09-08 | **v3.34 — 2026 stock remediation execution plan (§9A) fixed from owner directives: OLD-OUT sheet = Jan–Mar 2026 baseline mesh and consumption source; Jan–Mar incoming to be collected ASAP; Mar-end→mid-Apr row issues get a WH-correction remediation pass; post-18-Apr consumption and Mar→today incoming import clean.** | Owner / Technical execution |
| 2026-09-08 | **v3.50 — Tawal agreements→Project sync deployed + verified; 2026 payments as PE drafts; register_mir date fix; §9A remediation plan.** Hub v1.5.0 (`syncTawalAgreementsToNeosys_`, daily trigger) proven idempotent (skip-34 run logged); 12 missing Tawal projects created (WO-2026-0027…0038) — unblocks MIR 994, whose send the owner then cancelled; all 34 2026 Tawal payments imported as PE drafts (17 remit-109 → GL 13121, 7 invoice-linked, 6 Multiple + 3 unmatched held unallocated per owner; 17 remit-813 → new GL 13125); `register_mir` fixed for RV80 `dd-Mmm-yy` dates and MIR 991 recovered as MR-26-0991; the Custom DocPerm incident that briefly wiped standard perms on 6 doctypes was restored from canonical JSONs (§ master doc). | Owner / Technical execution |
| 2026-09-08 | **v3.49 — Tawal negative-child policy amended.** An explicitly labelled Retention child with one unique canonical association is a signed offset against that same Sales Invoice: the draft Payment Entry allocates the net positive receipt, leaves the retained balance outstanding, and a future PAC/FAC parent payment may settle only that remainder. All other credit notes are presumed penalties and stop at `PENALTY_CREDIT_NOTE_REVIEW`. The legacy cutoff is on the parent payment date, so current receipts for retained 10% on 2023/2024 invoices remain eligible. This is accepted design, not a claim of deployment: current code retains the blanket `CREDIT_MEMO_ALLOCATION_REVIEW` hold until TAWAL-ALLOC-RET and its tests ship. | Owner / Technical execution |
| 2026-09-07 | **v3.46 — live scripts mirrored; partial dispatch/per-item cancellation specified as the next warehouse gate.** Read the live `register_mir`, `sig_list_ready_mrs` and `register_stock_entry` scripts through the administrator API and replaced the three repository JSON script bodies; JSON parsed successfully and UTF-8 SHA-256 comparisons were identical live versus repository. The mirrors now preserve unconditional RV80 MR submission, PO-first Project resolution, the submitted-RV80 WH-ready feed, and post-issue cleanup of disposable test site `a`. The next implementation is deliberately not a spreadsheet-only counter: an atomic ERP per-line fulfilment endpoint will create linked Material Issue entries for full/partial DNs, update issued/cancelled/remaining quantities and immutable audit events, and permit cancellation only of each line's unissued remainder. It will neither modify RV80 confirmation nor J/K formula-reference columns in WH Out. | Owner / Technical execution |
| 2026-09-07 | **v3.45 — RV80 confirmation is direct approval; submit to ERP and release to WH.** Owner direction supersedes v3.44's ERP draft/reviewer hold for RV80-originated MIRs. Live `register_mir` now submits unconditionally after its existing creation validations, so the operational chain is **RV80 Confirm → verified mirlogs → ERP Material Request submitted (`docstatus=1`) → WH-ready feed → WH importer writes Pending Out rows**. There is no ERP reviewer for ordinary RV80 MIRs; warehouse dispatch is the later operational review, where missing physical/critical details will be handled under a future explicit dispatch gate. Unknown/ambiguous Project data is retained in source-provenance fields and may be flagged, but does not hold the MR as a draft. `sig_list_ready_mrs` accepts submitted RV80 source IDs (`SIG-MIR-*`) with legacy sync states including `DRAFT_CREATED`, `REVIEW_REQUIRED` and `MR_SUBMITTED`; **`docstatus=1` is the release authority**, not those legacy labels. Resolver changed to PO/contract-first, then source Project fallback: MIR 1018 PO `10001045` correctly maps to `WO-2026-0026` (`10001045 - Colocation 2026`), its MR was corrected/submitted, and it was verified in the live WH-ready feed. `Shabakat` remains `WO-2026-0039`; 1013/1014 remain submitted and WH-ready. The live Server Script was patched directly; mirror the final live script into the repo JSON before a future JSON-based deployment so it cannot revert this behaviour. | Owner / Technical execution |
| 2026-09-07 | **v3.44 — register_mir 403 root-caused; unresolved-Project REVIEW_REQUIRED soft-hold deployed; MIRs 1013/1014 landed.** Root cause of the "token lacks permission" 403s: in Frappe v15 a doctype with *any* Custom DocPerm rows ignores its standard DocPerm rows — the single `SIG Stock Viewer` row granted for Hamid's warehouse visibility had silently locked System Manager (and everyone else) out of SIG MIR Intake, SIG MIR Intake Line, SIG Site, Stock Entry, Purchase Receipt, Stock Reconciliation and Page, so `register_mir`'s intake duplicate-check read 403'd on every send. Restored append-only via `ERPNext/scripts/restore_sig_doctype_access.py` (20 rows; SIG Stock Viewer untouched; all 7 doctypes verify 200). New rule recorded: a custom-role grant must always be accompanied by re-appending the intended standard roles to the same doctype. Policy change (owner-approved in session): unresolved Project no longer hard-rejects — `register_mir` (rebuilt on the live script, which alone carried `norm_date`/`set_name`/PM-comment; the uncommitted local working copy had regressed and was NOT deployed) now reads per-line `project_N` (RV80 always sent it), stamps raw text to `SIG MIR Intake Line.source_project_name` (new field) + `Material Request Item.custom_source_project_name` (new custom field), marks lines `PENDING_REVIEW` (new disposition value), creates the MR as a **draft** (`DRAFT_CREATED`, never submitted), sets new intake state `REVIEW_REQUIRED` with `erp_mr` linked; `PROJECT_AMBIGUOUS` (count>1) and `PROJECT_REQUIRED` join `PROJECT_UNKNOWN` as review codes; hard errors (UOM/item/qty/warehouse + new `QTY_INVALID`) still park the whole MIR in EXCEPTION with no ERP document; fully-resolved MIRs keep the live posted flow verbatim. Select options deployed before the script. Stale EXCEPTION intakes SIG-MIRI-0133/0134 snapshot+deleted (MIR-994 precedent) and both MIRs re-posted from mirlogs with original provenance (1013: 3 lines FRD002; 1014: **4** lines FRD003 — mirlogs holds a 4th line E-TPE qty 1 the transcript undercounted) → SIG-MIRI-0136 + MR-26-1013 (Draft), SIG-MIRI-0137 + MR-26-1014 (Draft), `naming=mir_name`, Project null on every item (never guessed), SIG Sites FRD002/FRD003 auto-created → مستودع المزاحمية - SIG, re-POST → duplicate. Found missing live: `Material Request Item.custom_source_line_id` (line-id idempotency key — old script wrote it into the void, even MR-26-1015) — field created + backfilled for the two new MRs; historical MRs still null (owner say-so pending). **Same-session completion (owner instruction):** Project created (`project_name=Shabakat`, Open, SIG company; doc ID `WO-2026-0039` — naming series overrides explicit names, WO-series convention kept); all 7 lines reviewed against mirlogs (exact match), project set, both MRs **submitted** (docstatus 1, Pending), intakes → `ERP_DRAFT_CREATED`; both MIRs verified live in the `sig_list_ready_mrs` WH feed with project on every line. Going forward `Shabakat` resolves at intake (project_name match) so RV80 MIRs post straight through submitted. | Owner / Technical execution |
| 2026-09-07 | **v3.41 — W-6 recorded: WH dispatch notes move from WH sheet format to ERP print formats (late stage, aesthetic).** Owner: ERP formats are better, but the switch is sequenced **after stock movement is finalized** (W-5 cutover + stock mediation complete) — until then the field keeps receiving WH-format documents and the ERP print format stays unbuilt. Added as **W-6** in the white paper's WH wing phase table (executable only after W-5 + Finance stock sign-off) and re-annotated the Material Issue voucher row as deferred-by-design. The migration swaps the paper, never the flow. | Owner / Technical execution |
| 2026-09-07 | **v3.43 — self-service API key rotation disabled (admin-only).** Owner: users must not be able to change secrets/api keys (a self-rotation would silently desync UserPasswords col V and be hard to detect). Deployed: `user_api_key_admin_only` Server Script (User Before Save — PermissionError on any non-admin change of api_key/api_secret; blocks the `generate_keys` endpoint; allowed callers = Administrator, mohammed.gain@sigtele.com, 9eskot9@gmail.com, System Manager role) + `user_api_section_admin_only` Client Script (hides the API Access section for non-admins) + the fields were already read_only. Tested live: operator self-rotation → 403; tamper PUT ignored (read-only); normal self-saves 200; admin saves 200; operator's live key unchanged. One iteration: the first script version referenced `doc` inside a function wrapper — server scripts inject `doc` at top level only (every non-admin User save 500'd for a minute until the top-level rewrite). | Owner / Technical execution |
| 2026-09-07 | **v3.42 — Hamid attendance access + workspace decluttering.** hamid.j could not see attendance (roles were Projects User + SIG Stock Viewer only). Direct HR User grants were stripped twice by the Operations User role-profile re-apply on save — durable fix: **HR User added to the Operations User role profile** (imran/ilyas/awad inherit on next save). Main-module workspaces (Accounting, Stock, HR, Projects, Buying) reordered: operationally pertinent shortcuts and link groups first, everything else under an explicit **"Other"** header; onboarding blocks and Learn-tour shortcuts demoted; Bank Reconciliation shortcut verified to point at the `Bank Reconciliation Tool` doctype. | Owner / Technical execution |
| 2026-09-07 | **v3.39 — new-transaction naming defaults aligned to legacy Flexsoft.** Owner: new finance/procurement transactions should number exactly like the legacy Flexsoft methods (warehouse transactions stay on WH voucher numbers verbatim — excluded). Evidence compared from the `Legacy Flexsoft Data` capture (Flexsoft ran ERPNext: its own series are preserved in the exports) vs Neosys defaults: JE `ACC-JV-.YYYY.-`, PE `ACC-PAY-.YYYY.-`, PINV `ACC-PINV-.YYYY.-`, PRE `MAT-PRE-.YYYY.-`, MR `MAT-MR-.YYYY.-`, SO `SAL-ORD-.YYYY.-` verified already identical — no change. **Changed (Property Setters, reversible, no DocType edits):** Sales Invoice default → `SIG-SINV-.YY.-.###` (Flexsoft format; already live in Neosys via the ZATCA flow — 86 invoices, max SIG-SINV-26-097 — so the counter continues at 098; ACC-SINV-.YYYY.- and RET variants kept as secondary options); Purchase Order default → `PUR-ORD-.YY.-.####` (continues at PUR-ORD-26-0047 — Neosys already holds PUR-ORD-26- history to 0046, so the counter continues from Neosys data per the owner rule; the Series table is a bare table unreachable via REST/Server Script — counter corrections, if ever needed, are a one-line edit in Document Naming Settings). No Document Naming Rules interfere. | Owner / Technical execution |
| 2026-09-07 | **v3.38 — PC-SEND closed (PC_ErpSyncSmoke PASS).** PCConst.bas constants filled with the Am hub /exec URL + WEBHOOK_TOKEN; `PCErpSync.bas` + `PCClearanceExport.bas` imported into the workbook alongside the amended ACN (per-person ERP key: local mirror col V, `AC_GetErpApiKey`, UserPasswords VeryHidden, refresh opened to all logged-in operators — the sigpc ACN was the last of the three to receive the amendment). New **`PC_ErpSyncSmoke`** (read-only: ACN login → hub URL/token → personal key mirrored → hub ping) replaced the misleading PC_RunH1Smoke reference for the ERP path (H1 remains the local-internals test; its crash handler now captures Err before logging, fixing the "error 0" report; smoke step tracker names the failing section — both fixed after a version-mix 450 and a missing-label bug). Smoke result: PASS — logged in as Mohammed Salah Ibrahim Algain, personal key `59d531ca…` mirrored, hub ping ok. Remaining PC gates: PC-AUG (August close via the bulk pitch), PC-WEEK (weekly Sun–Sat from September), PC-REPORT. | Owner / Technical execution |
| 2026-09-07 | **v3.37 — per-person ERP keys live end to end + ecosystem test passed.** 14 people (15 UserPasswords rows) carry `api_key:api_secret` in col V (ERPKey); AC web app gained token-protected `seterpkey` + snapshot A:V. ACN.bas (rv80+wh) amended: snapshot mapper 22 cols, `AC_GetErpApiKey()` (local-mirror lookup — keys live in local Excel, no Google round-trip at POST time), UserPasswords forced VeryHidden after every refresh (`AC_UnhideUserPasswords` escape hatch), mirror refresh opened to all logged-in operators (was sadm-only — non-admins could never receive their own key). Senders per-person-first: `MirErpSend.bas`, `WhErpSend.bas`, `WhErpImportMR.bas` (its own credential copy patched too; `_ErpMirror` creation self-cleans on rename failure — stray-Sheet4 leak fixed; dedupe falls back to Out-sheet scan). **Ecosystem test passed:** sham confirmed MIR 9001 → `register_mir` → intake + **submitted** MR-26-9001 (resolver mapped item/UOM/warehouse/Tawal project; readback_ok; re-post → duplicate) → `WhErpImportReadyMRs` consumed it with per-person auth → trial cancelled+deleted afterwards (ERP clean). `sig_list_ready_mrs` now filters `docstatus:1` — cancelled MRs never listed. Pending: MR/stock/issue role grant (non-admin keys fall back to admin config until then); Baligh keyed but no UserPasswords row; Farooq no ERP user; sigpc ACN same amendment pass. | Owner / Technical execution |
| 2026-09-07 | **v3.36 — WH importer finalized as VBA + docs aligned.** White paper WH-wing section updated: W-2/W-3 marked delivered; `WhErpImportMR.bas` recorded as a **separate module** (deliberately not inside `WarehouseMgmt.bas` — ERP bridge stays isolated from core WH logic) with its read endpoint `sig_list_ready_mrs` (pipe-delimited output, sandbox-safe); `WhErpImportReadyMRs` flow (pull ready MRs → skip journal-listed → write values at the frontier → read-back → journal → SENT_TO_WH) and the live-workbook install steps (import WhErpSend.bas + WhErpImportMR.bas, named ranges ERP_API_KEY/ERP_API_SECRET, run the macro). Remaining: TN/PR/RN/BI/CR one-line hooks at routine tails. | Owner / Technical execution |
| 2026-09-06 | **v3.32 — ERP wing → WH Out (MIR return path) planned, not executed.** White paper gained §"ERP wing → WH Out (the MIR return path)": post-cutover, the importer writes ERP-originated MR rows **directly into the Out sheet as values** (formula band removed in the target band — the same hardcoding WH's `HardcodeReadyOutRowsCore` already does), after a **declared frontier step** recorded to the hidden `_ErpMirror` journal: (a) formulas removed, (b) mirlogs last row declared, (c) Out start row declared; then a callback flips the MR's `custom_sync_status` to SENT_TO_WH. Three-layer duplication cap: ERP sent-flag (`custom_sent_to_wh`), hidden `_ErpMirror` sheet (imported MIRs + payload hash; refuses re-import and existing-mirlogs duplicates), direction ownership (RV80-origin vs ERP-origin never overlap). Dormant sentinel ("row 9999") applies: import only appends after the frontier; historical mirlogs rows untouched. Execution deferred to post-cutover. | Owner / Technical execution |
| 2026-09-06 | **v3.31 — SIGPC PC-DEPLOY closed.** Am hub project `1m-8hx_YQQ4AZr…` main file replaced with the current `sig_fetch_hub_min.gs` (`doPost` `pc_clearance` dispatch + `doGet` `pc_monthly_report` action), `sig_fetch_hub_min_pc.gs` pasted alongside, `setupSheets` run (`pc_clearance`/`pc_receipt_lines`/`pc_employee_accounts` created; 48 custody accounts seeded), web app redeployed (Version 22) on the documented runbook URL. Verified read-only over HTTP: ping ok; `pc_monthly_report` returns ok with empty rows (no clearance pitched yet). Sender-side: `PCErpSync.bas` + `PCClearanceExport.bas` exist in the sigpc repo `deployed/`; `PC_ERP_HUB_URL`/`PC_ERP_HUB_TOKEN` still empty in PCConst.bas — filling them, importing both modules, compiling and running `PC_RunH1Smoke` is the PC-SEND gate. Same-day sigpc session (context): review-HTML fixes deployed and verified in output (`review999`: badge class, cycle date ranges, chronological sort, source links); Mistral receipt OCR restored on the paid key (Script Properties `MISTRAL_API_KEY`, cell-based setter, force backfill for the free-limit `error:final` rows; site-ID trigger removed). | Owner / Technical execution |
| 2026-09-06 | **v3.30 — mirror doc names simplified to WH voucher numbers.** Owner: `MAT-STE-2026-DN26-0400` is too long — the mirror document's name IS the WH voucher number verbatim (`DN26-0400`, `CR26-0300`, …), no MAT-STE/MAT-RECO prefix. `register_stock_entry` updated, all 7 test drafts renamed live (verified by read-back). Naming convention tables in the white paper updated. | Owner / Technical execution |
| 2026-09-06 | **v3.29 — WH wing W-2/W-3 executed.** `register_stock_entry` Server Script live (draft Stock Entries / Stock Reconciliation per the document map; `custom_source_id` dedupe; explicit SE name; SR single-`qty` field). Test pack passed for all 7 types: DN/DN_PARTIAL/TN/PR/RN created (drafts, readback_ok), BI → CUSTODY_WAREHOUSE_MISSING (correct until IH warehouses exist), CR → Stock Reconciliation draft, re-posts duplicate. `WhErpSend.bas` in `wh/deployed/` (generic numbered-param sender + `WhErpSendConfirmedDispatch` for DN full/partial); **DN hook patched into `ConfirmMIR_Core`** (the single success point both DN paths share, repo `WarehouseMgmt.bas`). TN/PR/RN/BI/CR hooks: identical one-line pattern at each routine's success tail — documented, insertion pending the workbook edit pass. 6A.8 items 24–25 (SE explicit name; SR `qty`). | Owner / Technical execution |
| 2026-09-06 | **v3.28 — WH wing delineated (plan, not executed).** White paper gained §"WH wing → ERPNext": (1) **dormant sentinel "row 9999"** in the ERP intake marks the mirror frontier — old mirlogs rows stay in mirlogs (already consumed by WH Out formulas), new confirmed batches append after the sentinel; no backfill, sentinel is inert; (2) full **WH transaction map** from the white paper (DN full/partial → Material Issue, TN → Material Transfer, PR → receipt, RN → return linked to source, BI → custody, IH → Bin, CR → Stock Reconciliation, DM out of scope) each as **draft** Stock Entries keyed `SIG-{type}-{no}-{rowkey}`; (3) execution W-1 sentinel, W-2 `register_stock_entry`, W-3 `WhErpSend.bas` post-step after the Prepared/Success coordinator, W-4 shadow reconcile, W-5 cutover. W-1/W-2 buildable now (needs item crosswalk + warehouse map; no stock remediation dependency). | Owner / Technical execution |
| 2026-09-06 | **v3.27 — RV80 wing R-1 live.** `SIG MIR Intake`/`SIG MIR Intake Line` doctypes + `register_mir` Server Script deployed (numbered-param payloads — sandbox has no JSON parsing; resolver maps incl. the new Pcs/Mtr/Each UOMs; MR drafts only; auto-rename `MR-{yy}-{mir:04d}`; PM comment; read-back). Test pack live: MIR 977 re-post duplicate, MIR 980 created (9 lines, readback_ok), MIR 981 bad-item exception, re-posts duplicate. Confirmed-by = ACN operator (Obed), PM = line data. `MirErpSend.bas` drafted in rv80/deployed/ (collect mirlogs → POST → log; additive call after mirlogs read-back; manual resend). Core chain untouched. 6A.8 items 22–23. | Owner / Technical execution |
| 2026-09-06 | **v3.26 — UOM delineation: WH UOMs prevail.** Material Codes' UOM vocabulary (15 raw spellings → 9 canonical: Pcs, Mtr, Set, String, Bucket, Roll, Box, Packet, Each) is now the ERP UOM standard per owner decision. Created in ERP: **Pcs, Mtr, Each** (1:1 with Nos/Meter/Unit — factor 1, no valuation impact); Set/Box/Bucket/Roll/Packet/String already exist. `wh_finalization_plan_v5.xlsx` gains a **UOM (WH canonical)** sheet (variants, counts, ERP action, conversion). Adoption: WH-linked items move to WH UOM via UOM Conversion Detail in batches (stock_uom edits on stocked items need the conversion path, not blind edits). | Owner / Technical execution |
| 2026-09-06 | **v3.25 — RV80 wing = pure post-step, core chain untouched (owner).** White paper's VBA-side section now states explicitly: `Material Requirement → mirlogs → formulas → WH` operates exactly as today — no compromise, no change (mirlogs write invariants, frozen-MIR imprint, WH Out formulas, cursor/adjacency guards, col M/N all preserved). The only addition is a post-step after the final confirmation (mirlogs read-back verified): the verified batch is POSTed to `register_mir`; the confirmation never depends on the POST, a POST failure cannot alter mirlogs (retry or exception queue). Open point recorded: cancellation mirroring via a future `mir_cancel` endpoint; until then cancellations surface through the R-4 weekly reconcile. R-1 (intake + endpoint + synthetic fixtures) remains the next executable step. | Owner / Technical execution |
| 2026-09-06 | **v3.24 — RV80 wing → ERP structural delineation.** White paper gained §"RV80 wing → ERPNext — structural delineation & execution": boundaries (RV80/mirlogs/ERP/transport), the ERP-side contract (`SIG MIR Intake` + `register_mir` with line-id dedupe + payload-hash conflict guard + resolver + MR drafts grouped by MIR/warehouse/route, never submit, read-back verified), the VBA side (`MirErpSend.bas` hooked after mirlogs read-back; dumb sender; per-person API key), and execution phases **R-1..R-5** with R-1 (intake + endpoint + synthetic tests from the legacy `Material_Request.xlsx` fixtures) **buildable now** — deliberately decoupled from warehouse-stock remediation since the intake needs the item crosswalk, not the stock-value reconciliation. WH wing (Out/DN/transfer/return → `register_stock_entry` drafts) sequenced after. | Owner / Technical execution |
| 2026-09-06 | **v3.23 — stock mediation progress plan (1-Jan opening-first).** White paper gained §"Stock mediation — progress plan": ERP current ≠ WH current because issues were never dispatched out of ERP (drafts inflated stock all year); the gap IS the missing dispatch. Method: S0 extract WH per-part Opening rows (1-Jan basis) → S1 value-map into ERP and **re-base the Repack on the opening** (Finance signs split rates + free-text policy) → S2 roll forward 2026 with issue/Out/DN/transfer/return as **draft Stock Entries** (`register_stock_entry`) → S3 reconcile current vs WH closing + exception register → S4 cutover (ERP-only). MIR-V1 intake drafts share the crosswalk; weekly mirlogs↔ERP reconciliations run throughout. | Owner / Technical execution |
| 2026-09-06 | **v3.22 — HR obligations, provisioning, corrections (recorded from the HR-ATT execution log).** White paper gained: office-sign-in obligations (`Employee.custom_office_signin` from Basic col AJ, 17 flagged; SIG Attendance Today rebuilt as one row per expected employee — IN/OUT columns, covering-leave join, Status Not signed in / Pending / On leave / Closed, absentees first); the report now answers "who didn't sign in today" from the obligation flag, never guessed. Office user provisioning: 14 office users + `hr@sigtele.com` given strong random passwords via `sig_reset_user_password` and delivered by Maytapi (exclusions: Hamid, Algain, Baligh, `9eskot9@gmail.com`); `.local` usernames renamed to real sigtele.com addresses via `sig_rename_user`; Employee `user_id` aligned. **Owner-caught correction recorded as policy: 6 emails were invented where Basic held `0`/`S`/`#N/A` — never invent identity data; pending the owner's real addresses for those 6, then rename/reset/send only them.** Pending backlog (white paper §Pending steps): shadow-week close (HR-ATT-G3), leave policy, Repack `MAT-STE-2026-REPACK-SR01` Finance sign-off, iqama-expiry notifications, MIR-V0/V1, My Work workspace. New 6A.8 items 17–19. | Owner / Technical execution |
| 2026-09-06 | **v3.21 — material codes and purchasing convenience.** White paper gained §"Material codes and purchasing convenience — WH codes prevail, provider-assisted item intake, VBA PO creation": (1) **WH codes prevail** — the WH code is the canonical material identity (deployed in operations), the MIR catalog/UOM crosswalk keys to it, never two masters; (2) **provider-assisted new-item intake** — unmapped codes at PO logic or direct receipts call an already-linked provider API for a suggested code + description, a human confirms, then the Item is created with the WH code; (3) **VBA PO creation** — draft Purchase Orders from Excel/VBA direct to ERP (MIR-V2 pattern, operator's per-person API key per G1 1.9a), accountants submit. MIR-V0 and the free-text 3.7% open decision updated to route through the intake, with `NON-CATALOG`/exception as the fallback. New 6A.10 tracks gates MIR-G1 (crosswalk), ITEM-0/1 (intake), PO-0/1 (VBA PO). | Owner / Technical execution |
| 2026-09-06 | **v3.20 — per-person API identity/access matrix + August bulk vs September live.** White paper gained §"User identities, per-person API credentials and access boundaries": every ERP-touching action is attributable to a person via per-person API keys (machine identities stay separate and least-privilege; the shared project credential is retired only after every path has its own key). Access matrix per owner: PM/Coordinators read-only finance view; field people HR-only; Accounting full finance; Admin (Hamid) = custom **SIG Admin** (ERP Admin minus finance submit/amend/cancel). G1 gained 1.9a (per-person key issuance) and 1.9b (access-matrix role tests). SIGPC petty cash: August moves to ERP via a **bulk pitch** (bulk hub handler reusing the per-cycle pipeline; per-cycle result list is the count), not the live per-cycle POST; September weekly uses the live path. | Owner / Technical execution |
| 2026-09-06 | **v3.19 — SIGPC petty-cash clearance design accepted.** Confirmed PC cycles forward to ERPNext as draft Journal Entries via the shared Am hub (`sig_fetch_hub_min_pc.gs`, already implemented: idempotent `pc_clearance` POST, employee→custody account, 30-tier category→expense map verified live, sum-vs-`approved_spend` check, draft JE with GL read-back verification, detail persisted to `pc_receipt_lines`). Design register added to the white paper (§"SIGPC petty-cash clearance to ERPNext — draft Journal Entries") and execution tracked in new 6A.9: verify the paired file is deployed (PC-DEPLOY), build the VBA sender (PC-SEND), close August in full (PC-AUG), weekly Sun–Sat cadence (PC-WEEK), per-person pitched-invoice report month + week views (PC-REPORT). Drafts only; Finance approves. | Owner / Technical execution |
| 2026-09-06 | **v3.17 — warehouse tree completed; scope explicitly narrowed to what was asked.** Owner asked for the three missing stores only and to skip the two unmapped Flooring/Waterproofing projects for now. Created `مستودع تبوك - SIG`, `مستودع جازان - SIG`, `مستودع القصيم - SIG` as leaf warehouses under `All Warehouses - SIG`, matching the naming/parent pattern of the three existing stores exactly (`warehouse_name` + company, letting Frappe append the `- SIG` abbreviation itself rather than hardcoding it). Verified live: all 10 warehouses read back correctly, all six real WH stores now present. The In-Hand custody group from the original warehouse-tree design was left out of this batch — that was a scope decision, not a slip, and is recorded as deferred rather than silently dropped. The two non-`1000` projects stay without a customer for the same reason: owner said skip, not "unknown." | Owner / Technical execution |
| 2026-09-06 | **v3.16 — first live MIR-G1 execution: workflow fix, Site doctype, Tawal mapping.** Owner asked which cheap, zero-data-dependency items to start on and approved execution of the two safest ones plus a rule for the one blocked on missing data. (1) Fixed `Material Request Routing`'s two terminal states (`Approved for Transfer`, `Approved for Purchase`) from `doc_status=0` to `1` — verified live afterward and confirmed no MR was sitting in either state pre-change, so nothing was orphaned. This one write was initially blocked by the session's own auto-mode classifier as a workflow-sensitivity precaution; the owner reviewed and explicitly approved it before the retry. (2) Created `SIG Site` (custom DocType: `site_id`, `site_name`, `region`, `default_warehouse`) and added `custom_site` Link fields to `Material Request Item` and `Stock Entry Detail` — empty of records, ready for the RV80 `SitesDB` import. (3) Project→Customer: checked for a safe data source first rather than inferring one — no live Sales Invoice or Sales Order links a project to a customer, and the original Flexsoft `Project.xlsx` export only ever populated 1 of 25 rows, so this was correctly left open pending owner input. Owner then supplied the actual rule (project names starting `1000` are always Tawal), which resolved 23 of 27 live Projects to `Telecommunications Towers Company / Tawal` — including two whose names also mention Mobily/STC, consistent with the white paper's existing Tawal-identity assumption that the numbered PO/contract is the contracting counterparty regardless of the underlying site operator. Left unset, not guessed: 2 cancelled test projects and 2 real projects (`Flooring Collective`, `Waterproofing Collective`) with no `1000` prefix and no stated rule. | Owner / Technical execution |
| 2026-09-06 | **v3.18 — HR workspace live (6A.7 first slice) + 6A.8 customization mechanics.** The standard `/app/hr` workspace now carries three public Number Cards (Open HR Tickets, Check-ins Today, Open Leave Applications), a "Check-ins by Type" Pie Group-By chart, three shortcuts and a "SIG HR Requests" links card — the first slice of the six-workspace design, built ahead of cutover on live HR data instead of waiting. Learned and recorded as reusable tools in new **6A.8**: Number Card `filters_json` rows must carry the doctype (omission = card stuck "Loading..." forever); Group By charts restricted to Line/Bar/Percentage/Pie/Donut with a fixed timespan vocabulary and mandatory `filters_json`; **Workspace child-table rows do not render unless mirrored as blocks in the `content` JSON**; links tables are flat Card Break/Link rows; REST mechanics (doctype-prefixed filters, `Expect:` header, TimestampMismatch → idempotent re-apply); custom DocTypes via REST (Module Def first, `format:` autoname, silent field-drop if the Custom Field isn't created first); Server Script rules (no underscore identifiers, **explicit `frappe.db.commit()` or inserts silently roll back** — naming-series reuse is the tell). Same day the HR domain went live end-to-end: Maytapi WhatsApp attendance → Employee Checkin (proven on the owner's phone), `xhr` messages → SIG HR Ticket / Leave Application via `register_hr_request`; artifacts in `ERPNext/scripts/hr/`. | Owner / Technical execution |
| 2026-09-05 | **v3.15 — 6A.7 execution table extended for reports, print formats, and the Arabic font.** Owner asked for "all implementation ideas" from the aesthetic/dashboard discussion to land in both documents, not just the workspace design. Added to `MASTER-ERP-INTEGRATION.md`: a concrete workspace layout template (sidebar/navbar/page-head/card-row/block/shortcuts regions, mapped directly onto Frappe's own Number Card/Dashboard Chart/Shortcut building blocks — no bespoke frontend), a "Reports still to build" table (Site Material Ledger, MIR Fulfilment, In-Hand Custody — genuinely new, distinct from the already-native reports listed earlier) and a Print formats subsection. This plan's 6A.7 table gained five rows: the two not-yet-built print formats, the three not-yet-built reports, and — recorded as **done**, not pending — the Boutros MBC Dinkum Arabic font embed on `SIG Tax Invoice`/`SIG Tax Invoice (Arabic Name)` (2026-09-03), with `Zatca PDF-A 3B`'s equivalent treatment left as a separate not-started item since Frappe blocks direct edits to that Standard print format, and the font's commercial licence still unconfirmed for production distribution volume. | Owner / Technical execution |
| 2026-09-05 | **v3.14 — 6A.7 split across two documents, not duplicated.** Owner set the governing distinction: `MASTER-ERP-INTEGRATION.md` is the explanatory white paper for cross-domain integration (RV80/MIR, WH, Finance, HR) — ERPNext itself needs no integration explanation there, only a pointer to this plan. This plan stays the execution/gate/evidence track, specifically because deploying ERPNext itself (this whole document) is the genuinely hard part; other domains' own deployment mechanics are referenced from their own docs, not restated here. Moved 6A.7's design tokens, native-report evidence, six-workspace table, cross-cutting rules, and out-of-scope note into the white paper's new "Workspace and interface design" section verbatim (content unchanged, only relocated). Left behind here: a six-row execution-tracking table naming only the ERPNext-side tasks (MR workflow fix, Site doctype/fields, warehouse tree, opening stock, Employee KSA fields, the Workspace records themselves) against the white paper's gates. Also fixed a real naming collision found during the move: the white paper's MIR gates (G0-G6) and this plan's own core gates (G1-G5, section 5) used identical labels for unrelated things — renamed the white paper's to `MIR-G0`…`MIR-G6`. | Owner / Technical execution |
| 2026-09-05 | **v3.13 — added 6A.7, Stage 2 workspace/interface design.** Detail behind roadmap Phase 4 (section 6): six role Workspaces (Accounting, HR, Warehousing, My Work, Operations, Projects), each mapped to an existing role profile with no new doctype beyond what the MIR/stock and HR customization work already defines. Found and recorded three native primitives during investigation rather than assuming they needed building: the **Project wise Stock Tracking** report (ref_doctype Project) already returns `cost_of_purchased_items`/`cost_of_issued_items`/`cost_of_delivered_items`/`project_value` per project when run live; the **Stock** module Dashboard already ships Stock Balance, Warehouse Wise Stock Balance, Stock Ageing, Stock Projected Qty and Stock Analytics against `Stock Ledger Entry`; and every List View/Query Report already has a native Export action, which is the entire "Excel copy of the dashboard" requirement. Design tokens (font stack, brand blue `#0289f7`, gray/semantic scale, `.indicator-pill` status-badge pattern, widget card radius/shadow) were read directly from Neosys's own served `desk.bundle`/`login.bundle` CSS rather than proposed, so custom Workspace/Number Card work reads as native rather than a bolted-on skin. Explicitly out of scope: reproducing RV80's EvidenceCore/OpsKPI cross-system dashboard, which the sigpc white paper's own governance (Appendix C.5) already rejected as unnecessary overhead. | Technical execution |
| 2026-09-04 | **Stage 5.3F pipeline text updated with every April/May lesson, ahead of June/July.** Folded rules 219-226 directly into the stage-by-stage instructions rather than leaving them only in the learning loop: `disable_rounded_total` on Stage B (and why Stage E's old "genuine business rounding" claim for purchase-side halala differences was wrong — it was ERPNext's own default, now fixed); `post_sales_invoice_batch.py` named in Stage C with its UOM-fix and header-vs-item-discount checks; Stage D's manifest-decision cross-check, optional-project handling, and non-stock-item oracle caveat; Stage E's per-reference-type resolution and mixed-payment handling; Stage F's leap-year-safe date computation and "large apparent gap has three known innocent explanations, check those first" note; a new paragraph on the recurring pre-session stray-draft collision pattern and how to clear it safely; and `finalize_existing()`'s cancelled-document handling. No new document created — this is the same Stage 5.3F section June/July will execute against. | Owner / Technical execution |
| 2026-09-04 | **May 2024 closed — a genuine source-data discovery, not a process bug.** 251 JE, 2 PO, 5 PR, 130 PI, 10 SI, 8 SE, 129 PE submitted, period frozen. Stage F's AR control caught a real SAR 1,827.82 gap: `SIG-SINV-24-009` carries a genuine Flexsoft "Additional Discount Amount" (Apply Discount On: Grand Total) that the pre-built Sales Invoice payload pack's item rows never reflected, even though the pack's own header total field already knew the correct answer. Swept all 33 already-submitted Sales Invoices comparing live total to the pack's stated total — confirmed this was the only one affected, not a systemic pack defect. Fixed by cancelling the wrongly-totaled invoice and submitting a corrected `-1` replacement with the discount applied, which in turn exposed and fixed a real gap in the shared `finalize_existing()` idempotency helper (it never handled a cancelled document, only submitted/draft). Also handled one payment (`ACC-PAY-2024-01038`) with the same partial-2025-reference pattern as March's `ACC-PAY-2024-00577`, and a false-alarm row-level oracle flag traced to a legitimate non-stock freight-fee line item (rule 225) — confirmed, not corrected, since nothing was wrong. Proactive pre-staging checks (new practice since April) caught a blank-project Stock Entry and a new UOM ("roll") before they could fail mid-batch. | Owner / Technical execution |
| 2026-09-04 | **April 2024 closed — first month run entirely through the six generalized stage scripts.** 186 JE, 4 PO, 1 PR, 183 PI, 3 SI, 6 SE, 181 PE, all reconciled to within immaterial rounding (largest delta SAR 3.93), period frozen. Confirmed the `disable_rounded_total` fix works: zero rounding_adjustment across all 183 April PIs. Found and fixed two new systemic bugs: (1) `post_stock_entry_batch.py` never filtered by manifest `decision`, so it staged and submitted 2 `SKIP_SUPERSEDED` originals alongside their own `-1` replacements, double-posting real stock — caught via a `NegativeStockError` on the correct replacement, fixed by cancelling both superseded originals and submitting the correct ones, then fixing the script to cross-reference `document_manifest.csv` (rule 224); (2) generalized the rule-212 "`already_exists` reports success but does nothing" fix to every stager via a new shared `finalize_existing()` helper, after hitting the identical bug on Purchase Order (rule 223). Also built the missing `post_sales_invoice_batch.py` (Stage C had none before), found and mapped one new Stock Entry project code (`PROJ-0027` → `WO-2026-0018`, confirmed via the live Flexsoft project name), and cleared 4 April-specific stray duplicate drafts (same pre-session debris pattern as March, verified byte-for-byte before deleting). A year-wide sweep found ~319 more such stray drafts (PO/PR) spanning years the current pipeline hasn't reached yet; decided **not** to mass-delete speculatively — continuing to clear them reactively, only when a real rename collision blocks the current stage. | Owner / Technical execution |
| 2026-09-04 | **Root cause found and fixed for the recurring small "rounding" on purchase documents — it wasn't Flexsoft's rounding.** Owner asked why the SAR 0.25-0.91 deltas kept appearing and whether they'd grow at scale. Traced to a real, fully preventable defect: Purchase Order/Receipt/Invoice payloads never set `disable_rounded_total`, so ERPNext silently rounded every non-whole-SAR `grand_total` to the nearest whole SAR and posted the difference to `5212 - تقريب` — confirmed on live GL (e.g. `ACC-PINV-2024-00022`: clean SAR 731.58 total, rounded to 732.00, 0.42 auto-posted). This is also what forced the Payment Entry batch script's allocation-capping workaround (rule 214) — the payment wasn't mismatched, the invoice's own `outstanding_amount` was silently truncated first. Sales Invoice staging already had this set correctly (zero rounding artifacts across 29 invoices), confirming purchase-side was the actual gap. Measured accumulated impact: SAR 32.26 (756 PIs) + SAR 1.53 (18 PRs) + SAR 0.80 (12 POs) = SAR ~34.6 total before the fix — immaterial today, but would have grown roughly linearly through the rest of 2024-2026 if left alone. Fixed prospectively in all three Stage B scripts; not retroactively corrected on already-submitted documents (immaterial, and unpicking a submitted rounding line needs a reversing entry against `5212` for no material benefit). | Owner / Technical execution |
| 2026-09-04 | **Fresh Jan-March reconciliation, prompted by the rename campaign — all three months tie.** Owner asked to check Flexsoft/Neosys alignment through March; per the standing rule that a reconciliation's shelf life ends at the next rename (Stage 5.3F-3), re-ran the five controls for all three months, not just March. January's apparent SAR 32.3M gap was fully explained by two legitimate target-only postings absent from Flexsoft's own January export by definition (the opening balance bridge JE, SAR 29,379,715.28, and the costing-repost Stock Reconciliation postings, SAR 2,946,155.89) — ties to SAR 4.01 once excluded. February's apparent large gaps were a bug in the comparison script itself (hardcoded `2024-02-28` silently dropped leap-year Feb 29) — ties exactly on stock and bank/cash once fixed, immaterially elsewhere. March reconfirmed unchanged from its Stage F close. Backfilled `month_close_2024-01.json`/`-02.json` to the same format as March's, since both predate the six-stage pipeline. | Owner / Technical execution |
| 2026-09-04 | **Legacy-name rename campaign — every migrated document now carries its exact Flexsoft `name`.** Owner clarified the earlier "only SI/opening-JE get renamed" answer was not what they wanted: every doctype's live `name` should be the Flexsoft legacy id, not just `custom_legacy_id`. Renamed all 2,468 Jan-March documents across 7 doctypes (JE 888, PO 12, PR 17, PI 756, PE 755, SE 22, SI 21) via the two-phase Property Setter pattern, run as one script per doctype. Found and deleted 29 stray duplicate drafts blocking the PO/PR renames (byte-identical to their submitted counterparts, `docstatus=0`, zero GL/stock impact — confirmed before deleting, not assumed). Fixed a real Property Setter bug where the initial POST silently persisted `value=0` for a Check-type property despite the payload. GL Jan-Mar stayed exactly balanced throughout (Dr = Cr = SAR 50,722,749.17). Built `legacy_rename_helper.py` and wired it into all six batch stagers (JE/PO/PR/PI/PE/SE) so every April document is renamed to its legacy name immediately after creation, before submit — closing the gap permanently rather than leaving another retroactive pass for later. Also built the two missing Stage B scripts, `post_purchase_order_batch.py` and `post_purchase_receipt_batch.py`, generalizing the ad-hoc March logic to the same `--month=` pattern as the other four stages — every one of the six stages now has a reusable script. | Owner / Technical execution |
| 2026-09-04 | **March 2024 closed — all six pipeline stages complete.** Stage D: 7/7 Stock Entries submitted after mapping two unmapped source UOMs (`Bags`, `Packet` → `Nos`, learning-loop rule 211); row-level oracle exact match across 93 item rows vs `Stock_Ledger.xlsx`. Built `post_stock_entry_batch.py --month=`, generalizing the ad-hoc March logic for reuse. Stage E: 236 of 237 eligible Payment Entries submitted straight off, GL exactly balanced (Dr = Cr = SAR 3,401,437.22); built `build_payment_link_manifest.py` and `post_payment_entry_batch.py --month=`. One payment (`ACC-PAY-2024-00577`) was initially excluded whole because 1 of its 22 references pointed at a not-yet-migrated 2025 Journal Entry — corrected to stage its 21 resolvable references and leave the remainder named and unallocated (rule 215), rather than dropping the entire SAR 62,824.25 payment. Also fixed a real idempotency bug where the batch script's `already_exists` short-circuit skipped `--submit` entirely, reporting clean success while submitting nothing (rule 212). Stage F: fresh five-control reconciliation against the Flexsoft GL export — stock and AR tie exactly (AR debit off by SAR 0.18); trial balance/AP/bank were off by ~SAR 62,826 before the deferred payment was resolved, and ~SAR 4 (accumulated halala rounding, immaterial) after. No alignment JE to `1911` was needed. `acc_frozen_upto`/`stock_frozen_upto` advanced to 2024-03-31, closing the month. Clarified and confirmed live that only Sales Invoice and the opening Journal Entry get the two-phase legacy-name rename; every other doctype (JE, PO, PR, PI, PE, SE) stays on its live naming series with identity carried in `custom_legacy_id` only — intentional and consistent for the whole year so far, not an inconsistency (rule 216). | Technical execution |
| 2026-09-04 | **March Stage B complete; PO/PR auto-linking generalized.** 3 Purchase Orders, 6 Purchase Receipts (row-level oracle exact: 644,427.00) and 235 Purchase Invoices (371,689.39 vs 371,690.30 source — SAR 0.91 rounding on 235 vouchers) submitted for March, zero errors, no disabled accounts touched. Built `post_purchase_invoice_batch.py --month=`, generalizing the Jan/Feb pilot logic with one real improvement: PO/PR references resolve automatically by `custom_legacy_id` at staging time instead of deferring every linked invoice to a manual pass (rule 208) — the coupling-work concern raised at the start of the March cycle. Neosys platform backup `5e7vdthid2` taken before Stage C (Sales Invoices) as the rollback point for everything through Stage B. | Technical execution |
| 2026-09-03 | **v3.12 — Stage 5.3F rebuilt as a named six-stage pipeline.** Auditing every artifact `outputs/migration_2024/` produced while closing Jan/Feb found two things: (1) a complete, correctly-classified **full-year** 2024 manifest already existed before any of that work started — `document_manifest.csv` / `import_pack_index.json` (3,777 source parents, every doctype), `je_manifest.csv` / `monthly_import_index.json` (Journal Entries, already broken out by month), `family_source_packs_2024.jsonl` (full row-level payloads) — none of which need rebuilding for any later month; (2) despite that, ~70 uniquely-timestamped one-off scripts and JSON outputs were produced improvising a pipeline around it, one exception at a time. Replaced the previous flat six-step loop with six named stages — A (standalone Journal Entries, always first, zero dependencies), B (PO → PR → PI dependency chain), C (Sales Invoices, legacy mode), D (Stock Entries, classified before staged), E (Payment Entries, always last, including the future-dated-advance handling this session added), F (reconcile and close) — each with one reusable `--month=` script and one status artifact (`month_close_YYYY-MM.json`) instead of a new file per problem. Generalized the standing rule: one script per stage, parameterized by month; one artifact per month. Confirmed via the existing `invoice_je_overlap_2024_01_02.csv` check that Flexsoft's JE and Invoice/Payment populations are genuinely distinct sources (0 overlaps found on 9 tested) — the real Jan/Feb effort was payment-to-invoice reference linking and PO/PR/PI dependency chaining, not JE/PE deduplication — and made that overlap check a standing per-month gate rather than a one-off. | Technical execution |
| 2026-09-03 | **v3.11 — held payments resolved; five operational lessons folded into the monthly loop.** The three held Jan/Feb payments (SAR 875,889.93) are not missing imports — each predates its own invoice by weeks to months (invoices dated March/June 2024). Imported as standalone unallocated advances with `custom_legacy_id` set, to be allocated via Payment Reconciliation once their invoice's month is reached; Payment Entry population is now 518/518 exact and `2261` (Payables) ties to Flexsoft within SAR 3.22. Added this as a standing exception to Stage 5.3F step 1. New Stage 5.3F-3 records five process defects found while closing Jan/Feb, generalised for every future month: (1) repost by source Transaction, not by item, when many items share one voucher — cut the Stage 5.3F-0 job count from ~289 to 15; (2) the repost scheduler runs hourly, not continuously — a queued job is normal, not a backlog, and a Desk-side 'Execute' click forces an immediate run when the API-level trigger is blocked; (3) a rename pass invalidates any script that hardcodes a pre-rename document name — resolve by `custom_legacy_id` and re-resolve the current name at time of use; (4) a failed repost can leave a partial Bin/GL mismatch even though it wrote nothing to GL; (5) a reconciliation artifact has a shelf life and must be re-run after any subsequent import, repost or rename before being cited. Corrected the Stage 5.3F precondition text, which still said Neosys was on FIFO after Stage 5.3F-0 had already switched it to Moving Average. | Technical execution |
| 2026-09-03 | **v3.10 — bounded repost execution started.** The active scope is 289 item/warehouse chains across 463 Stock Ledger rows. The first chain (`A-AC-LG-1.5T` / Sulai) was submitted as repost `37s1hkac52`; the runner stopped while it remained queued, preventing overlapping jobs. Continue sequentially by offset only after completion and verification. | Technical execution |
| 2026-09-03 | **v3.9 — minor stock residual deferred by design.** The Jan–Feb SAR 0.01 stock difference is retained as a named, evidenced correction-pass item. It is not silently absorbed and does not block the costing-policy conclusion; the release gate still requires repost completion and the five-control monthly close. | Owner / Technical execution |
| 2026-09-03 | **v3.8 — costing remediation executed and made a release gate.** Flexsoft's Moving Average policy and fractional `Nos` are now active in Neosys after a verified backup; 268 historical item overrides were set before the global change. Incorrect posted `STE-2026-0010` was cancelled through the supported API and recreated/submitted as `STE-2026-0010-1`, preserving source ID, timestamp and C-CNL `0.5 x 35.00`. Existing posted stock history still requires `Repost Item Valuation`; the singleton job `9umta0b297` is queued and must be polled before any retry. Full item/warehouse repost plus row-level Flexsoft comparison and Jan–Feb account/stock/AR/AP/bank reconciliation are mandatory before March or any further stock wave. Cancelled predecessors remain for audit and are excluded from active deduplication. | Technical execution |
| 2026-09-03 | **v3.7 — row-level valuation verification adopted as the standing stock gate.** Refined from "repost and check the aggregate" to "verify every stock row against Flexsoft's own figures." Clarified the mechanism: receipts already carry the source rate directly (proven exact on `MAT-PRE-2024-00026`); issues are engine-computed and cannot be overridden, so verification replaces injection there. Because Moving Average is deterministic, an exact match is proof the whole chain was replayed correctly, and any mismatch names a specific defect instead of being written off as engine noise. Applies to all 252 remaining stock documents, not only Jan/Feb. | Technical execution |
| 2026-09-03 | **v3.6 — root cause found for the stock variance; correction is now blocking.** Flexsoft uses **Moving Average** costing, Neosys is on **FIFO** — proven by tracing `C-FNC` (520 units value at 51,355.96 vs 51,325.00). UOM `Nos` also carries `must_be_whole_number = 1`, rounding a source 0.5 issue to 1.0. The two together are exactly the SAR 13.46 Jan/Feb variance (30.96 − 17.50). Closes preflight action 8 with the opposite answer to the one assumed. Added Stage 5.3F-0 (blocking correction, 30 documents to re-value — correct, do not revert) and Stage 5.3F-2 (monthly alignment: per-account lines, materiality gate, balance-sheet account `1911 - تسوية شهرية للترحيل`, trend tracking). Corrected an earlier recommendation to place the alignment account under Expense — that would have pushed migration artifacts into P&L and made monthly profit differ from Flexsoft. | Technical execution |
| 2026-09-02 | **v3.5 — rollback plan added.** `migration_2024_preflight.md` section 7 now carries rollback decision criteria, a document-level unwind path (drafts → January JEs → opening JE → stock reconciliations in **reverse** submission order), the Frappe Cloud restore points with what each loses, and a post-rollback verification checklist. Summarised here as Stage 5.3F-1. Recorded that as at 2026-09-02 the posted January 2024 state ties on every control and **no rollback is warranted**. Also recorded two code defects that survive any rollback: the `post_jan_je_batch.py` idempotency check (already produced 3 duplicates of 266, and fails outright above 500 journals) and the `reconcile_jan_2024.mjs` Excel date parsing, which reads 829/5,137,976.78 as 850/4,869,910.71 — the export is not stale. | Technical execution |
| 2026-09-01 | Added Flex source discovery and v3.5 execution roadmap. Flex GL carries SAR 32,325,871.180 debit/credit before 2024 with no 2020–2023 movement; the first observed GL postings are 1 Jan 2024. Stock Ledger starts at 2024-01-01 00:00:01 through `MAT-RECO-2024-00001`. The pilot now begins by mediating the carried ledger opening against the January-2024 stock-reconciliation GL effect so inventory is opened once, followed by 2024 and 2025 checkpoints before 2026 continuation. | Technical execution |
| 2026-09-01 | **v3.5 — full-history route made the preferred optional pilot.** Preserve and reconcile non-cancelled Flex history from the ERP period onward in the one Neosys ledger, subject to a backup, non-production proof of the legacy-ZATCA bypass, chronological batch loading and a 31 Dec 2025 account-by-account Flex-to-Neosys mediation. Posting date/time, not creation/modified/due/delivery dates, now governs cutoff membership; backdated/late-posted records require an exception register. The former opening-plus-2026 and separate-archive route remains the documented rollback fallback. Pre-2026 draft deletion is suspended during the pilot. | Owner / Technical execution |
| 2026-09-01 | **v3.4 — mapping feasibility proven (Stage 5.3A-2).** Every 2026 GL line was resolved against live target masters before building any importer. Accounts: **zero misses** across all 4,579 lines and all five voucher types. Cost centres: only two need action — `رئيسي - S` → `Main - SIG` (covering all 3,722 JE lines) and `10001045 - Colocation 2026 project`, which must be created (P11). Parties: **six** unresolved names in the entire replay, all naming variants with obvious target matches, now an explicit crosswalk requiring approval (P12); the Tawal alias and one Arabic spelling carry SAR 17.2m and need named confirmation. This reclassifies the Journal Entry importer from largest risk to largest volume but low risk, and moves residual risk to the unverified invoice-level AR/AP extract. Also corrected a sequencing error: the platform backup (P9) now runs **first**, before P4 and P5 delete 328 drafts. | Technical execution |
| 2026-09-01 | **v3.3 — consistency pass across the document set.** Refreshed the checklist status summary to the measured position and retained the 2026-08-29 snapshot beneath it. Completed the live test-document register (`SINVTest-0003` and `INV-2026-0001` were both missing) and recorded the two unallocated AR items. Rescoped gates G-TB, G-MD and G-PO/PR to the finalized 2026 scope. Marked the superseded 86-PO staging paragraph and the Material Request staging note. Made the VAT pack's dependency on `2281` explicit and moved scenario 2.9 to a pre-replay decision. Corrected the G5 entry condition — the replay creates no new ZATCA-reportable document, so it is gated by the Stage 5.3E-1 proving run, not G4 — and revised the G5 estimate from 15–25 to 30–45 days against the measured scope. Added definition-of-done item 7: no migration row in `Zatca Transactions` and a continuous ICV/PIH chain. | Technical execution |
| 2026-08-31 | **v3.2 — AR/AP opening resolved as legacy opening invoices.** The owner requires the payment-to-invoice link and the physical document trail for the accounting firm, so outstanding 2025 documents are imported as **submitted `is_opening` invoices** at original date and number, against `Temporary Opening`, with no tax rows, `custom_is_legacy_import = 1` and the original PDF/QR attached; the opening JE then carries no AR/AP lines. Drafts were considered and rejected — a Payment Entry cannot reference a draft, which is the whole point. Membership is defined by outstanding balance at 31 December 2025, not by invoice month, so the set ties exactly to AR 8,041,288.63 and AP 6,164,951.84. Two consequences recorded: `validate_sales_invoice` becomes a **third** mandatory bypass point because opening invoices carry no tax rows, and a `Temporary Opening` account must be created (P10) as none exists on the SIG chart. | Owner / Technical execution |
| 2026-08-31 | **v3.1 — execution order set.** Added Stage 5.3A-1 (two gating decisions) and restructured the preflight into three waves: Wave 1 is the single ZATCA app change plus its proving run and needs a deployment, so it precedes any import; Wave 2 is data preflight and runs in parallel; Wave 3 is the opening. Added Stage 5.3E-1, a three-test proving run that checks the legacy bypass, **re-checks that live B2B enforcement still blocks (the outstanding B11 negative regression)**, and verifies legacy QR rendering — with the blast radius bounded to a disposable minimal-value invoice. Recorded a newly found hard constraint: `1331` and `2261` are party-typed, so the opening AR of SAR 8,041,288.63 and AP of SAR 6,164,951.84 cannot post as lump sums and the 31 Dec 2025 outstanding-by-party extract is a missing prerequisite. Separated legacy evidence fields from the active ZATCA fields. | Owner / Technical execution |
| 2026-08-31 | **v3.0 — plan finalized.** Owner decisions: Flexsoft 2026 transactions are trusted as entered and replayed faithfully month by month, with a monthly reconciliation register replacing the Class A–E per-document approval register and a post-replay correction pass (Stage 5.3G); pre-2026 drafts are deleted from Neosys rather than retained; the SNB bank feed is forward-only and plays no part in the migration; account `2281` is approved for re-enablement. Stage 5.3 rewritten (5.3A–5.3I). Live re-verification corrected six stale facts in section 1.2 and added risks R9–R12. Opening position proven: 31 Dec 2025 stock SAR 5,725,006.11 ties exactly to trial-balance account `134`. 2026 warehouse mapping resolved per receipt from the Stock Ledger. | Owner / Technical execution |
| 2026-08-31 | Confirmed Flex Sales Invoice eligibility: submitted invoices remain in the 2026 replay scope whether Paid, Unpaid or Overdue; only genuine Drafts are excluded. `SIG-SINV-26-005` verified as submitted (Draft → Unpaid), QR-attached and currently Overdue. Strengthened the required `custom_is_legacy_import` design: legacy accounting/stock posting may proceed only with ZATCA clearance, reporting, retries, credential use and active hash/ICV-chain mutation suppressed; original QR/XML/PDF are retained as legacy evidence. | Owner / Technical execution |
| 2026-08-31 | Owner selected a 1 January 2026 financial cutover. Added Stage 5.3A/B: document-level replay classification, existing-draft treatment, chronological submission controls and mandatory monthly reconciliations; August opening/closing-stock plugs are prohibited. | Owner / Technical execution |
| 2026-08-29 | B16 resolved: approved legacy-preserving cost-centre structure (`SIG` → `Main`; bilingual departments; Operations/Projects combined; Procurement separate; no Contracts layer; Capex-8 placement exception) | Owner |
| 2026-08-29 | v2.6: Stage 2 recorded in section 6A — print-format remainder, Maytapi WhatsApp delivery (sandbox probed: no base64), retention/advance/discount structures A vs B, VAT reporting position, and Sales Order progress billing | — |
| 2026-08-29 | v2.5: B11 deployed (`8ac61f5`) and the deferred-clearance fix confirmed present by content diff, not ancestry; 10 named users created; platform backup taken 15:50 | — |
| 2026-08-29 | v2.4: B11 guard committed (`81cdfc7`) with a deferred-clearance trap fixed before commit; B17 closed — `custom_legacy_id` added across 19 migration doctypes; baseline section 9 corrected from `sig_` to `custom_` | — |
| 2026-08-29 | v2.3: B14 closed — `SIG-SINV-.YY.-.###` applied with counters 83/179/91, next invoice `SIG-SINV-26-092` | — |
| 2026-08-29 | v2.2: invoice QR design accepted — signature style with the SIG centre mark; 3.4a restated against the approved design, 3.4b (wire into the QR attachment path) and 3.4c (prove configuration-level fallback) added | Owner |
| 2026-08-29 | v2.2: B13 closed — non-approved VAT ledgers disabled, `2281` is the only selectable tax account | — |
| 2026-08-29 | v2.1: migration-readiness baseline set — B15 closed (Riyadh Warehouse default), test masters deactivated and tagged, config fixtures exported, cost centre file re-captured (B16 raised for identity remapping) | — |
| 2026-08-29 | v2.0: reversals converted to proper credit/debit notes, ledger flat; B15 raised — Stock Settings default warehouse is a dead link | — |
| 2026-08-29 | v1.9: ledger brought to zero on every account; test documents retained with their reversals rather than purged; full-site wipe considered and rejected | — |
| 2026-08-29 | v1.8: B14 decided — Sales Invoice adopts `SIG-SINV-.YY.-.###` with counters continued from the legacy dump (2026 → 91) | — |
| 2026-08-29 | v1.7: B10 closed — both test sales invoices reversed and verified, residual SAR 0.23 accepted by the owner as immaterial | — |
| 2026-08-29 | v1.6: designated `9eskot9@gmail.com` as the integration identity; removed API key/secret values from the baseline; recorded the supplied pair's 401 and made secure secret-store preflight the next gate | Technical execution |
| 2026-08-29 | v1.3: owner accepted Phase 2 deployment; B4 closed by excluding company `D`; B6 closed after Frappe Cloud confirmed deployed revision `d8aa877`; API credential hardening moved post-launch; B8 cancellation approved; B9 made the next technical gate; named-user migration added | Owner |
| 2026-08-29 | B9 closed: `ACC-SINV-2026-00008` cleared through the production path with distinct delivery/due dates and verified UBL `ActualDeliveryDate`, hash, UUID and QR | Technical execution |
| 2026-08-29 | Plan v1.0 finalized; local capture row counts verified; `INV-2026-000x` and `SIG-Production-CSID-01` recorded as superseded evidence | — |
| 2026-08-29 | v1.6: B10 reversal drafts created and verified (`INV-2026-0001`, `ACC-JV-2026-00001`); submission blocked at the execution layer; B14 raised — the naming series reissued `INV-2026-0001`, colliding with superseded historical evidence | — |
| 2026-08-29 | v1.5: full live GL measured (15 entries, 5 vouchers) and B10 quantified; B12 raised — `ACC-SINV-2026-00001` booked 110% VAT into the non-approved `VAT - SIG` account; reversal drafts scripted but blocked at the execution layer | — |
| 2026-08-29 | v1.2: live ZATCA state verified read-only — B2 closed (all six checks pass on the linked production chain, expiry 2027-08-28); B9 raised (delivery-date fix unproven on the current site); `SIG-Production-Compliance-CSID-2026` recorded as the non-passing record | — |
| 2026-08-29 | v1.1: legacy capture closed — Item Price corrected from 2 to 829, Material Request from 1 to 67, Stock Entry and Sales Order landed, Address/BOM/Project rebuilt with child tables. B4 replaced: the open issue is the company `D` permission boundary, not missing exports | — |

<a id="stock-remediation-history"></a>
## 9A. 2026 stock remediation — execution plan (owner directives, 2026-09-08; superseded in detail 2026-09-14)

Refines the Stage 5.3 stock mediation (v3.23 S0–S4) with the owner's data-reality dates.
**Baseline decision: the WH OLD-OUT sheet is the basic mesh for Jan–Mar 2026** — it owns
the per-part opening position and the Jan–Mar consumption. Plan version v3.34.

The 2026-09-08 sketch below (Facts fixed / Execution stages / Standing constraints) is kept
as the original directive record. **§9A.1–§9A.4 (added 2026-09-14) are what was actually
built, checked against independent sources, and corrected** — read those for the current,
detailed state; the original table's specific dates (mid-Apr, 18-Apr) turned out to be a
confidence gradient rather than hard cutoffs once the underlying data was worked directly (see
§9A.1). Full session detail lives in the `wh` project's
`docs/plans/WH_Stock_Remediation_2026.md` (twenty-two dated passes); this section is the
condensed, ERP-facing summary.

### Facts fixed by the owner

| Window | Consumption (issues) | Incoming (receipts) |
|---|---|---|
| Jan–Mar 2026 | **OLD-OUT sheet is the source** — parse it as the consumption journal | **Collect ASAP** — not yet staged |
| Mar-end → mid-Apr | Known problem rows | (same remediation pass) |
| Post-18-Apr 2026 | **Clean — import as-is** | Clean |
| Mar → today | — | **All warehouse incoming clear — import as-is** |

Corrections (WH `CorrectionMgmt`) are the sanctioned tool for the problem-row fixes.

### Execution stages (extends S0–S4)

| Stage | Work | Gate / output | Status 2026-09-14 |
|---|---|---|---|
| R-2026-1 | Export OLD-OUT (Jan–Mar 2026 band): per-part opening mesh + issue rows → staging | Row counts + value tie to WH's own Out sheet totals; item crosswalk 100% (WH codes prevail) | **Done** — see §9A.1 |
| R-2026-2 | Collect Jan–Mar 2026 incoming (receipts) — owner supplies data ASAP | Receipt journal ties to warehouse records; gaps listed as exception rows, never guessed | **Done** — Excel purchase sheet is the source, cross-checked against `logs` PR (§9A.1) |
| R-2026-3 | Post Jan–Mar 2026 as draft Stock Entries: opening re-base (S1) + consumption issues (old-out) + receipts | All drafts; no GL submission; valuation re-base needs Finance sign-off per v3.23 | **Partially done** — 7 new Item masters created (no price, no stock posted yet); the actual Stock Entry posting is being redesigned per-site/per-DN, not as a single bulk Stock Reconciliation (§9A.3) — nothing posts stock or GL yet |
| R-2026-4 | Apr 1 → Apr 18 remediation: parse the problem rows, fix via WH corrections, then stage the corrected consumption | Zero unresolved rows before staging; every fix recorded as a WH correction, not a silent edit | **Superseded** — the actual boundary that mattered was `logs` Type=CR (reconciliation) sign handling, not a date-bounded "problem row" pass; fixed systemically (§9A.1), not via a WH correction pass |
| R-2026-5 | Post-18-Apr consumption + Mar→today incoming: stage clean as-is | Row-level oracle exact vs source; weekly mirlogs↔ERP reconcile continues | **Superseded** — the whole Mar1→13-Sep window is handled by one formula once CR and item-code case are both fixed correctly (§9A.1); no separate "post-18-Apr" pass was needed |
| R-2026-6 | Cutover check: ERP position vs WH closing (S3/S4 of v3.23), then ERP-only | Signed reconciliation; exceptions register empty or owner-accepted | **Done, first pass** — see §9A.2 (124 items still short in ERP, SAR ~3.16M priced gap; not yet posted) |

### Standing constraints carried forward

- Everything posts as **drafts**; Finance owns submission and the valuation re-base
  (Repack `MAT-STE-2026-REPACK-SR01` sign-off still pending).
- Weekly mirlogs ↔ ERP reconciliation continues throughout (R-4).
- The cancelled `ZZ-*` test MR/SE docs remain cancelled in ledger history (purge deferred).

### 9A.1 — Finalized WH stock position: methodology and fixes (2026-09-14)

**Chain, not a re-derivation from Jan-1 forward.** Compounding two uncertain periods (Jan1-
forward and Mar1-forward) would stack error. Instead: WH's own **Feb-28 actual snapshot**
(Makkah + Muzahmiyah native files) plus **Jizan's Feb-27 snapshot** (45 rows, PDF-OCR, no item
codes — matched to WH item codes by exact name against the Material Codes catalog, 40/45
matched) is the anchor. From there, the `logs`-based chain runs **Mar-1 through the latest
reliable date (13-Sep-2026, checked directly)**, not to an arbitrary earlier cutoff — split into
two confidence columns (01-Mar–19-Apr "lower confidence" / 20-Apr–13-Sep "super clear", the
owner's own framing) shown side by side, not blended.

```
finalized(item) = actual_Feb28(Makkah+Muzahmiyah) + Jizan_Feb27(matched)
                 + Σ [logs Purchases(PR) + Returns(RN) + Reconciliations(CR)
                      + Transfers-in(cross-scope only) − Dispatches(DN)
                      − Transfers-out(cross-scope only)]   for Mar1→13-Sep
```

Scope is Makkah + Riyadh(=Muzahmiyah, owner-confirmed alias, no separate "Riyadh" stock exists)
+ Jizan (folded in once real Jizan `Transfer` activity was found, starting 04-Mar-2026 — none
before that date). A `Transfer` row with both ends inside this scope nets to zero and is
excluded from the combined total (listed separately, not silently dropped, since real transaction
volume exists); a row crossing into/out of scope (e.g. to Al Qasim) counts as a real in/outflow.

**Two real bugs found and fixed against independent evidence, not by inspection alone:**

1. **`logs` Type=CR (reconciliation) was being excluded** from the formula, staged originally as
   "sign not confirmed from the raw export." Wrong — checked directly against
   `dump/stock/SIG Full Stock Report.xlsx` (585 per-item-warehouse ledger sheets, WH's own
   running balance), which posts the raw `qty_reduced` sign straight to its own In/Out columns.
   Six items with a negative "finalized" quantity (not physically possible) all resolved to
   their exact SIG Full Stock Report closing balance once CR was included, signed as-is —
   `C-FNC-2.4m`: -6 → 0 ✓, `C-ODU-FDTN`: -2 → 2 ✓, `E-ODU-FEN-2k`: -1 → 1 ✓, three more.
2. **Case-insensitive code drift** (`E-ALM-8p` vs `E-ALM-8P`, `E-BKR-CHINT-100-1p` vs `-1P`, etc.)
   was being hand-patched per pair found. Replaced with a systemic fix: `wh_code_normalize.py`
   folds every item code, from every source, to WH's own Material Codes catalog casing before
   it's used as a dict key — "case should never be a significant issue" (owner). `E-ALM-8P`
   merged from a fragmented, nonsensical -20 to a clean 577.5-unit figure once applied.

**Excel March purchase rows are deliberately excluded** from the receipts formula — checked
directly (not assumed): all 55 `logs` PR rows in March match an Excel row exactly (item+qty,
nearest date); `logs` PR is a subset of what Excel reports, so summing both would double-count.
18 Excel March rows have no `logs` match at all and turned out to be one-off tool purchases with
no real item code (`---------` placeholder) — not trackable stock, listed but not added.

Tooling: `ERPNext/scripts/wh_stock/build_finalized_stock_position.py` (Step 1),
`fetch_current_stock_sle.mjs` (Step 2 — pulls ERP's current stock for the three matching ERP
warehouses, `مستودع مكة`/`مستودع المزاحمية`/`مستودع جازان`), `wh_code_normalize.py` (shared),
reused from the earlier Jan-Feb pass (`build_janfeb_rollforward.py`) and the material-additions
ledger (`build_remediation_ledger_jan_feb.py`'s `ALIAS_MAP` for genuinely-different ERP-vs-WH
code strings, e.g. `E-RM-FO-50`↔`E-RM-NOK-50`, the safety-rail ÷5 unit factor).

### 9A.2 — ERP-vs-finalized delta and import staging (2026-09-14)

`build_finalized_erp_delta.py` (Step 3) compares ERP's current stock (all three warehouses,
alias-and-case resolved on both sides) against the finalized WH figure, priced with WH's own
price list (unit-checked before multiplying, same discipline as the earlier opening-stock pack).
**Result: 124 items short in ERP (down from an initial miscount of 140/130 before the alias and
CR fixes above), 134 genuine mismatches, 198 matches, 31 still needing item-mapping review.
Priced gap ≈ SAR 3.16M (absolute, not netted).** `مستودع جازان - SIG` has **zero** Stock Ledger
Entries of any kind — ERP has never posted against Jizan; every Jizan-held item reads "Missing"
by construction, not a new finding.

`build_erp_import_staging.py` split the 124 into: **116 ready to post** (ERP Item master already
exists — confirms most codes/items were already created in an earlier pass), **8 need a new Item
master first** (created 2026-09-14: `E-BKR-NDR-HU-125/-63`, `E-SNSR-DT-5L/-2L`, `C-MNT-SYB-3m`,
`E-BKR-NDR-20`, `E-DC-CAB-6` — no price set, matching the established no-speculative-pricing
precedent; `E-ODU-FEN-2k` turned out to already exist), **0 need review** (was 7; all resolved by
the CR fix in §9A.1).

### 9A.3 — Posting design, redirected: per-site (pre-logs) / per-DN (post-logs), not a bulk Stock Reconciliation

A single bulk Stock Reconciliation (set warehouse qty directly) was staged, then explicitly
rejected by the owner: it discards the site/project attribution needed for cost accounting. The
corrected design, confirmed against live data before build-out:

- **Pre-logs (Jan–Feb, Old-Out-sourced)** — post consumption **per site**, aggregated from
  Old-Out's own Site ID column (already present per row).
- **Post-logs (Mar onward)** — post **per DN**, matching `logs`' own transaction granularity —
  one ERP entry per dispatch event, not a netted total.
- **Whatever doesn't cleanly attribute to a site or DN** — bulk correction only as the fallback,
  not the default.
- **`Out-Add` rows** need finalizing and site-attributing the same way — checked directly:
  719 of 722 `Out-Add` rows are pre-cutover (`Old-Out`-sourced); only 3 are post-cutover, and
  those are explicitly marked `"No stock/log/qty change"` in Trifecta's own notes (reference
  rows, not a real gap).

**Join key confirmed live, not assumed:** `Out`'s own `#` column **is** the MIR number, and it
equals `logs`' `DN number` column directly (verified: `Out #359` has two item lines matching
`logs` DN=359's two item lines exactly, including sub-line IDs `DN26-0359-1`/`-2`). This is the
path from a `logs` DN back to `Out`'s Site ID, confirming the owner's description
("linkable per logs to DN → MIR in Out, almost all MIRs are single-sited except very few").

**Data-hygiene finding, quantified, that the per-DN/per-site build must account for:** 369 `Out`
rows have a stale `Status = Pending` despite their own `Comment` field reading `"Linked to
Old-Out row N; Confirmed Finalized Retrospective."` — WH's `Out` sheet's Status column was never
synced after Trifecta's closure pass for these. All 369 are inside the Jan-Feb/Old-Out window
already handled correctly in §9A.1 (which reads `Old-Out` directly, not `Out!Status`), so this
doesn't affect the finalized figure — but it does mean: **never trust `Out!Status` or `Out`'s own
Date column at face value for a row with an Old-Out linkage; take the disposition from the
Comment field and the date from the linked Old-Out row instead** (confirmed concretely: `Out
#281`'s own Date reads 04-Jan, its linked Old-Out row 6 reads 05-Jan — a real, not hypothetical,
one-day drift). Flag the 369 back to WH as a source-side fix; work around it here in the
meantime.

**Checked for the feared gap and found it already closed, not open:** cross-referenced all 2,775
Confirmed `Out` rows against `logs` — the ~76 that didn't show an obvious `logs` link on first
pass all carry their own audit note (`"DN bridge — ... Reclassified from no-log false
negative"`, `"Old-Out check 2026-09-10: ... confirmed per logs"`) proving Trifecta already
hunted and closed exactly this category before this session started. No unaddressed
"confirmed-but-never-logged" population exists.

**`Out`'s date corruption is worse than a rounding drift, and now precisely bounded.** Owner's own
diagnostic, checked directly: an `Out` row whose comment says `"Confirmed Finalized
Retrospective"` **and** whose DN field is a legacy-format number (`026-05002`) rather than the
`logs`-era `DN26-XXXX` format is provably a pre-cutoff transaction that inherited a corrupted date
from a WH `Out`-sheet repopulation bug — **322 such rows found**, sample dates landing in
**October 2025** (over a year off), not a one-day drift like the earlier `#281` example. None of
the 322 have any `logs` presence (they predate `logs` entirely), so re-dating them from their
linked `Old-Out` row cannot conflict with the post-cutover data. Separately, **5 of 722 `Out-Add`
rows have no Document ID** (column U) at all — 3 are the already-known no-stock-impact reference
rows, 2 (`OLDOUT-1233`/`1234`) are confirmed dispatches with no MIR ever identified (cross-checked
instead against the "Material Out Jan-March" source) — these post per-site with no document
reference, the fallback case in §9A.3, not the DN-matched one.

**Decision (owner, 2026-09-14): fix this in the ERP-posting date-resolution logic, not by editing
the live `Out` sheet.** The per-site/per-DN posting batch (§9A.4) will resolve dates for these 322
rows from their linked `Old-Out` row directly, so ERP is correct regardless of whether WH's own
`Out` sheet is ever touched. The source-side correction (322 rows, exact rule and per-row true
date already known) is recorded here as a **ready-to-execute, non-blocking cleanup** for WH to
apply to the live workbook at their convenience — not a gate on this programme, and not something
edited directly in the shared, currently-open source file without separate explicit direction.

### 9A.4 — Not yet done (Step 4 proper)

Per-site (Old-Out) and per-DN (`logs`) posting itself has not been built or executed — §9A.3 is
the confirmed design and join-key validation only. Remaining before any stock/GL posting:
build the Old-Out→site aggregation and `logs`-DN→Out-Site join into an actual posting batch
(Material Issue / Stock Entry per the confirmed pattern), decide the ERP document type per case,
and — per the standing constraint above — post everything as **drafts**, gated on Finance/owner
review before any submission, same as every other posting in this programme.

### 9A.5 — Warehouse-scope check: Al Qasim, Tabuk, and other candidates (2026-09-14)

Everything above (§9A.1–9A.4) was scoped to `{Makkah, Riyadh, Jizan}` only. Owner flagged this
directly ("you didn't account for tabuk qasim?") — checked every WH source and the ERP side for
all warehouse labels that appear anywhere, not just those two. Findings:

- **Al Qasim — folded into SCOPE and the chain, opening confirmed 0, matches cleanly.** WH-side
  footprint is substantial: `logs` sheet `Stock 5` (609 entries, DN+CR only, 2026-03-10 to
  2026-08-16), `Transfer` sheet (138 rows in/out), `Out` sheet `WH` column (475 rows, dated
  05-May-2026 — a single bulk-entry batch, not real per-row dispatch dates, same date-corruption
  pattern already known from `Out`), and a live `Stock 5` tab in `WH.xlsm` labelled "Al Qasim".
  First attempt tried the chain in isolation (Al Qasim treated as its own scope, opening=0 at
  Mar-1) and checked it against `SIG Full Stock Report.xlsx`'s own live "Al Qasim" ledgers — that
  **failed badly** (only 4/55 items matched within 0.5 units). Owner corrected the read: the
  opening genuinely is 0 (same no-baseline case as Jizan, not an unknown to route around) — the
  isolated test was invalid because it left Al-Qasim-facing `Transfer` rows counted as external
  boundary crossings for Makkah/Riyadh/Jizan instead of internal reallocations once Al Qasim is
  properly in scope. Fixed by adding `"Al Qasim"` to `SCOPE` and `"Stock 5": "Al Qasim"` to
  `LOGS_SHEET_TO_WH` in `build_finalized_stock_position.py` (opening defaults to 0 automatically —
  no snapshot term needed) and re-running the full pipeline (Steps 1, 2 — added
  `مستودع القصيم - SIG` to `fetch_current_stock_sle.mjs` — and 3). Verified twice: (1) the
  previously-delivered Makkah/Riyadh/Jizan combined figures barely moved (3 items shifted by 0.1
  units, well inside tolerance — confirms the isolated test's large mismatches were a scoping
  artifact, not a real gap), and (2) Al Qasim's own 5 nonzero-today items (all fractional
  cable-offcut remainders, 0.1 units each) land as **Match** in the closure package's standard
  Delta sheet, same tolerance and categorization as every other warehouse — no special-case
  handling needed. ERPNext's `مستودع القصيم - SIG` warehouse still has **zero Stock Ledger Entries
  ever posted**, shown as its own "ERP Al Qasim" column in the delta (same informative-zero
  treatment already applied to Jizan) — expected given the finding above, not a new surprise.
- **Tabuk — checked, genuinely no data anywhere, correctly out of scope.** `WH.xlsm` has a `Stock
  3` tab labelled "Tabuk"/"Tk", but every one of its ~400 row-numbered rows is a fully empty
  template — zero item codes, zero quantities. Zero `logs` entries reference it (no `Stock 3` rows
  in the `logs` sheet at all). Zero `Transfer` rows reference it. `SIG Full Stock Report.xlsx` has
  no Tabuk-suffixed sheets and no "Tabuk" rows in its "List" index. ERPNext's `مستودع تبوك - SIG`
  warehouse has zero Stock Ledger Entries. This is not an oversight to fix — there is nothing
  recorded anywhere to reconcile.
- **Also found while checking (`Out` sheet's `WH` column has more labels than expected) — all
  confirmed dormant, correctly out of scope:** "Jeddah", "Madinah", "Taif" appear on a small
  number of `Out` rows (55, 44, 12 respectively), but every one is dated 14-Jan-2025 through
  12-Jan-2026 — before or right at this programme's Jan-1-2026 start — and none of the three has
  any `logs` entry, any `Transfer` row, or any sheet in `SIG Full Stock Report.xlsx`. Read as
  closed-out/legacy labels with no current footprint, same logic as Tabuk. Also found ERPNext has
  a `مستودع السلي - SIG` ("Al Sulai") warehouse with 1,447 old SLE rows (2024-01-01 to
  2025-09-14, i.e. entirely before this programme's period) now fully zeroed out — a closed
  legacy ERP warehouse with no corresponding WH-side sheet or label at all; out of scope for the
  same reason.
- **Net effect on everything already built:** `WH_Finalized_Stock_Position.xlsx`,
  `WH_Finalized_ERP_Delta_2026.xlsx`, and `WH_Closure_Package_2026.xlsx` were all regenerated with
  Al Qasim in `SCOPE`/`SCOPE_WH`. Previously-verified Makkah/Riyadh/Jizan figures are effectively
  unchanged (3 items moved 0.1 units, inside tolerance). The closure package's "Delta vs Full Stock
  Report" sheet now carries Al Qasim's items through the same Match/Surplus/Shortage/opex
  categorization as the other three (counts unchanged from the pre-Al-Qasim run — 330 Match, 111
  implied-zero, 9 opex, 4 shortage, 2 surplus — Al Qasim's own items all landed as Match), with an
  "Al Qasim Actual" column added for transparency. A one-line "Other Warehouses (checked)" sheet
  documents Tabuk and the other dormant labels below.

### 9A.6 — Out sheet Status/DN/qty remediation pass, and the handoff to ERP upload (2026-09-14)

A full pass over the live `Out` sheet's own Status/DN/Qty bookkeeping, separate from (and
downstream of) 9A.1-9A.5's stock-*position* math — this pass never touched `logs`/`Old-Out`/
`Transfer`, so none of it moved the finalized-position numbers already verified above. What it
fixed is `Out`'s own record of which rows are genuinely, evidence-backed Confirmed, which matters
directly for the next step (ERP upload) because that's exactly the field the WH→ERP mirror keys
off.

**What was found and fixed, in order of discovery:**
- **~180 rows corrected** across: bare "Likely pending"/"To cancel" comments with no evidence
  (872 rows relabelled, prefix-only, comments preserved); a first-pass bulk-Cancelled mistake on
  148 rows caught by the owner (MIR 297 - real Old-Out history - wrongly cancelled), reverted and
  re-checked properly (28 resolved via strict Old-Out+MIR double-check, 120 left genuinely
  unresolved); twin-MIR duplicate pairs (322/331, 328/332 - one real Old-Out DN split across two
  MIR numbers, first pass had wrongly double-confirmed both twins); a **numbering-overflow
  pattern** (MIR 43→44, 373→374, 263→264, and 7 more pairs - a row's own dispatch lands under a
  *different* document number than its own MIR, same person/site, adjacent counter) found by the
  owner and swept sheet-wide; a full `logs`-vs-`Out` qty audit (16 quantity corrections, `logs`
  taken as authoritative over `Out`'s own Qty Request field, with two verified against Old-Out
  directly and one - 383's `M-FSHR-6MM`/`M-SCRW-6` - correctly reverted from a wrong Old-Out-based
  "fix" back to `logs`' 0.35, since Old-Out's own entry convention drops decimals); a genuine
  **over-confirmation bug** (31 rows Confirmed with blank DN and no real dispatch behind them -
  root-caused to a specific VBA gap, see below - reverted to Pending).
- **Root cause found and patched in `WarehouseMgmt.bas`** (source at `wh/deployed/`, not yet
  deployed into the live workbook's VBA project - see "VBA deployment" below): `ConfirmMIR_Core`'s
  post-confirm step `VerifyConfirmedDNStatusesOnSheet` force-sets a row's Status to Confirmed
  whenever its Document-ID column matches a DN just assigned in that run - by string match alone,
  never checking that *that specific row* is the one which earned the DN through its own atomic
  commit. When the same MIR number exists on two physical rows (the numbering-overflow pattern
  above, or otherwise), one confirm run can force-confirm both. Patch: the run now tracks every
  Row Key actually committed (`allConfirmedRowKeys`) and the verify step only repairs a row's
  Status if *that row's own* Row Key is in that set; otherwise it's logged for review, not
  silently force-confirmed. This is the same defensive pattern this codebase already applies
  elsewhere (row-key-based DN write-back replacing an earlier "last N rows" rule; the RV80
  intake-materialization rewrite after the MIR 935 incident) - same bug class, closed the same way.
- **Downstream reports rebuilt** with fully refreshed `logs`/`Out` data:
  `WH_Finalized_Stock_Position.xlsx` (unchanged - 456 items, confirms this pass never touched the
  position math), `WH_Finalized_ERP_Delta_2026.xlsx`, and `WH_Closure_Package_2026.xlsx` (Delta vs
  Full Stock Report unchanged - 330/111/9/4/2 - same reason; new: Returns split onto their own
  sheet (28 rows, Confirmed/IH-linked only) and a new In-Hand Activity sheet (23 rows); the
  MIR→Site join for outcome/dispatch rows now prefers `Out`'s own DN column over its MIR number,
  fixing site misattribution for every numbering-overflow row - verified on MIR 263/ZRW982).

**VBA deployment: done (owner, 2026-09-14).** The `WarehouseMgmt.bas` patch was written to the
reviewable source file at `wh/deployed/WarehouseMgmt.bas` and the owner has since imported it into
the live workbook's actual VBA project directly - the fix is live. The same MIR-number-collision
class of over-confirmation should no longer recur on live confirms.

**Handoff to ERP upload - read this before writing anything to ERPNext:**

The WH→ERP mirror pipeline described earlier in this document (§"WH wing → ERPNext", `W-2`/`W-3`)
is **already built and live** - `register_stock_entry` (all 7 transaction types tested), the DN
hook patched into `ConfirmMIR_Core`'s success path, dedupe keys `SIG-{type}-{WH voucher number}`
(e.g. `SIG-DN-DN26-0400`), drafts only. That pipeline fires **forward**, on live confirms, from
this point on.

**It will not retroactively pick up anything this remediation pass fixed.** Every row this pass
flipped to Confirmed (or corrected the DN/qty on) reflects a transaction that already happened
historically - `ConfirmMIR_Core`'s success hook never ran for these edits, because they were
direct corrections to already-past events, not new confirms clicked today. So the next step is a
**one-time backfill**, not "wait for the live mirror to catch up":

1. **Source the backfill list from `Out`'s current live state**, not from a stale cache - pull
   every row with Status in `{Confirmed, Confirmed Retrospective}` and a real DN (matches
   `DN26-\d+(-\d+)?`), same filter `out_confirmed_with_comment.csv` already uses
   (`ERPNext/scripts/wh_stock/build_wh_closure_package.py:build_mir_site_map` /
   `build_dn_site_map`). `WH_Closure_Package_2026.xlsx`'s "Outcome Txns Full" and "Returns Full"
   sheets are the curated, Site-ID-attached view of exactly this set, already split
   dispatch-vs-return with the join-key fix applied (2026-09-14) - use those as the source list
   rather than re-deriving.
2. **Reuse the existing dedupe-key convention exactly** (`SIG-DN-{dn}`, `SIG-DN_PARTIAL-{dn}-{n}`,
   `SIG-RN-{rn}`) so this backfill and the live-forward mirror can never double-post the same
   voucher, and so `register_stock_entry`'s own idempotency check does the safety work for free -
   do not invent a separate key scheme for "retroactive" posts.
3. **Post everything as drafts**, per the standing constraint repeated throughout this whole
   section (§9A.3, §9A.4) - this backfill is not an exception to that.
4. **Per-site (pre-logs, i.e. rows whose evidence is an Old-Out link) / per-DN (post-logs, i.e.
   rows whose evidence is a `logs` DN)**, per the confirmed 9A.3 design - not a single bulk
   Stock Reconciliation.
5. **Known residual gaps, not yet resolved, check before assuming the backfill list is complete:**
   - **91 rows** with no Old-Out match anywhere and no `logs` DN of their own - genuinely
     unresolved (`WH_Out_113_Unresolved_Rows.xlsx`'s "No Old-Out match" category, minus what
     the owner's own review already dispositioned). These are not in the backfill list on purpose.
   - **MIR 297's 5 items** (`E-Lit-R-L`, `E-CAB-XLP-4-35`, `E-DC-CAB-16`, `E-DC-CAB-25`,
     `M-FSHR-12MM`, site ZRW982) - no evidence found either way, left Pending, not in the backfill.
   - Two `E-Lit-MT-150` items dated **2026-09-14** (during this very session) are correctly
     excluded from `WH_Closure_Package_2026.xlsx`'s Sep-13 cutoff - check for a newer closure
     package build before treating that cutoff as still current.
   - The 322-row Old-Out date-corruption finding and the 5-row Out-Add missing-Document-ID finding
     (both from the 2026-09-14 twenty-third pass, see `WH_Stock_Remediation_2026.md`) are still
     staged, not executed against the live WH.xlsm - out of scope for the ERP backfill itself, but
     relevant if the backfill's own qty/date fields look inconsistent for a given row.
6. **Full WH diversion to ERP (later phase, not this step)**: per the existing `W-4`/`W-5` gates
   above - shadow reconcile for clean weeks, then Finance stock sign-off, then WH becomes
   read-only for stock. This remediation pass and its ERP backfill are prerequisites for a clean
   `W-4` shadow period (a dirty `Out` sheet would poison the weekly reconcile with exactly the
   over-confirmation noise this pass just removed) - not the cutover itself.

---

*(2026-09-08 v3.34 and 2026-09-14 v3.63 change-log rows are recorded directly in the §9 table above, not left pending here.)*

### 9A.7 — WH returns: route by original stock movement, link in ERP (2026-09-14)

The live WH workbook already has a return-management surface: `Return` records the WH source DN,
returned quantity, In-Hand value, source DN line/source-row-key fields, and a return event row key;
`Manage Return` aggregates dispatched and returned quantities and exposes the source DN line/key
and closed state. The fields are the right source contract, but source-line/key fields were blank
on sampled confirmed return rows. Do not infer a source row from item/site alone where repeated
lines are possible, and do not fill historical gaps by guess.

**Choose the ERP movement from the original submitted Stock Entry, not from the WH label `RN` or
the `is_return` flag:**

- If the original DN is a **Material Issue** from a physical store, receive the returned quantity
  with a positive **Material Receipt** into that same source store. Preserve Site/Project context
  and the source issue reference.
- If the original movement is a **Material Transfer** (including BI into `In-Hand - SIG`), return
  it with a **Material Transfer** from the original target warehouse back to the original source
  store, unless an explicitly approved destination differs. Do not create a Material Receipt for
  stock ERP already holds in the transfer's target warehouse. The current shared In-Hand leaf does
  not provide per-custodian Bin balances; retain custodian provenance separately until
  per-custodian leaves are approved and built.
- If the original movement, source line, item, UOM, destination, or remaining returnable quantity
  cannot be established, hold the line for review. No automatic receipt, issue, or reconciliation.

**Linkage and quantity control:** `return_against` is not a standard Stock Entry field in the
reviewed v15 schema. Keep VBA responsible for sending the immutable WH voucher/row identities,
not looking up or inventing ERP document names. The ERP endpoint should resolve the original
submitted issue using its source identity and persist a real ERP Link to that Stock Entry. Store
the WH source-row key on both the original issue detail and the corresponding return detail; the
checked-in endpoint currently reads `rowkey` but does not add it to the item row. Configure
ERPNext Connections/navigation against the Link field. The Link is traceability, not a stock
reversal or a quantity/valuation rule. Prefer one ERP return Stock Entry per original issue and
movement route; if one WH RN spans multiple issues/routes, split it into linked ERP entries under
one idempotent RN operation.

The endpoint must enforce, server-side and transactionally, that cumulative returned quantity per
source line does not exceed its submitted issued quantity (after unit normalization), and that
duplicate retries cannot receive it twice. Define the return valuation policy explicitly; a Link
alone does not prove restoration at the original issue's value. Historical RNs without an exact
source-line match remain exceptions rather than being linked by a fuzzy item/site match.

**Release gate:** draft creation/read-back is insufficient. In an isolated test context, submit
representative DN issue/partial return and BI/In-Hand return pairs, then assert Stock Ledger
direction and balances by item/warehouse, source-line linkage, cumulative caps, duplicate handling,
and valuation/GL effects. Keep production RN mirrors as drafts under the standing Finance/owner
submission gate until these tests pass. This section supersedes the v3.63 change-log shorthand
that described `is_return`/`return_against` as a proven generic Stock Entry return mechanism.

### 9A.8 — ERP upload staged: batches A/B ready as drafts, returns held, two source-data findings (2026-09-15)

The one-time backfill of §9A.6 is now fully staged — payloads built, validated read-only against
live ERP, nothing posted. Builder: `ERPNext/scripts/wh_stock/build_erp_backfill_staging.py`;
payloads `_backfill_batches.json` (register_stock_entry-ready: trans_type/trans_no/posting_date/
from_wh plus per-line code_i/qty_i/uom_i/site_i/rowkey_i);
workbook `wh/outputs/WH_ERP_Upload_Staging_2026-09-15.xlsx` (summary + gates, batch sheets, site
register, feasibility, residual, purchase parity, unresolved codes, full Batch-A row traceability).

- **Batch A — 118 Material Issue drafts** (849 lines), one per Site ID, aggregated Jan-1–Feb-28
  from Old-Out (note-filtered, 3 duplicate rows excluded), posted Feb-28, from_wh Muzahmiyah
  (Old-Out carries no issuing-warehouse column; project convention, flagged not silent). Every
  line carries its Site ID.
- **Batch B — 508 Material Issue drafts** (2,669 lines), one per WH DN voucher Mar-1–Sep-13 from
  `logs`, trans_no in WH's own voucher format taken from Out's DN column (e.g. `DN26-0359`), so
  dedupe keys `SIG-DN-DN26-xxxx` match the forward mirror's convention exactly. Site via Out's own
  DN-column join (the overflow-safe §9A.6 fix — re-verified: DN26-0264 stages under ZRW982). Only
  1 of 2,669 lines has no site (DN26-0374). DN 433 spans two sheets (the one one-warehouse
  invariant exception) and stages as two split entries. 9 DNs dropped (606/759/797/824/900–903/966):
  every line is an item ERP lacks (fence/cable-tray family) — they join the 36-code unresolved
  list (create item or extend alias first, same no-speculative-price precedent). WH→ERP quantities
  resolved through the live Item master first (the Sep-6 created WH-canonical codes win, factor 1),
  alias map only as fallback (e.g. ÷5 rail lengths↔metres handled at the UOM level, see below).
- **Read-only live validation:** all existing `SIG-*` keys are the sham/RNTEST/commissioning test
  docs — zero collisions with staged keys; Item master resolves every staged line (UOM from the
  item itself); SIG Site count 0 as designed (sites auto-stub on first post; 372-line site
  register staged). Nothing was written to ERP.
- **FINDING 1 — the closure package's "Returns Full" sheet has a wrong join (corrected in this
  staging).** `logs`' RN `dn_number` column is the RN's OWN voucher sequence (RN26-00xx), not the
  MIR: proven by the In-Hand ledger, which carries `RN26-0052` as a `source_dn_id` and
  `RN-46-20260817094745-*` row keys whose date matches `logs` RN-46. The delivered sheet joined
  that column to Out's MIR numbers; 14 of 81 RN sequence numbers (23–74) coincide with real MIRs,
  and the sheet's 28 rows are exactly those coincidental matches (its "MIR" and Site ID columns
  are wrong, its IH-linked filter never actually fired). Per §9A.7 (no fuzzy item/site joins),
  returns are restaged HELD: all 76 RN vouchers with true `RN26-xxxx` ids, items, quantities,
  warehouse, exact-evidence IH chains marked, nothing auto-posted — pending WH Return-sheet
  source-DN reconciliation and the §9A.7 endpoint additions (source-line key on the return detail,
  route-by-original-movement, release-gate tests).
- **FINDING 2 — safety-rail unit split; the finalized rail figure is unreliable (target only).**
  WH stock snapshots/report rows for `C-SFTY-RAIL-ALMN` are in 5-metre LENGTHS (Feb-28 Makkah: 54)
  while WH transaction rows are in METRES (Mar-Sep PR 2,325 fits Yaseen's metre-denominated POs;
  dispatches run 35–85 per site = fence metres; Old-Out agrees). Step 1 summed them raw, so the
  finalized 359 carries a 54×(5−1) artifact — and the closure package's "Surplus −216" rail row is
  precisely that artifact's signature: 54×5+2,325−2,040−40+60 = 575 = the report figure. WH must
  confirm the report unit before the rail residual is used as a recon target. The staged dispatch
  quantities themselves are unaffected (metres, independently evidenced) and stage into the
  canonical Meter-UOM item.
- **Gates before anything posts (workbook Summary carries the same list):**
  - **G0 (one-line code fix): DONE 2026-09-15 (v3.80).** `register_stock_entry` now resolves a
    caller UOM matching the item's own `stock_uom` (case-insensitive) before falling back to the
    WH map (UOM_UNKNOWN otherwise); proven live with a Meter line, the map path, the UOM_UNKNOWN
    guard and the duplicate guard, all cleaned up after. En route the pass also deployed the
    v3.79 field-first pack, fixed that version's mangled CR branch (UnboundLocalError on every
    non-CR call) and closed its silent `Stock Reconciliation Item.custom_row_key` field gap.
  - **G1:** returns (Batch C) stay held per FINDING 1.
  - **G2 (submission-time):** ERP bins are near-empty relative to true consumption history
    (Jizan/Al-Qasim zero; Makkah 4 items) — 2,351 (item, warehouse) shortfall rows; issues cannot
    submit until per-warehouse opening positions exist. For the rail family the prerequisite is
    also the §E Repack (ERP's 2,765 rail metres sit under `CW-T-SR-90M` + 719 under
    `CW_T_SR_INC`, both awaiting Finance's rate sign-off) so consumption hits the canonical codes.
  - **G3 (Finance lane):** Mar-Sep WH purchases (236 `logs` PR rows) vs 49 ERP Purchase Receipt
    SLE rows — 131 items gapped, priced on its own sheet. Without these postings, ERP cannot
    absorb the backfill's consumption.
  - **G4:** residual recon (296 rows outside ±0.05 after A+B projection) — the fallback bulk
    reconciliation, warehouse-attribution decision + Finance sign-off; exclude the rail row per
    FINDING 2.
  - Scope notes: 91 unresolved Out rows and MIR 297's 5 items intentionally not staged (§9A.6);
    the two Sep-14 `E-Lit-MT-150` dispatches sit outside the Sep-13 cutoff; TN/CR effects surface
    inside the residual, not as separate batches.

#### §9A.8.1 — Procedural playbook for mass-posting runs (written 2026-09-15 for the next AI/session)

Everything below was learned by breaking it first. Read before ANY bulk write run against this
site — posting, backdating, or re-running.

**Before the run**
1. **Backup first, every time** (`backup_pre_submission.mjs` pattern → timestamped folder): full
   JSON of every to-be-touched doctype + created masters + an SLE/GL proof-of-state snapshot +
   MANIFEST. A run without a backup is a run you cannot undo.
2. **Never trust a script mirror** — `live === repo` byte-compare is part of every deploy
   (`deploy_g0_uom_fix.mjs` pattern: partial PUT of the changed field only, then read-back
   compare). Two mirrors of one script WILL drift (proven twice: the mangled CR branch; the
   diverging .py comment).
3. **Refresh every cached probe/名单 file immediately before the run** — the staging builder ran
   on a stale item list once and dropped 9 valid DNs; the supplier matcher ran on a stale list
   and mis-held 3 vouchers. `probe.json`-style caches are liabilities the moment anything changed.

**While writing**
4. **Proof every purpose branch with one real call after ANY Server Script edit.** A text-valid
   edit orphaned the Transfer/Receipt elifs (Transfers silently lost s/t_warehouse — "Source
   warehouse is mandatory" pointed at the symptom, not the mangled structure). A structure
   change that passes `compile()` can still be logically dead: run one DN, one TN, one PR, one
   RN, one CR through the endpoint and read them back before touching the batch.
5. **Corrected 2026-09-16 (v3.96) — this was never about `allow_negative_stock`.** The actual
   cause of every endpoint-POST failure that session was a `Content-Type: application/json` header
   wrongly applied to a form-encoded (`URLSearchParams`) POST body, in the caller script, not the
   endpoint — Frappe hard-fails parsing the request before any Server Script logic runs. Flipping
   the flag on and off never changed the outcome; it was coincident timing, not causation. Proof: on
   the same site, the same day, single ad hoc calls without that header succeeded throughout the
   "broken" window. **Standing rule instead:** if an endpoint POST fails with `JSONDecodeError` at
   `init_request`, check the caller's Content-Type against its actual body encoding before suspecting
   the site or any Stock Settings flag — a mismatched header fails 100% of the time, deterministically,
   which a load-related cause would not. `allow_negative_stock` remains a real, separate lever for
   genuine backdated `NegativeStockError`s (rule 9 below still applies to those) — it does not affect
   whether an endpoint POST parses.
6. **Backdated inserts need `set_posting_time=1` on Stock Entry, Stock Reconciliation AND
   Purchase Receipt** — all three silently replace a supplied posting_date with today. Assert
   dates on read-back for every document, every run; the failure is invisible until you look.
7. **Valuation gate:** lines the FROM warehouse cannot price need
   `allow_zero_valuation_rate=1` — `basic_rate`/`valuation_rate` are ignored by the insert-time
   check. Zero-rated lines are provisional by construction; Finance trues them up.
8. **Negative→zero bin corrections via a recon row 417** (the sign is mis-read as an outflow).
   Equivalent effect: a small Material Receipt offsetting the negative, at the item's rate.
9. **Corrected 2026-09-16 (v3.96) — do not assume JSONDecode bursts are load; check the request
   first.** A genuine repost-queue/load condition may still exist and justify pacing (≥1.2s between
   calls) and bounded retries for true `500`/`502`/`503`, but a `JSONDecodeError` specifically means
   Frappe could not parse the request body — verify the Content-Type/body-encoding match (rule 5)
   before spending retry budget on it; retrying a mismatched header 280 times produces 280 identical
   failures, never a clearing window. Real validation failures (a `417` carrying a named exception
   like `NegativeStockError`) must never be retried — resolve them explicitly (e.g. a bounded
   `allow_negative_stock=1` window, verified off again immediately after) — distinguish all three
   classes (transient load / bad request / real validation) by their actual signature, not by which
   one is convenient to retry.

**State and resume**
10. **Resumable or nothing**: the runner persists per-document results after every call; a
    killed run resumes by skipping successes and retrying the rest. A `duplicate` response is
    success (the endpoint's dedupe is the second net).
11. **Record the run state in this plan before ending a session** — a killed background run must
    be presumed partially complete; the next session re-fetches the live doc list, loads it as
    the skip-list, and continues. Never re-derive from the staging payloads alone.
12. **Identity is `custom_source_id`, never the doc name** — the naming series ignores explicit
    names and reuses numbers after deletes. All lookups, dedupes, and registers key on
    `custom_source_id` (= `SIG-<type>-<WH voucher>`), which is also what makes a rerun and the
    live forward mirror mutually safe.

**Verdict (updated 2026-09-15, v3.87):** G0 closed; **A+B posted (635 drafts)**; **G1 COMPLETE
(76 RN drafts)**; **G2 complete to draft stage (3 recons @ WH prices SAR 4.35M + rail Repack,
the −SAR 671,826 gap = G5 quantified)**; **G3 staged (58 Purchase Receipt drafts with supplier
+ WH prices + true dates; 8 held on supplier identity; 22 lines already covered)**. See the
posted-register workbooks in `wh/outputs/`. Everything is now in ERP as ~770 reviewable,
zero-impact drafts. Before any submission: Finance rates the 20 unpriced lines, resolves the G5
rail unit (re-ties the Repack), resolves the 8 held suppliers, reviews the draft stack and
submits in order: openings + repack (Feb-27) -> purchase receipts -> DN drafts -> RN drafts;
then G4 residual recon. Payment reconciliation stays at PO/PI level (PRs carry no PE link).
Plus the §9A.7 custom ERP-Link field before RN submission.

**Note (2026-09-15, later same day):** live ERP check shows this Verdict is stale — Stock
Entries are now 780/780 submitted (0 drafts), negative bins are 0, TN transfers and 20
zero-correction entries have since been submitted. Two drafts remain: `SIG-CR-G4-MK-RAIL`
(Stock Reconciliation, held pending the rail-unit question, Finding 2) and one unrelated
live-operations `SIG-RCV-*` Purchase Receipt (not part of this backfill). Whoever runs the
next posting session should re-verify against ERP directly rather than trust this paragraph.

### 9A.9 — SIG Warehouse Workbench: ERP as the complete warehouse operating system (finalized 2026-09-15)

**Stage 1 (Correctness) — DONE and live, 2026-09-15.** Deployed and proving-pack verified:
- 5 Custom Fields live (`sig_warehouse_workbench_custom_fields.json`): MR Item ×4
  (`custom_qty_issued`, `custom_qty_remaining`, `custom_line_status`, `custom_qty_cancelled`),
  MR header ×1 (`custom_dispatch_stage`).
- The 3-bug rollup fix deployed into `register_stock_entry` (source: this repo's copy, sentinel
  `SIG-MR-ROLLUP-BEGIN/END v1`), byte-compare read-back confirmed. **Sandbox gotchas found and
  fixed that weren't previously documented anywhere in this project: the RestrictedPython
  sandbox has no `next()` and no top-level tuple-unpacking assignment (`a, b = fn()` inside a
  Server Script raises `NameError: _unpack_sequence_ not defined`; a function returning a dict
  and indexed at the call site works fine) — add both to the standing §9A.8.1 sandbox-quirks
  list next time that section is touched.** `set()` was already known-bad (§6A.8); confirmed
  again here.
- Proving pack (`ERPNext/scripts/wh_stock/prove_workbench_stage1.mjs`), live, self-cleaning, all
  checks passed: draft entries correctly excluded (bug b), `DN_PARTIAL`-keyed entries correctly
  counted (bug a — now structural, not pattern-matched), cancelled entries correctly excluded,
  one line fully dispatched does not flip the header to `DISPATCHED` while another line is still
  open (bug c). **New finding: ERPNext's own native `validate_with_material_request` already
  refuses a Stock Entry whose linked MR-Item quantity would exceed the requested quantity**
  ("total Issue/Transfer quantity ... cannot be greater than requested quantity") — confirmed
  live. This is a second, independent layer against bug (c) beyond the rollup's own capped-sum
  math, as long as `material_request_item` is set on the detail (which it is). All 5 other
  purpose branches (TN/PR/RN/BI/CR) proven still working — nothing orphaned by the edit.
- One-time backfill run (temporary Server Script, deployed/called/deleted — child doctypes
  `Material Request Item`/`Stock Entry Detail` are not REST-listable for this API token, so the
  backfill runs server-side like `register_stock_entry` itself does, not via external REST
  queries): 56 Material Issue MRs recomputed (50 real + 6 proving-pack test artifacts, cancelled
  after), 54 changed (expected — the fields didn't exist before), **0 moved backward out of
  DISPATCHED** (none of the live MIR-sourced MRs had ever actually been marked fully dispatched,
  so the bug caused no live false-positive in practice — all 56 land on `PENDING`, consistent
  with every DN against these MRs still being draft-only under the standing trial gate). Delta
  report: `ERPNext/scripts/wh_stock/_backfill_mr_dispatch_state_delta.json`.
- **Lifecycle hooks: built, deployed, and proving-pack verified live, 2026-09-15.**
  `ERPNext/SIG_Warehouse/` — a real Frappe app (own git repo, `github.com/9eskot9-max/SIG_Warehouse`,
  public, mirrors `sig_whatsapp`'s layout exactly), containing
  `sig_warehouse/sig_warehouse/rollup.py` (`recompute_mr_dispatch_state` — the same algorithm as
  the sandboxed `register_stock_entry` copy, but real importable Python: no `next()`/`set()`/
  tuple-unpack restrictions, so it's written straightforwardly rather than worked around) and
  `hooks.py` wiring `doc_events`: `Stock Entry.on_submit`/`on_cancel` and
  `Material Request.on_cancel`/`on_update_after_submit` all call the rollup. **Deployment path
  (recorded for reuse):** pushed to GitHub (repo made public — Frappe Cloud's public-repo poll
  path needs no GitHub App installation, avoiding that whole side quest) → registered on the bench
  via `press.api.app.new` (undocumented but real; reverse-engineered from Press's own open-source
  code at `press/api/app.py`/`press/press/doctype/app/app.py` since the Frappe Cloud REST API
  hard-blocks generic `/api/resource/*` and `/api/method/run_doc_method` for API-key auth —
  `press.api.*` only) → **the one non-obvious step:** a brand-new App Source has zero App Release
  records until something polls GitHub for the latest commit, and no webhook exists until a push
  happens *after* the source is registered (ours was pushed first) — the fix is the dashboard's
  per-app row action **"Fetch Latest Updates"** (`Apps` tab → row `⋯` menu), which forced the
  first release synchronously; nothing in the Press API surface reachable via API-key auth exposes
  this directly. Then: `Update Bench` → select only the new app (leaving unrelated pending
  framework/app updates unchecked) → `Deploy and update site` → full bench rebuild (~8 min) →
  **still not live on the site** even after a successful deploy — code lands in the bench image,
  but the site itself needs the separate `Install App` action (`Sites → neosys.frappe.cloud →
  Apps → Install App`) to actually run migrations and register the module (confirmed via
  `Module Def` query: absent right after deploy, present after install). Total chain: push →
  register app source → Fetch Latest Updates → deploy → install on site.
  **Verified live**, via a Stock Entry created and submitted through the plain native REST API
  (never touching `register_stock_entry` at all, so only the new hook could be responsible):
  submit correctly flipped the MR to `DISPATCHED` (line `custom_qty_issued` 0→6,
  `custom_dispatch_stage` PENDING→DISPATCHED) and cancel correctly reverted it
  (6→0, DISPATCHED→PENDING) — both through `sig_warehouse`'s hook, confirming lifecycle
  recalculation (adjustment 2 of the finalized plan) is genuinely live, not just deployed.
  Test documents cancelled and left as audit trail (ERPNext refuses hard-delete of a cancelled
  submittable doc — expected, matches this project's standard test-residue handling).
- The UOM-conversion path (both the sandboxed and the app copy) remains logic-reviewed but not
  exercised against a real multi-UOM item in the proving pack (fell back gracefully when absent,
  never hit the conversion branch) — worth one real test once a suitable item is identified.

**Why, and the actual gate:** not "DN and RN buttons work in ERP" — the retirement gate is
**a warehouse operator can complete an ordinary working day entirely in ERP**, with WH's Excel
workbook reduced to a frozen migration archive: no live reporting dependency, no fallback stock
writer, no operator workspace. ERP owns voucher allocation, operator identity, request
entry/approval, document delivery, and the system of record for history. If any upstream MIR
source survives cutover it feeds ERP directly, not through WH mediation. This supersedes the
earlier draft of this section, which scoped only dispatch+returns as "Phase 1" and left
receiving/transfers/full custody as vague later-phase enhancements — that's not sufficient scope
for an actual replacement, and is corrected below.

**Architectural decisions (fixed, do not relitigate):**
- `sig_dispatch_mr` stays separate from the legacy WH-mirror endpoint (`register_stock_entry`)
  — different authorization model, different identity family, different blast radius.
- Named ERP users only; every write is server-enforced against warehouse and action permissions
  for `frappe.session.user` — never a blanket service-key `ignore_permissions`.
- One operation ID, an immutable request signature, explicit duplicate/conflict handling, and a
  status-lookup path for timeout recovery — no blind retries.
- Atomic validate → create → submit, with no manual draft-staging step in the operator path.
- **Submitted ERP movements are the only source of fulfilment truth.** Every dashboard field
  (dispatch stage, remaining qty, return state) is a derived, read-only projection recomputed
  from submitted documents — never an input a user or a view can set directly.
- Printing and WhatsApp delivery run independently, after successful posting, with their own
  retry — a delivery failure must never look like a posting failure or vice versa.
- **Kanban is a view of fulfilment, not a control for changing it.** Dragging a card to
  "Dispatched" must never issue stock. Enforcement: `custom_dispatch_stage` (and the return-side
  `custom_return_state`) are `read_only: 1` fields written only by the server-side rollup: Frappe
  refuses a Kanban drag against a read-only field, so drag-to-change is rejected at the platform
  level, not by convention. **Verification requirement, explicit:** the proving pack (§ Testing
  below) must include actually attempting the drag on a live test card and asserting it is
  rejected and stock is unchanged — don't just assert the field is marked read-only in the
  fixture, prove the UI can't be used to bypass it.

**Writer placement — resolved in favor of the bench app.** `MASTER-ERP-INTEGRATION.md`'s finding
#10 (line ~3102) already specifies this correctly; the interim draft of this section proposed
sandbox Server Scripts with a byte-identical duplicated rollup block as a *permanent* design,
which was the wrong call — that duplication is an acceptable interim safeguard during a single
migration, not an architecture to keep. **Decision: build a bench-deployed Frappe app, `sig_warehouse`,
modeled directly on the existing `sig_whatsapp` app** (`ERPNext/SIG_WhatsApp/` — real git repo,
standard `app_name/app_name/doctype/...` layout, `hooks.py`) and its **already-proven deploy
pipeline**: `ERPNext/scripts/deploy_sig_whatsapp_bench.ps1` (Frappe Cloud Press API —
`press.api.bench.deploy_information` to pick a release, `press.api.bench.deploy` to ship it) +
`migrate_neosys_site.ps1`. This is not a new mechanism to invent; it's the same one already
shipping `sig_whatsapp` to this exact site. The app holds every transactional writer
(`sig_dispatch_mr`, `sig_declare_disposition`, the shared rollup, the lifecycle hooks below) as
real importable Python — real `hashlib` for the operation-ID signature, real DB transactions
(`frappe.db.savepoint`, row-locking `for_update=True` reads on the MR and Bin before the cap
check, closing a real concurrency gap sandboxed Server Scripts can't close safely), and real unit
tests. **What stays as Server Scripts, unchanged:** `register_mir`, `register_stock_entry` (the
live WH VBA mirror contract), `sig_list_ready_mrs`, and the read-only `check_dn_availability`/
`get_stock_snapshot` — all already live, simple, and proven; no reason to move them.

**Recalculate on every lifecycle event, not just the two write endpoints.** A native ERPNext
submit, cancel, or amendment (a Stock Entry cancelled from its own form, an MR cancelled
directly) must also trigger the same rollup — fixing the three bugs inside `sig_dispatch_mr`
and `register_stock_entry` alone is necessary but not sufficient if a plain cancel from the
standard form silently leaves stale derived fields. **Mechanism:** `hooks.py` `doc_events` on
`Stock Entry` (`on_submit`, `on_cancel`) and `Material Request` (`on_cancel`,
`on_update_after_submit`) inside the `sig_warehouse` app, calling the same shared rollup
function the two endpoints call — one function, three callers (dispatch endpoint, disposition
endpoint, lifecycle hooks), never three copies. This is the precedent already used for the PR
threshold validator (`Purchase Receipt`, Before Validate, live) — DocType-event hooking into
native ERPNext forms is proven on this site, just previously as a Server Script; here it's a
`hooks.py` handler in the new app instead, for the same effect with real Python.

**Rollup correctness, restated precisely:** count only Stock Entry Details that actually link
`material_request_item` to this MR's own lines, filtered `docstatus=1, is_return=0`, and scoped
to `purpose` values that are genuinely fulfilment for this MR's `material_request_type` — a
Material Issue MR is fulfilled by Material Issue lines, not by an unrelated Material Transfer
that happens to reference the same MR Item link; don't blanket-include
`purpose in [Material Issue, Material Transfer]` as the interim draft did. Convert every counted
qty to the MR line's own stock UOM before summing or capping (a line requested in `Mtr` must not
be under- or over-counted against a detail posted in a different but convertible UOM).

**Historical cleanup — resolved, not "76 drafts to backfill."** Live-queried directly
(`Stock Entry` where `custom_source_id like 'SIG-RN-%'`, 2026-09-15): **77 of 79 RN-tagged Stock
Entries are already submitted** (`docstatus=1`). The remaining 2 are test residue, not real WH
data — `STE-2026-0044` (`SIG-RN-SHAM-RN-001`, still draft) and `STE-2026-0047`
(`SIG-RN-RNTEST-RN-001`, cancelled) — both from the RN release-gate proving run, correctly never
promoted. **The "780/780 submitted, zero drafts" statement earlier in this file and the "76
staged RN drafts, none submitted" statement in §9A.8 describe two different points in time, not
a live contradiction** — the RN batch was submitted in the same later pass that closed out the
other Stock Entry drafts (§9A.8's own Verdict paragraph is now stale, flagged inline above). No
backfill or re-verification work is needed for these 77; only the two test-residue documents
need cleanup (delete the draft, leave the cancelled one as an audit trail — standard test-residue
handling, no special action). Historical cleanup and new functionality are hereby fully
separated: there is no historical population left needing action before Phase 1 work starts.

**Home page (`SIG Warehouse` Workspace) — actionable counts, not vanity metrics.** Number Cards,
in priority order: **Pending Requests** (MR lines, `custom_line_status=PENDING`), **Partial
Requests** (`PARTIAL`), **Shortages** (requested qty > live Bin availability on an open line —
computed via `check_dn_availability`, not stored), **Receipts Due** (submitted PO lines with
outstanding qty against no/partial Purchase Receipt), **Transfers Awaiting Receipt** (submitted
Material Transfer Stock Entries with `add_to_transit=1` not yet closed by a receiving entry —
see Transfers below), **Declarations Overdue** (`custom_return_state != DECLARED` past an aging
threshold, e.g. 14 days), **Exceptions** (failed dispatch/disposition operations, delivery
failures, unresolved `SIG MIR Intake` exceptions). Every card's `filters_json` must carry the
doctype as its first array element (§6A.8 #1) or it hangs on "Loading..." forever.

**Workspace structure — one `SIG Warehouse` Workspace, native forms wherever they already exist:**

| Section | Function | Mechanism |
|---|---|---|
| Requests & Dispatch | New/approved MRs, pending/partial queue, availability, Dispatch action, shortages | Dispatch dialog (unchanged from the prior draft) + `sig_dispatch_mr` |
| Receiving | Outstanding PO receipts, receive quantities, rejected goods, supplier returns | **Native Purchase Receipt against PO lines** — `sig_register_purchase_receipt` (PO-ENTRY-0, already live per `MASTER-ERP-INTEGRATION.md`) already persists `purchase_order`/`purchase_order_item` on native PR rows; reuse it, no new receiving screen needed for Phase 2 |
| Transfers | Send between warehouses, in-transit movement, destination receipt | **Native Stock Entry, `Material Transfer`**, using the site's already-live `add_to_transit` field (confirmed present: `recreate_c_cnl_stock_entry_tls.js` already copies it) for the two-step transit→destination pattern where destination acceptance is required |
| Returns & Custody | DN-line declarations, physical returns, custody balances, custody return/consumption/reassignment | `sig_declare_disposition`, expanded per custody lifecycle below |
| Stock & Control | Stock balance, item ledger, reconciliation, authorized corrections | Native Stock Reconciliation + native Stock/Item Ledger reports |
| History & Exceptions | Search MIR/DN/PO/site, linked-document history, failed operations, delivery failures, audit trail | Query Reports over `custom_source_id`/`custom_row_key`/`operation_id`; `SIG Dispatch Operation` as the audit spine |

Custom receiving/transfer screens can wait — native Purchase Receipt and native Stock Entry (with
transit) are the operational functions and both already exist on this site; building bespoke UI
for them before dispatch/returns exist would be solving the easier problem first.

**Custody lifecycle — completed, and the two models kept distinct.** The prior draft's
"Declare Custody" left material stranded in a balance with no way back. `sig_declare_disposition`
gains **CONSUME** (custody qty is used up on a project/site — closes the position, no stock
movement, records the consuming reference) and **REASSIGN** (custody moves to a different
custodian — closes the source `SIG IH Position`, opens a new one, `source_stock_entry`/
`source_se_detail` carried forward for attribution) alongside RETURN, CUSTODY, and CLOSE.
**Allocation exclusivity, enforced server-side:** the cumulative sum of returned + custody +
consumed against one original DN line must never exceed the issued qty — one shared allocation
ledger per source line, checked before any of the five actions commits, so return/custody/
consumption can never overlap. **The two custody models stay distinct, not conflated:**
- **Already-expensed Material Issue custody** (a DN line an operator declares `CUSTODY` on): the
  Material Issue already removed the stock from ERP's books. Custody here is a **non-stock**
  record — `SIG IH Event`/`SIG IH Position` only, no warehouse balance changes. This is bookkeeping
  for "who's holding company property that's already been consumed from an accounting
  standpoint," not an inventory position.
- **BI-transferred custody** (material moved via `Material Transfer` into the real
  `In-Hand - SIG` warehouse): this **is** actual inventory sitting in a real ERP warehouse with a
  real Bin balance. A `SIG IH Event`/`Position` here is a *supplement* (who specifically within
  that warehouse leaf is holding what) layered on top of real stock, never a substitute for it.
  RETURN from this path is a real `Material Transfer` back out of `In-Hand - SIG`, not a non-stock
  event. `sig_declare_disposition` must branch on which model applies (checked from the original
  DN's `purpose`: `Material Issue` → non-stock model; `Material Transfer`/BI → real-warehouse
  model) and never let a non-stock CUSTODY action stand in for what should have been a real
  Material Transfer, or vice versa.

**Per-line MR fields** (Material Request Item, `read_only:1`, `allow_on_submit:1`, `no_copy:1`):
`custom_qty_issued`, `custom_qty_remaining` (`in_list_view:1`), `custom_line_status` (Select
`PENDING/PARTIAL/DISPATCHED/CANCELLED`, `in_list_view:1`, `in_standard_filter:1`),
`custom_qty_cancelled` (field added now, cancel-demand *action* deferred pending an authorization
rule). Stored, read-only, derived mirrors for filterability only — never a parallel truth to
ERPNext's native `ordered_qty`/`per_ordered`, which stay authoritative after submit. **Verify
before building on this:** run one real submitted dispatch against a throwaway MR and read back
`ordered_qty`/`per_ordered` — this native path has never fired yet because every prior mirror
entry was a draft.

**Delivery sequence:**

1. **Correctness** — rollup fixes (bugs a/b/c + UOM/purpose scoping above), lifecycle hooks on
   native submit/cancel/amend, per-line MR fields, resumable backfill across every Material
   Issue MR with a before/after delta report (the docstatus fix will legitimately move some MRs
   backward out of `DISPATCHED` — expected, must be visible not silent).
2. **Daily operations** — dispatch (`sig_dispatch_mr`, the dialog, the Kanban+cards home page)
   plus receiving and transfers through the **native** ERP surfaces named above (no bespoke UI).
3. **Returns and complete basic custody** — linked declarations (the §9A.7 ERP-Link fields:
   `custom_original_stock_entry` + `custom_original_se_detail` on Stock Entry Detail), the full
   five-action `sig_declare_disposition` (RETURN/CUSTODY/CONSUME/REASSIGN/CLOSE), the two-model
   distinction enforced, allocation-exclusivity enforced.
4. **Cutover** — reconcile stock, open demand, and custody positions between WH and ERP one final
   time; switch DN26 voucher allocation and document delivery (print/WhatsApp) to ERP; disable WH
   writes and any remaining WH-side mirror intake for the migrated scope; per-warehouse cutover
   dates set explicitly (one stock writer per scope, at a time — the project's existing
   principle).
5. **Enhancements** — richer As-Built analytics, a blind-count interface, advanced/lot-level
   custody, bulk multi-MR dispatch. Genuinely deferred; nothing above depends on these.

**New files** (bench app, `ERPNext/SIG_Warehouse/` — mirrors `ERPNext/SIG_WhatsApp/` layout):
`sig_warehouse/sig_warehouse/dispatch_operation.py` (`sig_dispatch_mr` + shared rollup),
`sig_warehouse/sig_warehouse/disposition.py` (`sig_declare_disposition`, five actions),
`sig_warehouse/sig_warehouse/status.py` (`sig_check_dispatch_status`/`sig_check_disposition_status`),
`sig_warehouse/sig_warehouse/hooks.py` `doc_events` block, `sig_warehouse/sig_warehouse/doctype/`
(`sig_dispatch_operation`, `sig_ih_event`, `sig_ih_position`), `sig_warehouse/public/js/`
(dispatch dialog, disposition dialogs, list-view bulk actions) — all deployed via
`deploy_sig_whatsapp_bench.ps1`'s exact pattern retargeted at `sig_warehouse`, then
`migrate_neosys_site.ps1`. Structural UI records (Workspace, Kanban, Number Cards, Query
Reports, Custom Fields) can still ship via the existing idempotent REST `deploy_*.py`
(`ERPNext/scripts/hr/`) convention — those are data records, not code, and don't need the bench
app's build/release cycle. `verify_warehouse_workbench.py` (standalone proving pack, self-cleaning,
includes the Kanban-drag rejection test).

**Open, non-blocking sub-questions:** exact per-warehouse DN26 cutover date; custodian identity
as Employee-Link vs free-text (WH's `custodian_key` may not map 1:1 to ERP Employees); dispatch
role name (`SIG Warehouse Dispatcher` new role vs reusing `Stock Manager`); dispatch UOM (MR
line's UOM only vs operator-chosen conversion).

**Stage 2 (Dispatch) — DONE and live, 2026-09-15.**
- `SIG Dispatch Operation` doctype (idempotency/audit: `operation_id`, `mr`, `stock_entry`,
  `operator`, `state`, `signature`, `line_count`, `created_at`), autoname on `operation_id`.
- `sig_dispatch_mr` and `sig_check_dispatch_status`
  (`ERPNext/SIG_Warehouse/sig_warehouse/sig_warehouse/dispatch_operation.py`), called at
  `sig_warehouse.sig_warehouse.dispatch_operation.<name>` (a bench app's whitelisted methods use
  their full dotted path — no short `api_method` alias the way Server Scripts have). Five-check
  authorization (named user only, `Stock Manager`/`System Manager` role, MR submitted +
  `Material Request Type = Material Issue`, `frappe.has_permission('Warehouse', 'write',
  doc=warehouse)`); real `hashlib.sha256` line-signature (no sandbox workaround needed — this is
  a real app, not a Server Script); per-line cap re-checked live against `custom_qty_remaining`
  before any document is created; atomic `insert()` → `submit()` → `frappe.db.commit()` → the
  same shared `rollup.recompute_mr_dispatch_state()` used by Stage 1's hooks (one function, three
  callers now: the hooks, this endpoint, and — once built — `sig_declare_disposition`).
  **Deliberately not implemented yet: DN26 voucher allocation** (decision 2) — Stock Entries get
  ERPNext's own naming series for now, since allocating real DN26 numbers before a per-warehouse
  cutover date risks colliding with WH's own still-live numbering. Flagged in the module
  docstring so it isn't mistaken for an oversight.
- Dispatch dialog Client Script (`sig_warehouse/public/js/material_request.js`, wired via
  `hooks.py` `doctype_js`): adds a **Dispatch** button to a submitted Material Issue MR when
  `custom_dispatch_stage` is `PENDING`/`PARTIAL`; calls the live `check_dn_availability` Server
  Script for the "Available" column, generates the `operation_id` client-side before the call
  (so a retry reuses it), shows a `frappe.confirm` immutability warning, then calls
  `sig_dispatch_mr` and reloads the form. Not yet interactively verified in a live browser
  session (the backend proving pack below exercises the same endpoint the dialog calls, but the
  dialog's own DOM/JS has only been reviewed, not clicked through) — do that before calling the
  UI itself done.
- **Deploy recipe reused exactly as recorded above** for a second, third, and fourth round
  (initial app + two follow-up fixes) — confirms it's the real repeatable path, not a one-off:
  push → (if not auto-detected) dashboard **Fetch Latest Updates** → **Update Bench** (select
  only the changed app) → **Deploy and update site**. No new GitHub/Frappe Cloud discovery
  needed this time.
- **Live proving pack** (`ERPNext/scripts/wh_stock/prove_stage2_dispatch.mjs`, self-cleaning, all
  checks passed): full 2-line dispatch → one submitted Stock Entry, MR → `DISPATCHED`; partial
  dispatch (4 of 10) → MR `PARTIAL`, line `custom_qty_remaining=6`; over-cap attempt (qty 7
  against remaining 6) → `CAP_EXCEEDED`, no document created; duplicate replay (same
  `operation_id` + same payload) → `duplicate`, same Stock Entry, no new document; conflict (same
  `operation_id` + changed payload) → `conflict`, no document created; `sig_check_dispatch_status`
  correctly resolves a real operation. Stock verified back at exact baseline after cleanup.
- **Real bug found and fixed by the proving pack, not by review**: the first run failed every
  case with `CAP_EXCEEDED` even against a freshly submitted, untouched MR — `custom_qty_remaining`
  defaults to `0` (Frappe's Float default), not `qty`, and nothing had ever called the rollup for
  a brand-new MR, because Stage 1's `hooks.py` only wired `Material Request.on_cancel` and
  `on_update_after_submit` — **`on_submit` was missing**. A native MR submit never initialized its
  own derived fields, so any dispatch attempt against a truly fresh MR would always see
  `remaining=0` and be refused. Fixed: added `on_material_request_submit` to `rollup.py` and wired
  `Material Request.on_submit` in `hooks.py`; redeployed; full proving pack then passed clean.
  This was a design gap in the original Stage 1 hook list above, not just an implementation slip
  — corrected there implicitly by this note; the four `doc_events` entries now are `Stock
  Entry.on_submit/on_cancel` and `Material Request.on_submit/on_cancel/on_update_after_submit`.
- **Dispatch dialog verified end-to-end in a live browser session, 2026-09-15 — closed out, not
  just deployed.** Opening a real production MR (`MR-26-0990`, MIR 990) initially showed no
  "Dispatch" button despite a successful deploy. Root-caused: the client script itself was fine
  (served correctly at `/assets/sig_warehouse/js/material_request.js`, HTTP 200) and the server
  *was* correctly assembling it into the doctype's `__js` payload (confirmed directly via
  `frappe.desk.form.load.getdoctype?doctype=Material%20Request` — the response body contained the
  file's content) — but the currently-open desk session's own cached bootinfo hadn't picked up
  the newly-registered hook. **Fix: `press.api.app.new`'s sibling `press.api.site.clear_cache`**
  (`{"name": "neosys.frappe.cloud"}, POST /api/method/press.api.site.clear_cache` — dispatches an
  async "Clear Cache" Agent Job; confirm completion via `press.api.client.get_list` on doctype
  `Agent Job` filtered by `site`, `job_type = "Clear Cache"`, `status = "Success"` before
  re-testing, rather than guessing at timing). After that, a fresh page load showed the button
  (desk on this Frappe version renders it under the `···` menu → `Actions > Dispatch` when the
  toolbar is narrow, not as a standalone header button) and the dialog itself worked correctly
  against real live data: opened, called `check_dn_availability`, and rendered
  Requested/Issued/Remaining/Available correctly for the MR's actual line. **Not submitted** —
  closed via the dialog's own × without confirming, since MR-26-0990 is real production data, not
  a test fixture, and dispatching it wasn't something the user asked for. **Standing note for any
  future `doctype_js`/Client Script change to this or another app**: `press.api.site.clear_cache`
  after every such deploy, confirmed via the Agent Job check above — don't assume a bench
  redeploy alone refreshes an already-open session's view of new hooks.
**Stage 2 — CLOSED, 2026-09-15.** The dashboard/home-page layer built and verified live:
- `SIG Dispatch Queue` Query Report (line-grain: MR/MIR/Item/Requested/Issued/Remaining/
  Warehouse/Line Status/MR Stage/PO/Days Open) — deployed via
  `ERPNext/scripts/hr/deploy_warehouse_dashboard_stage2.py`, the same idempotent REST pattern as
  Stage 1's custom fields (data records, no bench-app rebuild needed for these).
- 4 Number Cards: Pending Requests, Partial Requests, Dispatched Today, Dispatch Ops Today.
  **Bug caught and fixed before it misled anyone**: "Dispatched Today" first used
  `modified = Timespan today`, which counted 527 — every Stock Entry merely *touched* today
  (including this session's own testing/backfill), not genuinely dispatched. Fixed to
  `posting_date = Timespan today`; corrected count is 0 (accurate — no real dispatches posted
  today via the endpoint yet). The other Receipts-Due/Transfers-Awaiting-Receipt/Declarations-
  Overdue cards from the original home-page design are **not built** — they depend on
  receiving/transfer "due" tracking and Stage 3's return-declaration state, neither of which
  exist yet; the Workspace's `content` includes a header marking "Returns & Custody — Stage 3,
  not yet built" rather than a card with nothing behind it.
- `SIG Dispatch Queue` Kanban Board on Material Request, grouped by `custom_dispatch_stage`,
  filtered to submitted Material Issue MRs.
- `SIG Warehouse` Workspace (`/app/sig-warehouse`): Dispatch section (cards + Kanban + list/report
  shortcuts + Dispatch Operations audit list) and a Receiving & Transfers section linking
  directly to the **native** Purchase Receipt / Stock Entry lists — no new code, per the plan's
  own "native forms, not bespoke screens" call.
- **All of it proven live**, not just deployed: opened the Workspace, cards showed real counts
  (45 pending, 0 partial), the Kanban board listed real pending MRs, the Query Report showed the
  same real line data the dispatch dialog itself displays (cross-checked against `MR-26-0990`).
- **Kanban-is-a-view-not-a-control: two real bugs found and fixed by testing this live, not by
  reviewing it.**
  1. **`custom_sync_status` Select-option mismatch (found first, live drag test).** Dragging a
     real card was rejected — but investigation showed the rejection came from an unrelated
     pre-existing bug: `custom_sync_status` is a `Select` field whose option list
     (`DRAFT_CREATED/ERP_REQUESTED/EXCEPTION/MR_SUBMITTED/SENT_TO_WH`, set when the field was
     first added for the MIR intake flow) was never extended to cover the rollup's own output
     values (`PARTIALLY_CONFIRMED/PARTIALLY_DISPATCHED/DISPATCHED`). The rollup writes via
     `frappe.db.set_value` (a raw DB write, bypasses field validation), so this was silently
     "fine" until any full document save re-validated the record and failed — meaning **every**
     Material Issue MR the rollup had ever touched was one form-save (or Kanban drag) away from
     an opaque validation error, for any operator, for any reason, not just dispatch. Fixed live:
     added the three missing values to the Custom Field's `options`
     (`Material Request-custom_sync_status`).
  2. **`read_only:1` is a UI hint, not server enforcement — found by testing the actual write
     path, not by reading the field definition.** With bug 1 fixed, the drag gesture itself
     couldn't be reliably simulated (opened the form instead of reordering — a tool limitation,
     not a product one), so the underlying mechanism was tested directly: calling
     `frappe.client.set_value` (the same whitelisted API a Kanban drag calls) against
     `custom_dispatch_stage` **succeeded** despite `read_only:1` — proving the field was never
     actually protected against a direct write, only hidden from manual editing in the form UI.
     **Fixed properly**: set `permlevel:1` on all five derived fields
     (`Material Request.custom_dispatch_stage`; `Material Request Item.custom_qty_issued`/
     `custom_qty_remaining`/`custom_line_status`/`custom_qty_cancelled`) with no role granted
     write access at that level — Frappe enforces `permlevel` server-side on every
     permission-checked write path (`frappe.client.set_value`, form save, Kanban drag), unlike
     `read_only` which only suppresses the form input. The rollup's own writes are unaffected
     (`frappe.db.set_value` is a raw SQL update that bypasses permission/permlevel checks
     entirely, same as it already bypassed field validation for finding 1).
     **Honest limit on this verification**: re-testing `frappe.client.set_value` after the
     `permlevel` change still succeeded — because the token used throughout this session carries
     `System Manager` (confirmed: `roles` includes `System Manager`, `Stock Manager`, and nearly
     every other role), and Frappe's admin-tier roles bypass `permlevel` restrictions by design —
     that's expected behavior, not a failure of the fix. This was **not** verified against a
     genuinely restricted operator account (no such credential exists in this session); the real
     dispatch role decided in Open Question 11 (`Stock Manager` or a new `SIG Warehouse
     Dispatcher`) is a normal, non-`System Manager` role, so the fix should hold for actual WH
     operators — confirm this with one real non-admin login before depending on it in production.
     Both corrupted test writes to `MR-26-1039` were reverted to `PENDING` immediately after each
     check; live data was not left in a wrong state.

**Stage 3 — Returns & Custody — CLOSED, 2026-09-15.** `sig_declare_disposition` (RETURN/
CUSTODY/CLOSE, `ERPNext/SIG_Warehouse/sig_warehouse/sig_warehouse/disposition.py`) plus
`SIG IH Event`/`SIG IH Position` (custody ledger + derived position) and the per-line
`custom_return_disposition`/header `custom_return_state` rollup (`rollup.py`,
`recompute_return_state`). `SIG Returns Pending` report, `SIG WB Returns Undeclared` card,
Workspace "Returns & Custody" section deployed via `deploy_warehouse_returns_stage3.py`.
Proven live end-to-end with a self-cleaning proving pack
(`ERPNext/scripts/wh_stock/prove_stage3_disposition.mjs`): real dispatch → full RETURN
(new Material Receipt, submitted) → over-return refused (`CAP_EXCEEDED`) → duplicate/conflict
on `operation_id` → CUSTODY (no stock movement, real `SIG IH Event`/`Position`) → partial
RETURN + CLOSE on a third line → header rolls up to `DECLARED`. All 11 checks pass; stock
baseline (`G-EWC-10MM` at `مستودع المزاحمية - SIG`) confirmed restored to 10065 after cleanup.

**Root-cause chase on the proving pack's read-back failures — the real bug was permissions,
not caching; the caching fix was real but was not the cause.** Every read-back check
(`return_disposition_correct`, `custody_disposition_correct`, `partial_return_disposition`,
`close_disposition_correct`, `header_declared`, and Stage 2's own `full_dispatch_mr_dispatched`/
`partial_dispatch_ok`) failed on first run despite the underlying writes being demonstrably
correct (confirmed via raw `frappe.db.sql` SELECTs through a temporary Server Script, deployed
then deleted). The investigation went through two real, worthwhile fixes that turned out **not**
to be the actual cause, before finding it:
1. **First hypothesis (partially right, but not the cause): `frappe.db.set_value` bypasses
   `frappe`'s document cache.** True as far as it goes — confirmed via Frappe's own GitHub
   source (`clear_document_cache`, `frappe/__init__.py`) — and a real gap: the original fix only
   cleared the *parent* document's cache (`Material Request`, `Stock Entry`), not each written
   *child row*'s own cache entry (`Material Request Item`, `Stock Entry Detail`), which Frappe
   caches independently when fetched directly (e.g. `GET /api/resource/Stock Entry Detail/
   <name>`). Both fixes are kept in `rollup.py` (`recompute_mr_dispatch_state`,
   `recompute_return_state`) as correct, defensive practice for any future `frappe.db.set_value`
   caller. **But redeploying both fixes and re-running the proving pack still failed identically**
   — proving this cache gap was never the actual cause of the observed symptom.
2. **Second hypothesis (also real, also not the cause): stale `press.api.site.clear_cache`.**
   Ruled out the same way — ran it, confirmed the Agent Job succeeded, re-ran the proving pack,
   still failed.
3. **Actual root cause, found by comparing a plain `frappe.get_doc()` call (inside a temporary
   Server Script, correct) against the same read via the REST API / `frappe.client.get` (wrong)
   — the only difference between the two call paths is `Document.check_permission()` +
   `apply_fieldlevel_read_permissions()`, which the REST/RPC layer calls and a raw script does
   not.** `apply_fieldlevel_read_permissions` (Frappe core, `frappe/model/document.py`) silently
   **deletes any field whose `permlevel` is not in the caller's granted permlevel set, for every
   user except the literal `Administrator` account** — confirmed live: the Stage 1/2 `permlevel:1`
   fix (`custom_dispatch_stage`, `custom_qty_issued/remaining/line_status/cancelled`) and the
   Stage 3 fields (`custom_return_disposition`, `custom_return_state`, `custom_qty_returned`,
   `custom_qty_custody`) all had `permlevel:1` set on the field, but **no matching `Custom DocPerm`
   was ever added granting `permlevel:1` `read` access to any role** — confirmed via
   `GET /api/resource/Custom DocPerm?filters=[["parent","=","Material Request"]]` showing only
   `permlevel:0` rows. So every read through the REST/RPC layer — the Kanban board, the
   dashboard, the proving packs, **any real operator's own session** — silently lost these
   fields, while the underlying data was always correct. This directly **revises the "System
   Manager bypasses permlevel" claim in the Stage 2 write-up above**: that finding was about the
   separate *write*-permission check (`frappe.client.set_value`), not this *read*-side
   field-stripping — and on the read side, this session's own System-Manager-role API token did
   **not** silently succeed; it silently lost the fields, same as any other non-`Administrator`
   caller would. **Fixed**: added a `permlevel:1`, `read:1` `Custom DocPerm` for `System Manager`
   and `Stock Manager` on `Material Request` and `Stock Entry` (permlevel access for a child
   table's fields is governed by the *parent* doctype's `DocPerm`, not the child's own — so
   `Material Request Item`/`Stock Entry Detail` needed no separate grant). Recorded as an
   idempotent script, `ERPNext/scripts/hr/fix_permlevel1_docperms.py`, and re-running both
   proving packs afterward flipped every previously-failing check to pass, including Stage 2's
   (which had the identical latent gap since its own `permlevel:1` fix, unnoticed until Stage 3's
   proving pack forced a real read-back check). **Practical takeaway for any future `permlevel:1`
   field**: it is not usable in isolation — it must always ship with a matching `Custom DocPerm`
   read grant at that level for every role that needs to see the field, or the field silently
   disappears for everyone except `Administrator`.

**Known minor gap, not fixed this session**: `SIG IH Event`/`SIG IH Position` grant `read:1` but
`write:0`/`delete:0` to `System Manager` and `Stock Manager` — the production endpoint writes to
them via `ignore_permissions=True` so this doesn't block real usage, but it means the proving
pack's own cleanup can't delete its test `SIG IH Position` row (`403`), so repeated runs
accumulate `qty_open` on the same `position_key` until manually cleared. Attempted a live fix
(`write:1`/`delete:1` for `System Manager`) but it was blocked by this session's own safety
classifier as a permission-grant action requiring explicit user sign-off; left for the user to
approve directly rather than routed around.

### 9A.10 — Operational readiness declared: ERP is the live warehouse system, minus final reconciliation (2026-09-16)

**Owner assessment, 2026-09-16: the ERP Warehouse Workbench is ready to start real operational
use.** All four physical warehouses have an ACTIVE Stage 4 cutover with the WH Excel/VBA writer
confirmed disabled (§9A.9) — ERP is the sole stock writer for Jizan, Qasim, Makkah and Riyadh.
What is explicitly **not** yet closed, and should not be treated as closed by this declaration:

- **Reconciliation is still open.** The first As-Built acceptance run (§ `warehouse_stage5_initial_design.md`,
  "First As-Built acceptance run") found 1,102 non-match rows (115 mismatches, 360 WH-only, 27
  ERP-only, 474 needing site-allocation review, 126 exceptions) against the frozen legacy
  workbook. These were explicitly logged as **not a cutover blocker** (the cutover gate is "ERP
  is the sole writer going forward", not "ERP's historical balance matches the legacy workbook to
  the unit") but they are real open reconciliation work — someone still needs to work the triage
  workbook (`WH_Stage5_AsBuilt_Triage_2026-09-13.xlsx`) row by row and either correct the ERP
  balance or accept the difference as a documented exception. Until that pass is done, `SIG
  As-Built` and `SIG Warehouse Stock Value` report real, live ERP numbers, but "real" and
  "matches the legacy workbook" are not the same claim.
- Stage 5 gate 3 ("current ERP stock, submitted movements and custody positions reconcile") is
  therefore still open for all four warehouses — the other Stage 5 shared gates (1: active
  cutover, 4: permissions tested, 5: proving pack, 6: legacy comparison available) are satisfied.
- Stage 5 tracks 5B (blind counts), 5C (advanced custody detail) and 5D (bulk dispatch) remain
  deliberately unbuilt (policy-only libraries, no DocTypes/endpoints) — not required for
  day-to-day dispatch/return, but a physical count pass is the natural way to close the
  reconciliation gap above once someone is ready to run one.

**What this means in practice for anyone starting to use it live:** dispatch (`Issue` button on
a submitted Material Issue MR, or the Kanban board's per-card action menu), returns/custody
declaration (`sig_declare_disposition`), and cancel-remaining-demand are all real, audited,
idempotent endpoints — not drafts or previews. Numbers reported by `SIG As-Built` and `SIG
Warehouse Stock Value` are live ERP truth from this point forward; only the *historical* starting
balance they were seeded from still has open reconciliation items against the legacy workbook.

### 9A.11 — Live stock-accuracy reconciliation closed (2026-09-18)

**This closes the practical half of the §9A.10 caveat above.** The 1,102-row As-Built triage
workbook (formal row-by-row categorization against the frozen legacy snapshot) is a separate,
still-open, low-priority cleanup exercise — see below for why it no longer represents a live
stock-accuracy risk. What *is* now closed is the actual question that matters operationally: does
ERP's current live balance match physical reality, anywhere in the system, right now.

**What was investigated and resolved:**

- **ZAF012 "3 missing batteries" audit gap** — root-caused to one real historical DN never
  entered into ERP (`DN26-0432-1`, WH's own `Out`+`logs` sheets confirm Confirmed/Success
  status). Backfilled as `STE-2026-0891` (all 7 real line items, not just the battery). A
  follow-on sweep of WH's `logs` sheet (`Type=DN`, `Status=Success`) against ERP's `custom_source_id`
  found 5 more genuinely-missing historical DNs; 4 dispatched live via `sig_dispatch_mr`
  (`MR-26-1005/1007/1037/1038`), 1 held pending WH's own site-PDF confirmation
  (`DN26-0985-1`/ZHA180 — a DN-number collision with an unrelated ERP MR, not yet resolved either
  way).
- **E-ALM-4P deep historical negative dip** (-120.9, 2026-04-14 to 2026-05-06) — diagnosed as a
  Purchase Receipt posted 7-8 weeks late (`MAT-PRE-2026-00215`, +304, posted 2026-06-07 for
  consumption that started 2026-04-06), not a missing transaction. Already self-corrected by the
  2026-09-13 physical Stock Reconciliation (reset to 225.0, matching the live Bin exactly).
- **System-wide negative-balance sweep** — every Stock Ledger Entry where the running balance
  ever went below -5 (48 item/warehouse combinations, worst case -648.0) was individually
  triaged by how it was closed out: 38 via a real physical Stock Reconciliation count, 3 via a
  genuine Purchase Receipt, 6 via a prior 2026-09-15 correction pass already explicitly
  cross-checked against WH's own live Makkah/Riyadh/Qasim sheet, 1 a normal Material Transfer
  misclassified by the sweep's threshold. **Confirmed separately: zero Bins are negative anywhere
  in the system today.**
- **Root cause identified for the Makkah-heavy cluster** (safety rail, DC cable, and most of the
  other 48): Makkah warehouse almost never receives a direct Purchase Receipt (33 ever, vs 409 at
  Muzahmiyah) but dispatches to Makkah-area sites are still sourced against Makkah's own ERP bin,
  so it accumulates a paper deficit until a periodic physical count or manual correction zeroes
  it. This is a **process gap** (dispatch source-warehouse selection defaults), not a current
  data-accuracy problem — flagged for a future fix, not urgent.
- **One genuine, unrelated open item**: `M-GP-3MTRS` at Muzahmiyah is physically at 0 (confirmed
  by the 2026-09-13 count; last real Purchase Receipt was 2024-06-06). This is an ordinary
  "needs reordering" procurement gap, not an ERP data problem — it's the one line blocking
  `MR-26-1006` from fully dispatching.

**What remains explicitly open, and why it's now low-priority:** the 1,102-row formal As-Built
triage workbook (`WH_Stage5_AsBuilt_Triage_2026-09-13.xlsx`) still has not been worked row by
row. Given the above — a direct, independent audit of every significant live deficit in the
system found nothing wrong that wasn't already resolved — the triage workbook's remaining value
is mostly categorization/paper-trail completeness (documenting *why* each historical row differs,
for audit purposes) rather than surfacing any further real stock-accuracy risk. It can be worked
opportunistically rather than treated as a live-use blocker.

### 9A.12 - Kanban reliability, backfill double-count, source-warehouse choice (2026-09-19)

- **Kanban board** (`SIG Dispatch Queue`): now genuinely working on the live 216-card board - stage-colored
  borders, per-column counts, search, Dispatch Tool, green/yellow/red stock-availability dot per MR
  (green = covered at the line's own warehouse, yellow = short there but covered elsewhere, red = short
  everywhere), and the card "+" opens Issue / Return / Cancel remaining instead of assign-to. It had never
  run before because of four separate bugs (wrong hook; `const` used before declaration; an unconditional
  badge write looping inside a `MutationObserver`; script not loading on a direct or reloaded visit). Loaded
  via `app_include_js`, which is the only path that is reliable on a cold load.
- **Backfill rule (new):** WH executed `DN26-1005/1006/1007/1037/1038` on 2026-09-14 and ERP's baseline was
  read from the live WH sheets afterwards, so many of their lines were already reflected. Backfilling them
  blindly double-deducted (E-RM-NOK-50 ended 2 below WH). Corrected with `STE-2026-0896` (receipt, offsets the
  MR-26-1006 issue and the earlier MR-26-1005 issue) and dispatches `STE-2026-0897`/`0898`
  (`DN26-1040`/`DN26-1041`); all 12 items re-verified equal to WH. Before backfilling any historical DN, compare
  ERP Bin with `Stock Ry`/`Stock Mk` in the live WH workbook and post only lines that differ.
- **`M-GP-3MTRS`** was not a missing purchase: WH delivered the last unit on `DN26-1006-1`.
- **Makkah source warehouse:** the MR line warehouse comes from the request's WH text with no stock check
  (`register_mir` `WH_MAP`), so 95 of 129 open lines on "short locally, covered elsewhere" requests were
  Makkah. The dispatch dialog now lets the operator choose the source warehouse and pre-selects one that covers
  every line. `sig_dispatch_mr` already took `from_wh` independently, so no backend change was needed.
- **Open:** 88 item/warehouse differences between ERP and the WH live sheets
  (`outputs/wh_vs_erp_stock_diff_2026-09-19.csv`) need a physical confirmation; `C-MNT-EB-3m` is 2 over in ERP;
  `DN26-0985-1` (ZHA180) still awaits the WH site PDF.

### 9A.13 - Post-May MIR -> MR backfill and closure (staged, 2026-09-21)

**Goal.** Every post-May MIR (>= 543) gets an ERP Material Request, with **no stock movement**. Baseline: 190 of 220 WH DN groups
for the WH-confirmed MIRs already exist as submitted Stock Entries (`custom_source_id = SIG-DN-DN26-####`), so stock is already
reconciled; the gap is MR existence and MR<->Stock Entry linkage. The 30 "missing" DNs are mostly `-1/-2` suffixed and probably
sit under the un-suffixed voucher - verify before treating as missing. Baseline: `outputs/post_may_dn_baseline_20260921.json`.

**Closure rules (owner decision).**
1. Fully dispatched MIR with a confirmed WH Return for the same site + item on/after the MIR date -> link the Return (RN) to the MR; not auto-closed.
2. No return, dispatch before 2026-08-09, no pending line -> `CLOSED`.
3. No return, dispatch on/after 2026-08-09 -> `CLOSED` only if the DN lines are `Closed?=1` in WH `Manage Return`; else `OPEN_AS_BUILT` (as-built check pending).
4. **A partial dispatch whose remainder was cancelled is never `CLOSED`.** It stays `PARTIAL_OPEN` with the cancelled quantity recorded on the line (needs a distinct line status, e.g. `CANCELLED_REMAINDER`, so the recompute does not treat cancel as fulfilled). This is a change to `recompute_mr_dispatch_state` in `register_stock_entry_script.py`.
5. Pending-only MIRs import as `PENDING`; cancelled-only MIRs are skipped; no `Out` row (1016) goes to source review.

**Stages (each: dry run -> owner OK -> apply -> read-back).**
- S1 Stage: `scripts/hr/stage_post_may_mr_closure.py` -> `outputs/post_may_closure_staging_20260921.json` (done; read-only).
- S2 Verify DN suffix mapping (30 DNs / 16 MIRs) and 1005/1007/1006 line-level checks; confirm dispatch-date source (Out date vs Logs).
- S3 Patch dispatch-state recompute for rule 4 (never-closed on cancelled partial) and test on a copy/dry run.
- S4 Create MRs (no stock) for the ~211 missing MIRs, in small batches, with the retrospective flag (`custom_source_confirmed_by = Retrospective WH import`); link existing Stock Entries by DN id.
- S5 Recompute dispatch state for the ~275 imported-but-PENDING MRs and the new ones; apply closure dispositions.
- S6 Link Returns (rule 1); report residual OPEN_AS_BUILT list for as-built review of DNs after 2026-08-09.

**Staging result (WH219.xlsm, 491 MIRs >= 543):** CLOSED 167, LINK_RETURN 43, OPEN_AS_BUILT 71, PARTIAL_OPEN 59 (2 with cancelled lines), PENDING 142, SKIP_CANCELLED 9. No ERP records were changed.

*Update:* `Closed?` on pre-2026-08-09 Manage Return rows was bulk-defaulted by the owner and is ignored; pre-cutoff MIRs close only by "no return, nothing pending", and returns found in `Return` are linked first. Counts re-staged in `outputs/post_may_closure_staging_20260921.json`.

**9A.13 v2 rules (owner, 2026-09-21) - supersede the closure rules above.**
- **Closed = both:** no pending/cancelled remainder line **and**, for dispatches on/after 2026-08-09, return declared done (`Manage Return Closed?=1`). Every fully dispatched MIR whose lines are all pre-2026-08-09 is `CLOSED` by default.
- **A partial is never closed** - whether the remainder is pending, cancelled or has a return. Any `Pending` line counts as a remainder regardless of its zero quantity. Returns are *linked* (`returns[]`), never closers.
- **No double requests:** MIRs near-identical to a confirmed MIR, or with the same site + items on a different PO, are skipped (13: 546, 560, 666, 693, 773, 783, 892, 990, 993, 1000, 1002, 1009, 1010). Where one already exists in ERP as an MR, the action is `CLOSE_EXISTING_MR` (cancel/close as duplicate, no stock). Medium partial matches 998/778/777 skip only the matched lines (`partial_dup_skip_lines_vs`).
- **Actions staged** (`outputs/post_may_closure_staging_20260921.json`, 491 MIRs): CREATE_MR 213, UPDATE_EXISTING_MR 256, CLOSE_EXISTING_MR 13, SKIP 9 (cancelled). Dispositions: CLOSED 186, OPEN_AS_BUILT 75, PARTIAL_OPEN 77, PENDING 131, SKIP_DUPLICATE 13, SKIP_CANCELLED 9. MIR 1006 stays `PARTIAL` (33/50) and is an update of MR-26-1006; 1005/1007 are `PARTIAL_OPEN` in WH but `DISPATCHED` in ERP - line check required before any change.
- **Open before apply:** 783 skip depends on 1005's line check; MIR 1016 has no `Out` row.

**9A.13 readiness checks (2026-09-21, read-only).**
- **Quantities:** for the WH-confirmed post-May DNs, 829 line quantities equal ERP's Stock Entry quantities; 0 lines have ERP < WH or ERP > WH. 30 confirmed WH lines (22 MIRs, e.g. `EC-NOK-IND`, `E-BKR-CHINT-125-1p`, fencing items on 635/790) have **no matching item in the ERP DN** - decision: do not keep these as MR lines (they would look dispatchable); log them in the import report.
- **Partial dispatch mechanics:** issued qty is derived only from submitted Stock Entry Detail rows carrying `material_request_item` (`recompute_mr_dispatch_state`). Only 30 of 1,862 post-May Stock Entry Detail rows carry that link today. Retrospective MRs therefore need the link written (`material_request` / `material_request_item` are not `allow_on_submit`, so a server-side `db.set_value`, not REST PUT, no re-post) before recompute; otherwise dispatched lines look fully pending and could be dispatched twice.
- **No stock change:** creating/submitting a Material Issue MR posts no SLE/GL; the link write is metadata only. Not yet proven live: run one canary MIR and compare Stock Ledger Entry count, Bin and Stock Entry docstatus/modified before/after.

### 9A.13 - Safe-apply runbook (staged; nothing applied yet)

**Standing guards (every stage):** dry run first; one batch per owner OK; before-image of every touched doc saved to `outputs/backup_9A13/`; idempotent (re-run creates nothing twice, keyed on `custom_external_source_id = SIG-MIR-<n>`); stop on first error; read-back after each batch; no Stock Entry is created, cancelled, amended or re-submitted at any point.

| Gate | Work | Pass criteria (else stop) |
|---|---|---|
| G0 Baseline snapshot | Save counts: Stock Ledger Entry, GL Entry, Bin totals per item/warehouse, Stock Entry docstatus+modified for the ~370 post-May entries, MR count/status | Snapshot file written |
| G1 Pre-checks (read-only) | 1005/1007/1006 line check; confirm DN suffix (`-1/-2`) mapping to one voucher; list the 11-MIR gap (491 vs 502); confirm dispatch-date source; add qty check to the 43 return links; 30 unmatched confirmed lines listed | Owner signs the lists |
| G2 Logic patch | `recompute_mr_dispatch_state`: cancelled remainder recorded, never closes a partial; closure = no pending AND (pre-9-Aug or return declared). Test on a copy/dry run against staged MIRs | Dry-run output equals staged dispositions |
| G3 Canary | 1 MIR (fully dispatched, pre-9-Aug): create MR, write link, recompute, close. Then 1 partial (e.g. 708) | SLE, GL, Bin, Stock Entry docstatus/modified all identical to G0; MR state as staged; line dispatch attempt shows only non-confirmed lines |
| G4 Small batch | ~10 MIRs mixed (closed, partial, pending, open-as-built) | Same diff check; zero errors |
| G5 Bulk creates | 213 CREATE_MR in batches of 25-50, pending-only MIRs first, then dispatched | Diff check each batch |
| G6 Updates | 256 UPDATE_EXISTING_MR: link + recompute + closure. Includes 1006 (must stay PARTIAL 33/50) | 1006 unchanged in qty; no PENDING MR left with a confirmed DN |
| G7 Duplicates | 13 CLOSE_EXISTING_MR (close/cancel as duplicate, no stock) | Each cites its confirmed MIR in the remark |
| G8 Return links + as-built | Link 43 returns after owner confirms quantities; hand the 75 OPEN_AS_BUILT to as-built review | Owner review |
| G9 Final verification | Re-run baseline diff vs G0 (must be zero stock delta) and the full 502-MIR status report | Zero stock diff; status counts match staging |

**Rollback:** cancel/delete MRs created by this run (tagged `Retrospective WH import` + run id); restore link fields from the before-image; re-run recompute. Because no stock document changes, stock needs no rollback.

**9A.13 amendments after the loop review (2026-09-21).** (1) Backfill rule 9A.12 applies in spirit: WH's sheets may already include some of these dispatches, so the MR import never posts stock; only metadata. (2) Learning-loop rule 265: the site+item duplicate match is a *claim*; every skip cites its confirmed MIR, PO and dates, and Tier 3 duplicates are closed last after review. (3) The 13 duplicate skips and the 22 unmatched-line MIRs are Tier 3. (4) See Loop 06 (6B) for the reusable loop, tiers and G0 evidence.

**9A.13 G1 pre-checks - executed 2026-09-21 (read-only; report `outputs/post_may_g1_prechecks_20260921.md`, script `scripts/hr/g1_prechecks_9a13.py`).**
- **WH keeps a `Pending` twin beside each `Confirmed` row** (MIR 1005, 1007, 997, 999 and every 1006 line): a Pending row is a real remainder only if its item was not confirmed for at least the pending qty within the MIR. Staging now applies this: PARTIAL_OPEN 77 -> 73, OPEN_AS_BUILT 75 -> 79. **1005 and 1007 are not conflicts**: ERP `DISPATCHED` is right (WH = one Pending twin + one Confirmed row, same qty). 1006 is a true partial in both (E-CAB-XLP-4-50 10.7/12, M-RGS-2.5 0.3/1, E-CAB-F-3-4 3/10, M-FSHR-12MM 0/4, E-CLUG-50 0/4); note WH also confirms E-PIN-LUG-50MM qty 8 vs MR qty 4 (ERP issued 4).
- **DN suffix (-1/-2):** all 29 suffixed groups map to the *base voucher* in ERP; 4 do not cover WH qty (608-2, 616-1, 824-1, 924-2) - the known unmatched-item lines (Tier 3).
- **11-MIR gap:** 13 MIRs in the 502 list are absent from WH219 `Out`: 991, 1017-1019, 1035, 1040-1046 (ERP-originated, already in ERP, mostly PENDING; 1041 DISPATCHED) plus 1016 (no source row). No import needed; 991 to be reviewed.
- **Dispatch date source:** Out date and ERP posting date agree on the cutoff side for 214 of 219 DN groups; the 5 exceptions (MIR 877, 879, 880, 881, 884; Out 2026-08-04, ERP posted 2026-08-16, i.e. a backfill date) - **WH Out date is kept as the dispatch date**, so these are pre-cutoff.
- **Return links:** 57 MIRs have same-site/item return matches; for 8 MIRs (708, 710, 917, 930, 931, 934, 936, 989) the returned qty exceeds this MIR's dispatched qty because the site's returns span several MIRs. They are flagged `return_link_review` (Tier 3): allocate the return to MIRs in date order, cap at dispatched qty, owner confirms.

**9A.13 delta rule (owner, 2026-09-21): dispatched lines are dismissed - the shortfall is never re-added as pending.**
- A line with any confirmed dispatch is `DISPATCHED`; requested-minus-dispatched is dropped, not carried as a pending remainder. New MRs (CREATE_MR) are created with line qty = WH confirmed qty for dispatched lines, so no delta exists.
- Existing ERP MRs: **76 lines in 29 MRs** carry MR qty > WH confirmed qty (mainly 704: 16, 703: 12, 572: 4, 694/678/806/784/1006: 3 each). Staged in `dismiss_delta_lines` (`outputs/post_may_delta_lines_20260921.json`). Applied in G6 (Tier 2/3) by a server-side write of the line qty down to the issued qty (`frappe.db.set_value`, `update_modified=False`, original qty + reason kept in the before-image and an MR comment), then recompute. Qty is not `allow_on_submit`, so REST PUT is not an option. This lowers a submitted MR's requested qty; it does not touch stock.
- **1006:** its three delta lines (`E-CAB-XLP-4-50` 10.7/12, `M-RGS-2.5` 0.3/1, `E-CAB-F-3-4` 3/10) are dismissed; it stays `PARTIAL` because `M-FSHR-12MM` (0/4) and `E-CLUG-50` (0/4) were never dispatched. The "33 of 50, 17 remaining" figure changes accordingly (dispatched 33, never-dispatched remaining 8).
- The G2 recompute patch is therefore not a global change: dismissal is a per-line data correction done at import, so live partial dispatches keep their remaining quantity.

**9A.13 small-value remainder waiver (owner proposal, 2026-09-21; class list pending owner approval).**
- A partial whose *only* remaining lines are small-value consumables is closed: the small lines are added to the MR then set to `CANCELLED` with reason `SMALL_VALUE_WAIVED`, and the MR goes `CLOSED`. This is the one deliberate exception to "a cancelled partial is never closed"; every other cancelled remainder still keeps the MR `PARTIAL`. The waiver reason must be stored (line remark / MR comment) so the recompute and reports can tell it from a real cancel.
- Proposed small-item classes (prefix): `M-SCRW`, `M-FLT-WSHR`, `M-FSHR` (fishers), `E-CLUG` (lugs), `E-PIN-LUG`, `E-ST-JNT` (straight joints), `E-TPE`, `E-CBLE-TIE`, `E-HS-MC`, `E-BB-INSU`; prices from WH `Material Codes` are all <= SAR 5 (fisher 12mm/10mm SAR 5). Alarm cable, DC/AC cable, flexible pipe, glands and breakers are excluded (metre-priced lines can exceed SAR 300; breakers SAR 11+).
- Effect (`outputs/post_may_small_item_waiver_candidates_20260921.json`): 158 of 284 remainder lines fall in these classes; with class list A, 19 of 72 partial MIRs would have only small remainders and close (545, 566, 569, 571, 669, 678, 680, 681, 683, 708, 714, 784, 844, 874, 985, 989, 995, 1013, 1033). Adding a "line value <= SAR 25" test raises this to 36 of 72. `scripts/hr/rank_remainder_items_9a13.py` reproduces the ranking.
- Live note (2026-09-21 ~23:00): neosys.frappe.cloud returned HTTP 503 on `/api/method/ping` (site-wide, not credential or query related); the ranking used WH prices, no ERP call needed. Re-run the G0 diff before any write once the site is back.

**9A.13 small-value waiver - owner decision applied to staging (2026-09-21).**
- **Class-small only:** a partial whose only pending lines are the listed small classes (`M-SCRW`, `M-FLT-WSHR`, `M-FSHR`, `E-CLUG`, `E-PIN-LUG`, `E-ST-JNT`, `E-TPE`, `E-CBLE-TIE`, `E-HS-MC`, `E-BB-INSU`) is `CLOSE_WAIVE_CLASS`: 19 MIRs (545, 566, 569, 571, 669, 678, 680, 681, 683, 708, 714, 784, 844, 874, 985, 989, 995, 1013, 1033). Lines set `CANCELLED` with reason `SMALL_VALUE_WAIVED`, MR `CLOSED`. Not other items, however cheap.
- **Lines <= SAR 25 outside the classes** (real qty > 0 required - a WH qty of 0 is an unknown quantity and never counts as small): 12 MIRs (808, 832, 833, 836-841, 843, 845, 965; all `E-ALM-4P` alarm cable, SAR 5-6.3) are staged `PENDING_OWNER_DECISION` and stay pending - owner chooses dismiss or keep per line: `outputs/post_may_small_value_decision_list_20260921.md`. Correction found while building it: an earlier pass valued WH qty-0 lines at SAR 0 and wrongly swept in batteries, cabinets and breakers (703, 704, 831); fixed.
- Staging JSON fields: `small_waiver`, `waived_lines`, `proposed_waive_lines`.

### 9A.13 - G2 design revised after reading the live rollup (2026-09-22)

**Finding:** the live dispatch-state logic is `SIG_Warehouse/sig_warehouse/sig_warehouse/rollup.py` (the Server Script copy in `register_stock_entry_script.py` is the older subset with no cancel handling). It already has (a) per-line `custom_qty_cancelled` (no-stock dismissal, `allow_on_submit`), (b) `recompute_mr_lifecycle_state`: a fully dispatched MR becomes `CLOSED` only when every outbound Stock Entry has `custom_return_state = DECLARED` - i.e. the owner's "no pending items AND declared return" rule already exists, and (c) the defect the owner described: `stage = "CLOSED" if any_cancelled` - cancelling a partial's remainder closed the MR.

**Local patch (not deployed):** `rollup.py` now takes a per-line reason (`custom_cancel_reason`, new Custom Field in `sig_warehouse_workbench_custom_fields.json`: `OPERATOR_CANCEL` / `SMALL_VALUE_WAIVED` / `DELTA_DISMISSED`). All lines resolved -> `PARTIAL` if any real (operator) cancel and anything was dispatched (a cancelled partial is never CLOSED); `CLOSED` if cancelled and nothing was ever dispatched; otherwise `DISPATCHED`, which the lifecycle closes once returns are declared. Waiver/dismiss reasons resolve a line like a dispatch.

**Supersedes the earlier "lower the MR line qty" idea:** dismissals (76 delta lines / 29 MRs and 158 small-class lines) are written as `custom_qty_cancelled` + `custom_cancel_reason` (metadata, no qty edit on submitted MRs, no stock).

**Closure route in ERP:** dispatched MR -> outbound Stock Entries need `custom_return_state = DECLARED` (field is NOT `allow_on_submit`: server-side `db.set_value`, plus `custom_return_closed_by/on`). Pre-2026-08-09 fully dispatched MIRs get `DECLARED` (retrospective default, per owner); post-cutoff only with `Closed?=1` or a confirmed linked return; then the lifecycle recompute sets `CLOSED`.

**Owner decisions applied:** class-small lines are dismissed everywhere (158 lines) -> 19 MIRs close after dismissal; `E-ALM-4P` (alarm cable) is left for the owner - 12 MIRs (808, 832, 833, 836-841, 843, 845, 965) stay `PENDING` with their small lines dismissed (`small_waiver = DEFERRED_ALM4P_OWNER`).

**Awaiting approval (outward-facing / schema):** (1) deploy the `custom_cancel_reason` field to the live site; (2) commit/push the `rollup.py` change to `SIG_Warehouse` and update the Frappe Cloud bench. Nothing else is applied.

**9A.13 MR-creator review (2026-09-22; Codex handover `outputs/post_may_mir_handover_20260922.md`).** The MR creation path is PowerShell -> live `register_mir` Server Script (`upload_mir_payload.ps1`, `register_mir_server_script.json`); no Python creator exists. Reusable for the ~213 CREATE_MR MIRs (creates `SIG MIR Intake` + submitted MR named `MR-{yy}-{mir}`; idempotent on `SIG-MIR-<n>`; MR `on_submit` runs the rollup). Gaps before it can be used: (1) the existing payload covers only 4 of the 213 - a new reviewed payload must be built from WH219 (dispatched lines at confirmed qty, real remainder at pending qty, small/delta lines added then dismissed); (2) `WH_MAP` lacks the `Riaydh` (22 lines), `Al Qasim` and `Tabuk` aliases (why 569/854 needed a retry) - patch the map or normalise in the payload; (3) `qty <= 0` lines raise `QTY_INVALID` and park the MIR in EXCEPTION; (4) MR date is the first line's date; (5) no MR-line <-> Stock Entry link is written, no dismissal, no closure - those remain the link-writer / dismissal / DECLARED stages. **WH finding:** 74 `Pending` Out rows have qty 0 and comment `close` = WH-closed lines (not real remainders); 25 more `Pending` rows are "reverted to pending 2026-09-14" over-confirmations (real pending). Staging currently counts the 74 as remainders - owner to confirm they be treated as dismissed/closed.

**9A.13 zero-qty Pending rows = never requested (owner + log check, 2026-09-22).** All 75 WH `Out` rows with status `Pending`, qty 0 and comment `close` (24 MIRs) were checked against WH `logs` (Type DN) and `TxJournal`: **none has any trace** - no Success, no Failed attempt, no journal entry, no confirmed twin. They were never requested or attempted. Rule: **not added to newly created MRs** (`wh_closed_handling = omit_on_create`, 2 MIRs) and, where the ERP MR already carries the line (imported earlier with a snapshot qty), dismissed with reason `WH_CLOSED` (`dismiss_existing_line`, 22 MIRs; `custom_cancel_reason` option added; `rollup.py` treats it as a waiver). MIRs made only of such rows are skipped like cancelled ones: **543 and 627** (so "5 genuinely pending" is now 3: 649, 715, 810).
**Re-staged (491 MIRs):** CLOSED 204, OPEN_AS_BUILT 81, PARTIAL_OPEN 53, PENDING 129, SKIP_DUPLICATE 13, SKIP_CANCELLED 11; actions CREATE_MR 213, UPDATE_EXISTING_MR 256, CLOSE_EXISTING_MR 13, SKIP 11 (some rows of CREATE/UPDATE counts shift by the two new skips - see staging JSON). Small-class dismissals fall from 158 to 112 lines (46 were zero-qty rows) and `CLOSE_AFTER_DISMISS` from 19 to 7 MIRs; the other 12 now close through their disposition (fully dispatched, nothing pending). Scripts: `stage_post_may_mr_closure.py` -> `rank_remainder_items_9a13.py` -> `merge_dismissals_9a13.py` (run in that order).

**9A.13 category review pass (2026-09-22, read-only; `scripts/hr/review_categories_9a13.py` -> `outputs/post_may_category_review_20260922.json`, applied by `apply_review_flags_9a13.py`).** Findings and re-categorisation: (1) ERP already holds `custom_return_state = DECLARED` for 19 CLOSED-staged MIRs (consistent) and for MIR **1014**, which was OPEN_AS_BUILT -> reclassified `CLOSED`; 9 partials also have DECLARED returns and correctly stay partial. (2) **70 of 129 pending-only MIRs are older than 90 days** (dated 2026-05/06; MIR 601 dated 2025-11-03, likely a typo) - flagged `STALE_PENDING_OVER_90D` for owner review, no action change. (3) **9 MIRs / 34 remainder lines are superseded** by a same-site confirmed dispatch of the same item under another MIR (674, 699, 810, 921, 1030, 615, 777, 778, 998) - flagged `SUPERSEDED_LINES` with the confirming MIR, moved to Tier 3, owner to confirm dismissal. (4) MIR **872** has a Confirmed row (`G-BB-0.25M`) with no DN - anomaly, Tier 3; it is the only confirmation behind 810's remainder. (5) Seven MIRs whose DN Stock Entry is absent or has a return state PENDING (985, 910, 1005, 1006, 1007, 1037, 1038) are Tier 3 (985/910/1005-1007 are the known 9A.12 / unmatched-line cases). (6) No multi-site or multi-PO MIRs; no Confirmed qty-0 rows. Tier counts now 285 / 147 / 59; dispositions CLOSED 205, PENDING 129, OPEN_AS_BUILT 80, PARTIAL_OPEN 53.

**9A.13 owner decisions after the category review (2026-09-22).** (1) The **70 stale pending MIRs (>90 days) are sidelined** (`action = SIDELINED_PROJECT_CONFIRMATION`): not created (3 were CREATE_MR), and the 67 already in ERP as PENDING MRs are left untouched until the projects team confirms they are still needed. (2) **34 superseded lines assessed:** 23 lines likely duplicate re-raised requests (same PO/project, confirmed under another MIR at the same site, same qty, confirming MIR dated on/after: 615->622, 777->796, 778->795, 921->969, 998->995 - 998 also has each item entered twice) = `LIKELY_DUPLICATE_DISMISS`; 10 lines unclear (674->576, 699->646, 1030->838: confirmed *earlier* under a *different* PO/project - may be a genuine second request) = keep pending, ask projects; 1 line unreliable (810->872, whose confirming row has no DN).

**9A.13 sidelines for owner/WH recheck (2026-09-22).** The 70 stale (>90d) pending MIRs and the 9 MIRs behind the 34 superseded lines (615, 674, 699, 777, 778, 810, 921, 998, 1030; `action = SIDELINED_WH_DECISION`) are skipped in every stage until rechecked. Workbooks (comment column rightmost; built by `scripts/hr/build_recheck_workbooks_9a13.py`): `outputs/post_may_recheck_1_stale_pending_70_20260922.xlsx` (every Out line of the 70 with dates, age, ERP MR/stage) and `outputs/post_may_recheck_2_superseded_lines_9mirs_20260922.xlsx` (all lines of the 9 MIRs; the 34 issue lines highlighted with the MIR that dispatched the item, date, qty, DN, dispatched project/PO and assessment).

**9A.13 false-confirmation check and correction (2026-09-29, owner: MIR 872 `G-BB-0.25M` was never dispatched).** `scripts/hr/verify_confirmed_rows_9a13.py` (read-only) checks every WH `Out` row that says `Confirmed` for MIR >= 543 against `logs` (Success, DN number = MIR, same item, summed qty) and `TxJournal`. **1,772 of 1,777 rows are evidenced (4 more are ERP-era >= 1035); exactly one is not:** 872 `G-BB-0.25M` - no DN, no logs/journal row, and the stock chain for that item runs 45->44 (DN 782), ->43 (794), ->42 (875, 6 Aug), ->41 (808, 10 Aug) with no 872 deduction. Cause: WH **row-key collision** - the Out rows for 872 `G-BB-0.25M` and for 863 `C-GLND-2` / `M-FCON-MTL-2.5` all carry `DN-872-20260803110129-000032`, so confirming DN26-0863 (3 Aug 17:13) also marked 872's line Confirmed. No other Row Key is shared across MIRs. `scripts/hr/correct_false_confirmations_9a13.py` (idempotent, before-images kept, run last in the staging pipeline) applies: **872 -> PENDING** (3 pending lines; `UPDATE_EXISTING_MR` with `add_lines = G-BB-0.25M x1`, because MR-26-0872 holds only the two lines that were pending at import; the E-BB-INSU small-value dismissal is dropped), **810 -> released from `SIDELINED_WH_DECISION`** (its only superseded line depended on 872) to `CREATE_MR` with all 11 lines, tier 1, warnings `G-CAD-WELD` not in ERP and fractional qty 0.25 on `G-BB-0.25M`. The other 8 sidelined MIRs (615, 674, 699, 777, 778, 921, 998, 1030) rest on Confirmed rows that are all log-evidenced, so they stay sidelined for the WH decision. Counts now: PENDING 130, PARTIAL_OPEN 52 (dispositions otherwise unchanged); sidelined-WH 9 -> 8. The recheck workbook `post_may_recheck_2_superseded_lines_9mirs_20260922.xlsx` was not regenerated and still lists 810. Nothing was applied to ERP.

**9A.13 line pre-flight vs live ERP (2026-09-29, read-only; `scripts/hr/preflight_mir_lines_9a13.py` -> `outputs/post_may_preflight_lines_20260929.json`).** Mirrors the `register_mir` hard errors over the 392 CREATE_MR / UPDATE_EXISTING_MR MIRs. **Hard blockers: 28 MIRs.** (1) `ITEM_NOT_IN_ERP` 12 MIRs: `EC-NOK-IND` x11 lines (566, 567, 569, 571, 572, 574-578, 608) - a WH code for ERP's `E-EC-NOK-IND` (same description; 9A.14 rule: resolve by description in the payload builder); `G-CAD-WELD` x1 (810; also the stale, un-imported 649 and 715). `G-CAD-WELD` "Cadweld Connection" (Set) has never had stock anywhere: no WH stock-sheet row, price #N/A, no log row, no ERP item/Bin; the stocked cad-weld item is `G-PWDR-FRS-90` (powder, ERP Riyadh 0 / Jizan 9), which MIR 389 dispatched beside the same G-CAD-WELD request. (2) `WAREHOUSE_UNKNOWN` 15 MIRs (566-579, 854): WH texts `Riaydh` / `Al Qasim` are missing from `WH_MAP` (known). (3) `UOM_UNKNOWN` MIR 786: unit `#N/A` on an `E-EC-NOK-IND` row. **Soft (review hold, lines kept, project unlinked): `PROJECT_AMBIGUOUS` on 136 CREATE_MR MIRs** - PO 10001045 matches two Projects (WO-2026-0026 Completed, WO-2026-0050 Open; 314 lines), 1000705 two, 1000649 three; `register_mir` does not fall back to the source project text once ambiguous. No disabled or non-stock items, no fractional-on-whole-UOM lines.

**Item-master duplicates vs WH catalog - audit and staged fixes (2026-09-29, read-only; owner: WH sheets are the stock truth).** `scripts/hr/audit_item_master_vs_wh.py` -> `outputs/item_master_audit_20260929.json`; `scripts/hr/stage_item_master_fixes.py` -> `outputs/item_master_fix_stage_20260929.json`. ERP 923 items vs WH catalog 459: 437 match, 486 ERP-only (mostly Finance/service/PO-line items with no stock), 22 WH-only (incl. `EC-NOK-IND` = ERP `E-EC-NOK-IND`, `G-CAD-WELD`), 19 UOM differences (String/Strings, Pcs/Box for the repacked fisher/screw family). **DC cable 35 mm:** ERP `E-DC-CAB-A-35` "(Amaleege)" is a Flexsoft-legacy item - two 2024 Purchase Receipts (MAT-PRE-2024-00056/57) from Amaleege Cables Company, 1,638 m @ 16.04; 989.3 m left in Riyadh. WH has one code `E-DC-CAB-35` and no Amaleege row. Reconciled per warehouse, `E-DC-CAB-35` alone already equals the WH sheets (Riyadh 295.75 = ERP 253.75 + 42 dispatched since; Makkah 99.6 = 75.6 + 24; Jizan 134.5) - so the 989.3 m on `A-35` is stock WH does not hold. **A merge would put ~989 m of phantom stock onto the WH item; the fix is zero-then-merge: Stock Reconciliation to 0 (SAR 15,850 write-off, Finance sign-off), then Frappe rename-with-merge into `E-DC-CAB-35` - ONE code, no alias/crosswalk table (owner 2026-09-29: WH-coded items are never disabled or renamed).** The same pattern holds for 7 ERP-only variants (SAR 106,011 in total: `E-SNSER-DT-5L/2L`, `E-CAB-XLP-J-4-120`, `E-BKR-NDR-20A`, `E-DC-CAB-6c`, `M-DSL- RBR-PPE-3/4`): the WH-coded twin already equals WH. 10 more variants (e.g. `E-DC-CAB-J-35`, `A-70`, `J-70`, `E-CAB- F-4-35`) have zero stock and only ledger history: rename-with-merge into the WH code (history is kept); 4 have no ledger rows: delete; 2 (`E-EC-NOK-IND`, `E-DCDB-250`) have no ERP item under the WH code: rename the ERP item to the WH code. Description-based twin matches (e.g. `G-GERD-XCON-(8-10mm2)`, `C-A-Silicone`, `CW-T-SR-SP`) need a human check before any merge. Merge prerequisites to verify against the deployed v15 source first: same stock UOM / is_stock_item, valuation repost after merge, one canary on a zero-stock variant. The 32 stock-holding ERP-only items (SAR 646,128) DO have WH twins (owner: "must have variants in WH") - the Flexsoft purchase-side codes differ from WH's (`FO` = Fiber Ocean = Nokia: `E-RM-FO-50` = `E-RM-NOK-50`, `E-DCP-FO-36KW` = `E-DCP-NOK-36`, `E-IRC-NOK-1000A` = `E-IRC-NOKIA`; `E-TL-*M` = `C-TWR-LGHT-*M`; Zamil `3TL/3TR` = `EM-PK-ZAM-3T`; `E-LIT-GR-L` = `E-Lit-R-L`; `E-RM-ETK-50`/`E-RM-FP-50` = `E-RM-FP-ELT-50`; `TC-A-INC-LBL` = `M-LBL`; etc.; `outputs/item_master_gap_twins_20260929.json`). For 16 of 19 twins the ERP twin already equals the WH sheet at the WH snapshot, so the variant balance is extra: zero-then-merge. The 3 Nokia items (SAR 346k) do NOT reconcile cleanly (WH receipts 57 pcs of E-RM-NOK-50 in 2026 vs ERP purchase receipts of 153 as `E-RM-FO-50`; only 2026-08-19 13 pcs match) - WH physical count first, no write-off before. 8 small legacy tools (`T-C-*`, `T-E-Cutter-10`, `T-P-HLIGHT`, `E-Tool-Label`) have no WH item. The Material Codes "Total Stock" column is a hard-coded snapshot (E-DC-CAB-35 = 1,539.5), not a live sum: do not use it as stock truth. Nothing was changed in ERP. Item import/update (WH-code-prevails crosswalk MIR-G1, Item Intake ITEM-0/1) is still "Not started" in the plan.

**Item merge attempt and blocker (2026-09-29).** Full Frappe Cloud DB backup taken first: `9ug2b1kbov`, 2026-09-29 21:52 (no files; script `backup_neosys_site.ps1`, run with the current Cloud key `frappe_cloud_press_api_2026_09_28.env` because the older `sig_frappe_cloud_api.env` returns AuthenticationError). Deployed-source check (erpnext version-15 `item.py`): `rename_doc(merge=True)` requires equal stock UOM / stock-item / serial / batch flags, deletes both items' Bins, temporarily flips `allow_negative_stock`, and re-posts the twin's Bins from the merged Stock Ledger - so a variant must hold zero stock first. **Canary `E-DC-CAB-J-70` -> `E-DC-CAB-70` (`scripts/hr/merge_item_variant_9a15.py`) was REFUSED by ERPNext: "cannot repost item valuation before 2025-12-28" - `Accounts Settings.acc_frozen_upto = 2025-12-28`.** Every Flexsoft-legacy variant has ledger rows from 2024-2025, so none can be merged while the books are frozen; the failed call rolled back (verified: variant and twin unchanged, `allow_negative_stock` still 0). Options: (a) zero the variant's stock with a Stock Reconciliation dated after the freeze, then disable the variant (one ACTIVE code; history keeps the old code; ERP forbids deleting items with ledger rows); (b) Finance lifts the freeze for the merge - not recommended: the repost re-values 2024-25 entries while GL is not reposted. Only variants with no ledger rows can be deleted. The freeze setting was NOT changed.

**How the variant stock entered - Purchase Receipt -> Invoice -> Payment trace (2026-09-29, read-only; `scripts/hr/trace_variant_purchases_9a15.py` -> `outputs/variant_purchase_trace_20260929.json`).** Every variant balance came from Flexsoft-legacy Purchase Receipts (2024-2026) or opening Stock Reconciliations; the WH twin was then re-set to the WH count by the opening recons (`SIG-CR-OPN-*`, 2026-02-27) and the G4 closing recons (`SIG-CR-G4-*`, 2026-09-13), which post their difference to `5129 Stock Adjustment` - and never touched the variant codes. Example: `EM-PK-ZAM-3T` was raised to 18 units @ 7,750 = SAR 139,500 by recon `MAT-RECO-2026-00013/14`, while `3TL`+`3TR` still carry the same 18 units @ 7,750 from the paid 2024 Zamil receipts: the same units are booked twice. Payment status: **billed and paid** (real spend) - Zamil `3TL/3TR` 385,750 each fully paid, `4TL/4TR` 671,200 billed / 584,005 paid each, Amaleege `E-DC-CAB-A-35` SAR 26,274 paid, Shabakkat `G-ERD-SPIL-1.5m` 1,045 paid; **billed, unpaid** - Motoma breakers `E-BKR-NDR-16A/40A/20A` (906 / 1,848 / 915), `E_DCDP_R` 6,250; **received, not billed (GRNI open)** - Alma Start `E-TL-*` 52,480, Dana `E-LIT-GR-L` 47,500, United Specialists `E-RM-ETK-50`/`E-RM-FP-50` 10,800, Shabakkat `G-ERD-ANGL-1.5M:` 10,965, ABB 5,650, Nokia `E-RM-FO-50` 175,170 / `E-DCP-FO-36KW` 128,250 / `E-IRC-NOK-1000A` ~43,200 (billed 8,790 / 5,150 / 198,800 and paid 5,940 / 5,150 / 127,800 in total); no receipt at all (entered by opening reconciliation) - `E-SNSER-DT-5L/2L`, `E-CAB-XLP-J-4-120`, `E-DC-CAB-6c`, `M-DSL- RBR-PPE-3/4`. Resolution rule that follows: a paid/billed variant duplicates a recon-created twin -> zeroing the variant (debit 5129) reverses the recon's phantom credit to 5129, so the P&L effect nets to about zero per pair (Finance to confirm against the 5129 balance); an UNBILLED post-2025-12-28 receipt whose goods WH already counts under the twin should be cancelled (clears stock and GRNI, no P&L) and the supplier invoice booked against the WH code; pre-freeze receipts cannot be cancelled.

### 9A.15 - Item-master cleanup backlog (deferred by owner 2026-09-29: "needs too much work")

Nothing below has been applied to ERP. Evidence: `outputs/item_master_audit_20260929.json`, `item_master_fix_stage_20260929.json`, `item_master_gap_twins_20260929.json`, `variant_purchase_trace_20260929.json`; the findings are in the paragraphs immediately above (audit, merge blocker, purchase/payment trace, Nokia check). Backup taken before the merge attempt: Frappe Cloud `9ug2b1kbov` (2026-09-29 21:52, DB only). Owner rules: WH sheets = stock truth; ONE item code = the WH code; no alias/crosswalk tables; WH-coded items are never disabled or renamed.

| # | Task | Status / blocker | Effort |
|---|---|---|---|
| IM-1 | Zeroing of paid duplicate pairs (Zamil `3TL/3TR/4TL/4TR`, `E-DC-CAB-A-35`, `E-SNSER-DT-5L/2L`, `E-CAB-XLP-J-4-120`, `E-BKR-NDR-20A/40A/16A`, `E-DC-CAB-6c`, `M-DSL- RBR-PPE-3/4`, `G-ERD-SPIL-1.5m`, `E-RM-ETK-50`, `E-RM-FP-50`, `TC-A-INC-LBL`, `EM-HVACP-ABB-S3- ...`) by Stock Reconciliation dated after 2025-12-28, then disable the variant | Finance to confirm the net effect on `5129 Stock Adjustment` (expected ~0 per pair: reverses the recon's phantom credit) and sign off; merge is NOT possible while `acc_frozen_upto = 2025-12-28` | Medium |
| IM-2 | Unbilled, post-freeze receipts whose goods WH already counts under the twin (Alma Start `E-TL-*`, Dana `E-LIT-GR-L`, United Specialists, ABB, Shabakkat `G-ERD-ANGL-1.5M:`): cancel the Purchase Receipt (clears stock + GRNI, no P&L) and book the supplier invoice against the WH code | Needs WH confirmation of goods per receipt; pre-freeze receipts cannot be cancelled | Medium |
| IM-3 | Nokia / Fiber Ocean (`E-RM-FO-50`, `E-DCP-FO-36KW`, `E-IRC-NOK-1000A`, ~SAR 346k) | WH physical count first; then reconcile ERP purchase receipts vs WH `In` receipts (see the open check below) | High |
| IM-4 | Item sync (import/update) WH catalog <-> ERP Item master: create the 22 WH-only codes, update names/UOMs (41 name and 19 UOM differences; UOM edits are blocked once an item has ledger rows), keep WH code canonical; RV80 hook via the existing Item Intake design (MASTER 4.1, ITEM-0/1) | Not built; the RV80 item-import pattern the owner referred to was not found in the ERP repo - owner to point to it | High |
| IM-5 | Description-only twin matches to verify before any action: `G-GERD-XCON-(8-10mm2)`, `C-CRNR-POST-ACC`, `E-RELAY-CO-230V-6A`, `CW-T-SR-SP`, `C-A-Silicone`, `C-URMNT6-5M` (probably `C-MNT-5m`) | Human check | Low |
| IM-6 | Legacy tools (`T-C-*`, `T-E-Cutter-10`, `T-P-HLIGHT`, `E-Tool-Label`, < SAR 150) - not in the WH catalog | Owner: add to WH catalog or write off | Low |
| IM-7 | WH-side duplicate codes inside the WH catalog itself (e.g. `E-BKR-NDR-125` vs `E-BKR-NDR-HU-125`, `-63`/`-HU-63`) | WH decision; ERP never disables WH-coded items | Low |

**Easy remedies (safe, no stock effect) - to do in the Item form / by hand:** (a) delete the 4 variants with no ledger rows: `E-ODU-NOK-2K.`, `E-CAB-CC-2C-1.5`, `FA-S-SHO-RM-42`, `E-DCDB-250` (check no open PO/MR uses them; ERP refuses the delete if linked); (b) tick **Disabled** on the zero-stock legacy variants: `E-DC-CAB-J-35`, `E-DC-CAB-A-70`, `E-DC-CAB-J-70`, `E-CAB- F-4-35`, `E-CAB-XLP-J-4-70`, `EM-PK-ZAMI-4T`, and the test item `Cable2m`; (c) MIR loading: add `Riaydh` / `Al Qasim` to the `register_mir` warehouse map, fix the `#N/A` unit on MIR 786, dismiss the `G-CAD-WELD` line on MIR 810, and resolve the ambiguous POs (`10001045` -> WO-2026-0050, `1000705`, `1000649`) in a small PO -> Project table.

**Why `#N/A` appeared and what else is messy at the MIR entry point (2026-09-29, owner: "we asked the VBA not to follow item UOM, codes are enough").** No Material Request or MIR Intake Line in ERP carries an `N/A` unit (0 rows). The `#N/A` is in the WH `Out` sheet only: 5 lines (MIRs 609, 654, 663, 667, 786), all item `E-EC-NOK-IND` - the sheet looks the unit up in Material Codes, and that code is not in WH's catalog (WH's is `EC-NOK-IND`), so the lookup fails. It only became a blocker because the deployed pieces never adopted the owner rule: RV80 `MirErpSend.bas` still posts `unit_i` (mirlogs col K) verbatim, and the live `register_mir` still required the unit to be in a hand-kept `UOM_MAP` (`UOM_UNKNOWN`). The "unit from the ERP item master, never from the sheet" rule existed only for the new 9A.14 payload builder. **Mess measured on the 2,700 post-May `Out` lines:** 20 spellings of 11 units (`Pcs.`, `Pcs`, `Pc`, `MTR`, `Mtr`, `Mtr.`, `Strings`, `Strings.`, `String`, `Box.`, `Box`, `Set`, `Set.`, `Roll.`, `Roll`, `Bucket.`, `Bucket`, ...); 6 spellings of 4 warehouses (`Al Qasim` x475, `Riaydh` x22, `jizan` x2 - the live warehouse map only knew `Qasim`, `Riyadh`, `Makkah`, `Jizan` in exact case); 3 case variants of catalog codes (`E-Alm-8p`, `E-ODU-FEN-2k`, `E-BKR-CHINT-125-1P`); 44 blank codes; PM names with a trailing tab. **Patch staged in `scripts/hr/register_mir_server_script.json` (NOT deployed):** the MR line uses the ERP Item's `stock_uom` and canonical code casing (the sheet unit is kept only as `source_uom`); warehouse text is folded (case, spaces, `Al Qasim`/`Riaydh`/`jizan`, ...). To do next in the same spirit: RV80 `MirErpSend.bas` to stop sending `unit`, validation lists on the WH/RV80 warehouse and item-code cells, and one governed normalizer (codes case-insensitive to the single WH code; warehouses; PO -> Project table) shared by RV80, WH and ERP, like the Tawal PO/BA resolver.

**Simple fixes applied 2026-09-29 (owner: "do the simple fixes"; site backup `9ug2b1kbov` + item before-images in `outputs/backup_item_easy/`).** (1) **`register_mir` patch DEPLOYED** (before-image `outputs/backup_register_mir/register_mir_live_before_20260929_210751.json`; live == repo mirror): MR lines use the ERP Item's `stock_uom` and canonical code casing, the sheet unit is ignored (kept as `source_uom`), warehouse text is folded (`Al Qasim`, `Riaydh`, `jizan`, ...). Canary MIR `990001` (lowercase code `e-alm-8p`, unit `#N/A`, warehouse `Al Qasim`) -> `created`, `readback_ok`, MR line `E-ALM-8P` / `Mtr` / Qasim warehouse; the test MR `MR-26-990001` (+ intake `SIG-MIRI-0414`) was cancelled. RV80 `MirErpSend.bas` needs no change to work (the server now ignores the unit). **Same weakness remains in the live `register_stock_entry` (exact-case `WH_MAP` and a hand-kept `UOM_MAP`, unit required per line) - it posts stock, so it is a separate, carefully tested change (see IM-8).** (2) Items (`apply_easy_item_fixes_9a15.py`): deleted `E-CAB-CC-2C-1.5`; renamed `E-DCDB-250` -> `E-DCDB-LND-250A` (WH code; no ledger rows); disabled `E-DC-CAB-J-35`, `E-DC-CAB-A-70`, `E-DC-CAB-J-70`, `E-CAB- F-4-35`, `E-CAB-XLP-J-4-70`, `EM-PK-ZAMI-4T`, `E-ODU-NOK-2K.` and `FA-S-SHO-RM-42` (ERP refused to delete these two: still linked, "disable instead"). `Cable2m` was left alone (already disabled; open `MAT-MR-2026-00001` / `PUR-ORD-2026-00001` reference it). Not done: IM-1..IM-7 above.
| IM-8 | Apply the same UOM-from-item-master + warehouse folding to `register_stock_entry` (DN/TN/PR/RN/BI/CR posting), with a canary and stock-diff check | Not started | Medium |

**`G-CAD-WELD` WH-sheet history (2026-09-29, read-only scan of every WH219 sheet by exact code): the item has NO stock history.** Only the catalog row (Material Codes: unit Set, price `#N/A`, stock 0) and four never-fulfilled `Pending` requests exist: MIR 389 (2026-03-08, 5G7, site ZJZ272, 10 sets; comment "To Cancel - Likely Pending", review sheet class `NO_LOG_AT_ALL`), MIR 649 (2026-05-21, 5G6, ZUZ042, 6), MIR 715 (2026-06-17, 5G7, ZRW783, 4) and MIR 810 (2026-07-16, 5G7, ZAS033, 3) - 23 sets requested, none ever supplied; the WH dashboard lists it as a deficit of -13 blocking 649/715/810. No `In` receipt, no stock-sheet row in any warehouse, no `logs`/`TxJournal`/`Old-Out`/`Out-Add`/`Return`/`Bulk`/`Correction` row. The cad-weld material that WH does stock and dispatch is `G-PWDR-FRS-90` (MIR 389 dispatched 10 pcs as DN26-0389-1). Recommendation: dismiss the `G-CAD-WELD` lines (do not create the item) and ask projects whether 649/715/810 need `G-PWDR-FRS-90` instead.

**RV80 item list = ERP (owner 2026-09-29: "we HAVE to have a sub that REPLACES items and codes in WHC, per ERP") - built.** Findings first: RV80 had no item-import sub; `WHC` (hidden table S.N/Category/Code/Item Name/Unit + ERP stock F:G) is the item master, `Material Codes` is a formula view of it, and the only refresh (`Logs_RefreshMaterialCodesStockFromERP`) touches the stock columns only. **ERP side (live):** Custom Fields `Item.custom_wh_catalogue` (Check, "In WH / RV80 material catalogue") and `Item.custom_wh_category`; 438 enabled ERP stock items matching WH catalogue codes flagged; read-only Server Script `get_item_catalogue` (pipe rows `code|category|name|uom`, enabled stock Items with the flag) - smoke: 457 rows; `scripts/hr/deploy_item_catalogue_9a15.py`. Missing WH codes created in ERP under the WH code and flagged (`scripts/hr/create_missing_wh_items_9a15.py`): `M-ANTI-SIPHN-3/4`, `E-Lit-NOK-100`, `C-CLMP-3/4`, `E-Fuse-63A`, `EM-HVACP-ETN-P`, `E-LDP-S`, `E-LDP-S-UF`, `M-RDCR-STL-3/4`, `M-RDCR-PVC-3/4`, `E-TRF-50`, `EM-CST-ZAM-3T`, `E-DCDP-BTRY`, `C-TWR-LGHT-55M/150M/170M`, `E-BKR-NDR-HU-16/32/40` (WH's own duplicate codes mirrored, IM-7); ERP `E-EC-NOK-IND` **renamed to the WH code `EC-NOK-IND`** (verified: 36 ledger rows and bins 2+2 followed the item) - so the 5 WH `Out` lines that still carry `E-EC-NOK-IND` (MIRs 609, 654, 663, 667, 786) must be corrected to `EC-NOK-IND` in WH/RV80; never created: `G-CAD-WELD` (no stock history) and the `-` placeholder row. **RV80 side (staged, NOT yet imported into the workbook):** `rv80/deployed/ItemCatalogueSync.bas` (`V-itemcat.rv80.260929001`), sub `ItemCat_ReplaceWHCFromERP`: reads the endpoint with the read-anchor key, shows a preview (added / removed / renamed / unit changed) and asks to confirm, keeps the old list on hidden sheet `WHC_prev`, replaces WHC A:E and resizes the table, extends the `Material Codes` formula view, then runs the existing stock refresh; refuses < 300 items, duplicate codes, or dropping > 50% of the list. Dry comparison against the v802 workbook: ERP 457 vs WHC 452 -> removed `-` and `G-CAD-WELD`; added `C-FNC-P-Gate-S`, `C-MNT-ANTN-6M`, `E-CLUG-PIN-35M`, `E-CLUG-PIN-50M`, `E-ODU-FEN-2K`, `E-RM-EXI-75`, `S-SHO-RM-42`; 62 names differ (ERP names still carry legacy tags such as "(Riyadh Cable)" - clean via the item sync, IM-4) and 18 units differ (`Strings`/`String`, `Set.`/`Pcs`). To add or remove an item in RV80 from now on: tick / untick "In WH / RV80 material catalogue" on the ERP Item. Import + first run in Excel is a manual step (VBE: File > Import ItemCatalogueSync.bas, Alt+F8 `ItemCat_ReplaceWHCFromERP`); VBA could not be compiled or run from here.

**RV80 items + projects imported together from ERP (2026-09-29, owner: "make it so the project part and the items part are imported together").** `rv80/deployed/ItemCatalogueSync.bas` is now `V-itemcat.rv80.260929002`: one sub `ERP_ReplaceCataloguesFromERP` (alias `ItemCat_ReplaceWHCFromERP`) reads BOTH ERP endpoints first, shows ONE preview (items added/removed/renamed/unit; projects added/removed/changed) and asks ONE confirmation, then replaces WHC A:E and the new hidden sheet `ERPProjects` (ERP Project | PO | Project Name | Status), keeps `WHC_prev` / `ERPProjects_prev`, and finishes with the existing ERP stock refresh. New read-only endpoint `get_project_catalogue` is LIVE (47 non-cancelled Projects; `scripts/hr/deploy_item_catalogue_9a15.py --projects`). RV80 had no existing ERP project import (only the stock snapshot read and the MIR/evidence sends), so `ERPProjects` is new; the MIR entry form/userform that picks Project and PO is not in the exported code and still has to be pointed at `ERPProjects` by the workbook owner. **`register_mir` v2 DEPLOYED** (before-image `outputs/backup_register_mir/register_mir_live_before_v2_20260929_225608.json`): an explicit ERP Project id in the MIR line `project` is authoritative; when several ERP Projects share a PO the single **Open** one wins (only otherwise `PROJECT_AMBIGUOUS`). Canary MIR `990002` (PO `10001045`, text project `5G7`, warehouse `riaydh`, unit `#N/A`) -> `created`, line project `WO-2026-0050` (the Open one, not the Completed `WO-2026-0026`), MR cancelled. Still ambiguous by design (all candidates Completed): POs `1000705` (2 projects) and `1000649` (3) - use the ERP Project id. Security notes from the RV80 export review: `erp.bas` carries an ERP API key/secret as plain-text constants and `sitesdbImport.bas` a workbook-protection password - rotate/move them out of the workbook source.

**RV80 current cleanup supersedes the 2026-09-29 stock-refresh notes (2026-10-24):** `ItemCatalogueSync.bas` now refreshes the ERP item catalogue and ERP project list only; no stock endpoint or stock-preservation logic runs, and the sync no longer creates `WHC_prev` / `ERPProjects_prev`. The deployed BAS source no longer contains the retired Plans/LT2 import/export, PRG progress, site-planner email, Google visit-row fetch/recovery, PIMP plan-export evidence, or visit/planning KML entry points. Active Tags intake/reporting, TCN-MDT workflow and KML, site-access KML, site resolution, SIGExtract and ERP evidence posting are retained. A full pre-cleanup source snapshot is at `D:\rv80\_archive\vba\full-deployed-source-before-legacy-cleanup-20261024\`; the updated BAS files are in `D:\rv80\deployed`. These are source exports only: the embedded VBA modules in an open RV80 workbook still need importing before the workbook runs this cleaned code.

**Correction and Builder/TCN project import (2026-09-29, owner: Builder has PROJECT columns for tcnword; AR:AS is not part of this).** Builder `AR:AS` are the Tags item-title rename rules (`Tags_ApplyBuilderItemRename_V2`) and are NOT touched or synced; an ERP "equipment family" master built on them was proposed and dropped - nothing was created for it in ERP. What the code actually does: no exported RV80 module imports ERP projects into Builder or TCN. `tcnword.bas` `ResolveProjectFamily_Enhanced` maps PO -> family (5G / Capex / Incident) from a **hard-coded `Select Case`** (comment: "ERP project setup registry") - 17 POs copied by hand; Builder col R holds the local stream/alias rows (`5g`, `capex8`, `itc`, `mobily`, ...) with Tawal PM (S:U), our PM (W:Z, BD) and family (AB), all local. **Built:** ERP Custom Field `Project.custom_family` (Select 5G/Capex/Incident) seeded from that hard-coded list onto 20 ERP Projects (both `10001045` projects = 5G, etc.; Open projects without a family: `WO-2026-0016` Flooring, `0017` Waterproofing, `0039` Shabakat - not TCN work); `get_project_catalogue` now returns `id|po|name|status|family`; `ItemCatalogueSync.bas` (`V-itemcat.rv80.260929003`) writes the family into `ERPProjects` column E in the same one-click download as the items and exposes `ErpCat_FamilyForPo(po)` (Open project wins); `tcnword.bas` (`V-tcn.rv80.260929001`) `ResolveProjectFamily_Enhanced` now asks ERP first and keeps the `Select Case` only as fallback. Aliases/streams in Builder col R and all PM data stay local. To apply in Excel: re-import `ItemCatalogueSync.bas`; in `tcnword` replace only the `ResolveProjectFamily_Enhanced` function with the deployed one (do not re-import the 7,500-line module blindly); run `ERP_ReplaceCataloguesFromERP` once. Not compiled or run from here.

**Open check for later - Nokia / Fiber Ocean items (owner asked to record this 2026-09-29; NOT to be written off or merged until WH physically counts).**
- `E-RM-FO-50`: ERP's purchase receipts total 153 pieces in 2026 (50 in January, 90 in February, 13 in August). WH's own receipts of `E-RM-NOK-50` total 57 pieces. Only the 13 pieces on 2026-08-19 match on both sides.
- The other two (`E-DCP-FO-36KW`, `E-IRC-NOK-1000A`) are similar. ERP books 25 of the first and 3 of the second, where the WH sheets show 1 of each.
- Why it matters: either Finance booked purchases that were never physically received, or WH under-recorded. Do not write these off until WH does a physical count.
- Sheet caution: the `Total Stock` column in WH Material Codes shows 90 for `E-RM-NOK-50`, but the stock sheets show 12. That column is not live, so it is not used.
- Evidence: `outputs/item_master_gap_twins_20260929.json` (rows `E-RM-FO-50`, `E-DCP-FO-36KW`, `E-IRC-NOK-1000A`, verdict `COUNT_WH_FIRST`); WH `In` sheet receipts PR26-0012/0022/0039/0048/0055/0062 vs ERP Purchase Receipts MAT-PRE-2025-00043/-00065, MAT-PRE-2026-00001/-00013/-00027.

**9A.13 G3 canary - executed and PASSED (2026-09-23).** Proves the deployed `rollup.py` fix on a
throwaway, clearly-tagged test MR (`MR-2026-0104`, `custom_mir_number = G3-CANARY-9A13`, 2 lines
of high-stock inert items, 1 unit each) - no production MIR touched: dispatched line A (real,
tiny Stock Entry `STE-2026-0907`, DN26-1048) via `sig_dispatch_mr`, cancelled line B's demand via
`sig_cancel_mr_lines` (no stock). Read-back: `custom_dispatch_stage = PARTIAL` (line A
`DISPATCHED`, line B `CANCELLED`) - the exact fix; the pre-fix code would have set `CLOSED` here
since both lines were "resolved". Cleanup: cancelled the Stock Entry (bin quantities confirmed
back to exact baseline) and the MR; hard-delete of both is blocked by `LinkExistsError` against
their `SIG Dispatch Operation` audit rows - left cancelled, by design, not deleted. Script:
`scripts/hr/g3_canary_9a13.py` (dry run / `--yes` / `--cleanup-only`).

**Still needed for a full G3 close:** the other canary in the runbook (create + link + declare
DECLARED-return + close, on a real retrospective MIR) needs a link-writer endpoint that does not
exist yet - not built. Everything below G3 (G4 batches, G5 bulk creates, etc.) still waits on
that and on the payload builder from WH219.

### 9A.14 - Forward dispatch plan: MR-numbered DNs, and the rest of 9A.13 / G3 (finalized 2026-09-24)

**Purpose.** One ordered plan for (a) making every DN carry its MR's number again, (b) the metadata
tooling that G3 and the rest of 9A.13 need, and (c) closing G3. It supersedes the "do not reproduce
the legacy suffix convention" guidance (MASTER-ERP-INTEGRATION.md 0.2b and the 2026-09-23 deferral
note): the owner decided the opposite on 2026-09-24, and the WH data supports it.

#### A. Decisions (owner, 2026-09-24)
1. **A DN is named after its MR.** `DN26-<MIR>` when that first dispatch clears every remaining line
   of the MR; `DN26-<MIR>-1`, `-2`, ... for partial dispatches and for every dispatch after the first.
   Evidence that this can be decided at dispatch time: in `WH219.xlsm`, 2,704 of 2,715 confirmed
   lines had `DN == MIR`; 141 MIRs have only a `-1` DN (suffix given at the first *partial*
   dispatch); only one MIR (368) mixes a plain DN with a suffixed one. (My earlier claim that the
   suffix could only be decided in hindsight was wrong.)
2. **The 14 ERP-era vouchers get an `X` suffix** so they cannot collide with MR numbers:
   `DN26-1035`..`DN26-1048` become `DN26-1035X`..`DN26-1048X` (issued 16-23 Sep 2026; the global
   counter's number space overlapped MIR numbers 1035-1046). The original number is kept in a new
   read-only `Stock Entry.custom_legacy_dn`; `SIG Dispatch Operation.dn_voucher` (audit) is untouched.
   Cost: PDFs and WhatsApp messages already sent show the old number (14 documents, 8 days).
3. **MRs without a MIR number are a safety net only.** Live check 2026-09-24 of all 311 Material Issue MRs:
   7 have a blank MIR number (all created 2026-09-16 in the proving pass, 6 cancelled) and 22 have a
   non-numeric one (all `STAGE*TEST` / `HOOKTEST` / `G3-CANARY-9A13` test artifacts); every real MR carries
   its MIR number. If a hand-made MR ever has none, the dispatch still succeeds using `DN26-X<counter>`
   (never a failure, never a number that could clash with an MR).
4. WH-era vouchers (`DN26-0001` .. `DN26-0519` etc.) already follow the MIR rule and are not touched.

#### B. Allocator design (`sig_warehouse`: `sig_dispatch_mr` -> `cutover.allocate_dn_voucher`)
- Lock the Material Request row (`SELECT ... FOR UPDATE`), not one global row, so two users cannot
  take the same suffix for the same MR.
- Prior allocations for the MR = the union of (a) every `SIG Dispatch Operation` for it (any state, including
  cancelled: a number is never reused) and (b) every Stock Entry, in any state, whose `custom_source_id`
  matches this MIR's voucher pattern (`DN26-<MIR>` or `DN26-<MIR>-<n>`, also inside the legacy
  `SIG-DN-...` form; the pattern must not match `...X` or a longer number). Matching by voucher, not by
  the MR-line link, means numbering does not have to wait for 9A.13 to link legacy dispatches. A plain
  voucher counts as sequence 1. Known limit: ERP holds each WH-era partial under its base voucher
  (G1 finding), so a MIR where WH did two partials (`-1`, `-2`; about 13 MIRs) appears once and would
  get `-2` instead of `-3`: correct those from `WH219.xlsm` when the allocator ships.
- Sequence 1 and this dispatch clears every open line -> plain `DN26-<MIR>`; otherwise `-<seq>`.
- **Uniqueness guard, independent of any link:** if a Stock Entry (any docstatus) already carries the
  chosen voucher, bump the suffix until it is free. Accepted consequence: an old MR whose legacy DNs
  are not yet linked could get a suffix that differs from its "true" history (cosmetic), but can
  never collide.
- The global counter stays only for the `X` namespace (next value 1049 today).
- Downstream: the SIG print formats and the WhatsApp caption read `custom_source_id` verbatim, but the
  WhatsApp PDF **filename** regex needs widening for the `X` forms (see R3).

#### C. Ordered work (each step: dry run -> owner OK -> apply -> read-back; stop on first error)

| # | Work | Gate to pass |
|---|---|---|
| 0 | Record the decisions (this section) and fix the two contradicting doc notes | Done 2026-09-24 |
| 1 | **Metadata writer** in `sig_warehouse`: one whitelisted method with dry run, before-image, idempotency key and an allow-list of MIRs. Operations: (i) link a Stock Entry line to its MR line (`material_request`, `material_request_item`); (ii) stamp `custom_return_state = DECLARED` (+ `custom_return_closed_by/on`); (iii) dismiss lines (`custom_qty_cancelled` + `custom_cancel_reason`); (iv) rename `custom_source_id`, saving `custom_legacy_dn` (used by step 5). All through `frappe.db.set_value(..., update_modified=False)`; REST cannot do these (permlevel 1 and not `allow_on_submit`). Create the `custom_legacy_dn` field first (field-first). Deploy with `scripts/hr/deploy_sig_warehouse_bench.py`. | Unit-tested on the throwaway MR; deployed; read-back |
| 2 | **Fresh G0 snapshot**, taken immediately before step 3 (`scripts/hr/g0_snapshot_9a13.py`) | Snapshot file saved |
| 3 | **G3 canary A = MIR 579** (Tier 1, `CLOSED`): create the MR via `register_mir` with a one-MIR payload (1 line `E-BKR-100-3p` x 1, site ZMD775, Riyadh WH, dated 2026-05-06), link it to the Stock Entry carrying `DN26-0579`, stamp `DECLARED`, recompute; expect `CLOSED`, line `DISPATCHED`. **Canary B = MIR 600** (Tier 2, `PARTIAL_OPEN`): create the MR with the 5 confirmed lines at confirmed qty plus `C-MNT-3m` x 1 pending; **omit** the qty-0 `E-RM-HU-50` line (never requested); link the 5 lines to the Stock Entry carrying `DN26-0600-1`; recompute; expect `PARTIAL` with only `C-MNT-3m` dispatchable. MIR 600's pending rows are dated 2025-11-03 (likely a typo): set `transaction_date` from the 2026-05-12 dispatch. | Scoped diff (below) clean; states as expected; the dispatch dialog for 600 offers only `C-MNT-3m` |
| 4 | **DN allocator change** (section B) + tests + canary dispatches on throwaway MRs with an out-of-range `custom_mir_number` (9001: expect `DN26-9001` when the dispatch clears every line; 9002 dispatched twice: expect `-1` then `-2`); then cancel them. Deploy through the Press API. | Canary names as expected; existing dispatch / return / cancel / Kanban flows unchanged (open dialogs, no submits) |
| 5 | **Widen the SIG WhatsApp filename regex first (R3), then rename the 14 ERP-era vouchers** with the step-1 method (X suffix, `custom_legacy_dn` set). Do it after step 4 so no new plain voucher can clash with the renamed ones. | Read-back of all 14; PDFs regenerate with the new names; no duplicate `custom_source_id` |
| 6 | **G4 (about 10 mixed MIRs), then G5-G9** of the 9A.13 runbook, in risk-tier order (Tier 1, 2, 3), from the staging file. The full payload builder from WH219 is built here (with the `Riaydh` / `Al Qasim` / `Tabuk` warehouse aliases, zero-qty lines omitted), not before. | Per-gate criteria in the 9A.13 runbook |

**Scoped diff (replaces "everything identical to G0").** The site is live: real dispatches since the
2026-09-21 G0 (STE-2026-0901..0905) and the throwaway canary's permanent reversal entries make a
global diff meaningless. For each canary compare before and after: Stock Ledger Entry and GL Entry
rows for the touched items/warehouse (expect no new rows); Bin `actual_qty` for those items/warehouse
(expect no change); the linked Stock Entry's `docstatus` and `modified` (expect unchanged, since the
writer uses `update_modified=False`); and Bin `indented_qty` (recorded, not a pass criterion: it is a
request-side metric and may move when an MR is created).

#### D. Risks and mitigations
- **R1 - live dispatch path change (step 4).** Moderate. Mitigate with the throwaway-MR canary, a
  clean failure (if the new allocator raises, the dispatch fails with the existing error shape and
  never silently falls back to the global counter), and a one-commit revert.
- **R2 - renaming submitted documents (step 5).** Metadata only, no stock effect, but sent PDFs keep
  the old number. Keep `custom_legacy_dn` searchable and show it in the DN print footer for the 14.
- **R3 - SIG WhatsApp PDF filename (checked 2026-09-24, `sig_whatsapp/maytapi.py::_pdf_filename`).** The
  original filename regex truncated `DN26-1043X` and did not match `DN26-X1049`. **Fixed and deployed
  2026-09-29:** `SIG_WhatsApp` commit `271df4f` accepts plain, `-1` sequence, trailing-X, X-counter and
  X-number forms; bench build `6cop77h7hl`, site update `ehl9ef15qr`. The deployed matcher covers
  `DN26-0579`, `DN26-0600-1`, `DN26-1043X`, `DN26-X1049`, and `DN26-1035X1`. No voucher-based dedup was
  found in the visible code (the log check only tests that `Maytapi Message Log` exists); no WhatsApp
  message was sent as part of this change.
- **R4 - re-dispatch after a full dispatch (corrected 2026-09-24).** An earlier draft listed "amended MR, then
  dispatched again" as a normal case. It is not: through the UI a fully dispatched MR cannot be dispatched again
  (card menu offers only Return; the dialog stops with "No open lines"; the form Issue button shows only for
  PENDING/PARTIAL), and MR amendment only happens inside a single dispatch, on an open line, via "Amend MR if
  dispatch quantity exceeds Left". The only way an MR reopens is a privileged cancel of the Stock Entry itself
  (`on_stock_entry_cancel` recomputes the MR back to PENDING/PARTIAL). In that exceptional case the cancelled
  voucher is never reused, so the next dispatch takes the next sequence (`DN26-1053` cancelled -> `DN26-1053-2`).
  `sig_dispatch_mr` has no explicit "MR already DISPATCHED" refusal (it only checks qty against remaining, with
  the amendment escape hatch), so a direct API call could still dispatch onto a closed MR: add a server-side
  guard in step 4 that refuses a dispatch when every line is DISPATCHED/CANCELLED and amendment is not requested
  on an open line.
- **R5 - legacy history (revised).** Numbering no longer depends on 9A.13 links (voucher-pattern match, see B).
  The residual risk is the two-legacy-partials case above; the uniqueness guard keeps it collision-free.
- **R6 - regex tooling.** Any script matching `DN26-\d+` will read `DN26-1043X` as `DN26-1043`; the
  `scripts/hr` checks (G1, staging, canary) must match `DN26-\d+X?(-\d+)?` before step 5.
- **Rollback:** every writer call saves a before-image to `outputs/backup_9A13/`; the allocator
  change is one commit; renames are reversible from `custom_legacy_dn`.

#### E. Outcome assessment
Worth doing. It removes the drifting second numbering system, restores the rule the warehouse already
works to (the number on the paper is the MR number), keeps traceability without opening the MR, and
never touches the stock ledger. The costs are one moderate-risk change to live dispatch and 14
already-sent documents that keep the old number. The safe order is tooling, then G3, then the
allocator, then the rename, then the 9A.13 bulk work: the writer is shared by G3, the rename and the
backfill, and the allocator must exist before the rename so no new voucher can clash.

#### F. Parked, not in this plan
The alarm-cable (`E-ALM-4P`) decision (12 MIRs); the 70 stale and 9 superseded MIR rechecks
(workbooks already sent); the "DN(s) issued" MR field (needs the links first); portfolio-aware
availability dots.

#### E2. Status and pending postings (2026-09-25)

**Post-May MIR -> MR linking, where it stands.** Steps 0-3 of section C are done (decisions, writer deployed and
tested, G0 snapshot, both real canaries 579 and 600 closed). **Steps 4/5 are deployed and provisionally closed**
(9A.14 closeout below); **step 6 remains open** for the G4-G9 batches. Live counts on 2026-09-25 against the
491 staged MIRs (`post_may_closure_staging_20260921.json`):

| Staged action | MIRs | State |
|---|---:|---|
| CREATE_MR | 207 | 2 exist (the canaries 579, 600); **205 not yet created** |
| UPDATE_EXISTING_MR (link, add dispatched lines, close) | 184 | MR exists; **not yet linked/closed** |
| CLOSE_EXISTING_MR | 13 | MR exists; not closed |
| SIDELINED (project confirmation 67, WH decision 9) | 76 | waiting on owner/project answers |
| SKIP (duplicates) | 11 | none needed |

ERP holds 292 MRs with a MIR number >= 543 (264 Pending, 14 Cancelled, 7 Issued, 6 Partially Ordered, 1 Draft):
mostly header-level "Pending" that G4-G9 must link and close. DN-to-MIR mapping study: 318 of 337 clean
(286 exact + 32 after alias); the 14 "WH dispatched, not in ERP" cases are now explained (dropped lines, below) and 7 are ERP-era vouchers.
**Still to build before step 6:** writer operations ADD_LINE and RAISE_QTY (70 existing MRs lack their dispatched
lines, 12 need a raised quantity) and the alias-free payload builder (unit from the ERP item master, no code aliases,
fisher/screw Box-Pcs "dispatch per the DN", zero-qty Pending rows omitted, typo-date rule).

**Corrections for the dropped dispatch lines** (the 28 lines / 22 items / 11 DNs of
`outputs/wh_dropped_lines_22_items_20260924.md`; cause: the 2026-09-15 backfill skipped lines whose item master was
created about two hours later; 4 C-FNC-P-CPost lines are a different, unverified cause). One new Material Issue per DN
(one site per posting) via `scripts/hr/post_dropped_dn_lines_9a14.py` (dry run by default, `--dn N --yes`).
Restore point: Frappe Cloud backup `cqo9hu0ovp` (2026-09-25).

| DN | Site | Status |
|---|---|---|
| 541 | ZUZ042 | **Posted** STE-2026-0917 (canary, PASS) |
| 353 | FBD011 | **Posted** STE-2026-0918 |
| 402 | 431-00-000 | **Posted** STE-2026-0919 (from Muzahmiyah, the original entry's warehouse) |
| 455 | 403-00-000 | **Posted** STE-2026-0920 (from Muzahmiyah) |
| 486 | ZNJ104 | **Posted** STE-2026-0921 |
| 535 | ZYB990 | **Posted** STE-2026-0922 |
| 590 | ZRN997 | **Posted** STE-2026-0923, dated 2026-09-08 04:28:46 (shifted from WH date 2026-05-12: earlier makes the 09-08 issue STE-2026-0773 negative) |
| 616 | ZRY081 | **Posted** STE-2026-0925, 2026-06-21 04:28:31 (just after the same-day receipt) |
| 635 | FMJ08 | **Posted** STE-2026-0926, 2026-05-19 23:59 |
| 716 | ZNJ104 | **Posted** STE-2026-0927, 2026-06-21 23:59 |
| 790 | HAL0087 | **Posted** STE-2026-0928, dated 2026-08-13 04:28:37 (shifted from WH date 2026-07-17: SCO-WALL / END-POST stock only exists after the 08-13 receipts) |

**All 11 dispatch corrections are posted and verified (bin down by exactly the line quantity, one new ledger row per line, original entry unchanged).**
Dating rule used (owner OK 2026-09-25): the WH dispatch date at 23:59 when ERP accepts it, otherwise the earliest date/time at which every later balance stays non-negative
(`earliest_ok` in the script; a later Stock Reconciliation ends the check); the true WH date is always in the remarks.

Not posted by design: E-BKR-CHINT-125-1P, E-ODU-FEN-2K, C-TWR-LGHT-150M (already aligned); C-FNC-2.4M and C-FNC-2.7M
(near-misses, physical count first). Dating decision (owner, 2026-09-25): earliest date/time ERP accepts, true WH date in the remarks; no system-wide negative-stock switch.

**Closure gate (owner, 2026-09-25) - applies to every MIR in G4-G9.** An MR is closed only when **both** hold:
(1) every line is either dispatched or cancelled/dismissed (nothing pending), **and** (2) the return is clarified
for what was dispatched (`custom_return_state = DECLARED`). Nothing is closed on condition (1) alone; a partial is
never closed. In the staging file this means the 205 `CLOSED` MIRs are closable (185 dated before 9 Aug, where the
owner's default-closed decision is the return clarification; 20 on/after 9 Aug with Manage Return lines closed) and
the 80 `OPEN_AS_BUILT` MIRs (79 on/after 9 Aug) stay open until their return is declared. The writer's DECLARE
step is therefore run per MIR only after the return evidence is checked, never in bulk before it.

**Return check and correction (2026-09-25).** All 76 Confirmed WH `Return` documents (164 lines) were compared with the 77 ERP return
Material Receipts (`SIG-RN-*`, 161 lines; `outputs/return_wh_vs_erp_20260925.json`): 73 match line for line, 3 differ only by
item-name variant or key (RN26-0004 and RN26-0013 fisher on the old `-BOX` item; RN26-0076 posted as `RN26-0076-OC`, units not
compared), and **1 is short: RN26-0038 (MIR 708, site ZRW982, 2026-08-09) was posted as STE-2026-0697 with 6 of its 9 lines**
(silent line-drop, same cause as the dispatch lines: E-Lit-R-L 1, M-FSHR-12MM 0.4, M-SCRW-12 4 missing). The 12 "Confirmed IH" rows
(IH26-0001..0004) are In-Hand custody, correctly not stock receipts. Every pre-9-Aug return in the sheet is posted, so a pre-9-Aug
MIR with no `Return` row has no return.
**Posted:** one new Material Receipt **STE-2026-0924** (`SIG-RN-RN26-0038-CORR1`, 2026-08-09 23:59, site ZRW982, Muzahmiyah), on the
**current item names** (Pcs items; no `-BOX` item), valued at each Bin's current rate, via `scripts/hr/post_return_lines_rn0038_9a14.py`.
Ledger rows exist (+1, +0.4, +4). **Read-back done 2026-09-25 (after the hourly repost, 18:00):** the three
Repost Item Valuation jobs completed. M-FSHR-12MM moved 2.5 -> 2.9. **E-Lit-R-L (18) and M-SCRW-12 (48) did not move, correctly:** a Stock
Reconciliation (MAT-RECO-2026-00017, 2026-09-13 11:40) sets an absolute balance, so a receipt dated before it corrects the *history and
valuation* but cannot change today's stock; the physical count is authoritative. **Consequence for every back-dated correction:** check
each item's ledger for a later Stock Reconciliation before expecting the Bin to move; where one exists the correction is documentary
only (the count already absorbed the error). RN26-0038 is closed.

**C-FNC-2.7m reconciliation (2026-09-27), from WH's own item stock card.** The card showed 3 purchase/dispatch pairs (42 m
total). Matching each against ERP's ledger found 2 of the 3 already fully posted (07-16 purchase MAT-PRE-2026-00224 -> 07-29
issue+purchase pair, both in ERP as STE-2026-0768/MAT-PRE-2026-00228); only DN26-0790's 35m issue and the DN26-0942 pair (2m,
sourced from an internal correction, not a WH DN/RN document) were missing. This replaced the earlier "37m dispatched, ERP
short 2m" read, which wrongly summed the three pairs instead of checking each against ERP.
Posted (`scripts/hr/post_fnc27m_9a14.py`): **STE-2026-0931** (Material Issue, 35m, DN26-0790's 2nd correction, dated
2026-07-29 23:59 - the same-day DN824 pair blocks the true WH date 07-17 - true date in remarks); **STE-2026-0932**
(Material Receipt, 2m, a genuine cash market purchase confirmed by the owner - 10 SAR paid to Rauf, not the item's true
internal-recovery origin relabelled for optics, which was declined); **STE-2026-0933** (Material Issue, 2m, DN26-0942, against
the receipt). Bin: 56 -> 21 -> 23 -> 21, exactly as expected. **C-FNC-2.4m still needs the same per-pair check against its own
ledger before posting** (the flat "226 vs 220" read is likely wrong the same way).

**C-FNC-2.4m reconciliation (2026-09-27), same method.** ERP held only the two purchases (175+45=220, matching the
prior bin); neither Out row nor the CR26-0019 dismantle-correction was posted. Posted (`scripts/hr/post_fnc24m_9a14.py`):
**STE-2026-0934** (Material Issue, 45m, DN26-0535's 2nd correction, dated 2026-04-30, the WH date - no blocking prior
transaction); **STE-2026-0935** (Material Receipt, 6m, genuine cash market purchase confirmed by the owner - Rauf bought
it in the market for 10 SAR - dated 2026-05-18); **STE-2026-0936** (Material Issue, 181m, DN26-0635's 2nd correction,
dated 2026-05-19, against stock after STE-2026-0935). Bin: 220 -> 175 -> 181 -> 0, matching WH's card exactly (closing
stock 0). **Both fence items (2.4m and 2.7m) are now fully reconciled; no further C-FNC dispatch corrections outstanding.**

Learned while posting (candidates for the learning loop): (a) corrections are **not** zero-cost - ERP values the issue
at the bin's stock rate (E-LDP posted 200.00; original backfill entries also carried value); (b) originals sit at
posting time 02:05, so same-day receipts read as negative stock - post at 23:59; (c) a back-dated issue is refused
when any later transaction would go negative, so a missing back-dated issue shows up as a blocked correction;
(d) a failed submit leaves a draft - the script reuses it; (f) a back-dated entry queues a Repost Item Valuation that the scheduler runs on the hour (Bin can look unchanged for up to an hour), and a later Stock Reconciliation makes a back-dated correction change history but not today's Bin; (e) WH says Makkah for MIRs 402/455 but ERP issued them
from Muzahmiyah: post from the original entry's warehouse.

#### G. Clarity points and worked examples (added 2026-09-24 after owner review; verified against the code and live data)

**What the system actually allows (the rule the allocator must respect):**
1. A **fully dispatched MR cannot be dispatched again** through any screen: the Kanban card menu offers only
   Return, the dispatch dialog stops with "No open lines to dispatch on this request", and the form Issue
   button shows only for PENDING/PARTIAL. There is therefore no normal "amended then dispatched again" or
   "cancelled and redone" flow.
2. **MR amendment exists only inside one dispatch:** the "Amend MR if dispatch quantity exceeds Left" tickbox
   raises an *open* line's quantity in that same dispatch (reason required). It does not reopen a closed MR
   and it does not change the DN number.
3. **The only way an MR reopens is a privileged cancel of the Stock Entry** (`on_stock_entry_cancel` recomputes
   it). This is exceptional, not a working flow; the cancelled voucher is never reused.
4. **A server-side gap exists:** `sig_dispatch_mr` has no explicit "MR already fully dispatched" refusal (only
   a quantity-vs-remaining check with the amendment escape hatch), so a direct API call could dispatch onto a
   closed MR. Step 4 adds that guard.
5. **Every real MR has a MIR number.** Live check 2026-09-24: 311 Material Issue MRs; the 7 with a blank MIR
   number (all from the 2026-09-16 proving pass, 6 cancelled) and the 22 with a non-numeric one
   (`STAGE*TEST`, `HOOKTEST`, `G3-CANARY-9A13`) are test artifacts. The `DN26-X<counter>` route is a safety
   net only.
6. **Legacy partials continue the WH numbering.** If WH issued `DN26-0600-1` for a partial MIR, the next ERP
   dispatch of that MIR is `DN26-0600-2`; if WH had issued `-1` and `-2`, the next is `-3`. If the WH DN was
   plain the MIR was fully dispatched and nothing remains to dispatch.

**Worked examples (all reachable in the current system):**

| Case | MR | Dispatches | DN numbers |
|---|---|---|---|
| Issued in one go | MR-26-0579 | 1 | `DN26-0579` |
| Partial, then the rest | MR-26-1050 | 2 | `DN26-1050-1`, then `DN26-1050-2` |
| Three dispatches | MR-26-1051 | 3 | `DN26-1051-1`, `-2`, `-3` |
| Partial, remainder later cancelled ("Cancel remaining") | MR-26-1052 | 1 | `DN26-1052-1` (a submitted Stock Entry cannot be renamed afterwards; matches the 141 legacy MIRs that only ever had a `-1`) |
| Over-quantity on an open line in the same dispatch (line 10, dispatch 12, amend ticked) | MR-26-1054 | 1 | `DN26-1054` (the amendment does not change the number) |
| Legacy WH partial, remainder dispatched in ERP | MR-26-0600 | WH: `DN26-0600-1` | ERP dispatch: `DN26-0600-2` |
| Legacy WH double partial (`-1`, `-2`), remainder in ERP | (about 13 MIRs) | WH: `-1`, `-2` | ERP dispatch: `-3` (needs the WH-data correction in section B) |
| The 14 ERP-era vouchers after the rename | MR-26-1042 | 1 | `DN26-1043` becomes `DN26-1043X` (original in `custom_legacy_dn`); the MR's own next DN is then a free `DN26-1042` / `-2` |
| *Exceptional:* Stock Entry cancelled by a privileged user, MR reopens | MR-26-1053 | 2 | `DN26-1053` (cancelled), then `DN26-1053-2` |

**Errors in earlier drafts, corrected (recorded so they are not reintroduced):** an example of "fully
dispatched, amended, then dispatched again" and an example of "MR with no MIR number" were listed as normal
cases; neither is normal behaviour of this system.

**9A.14 step 1 - executed and PASSED (2026-09-24).** Backups first: Frappe Cloud site backup `8v7jqkvvvg`
(24 Sep 13:33), app git tag `pre-9a14-writer` (pushed), data snapshot
`outputs/backup_9A13/g0_baseline_20260924_1104.json`. Then, field-first: `Stock Entry.custom_legacy_dn` created live
(`scripts/hr/create_custom_legacy_dn_field_9a14.py`, read-back verified). Then the writer
`SIG_Warehouse/sig_warehouse/sig_warehouse/retro_ops.py` (`sig_retro_apply`: LINK, DECLARE, DISMISS, RENAME_DN,
RECOMPUTE; dry run by default; before-image; idempotent; only MRs marked retrospective/test; DISMISS takes waiver
reasons only; RENAME_DN limited to DN26-1035..1048 plus reserved test numbers 9901/9902), commits `d03b8d3` and
`9cc7ed6`, 7 pure-logic unit tests. **Live test `scripts/hr/test_retro_ops_9a14.py`: 29 of 29 checks pass** on a
throwaway MR (MIR 9901) and an unlinked throwaway Stock Entry: refusals (wrong MIR, item mismatch, over-quantity,
disallowed reason, rename without X, declare before link), dry run writes nothing, LINK (line issued, MR PARTIAL,
Stock Entry `modified` unchanged, idempotent), DISMISS (line CANCELLED / WH_CLOSED, MR DISPATCHED not closed),
DECLARE (Stock Entry DECLARED, MR CLOSED, idempotent), RENAME_DN (X form, original kept, second rename refused), stock
back to baseline; throwaway MR/SE cancelled (not deletable: audit links). One bug found by the first live run and
fixed in `9cc7ed6`: `_fail(..., reason=...)` keyword clash crashed the disallowed-reason refusal (nothing was ever
written).
**Deploy lessons (record for the next release):** (1) a green "build Success" is the bench build only; the site must
also be moved onto it (`press.api.site.update`), and that option can appear several minutes after the build - poll
`press.api.site.check_for_updates` until `update_available` is true, and refuse to trigger it if any other app is pending
(`scripts/hr/trigger_site_update_when_ready.py`). (2) The site reports `Active` immediately after `site.update`; confirm
by behavior, not status (a 2-minute stable `Active` + nothing pending, then the live test). (3) Another workstream also
commits to `SIG_Warehouse` (`e1e03be`, field-session force-post): stage only your own files. (4) Test vouchers are never
reusable (even from a cancelled entry): the test takes fresh suffixes per run (`RETRO_TEST_SUFFIX`).
Next: step 2 fresh G0, step 3 G3 canaries (MIR 579 and 600).

**9A.14 step 3 - G3 canaries on real MIRs, executed 2026-09-24 (`scripts/hr/g3_real_canary_9a14.py`).**
*Canary A, MIR 579 (clean closed case): PASSED, 15/15.* Created `MR-26-0579` through `register_mir` (one line
`E-BKR-100-3p` x 1, dispatch 2026-05-06), linked it to `STE-2026-0350` (`SIG-DN-DN26-0579`), declared, MR `CLOSED`.
*Canary B, MIR 600 (real partial): PASSED, 18/18.* Created `MR-26-0600` with 6 lines (5 dispatched at confirmed qty
plus `C-MNT-3m` x 1 pending; the qty-0 `E-RM-HU-50` row omitted; pending row's 2025-11-03 date replaced by the
2026-05-12 dispatch date), linked the 5 lines to `STE-2026-0371` (`SIG-DN-DN26-0600`); MR `PARTIAL`, only `C-MNT-3m`
dispatchable. Scoped diff clean for both: Stock Ledger Entry rows, GL rows of the DN Stock Entry, Bin `actual_qty`,
Stock Entry `docstatus` and `modified` unchanged.
**Findings from the canaries (all fixed in `retro_ops`, all now covered by the live test, 33+ checks):**
1. *WH text is not the source of truth for warehouse/unit.* MIR 579 is **Al Qasim** (Capex9) and 600 is Jizan (the
   plan had guessed Riyadh); `register_mir`'s `WH_MAP` has no `Al Qasim`, so the payload sends `Qasim`. **MR line
   units come from the ERP item master (`stock_uom`), never from the WH sheet** ("Pcs.", "Strings"); the run stops if
   an item's ERP unit is not one `register_mir` accepts.
2. *Backfilled Stock Entry lines use other unit names.* 3,294 lines say `Nos` and 1,072 `Meter`, all at conversion
   factor 1, while MR lines use `Pcs` / `String` / `Mtr`. `LINK` now accepts a mismatch only when both names are in one
   group (`Nos/Pcs/Unit/Each/String(s)`, `Meter/Mtr/m`) and the factor is exactly 1; anything else (`Box` vs `Pcs`) is
   still refused (`a9244fc`).
3. *Linking bypassed ERPNext's own quantity bookkeeping.* ERPNext computes `Bin.indented_qty` for open Material Issue
   MRs as the sum of `stock_qty - ordered_qty`, subtracted, and refreshes `Material Request Item.ordered_qty` (sum of
   linked, submitted `Stock Entry Detail.transfer_qty`) only on Stock Entry submit. After a retro link the issued
   quantity stayed counted as outstanding demand (MIR 579: `indented_qty` -1 -> -2, no recovery), which would have
   understated Projected Qty for about 190 MRs. `LINK` and `RECOMPUTE` now call ERPNext's own
   `update_completed_qty()` / `update_requested_qty()` (`a196e47`); `MR-26-0579` was repaired with `RECOMPUTE`
   (`indented_qty` -2 -> -1, `ordered_qty` 1, `per_ordered` 100). Known remaining limit: a *dismissed / cancelled*
   remainder still counts in `indented_qty` (as with the live "Cancel remaining" action).
4. *ERPNext `status` stayed "Pending".* `set_status()` evaluates the in-memory document, which still held the old
   `per_ordered`; native MRs read `Issued` / `Partially Ordered`. Reload before `set_status` (`073e6c9`); the live test
   now asserts `Partially Ordered`; `MR-26-0579` (Issued) and `MR-26-0600` (Partially Ordered) to be repaired with
   `RECOMPUTE` once that release is live.
**Canary pass criteria now (replaces "identical to G0"):** scoped ledger/GL/Bin-actual/Stock-Entry unchanged **and**
`indented_qty` back to baseline for dispatched items (lower only by real pending qty) **and** ERPNext `status` follows
`per_ordered`.

**9A.14 step 3 / G3 - CLOSED (2026-09-24).** After the `073e6c9` release went live (site update `544uo2rc6b`, six
stable polls) the writer's live test passed **34/34** (adds: creating an MR lowers `Bin.indented_qty`; `LINK`
restores it for the issued line and keeps demand for the open one; `ordered_qty` set; ERPNext status follows
`per_ordered`). `RECOMPUTE` then repaired the two real canary MRs: `MR-26-0579` -> `Issued`, `per_ordered` 100,
stage `CLOSED`, `indented_qty` back to its baseline -1; `MR-26-0600` -> `Partially Ordered`, `per_ordered` 93.3,
stage `PARTIAL`, `indented_qty` lower only by the pending `C-MNT-3m` unit. Writer releases: `d03b8d3`, `9cc7ed6`,
`a9244fc`, `a196e47`, `073e6c9`. Steps 4/5 (DN allocator, WhatsApp filename regex, 15-record X rename) were
deployed 2026-09-29 and are provisionally closed; the first real partial dispatch remains the live outcome check.
Next is G4-G9 using the now-proven per-MIR procedure (`g3_real_canary_9a14.py` is the template for the batch
runner; the batch must reuse its pre-checks: WH vs Stock Entry line-for-line match, unit from the ERP item master,
warehouse alias, zero-qty rows omitted, typo-date rule, scoped diff and the `indented_qty` / status checks).

**Fix status check - 2026-09-24 (live, after release `073e6c9`; every line verified against the running system, not notes).**

| Fix | Where it stands | Evidence |
|---|---|---|
| Dispatch Queue board (toolbar button, lag, stale search, double registration) | **Closed, live** | `f68da12` deployed; on the current release: 278 cards, availability dots 269, search box and tool button present, `window.sig_wh` exports both functions, no console errors; canary MRs sit in the right columns (PARTIAL 4->5, CLOSED 2->3, PENDING 264 unchanged) |
| Cancelled partial never closes (`rollup.py`) | **Closed, live** | `rollup.py` untouched since `f68da12`; proven on the throwaway MR (PARTIAL) and by the real canaries; `custom_cancel_reason` field live (options incl. `WH_CLOSED`) |
| HR Number Cards (relative dates) | **Closed, live** | 4 cards on `dynamic_filters_json`; rendered 64/0/0/64 = independent database counts; deploy script updated |
| Retro metadata writer (`retro_ops`) | **Closed, live** | releases `d03b8d3` .. `073e6c9`; live regression test 34/34; `custom_legacy_dn` field live |
| G3 canaries (MIR 579, 600) | **Closed** | 15/15 and 18/18; both MRs repaired (`Issued` / `Partially Ordered`); scoped ledger/GL/Bin/Stock Entry diff clean |
| Throwaway test artifacts | **Clean** | 9 test MRs and 8 test Stock Entries, all cancelled (docstatus 2); stock at baseline |
| Learning loop | **Updated** | rules 272-285 in `erpnext_learning_loop.md`; Loop 07 and 7 failure-table rows in this plan |

**9A.14 steps 4/5 - deployed 2026-09-29.** `SIG_Warehouse` commit `0bc489b` added the MR-number allocator;
follow-up commit `15c0510` preserves suffixes recorded in the WH219 history where ERP has only the base voucher.
The allocator uses the MIR number, counts existing/cancelled ERP dispatches, applies the legacy suffix floor,
then issues `-1`, `-2`, `-3`, etc.; it refuses dispatch on a fully dispatched MR. Bench builds `583hg5195e`
and `7mt430e7c8`; final site update `1so0mak3jb` applied Warehouse hash
`15c0510521b2c02dddcb2a977b95b992cd15bcf7`. `SIG_WhatsApp` commit `271df4f` widens the PDF filename
matcher; live Warehouse and WhatsApp hashes match their bench builds, and Press reports no pending updates.
The WH219 history established suffix floors for 18 still-open MIRs: floor 2 for 545, 566, 568, 571, 572,
614, 615, 646, 704, 710, 780, 808, 830, 922, 969; floor 3 for 612, 686, 923. The live
`sig_retro_apply` dry run accepted all 15 rename records; apply/read-back confirmed 15 unique source IDs,
with every original saved in `custom_legacy_dn` and no plain `DN26-1035`..`DN26-1048` remaining. Fourteen
distinct original values were renamed; two linked entries shared `DN26-1035`, so the submitted entry is
`DN26-1035X` and its cancelled duplicate is `DN26-1035X1`. After the final update, the authenticated Desk
loaded the SIG Warehouse workspace at `/app/warehouse-workspace`. The throwaway 9001/9002 allocator canaries
were not run, so sequence issuance on a real partial dispatch is still unverified; the first real dispatch
remains the live behavioral check.

**Still open:** 9A.13 G4-G9 batch (template: `g3_real_canary_9a14.py`); parked: `E-ALM-4P` decision (12 MIRs),
70 stale + 9 superseded MIR rechecks, "DN(s) issued" MR field. **Housekeeping:** the plan, learning loop and new scripts are edited/staged in the parent repo but not committed;
`SIG_Warehouse` also holds another workstream's uncommitted edits (`field_feed.py`, `field_sessions.py`,
`site_visits.py`) that must not be swept into a commit.

**9A.14 mapping study - is the WH DN -> ERP Stock Entry -> MR line mapping correct? (2026-09-24, read-only;
`scripts/hr/study_dn_mr_mapping_9a14.py`, results `outputs/post_may_dn_mapping_study_20260924.json` and
`..._final_20260924.json`, alias table `outputs/post_may_item_alias_map_20260924.json`).**
Scope: all 339 post-May MIRs with a WH-confirmed DN, against 465 ERP Material Issue Stock Entries (2,434 lines) and 128
already-imported MRs, plus the 85 links ERP itself created for native dispatches.
**Result: 318 of 339 (94%) map line-for-line** (286 exact; 32 exact once item aliases are resolved). The rest: 14 MIRs
(22 lines) WH dispatched but ERP has no such movement; 7 ERP-era/missing-voucher MIRs to map by operation. Rules the data
supports, and the ones it does not:
1. **DN number = MIR number holds for every post-May MIR** (0 exceptions across 339; the 11 earlier `DN != MIR` lines were all pre-543). Voucher = base number `DN26-NNNN`; ERP stores **no** suffixed vouchers (`-1`/`-2` never appear in ERP).
2. **Suffixed WH groups merge under the base voucher**: of 32 MIRs with 2+ groups, 29 are one ERP Stock Entry equal to the sum of the groups; MIR 616 has only group 1 in ERP (group 2 = `C-MNT-WM-3m` never reached ERP); 924 and 969 differ (an item missing).
3. **Item codes differ between WH and ERP for 34 MIRs (50 instances, 7 pairs).** Pure code aliases (same item and unit): `EC-NOK-IND`->`E-EC-NOK-IND` (11), `E-Alm-8p`->`E-ALM-8P`, `C-FNC-P-CPOST`->`C-FNC-P-CPost`. **Pcs -> Box "auto-repack" pairs (different ERP items):** `M-FSHR-12MM/14MM/6MM` and `M-SCRW-6` -> their `-BOX` twins (WH and the Stock Entry agree numerically, e.g. 0.2 box; the MR lines imported earlier are in pieces). This also explains most of the earlier "22 MIRs with unmatched items". **Rule: build/target the MR line with the Stock Entry's own item code; never link an MR line of one item to a Stock Entry line of the other.** The writer's `ITEM_MISMATCH` refusal is therefore correct and must stay; alias handling belongs in the payload builder.
4. **WH-dispatched but absent in ERP (14 MIRs, 22 lines):** `C-MNT-TB-1.5m` (590), `C-MNT-WM-3m` (616), fencing set (635: `C-FNC-2.4m` 181 m + posts + wire; 790: `C-FNC-2.7m` 35 m + posts + gate post + wall bracket; 942), `C-TP-PRIMR-17L`/`C-STL-BRSH-TP` (716), `E-BKR-CHINT-125-1p` (781, 791, 947, 969, 977, 1021), `E-ODU-FEN-2k` (924), `E-CLUG-25` (948). These dispatches never entered ERP stock. They are **not linkable**; owner decision needed per line (record as `WH_CLOSED`-style dismissal with a note, or post the missing Stock Entry).
5. **Existing MRs are pending-only imports: 70 of the 128 existing MRs lack the dispatched items (423 Stock Entry lines).** Only 47 are clean. "Link and recompute" is therefore not enough for those: the dispatched lines must first be **added to the MR** (a writer `ADD_LINE` operation, or reuse `sig_add_mr_line`), at the Stock Entry's item code and quantity. In 12 MIRs a dispatched quantity exceeds the MR line (raise the line: 646, 655, 703, 704, 714, ...); 8+ have unit issues (`Nos` vs `Packet` etc., outside the equivalence groups). New writer operations needed: `ADD_LINE`, `RAISE_QTY` (owner-approved amendment semantics), plus the alias-aware payload builder.
6. **ERP-era vouchers (>=1035) cannot be mapped by number.** In ERP `DN26-1037` is MIR 1007's dispatch (site MW300), `DN26-1038` is MIR 1037's, and so on (site labels differ for 1037 and 1038); 1005/1006/1007 dispatched in ERP under `DN26-1036..1041`. Map these through `SIG Dispatch Operation.mr`, and treat the number clash as the reason for the `X` rename (confirms step 5 of 9A.14).
7. **Warehouse:** every WH-confirmed MIR agrees with the ERP source warehouse (two only differed by the spelling `jizan`). **Site:** agrees except the ERP-era 1037/1038. **Date:** 6 MIRs fall on the other side of 2026-08-09 (877, 879, 880, 881, 884: WH 2026-08-04, ERP posted 2026-08-16; 780: WH 2026-08-26, ERP posting 2026-07-13). Rule stays "WH `Out` date is the dispatch date", **780 to be confirmed by the owner** (ERP says July, WH says late August).
8. **Native check:** all 85 links ERP created itself for native dispatches join an SE line to an MR line with the *same item* and never above the MR line quantity - the rule the writer enforces.
**Effect on the plan:** the 22 "unmatched-line" Tier-3 MIRs are mostly alias cases (resolvable), 14 are real gaps; the number of existing MRs that need lines added (70) is the largest piece of G4-G9 work; canaries 579 and 600 remain valid (both exact).

**9A.14 mapping study - owner review and resolution (2026-09-24). Supersedes rules 3-6 of the study above; the alias table
(`post_may_item_alias_map_20260924.json`) is withdrawn.** Script v2: `scripts/hr/study_dn_mapping_v2_9a14.py`, result
`outputs/post_may_dn_mapping_v2_20260924.json`.
1. **Item identity: no alias table.** A WH item resolves to an ERP item by code (case-insensitive - ERP treats
   `E-Alm-8p`/`E-ALM-8P`, `C-FNC-P-CPOST`/`C-FNC-P-CPost`, `E-BKR-CHINT-125-1p`/`-1P`, `E-ODU-FEN-2k`/`-2K` as one record), else by a
   **unique item description** (`EC-NOK-IND` = "Cabinet Indoor Nokia (Fiber Ocean)" = `E-EC-NOK-IND`, the identity the Jan-Feb
   remediation ledger and `post_g4_transfers.mjs` already used). Of the 190 WH codes used after May: 184 exact, 4 case-only,
   1 by description, 1 unresolved (`G-CAD-WELD`, "Cadweld Connection", not in ERP). **Fisher / screw Box<->Pcs family
   (`M-FSHR-6/10/12/14MM`, `M-SCRW-6`):** the original code was moved from Box to Pcs today by
   `scripts/cutover_fisher_10_12_14_to_pcs.py` (Repack Entry, then a rename: the original code is now the Pcs item and the old
   Box item became `<code>-BOX`, dragging every historical dispatch line with it). Owner rule: **dispatch per the DN, no unit
   conversion (cost is taken at posting, so values are identical), and no pending rows for these items** - a new MIR under the
   new policy if anyone needs them. In the builder: MR line = the Stock Entry's own item code and quantity; pending lines of the
   family are dropped/dismissed (`SMALL_VALUE_WAIVED` class already covers `M-FSHR`/`M-SCRW`).
   **v2 result (337 non-ERA MIRs): 290 exact + 28 repack-only = 318 map cleanly (94%); 14 genuine gaps; 5 without a Stock Entry.**
2. **Existing MRs missing dispatched lines (70 of 128 imported MRs; 423 Stock Entry lines): this is part of the process.** The
   imported MRs held only the lines that were pending at import; closing every post-May MIR means adding the dispatched lines
   at the DN's quantity, linking, and closing per the rules. Needs the writer operations `ADD_LINE` (and `RAISE_QTY` for the 12
   MIRs where the dispatched quantity exceeds the MR line), each with dry run, before-image and a canary on two of the 70.
3. **The 14 gap MIRs (22 lines): WH really dispatched them (21 of 22 have a `Success` row in the WH `logs`; MIR 948 has only a
   journal `SUCCESS`); ERP lost them at import.** The backfill built each Stock Entry from log rows (`remarks: "WH backfill DN | 8
   log rows"`, yet 3 lines) and dropped lines whose item did not resolve at posting time: 10 of the 14 items were **created at
   04:09 on 2026-09-15, two hours after the DN Stock Entries (02:05-02:07)**; 3 were case variants the first resolver missed;
   MIR 948's `E-CLUG-25` has no log row (WH logging gap). Whether to post the lines depends on stock, not on the MR
   (learning-loop rule 9A.12: post only what differs from the WH sheet): (a) **already aligned, do not post** (ERP bin = WH
   sheet now): `E-BKR-CHINT-125-1p` (MIRs 781, 791, 947, 969, 977, 1021; 10 units), `E-ODU-FEN-2k` (924), `E-CLUG-25` (948),
   plus 910 (`E-DCDP-R`, bin 6 = 6), 985 (all seven items reconcile once ERP-native dispatches after the WH219 snapshot are
   counted: e.g. MR-26-1042's `DN26-1043` = 2/24/4/4/4), and 1006's extra 4 `E-PIN-LUG-50MM` (bin 155 = 155); (b) **ERP still
   holds exactly the dispatched quantity, WH sheet shows 0** (post-safe candidates, owner to confirm): `C-FNC-GATE-POST` 2 and
   `C-STL-SCO-WALL-10MM` 2 (790), `C-MNT-TB-1.5m` 1 (590), `C-MNT-WM-3m` 1 (616), `C-STL-BRSH-TP` 2 and `C-TP-PRIMR-17L` 3 (716);
   (c) **partly explained, physical confirmation needed** (the 9A.12 "88 differences" list; the fence family is absent from the
   WH stock sheet): `C-FNC-2.4m` (635: 181 dispatched, ERP holds 220), `C-FNC-2.7m` (790+942: 37 vs 35), `C-FNC-END-POST`
   (9 vs 8), `C-FNC-P-CPost` (13 vs 6), `C-TIGHT-WIRE` (3 vs 2). Line-level record on the MR: a new waiver reason for a
   historical dispatch with no ERP movement (`rollup.py` + field option), no stock document.
4. **ERP-era MIRs (>=1035 and the offset 1005-1007): mapped one by one through `SIG Dispatch Operation.mr`; 1005, 1007, 1037,
   1038 match item-for-item and quantity-for-quantity** (WH `DN26-1037` is ERP `DN26-1038`, and so on - the voucher clash the `X`
   rename removes). MIR 1006 matches except `E-PIN-LUG-50MM` (WH 8, ERP 4; stock aligned, see 3a). MIR 910 and 985 have no ERP
   Stock Entry but stock is aligned (3a). **Mapping rule confirmed: by voucher number for MIRs < 1035 (0 exceptions), by
   dispatch operation for MIRs >= 1035.**

**9A.14 - the 14 gap MIRs studied properly (2026-09-24; `scripts/hr/study_log_vs_erp_dn_9a14.py`, `outputs/wh_log_vs_erp_dn_study_20260924.json`).**
Question: were these DNs in the WH logs but never reflected in ERP, perhaps during the WH -> ERP deployment phase? Method: every
successful WH `logs` DN row of 2026 (2,761 rows, 522 DN vouchers, 2026-03-03 .. 2026-09-14 16:17) against the ERP Stock
Entry lines of the same voucher.
* **2,684 of 2,749 (DN voucher, item) pairs match (97.6%).** 65 do not, in two very different groups.
* **Group 1 - the deployment window (real): whole DNs missing, 4 DNs / 21 lines: DN26-0985, 1005, 1006, 1007, all logged on
  2026-09-14 between 13:13 and 16:17.** The backfill's last DN was logged 2026-09-13 13:01 (posted 2026-09-15 02:05-02:07);
  the ERP cutovers became ACTIVE on 2026-09-16 (Jizan 02:08, the other three 08:15-08:16). Dispatches made in WH in that gap
  reached neither the backfill nor native ERP dispatch. 1005, 1006, 1007 (and 1037, 1038, also 14 Sep) were replicated later by
  the 9A.12 correction; **985 (7 lines) never was.**
* **Group 2 - not a window: 44 line-level drops inside DNs that DO exist in ERP, spread evenly over March-September and over
  pre-May (19) and post-May (25) MIRs.** 4 of the 44 are artefacts of the voucher clash (WH `DN26-1037/1038` are MIRs 1037/1038;
  ERP's `DN26-1037/1038` are other MIRs' dispatches), leaving **40 real lines in 20 DNs**: 28 items created after the backfill
  posting, 11 case variants the first resolver missed (`C-FNC-P-CPOST` 4, `E-BKR-CHINT-125-1P` 6, `E-ODU-FEN-2K` 1), 1 item still
  absent from ERP (`C-TWR-LGHT-150M`, DN26-0352). The builder silently dropped every line whose item did not resolve; the
  Stock Entry remark ("N log rows") shows the shortfall.
* **MIR 910 is not a gap:** its WH log type is `DNIH` (dispatch into a custodian's In-Hand ledger, `reduced = 0`), so no
  Material Issue is expected; it belongs to the custody ledger.
* **Proof the drops explain the stock differences:** for each affected item, ERP minus WH-sheet quantity vs the total quantity of
  dropped dispatches over ALL DNs: **22 of 27 items match exactly** (e.g. `C-FNC-P-CPOST` 13 = 4+3+4+2; `C-FNC-20M` 74;
  `EM-AC-RBR-INS-1/2` 24; `C-PNT-ROLR-S` 20). Of the other five, three are already aligned (`E-BKR-CHINT-125-1P`, `E-ODU-FEN-2K`,
  `C-TWR-LGHT-150M`: ERP = WH, so posting would double-deduct) and two are near misses (`C-FNC-2.4M` 220 vs 226, `C-FNC-2.7M` 35
  vs 37). **These drops are the main cause of the open 9A.12 list of 88 ERP-vs-WH differences.**
* **Proposed resolution (needs owner OK, stock-affecting):** for the 22 exactly-explained items post the dropped lines as
  correction Stock Entries (one per original DN, tagged `WH backfill correction`, linked to the MR line, dated with care
  because of the backdated-posting repost cost, learning-loop 263); do **not** post the three aligned items, and treat the two
  near-miss fence items by physical count. For MIR 985 (Sep-14 window) the stock is already aligned (ERP-native dispatches after
  the WH219 snapshot explain the residuals), so it is recorded on the MR as dispatched-with-no-movement.

#### H. Pending entanglements (standing process, from 2026-09-27)

**Standard going forward:** the G4-G9 bulk closure does not stop for a MIR whose facts do not cleanly fit the rule.
Anything ambiguous (a real quantity gap, a return shared across MIRs, a unit conflict, an orphaned test artifact) is
flagged here with what was decided, and the bulk proceeds. This section is the running TODO for anyone re-checking
later; it is not a blocker list.

- **MIR 939 (E-DC-CAB-35): resolved, no action.** Requested 6m, dispatched 3m. Per the standing rule ("whatever was
  dispatched closes the item"), 3m is final; the 3m delta stays dismissed. No further posting.
- **MIRs 710 and 708 (site ZRW982, 2026-08-09): return-overspill flag, accepted as-is.** Both point to the same
  return, RN26-0038, which is fully and correctly posted in ERP (all 9 lines match WH's own card, see the
  2026-09-25/27 return reconciliation above). The flag exists only because the staging script cannot cleanly split
  one return document's attribution between two MIRs dispatched from the same site the same day, not because
  anything is missing from ERP. **Decision (owner, 2026-09-27): declare the return DECLARED for both MIRs against
  the one posted RN26-0038, do not attempt to re-split it.** Flagged here as a possible bookkeeping ambiguity
  (two MIRs crediting one return) for a later look, not a stock error.
- **STE-2026-0883 / STE-2026-0885 (Stage 4 proof-dispatch test artifacts, 0.01m E-ALM-4P each, 2026-09-16):
  cleaned up 2026-09-27.** Could not cancel either (0883: its linked MR is already cancelled, which blocks a Stock
  Entry cancel; 0885: same). Posted a reversing Material Receipt for each instead (STE-2026-0937, STE-2026-0938),
  matching how STE-2026-0884 (already cancelled at the time) was handled with its own reversal, STE-2026-0887. Net
  stock impact of all three Stage 4 proof runs is now zero, as intended.
- **38 flagged CLOSED MIRs and the general "review" list from 2026-09-25/27:** owner declined to review now
  ("too unclear, ignore; if a future dispatch needs a MIR we will raise a new one"). Left untouched.

#### I. Marker-gate extension deployed (2026-09-27)

`retro_ops.py` now accepts an MR via a second path: an explicit, git-reviewable allow-list
(`approved_closure_mirs_9a14.json`, the 205 MIRs the 2026-09-21 staging run classified CLOSED) - not a
loosened marker check; anything off the list is still refused exactly as before. Added `BACKFILL_SITE`
(fills a *blank* `custom_site`, never overwrites one already set). 6 new pure-logic tests, 15/15 pass.
Committed `bf80d25` (own files only - `hooks.py`/`field_feed.py`/`field_sessions.py`/`site_visits.py`/
`tag_feed.py` in this shared tree belong to another workstream and were left untouched, per rule 275),
pushed, deployed (bench build `a5aennpkb9`), site updated (`site.update` job `8bta05u2s1`).
**Two lessons from this deploy:** (a) `bench.deploy` queued against the git HEAD *before* the push landed
on GitHub - Press deploys from the remote, so push first, then deploy, and re-check the selected hash;
(b) `site.update` moves the site to whatever the *next_hash* is **at the moment it is called**, so a
second bench build that finishes after the first `site.update` fires needs its **own** `site.update` call
- `check_for_updates`/`site.get` reporting Active is not proof the second release is live (extends rule
273); the real proof was a behavioural probe (RECOMPUTE against a native MR, MR-2026-0050/MIR 595: refused
with the old `MR_NOT_MARKED_RETROSPECTIVE` reason until the second `site.update`, then accepted).
**Verified live:** MR-2026-0050 (MIR 595, native) now passes `_load_mr`. **STE-2026-0257 / DN26-0374's
missing site fixed** via `BACKFILL_SITE` (`custom_site` -> ZRH824, verified by read-back). Both real cases
resolved; ready to start LINK+DECLARE+RECOMPUTE on the clean subset of the 56 native CLOSED MIRs.


## 9B. Historical Tawal invoice-to-Site/Cycle linking — **closed (2026-09-29)**

Historical invoice associations from the `SIG Tawal Invoicing.xlsm` `INVOICE DETAILS` source, beginning at row 375 (`INV_SIG__0243`), have been linked retrospectively. Each accepted association has a `SIG Site` and a `SIG Site Cycle` identified by Site ID + WO; all 1,665 target cycles are in terminal **5 - Closed** stage. The cycles are linked to their Site pages, and the invoices link directly to both Sites and Cycles in the read-only `Tawal Site & Cycle Links` child table.

The live Sales Invoice **Connections** tab also now has a **Site → SIG Site** group. Its dashboard link resolves the multi-site child table (`custom_tawal_site_cycle_links.site`), so invoices with several site associations are represented without relying on the single-valued `custom_site` field. The change is deployed in `SIG_Warehouse` commit `cc729ff8465b` (Frappe Cloud build `8t141u5sue`, Success) and was visually verified on `SIG-SINV-25-076`.

**Completion and boundaries:** 1,435 target Site IDs were verified; 1,665 closed Site/WO cycles, invoice-link records, and direct invoice child rows were verified across 224 submitted Sales Invoices. Four invoice IDs (19 source rows) remain held for identity review, and one duplicate source row was collapsed; these are excluded from the completed links. No invoice amounts, tax, accounting status, or open ToDos were changed or created. The detailed decision, row-level manifests, and verification are recorded in `../outputs/tawal_invoice_site_cycle_backfill_decision_20260928.md`, `../outputs/tawal_invoice_site_cycle_create_close_link_stage_20260928.csv`, and `../outputs/tawal_invoice_site_cycle_verification_20260928.json`.


## Operations cycles: evidence progression revision (2026-10-19)

Source implemented in `SIG_Warehouse_fix_cycle_ops`, branch `codex/operations-cycle-evidence-v2`, PR #32 merged as commit `1b47c16ce191c14a5f5f1dded51917f6e9004f32`. Frappe Cloud bench build `cgtaiv8s7f` succeeded; production site update completed successfully on 2026-10-19 at 18:54 Riyadh time. The live site reports SIG Warehouse `1b47c16` and Active status.

The approved automatic Handover trigger is TCN + MIR + Visit + Tags, or TCN + MIR + two accepted visits on the same cycle. Existing recorded downstream evidence and saved PM progression remain valid; no historical cycles are demoted, closed or stripped of comments. Photos are removed from pending tasks while recorded photo history remains available. Site headings display `Site - amount SAR`, with the WO beneath and no amount text when the value is absent.

A shared source rule now aligns the dashboard, Project Progress and evidence intake. It also repairs the daily job's obsolete As-Built checkpoint, keeps partial legacy Plan work actionable without requiring old Mapping evidence, and appends numeric value and visit count to cycle exports. Pre-release read: 532 open cycles, 347 visits, visit counters match actual visits. Preview: 36 forward moves, no demotions or closures. Tests: 48 PASS, JS syntax PASS, exact live-script rewrite is idempotent and compiles with RestrictedPython 8.0. Production in-place migration completed with failing patches not skipped. The live Workbench route was checked under Cloud Login As impersonation for coordinator m.waled@sigtele.com; it rendered the new stage labels, inline site value and task list without Photos tasks. Fresh direct coordinator/PM login, Arabic browser acceptance and repeatable migration on a separate staging site remain NOT TESTED. Permission baseline snapshots before and after are in `ERPNext/backups/permission_release_ops_cycle_evidence_20261019/`; the snapshot diff reported zero additions/removals, and raw Custom DocPerm (590 rows) and User Permission (121 rows) matched exactly. No permission or assignment changes are proposed. Release plan: `SIG_Warehouse_fix_cycle_ops/docs/operations_cycle_evidence_v2.md`; backups and row preview: `backups/operations_cycle_rules_20261019/`.

**Follow-up task projection correction — 2026-10-19 (staged, not deployed):** the live cycle page showed As-Built BOQ file under Handover and retained Handover/As-Built Operational work after HO documents. Stage work is projected by current cycle stage: Plan items only in Plan, Tags and applicable As-Built Operational only in Handover, As-Built BOQ file only in Invoicing. Invoicing suppresses all Handover tasks and the separate open/closed As-Built Operational display; Warehouse records remain unchanged. The items are virtual projections, not native ToDos, so deployment automatically removes the stale rows without modifying cycle evidence or writing closure events. Regression coverage passes; production deployment and post-deploy route verification are pending.

**Current deployment reconciliation — 2026-10-19, 22:27–22:35 Asia/Riyadh:** the staging description above is historical. Cloud now shows installed SIG Warehouse `2175bd7`, site Active and no pending update. The task suppression and Handover reconciliation are deployed; current read-back is 532 open cycles and 1,168 work items. The [structural review](operations_petty_cash_structural_review_20261019.md) finds remaining gaps beyond those fixes: 269 Initial cycles carry 807 TCN/MIR/Visit items, four Handover cycles have no next action, and Project/BA/staffing sources can disagree. PC Employee scope, native draft-JE confirmation and hourly review-group ToDos are also live; client invoicing is separate. Fresh actual-user acceptance remains NOT TESTED. This read-only review changed no production data or access.


## 10. Staged: planner Must mark and critical-site timing (2026-10-25)

- **Must mark (live):** Planner Mark on SIG Site Cycle offers Hold, Visited and Must. Must puts the cycle first in the weekly plan. It does not change timing. Anyone with SIG Site Cycle write (SIG Field Ops, Projects User, System Manager) can set it. Projects Manager has no cycle read, so cannot set it either.
- **Critical-site timing (staged, not built):** RV80 forces critical sites to 8 hours from midnight, and critical Incident sites to 06:00-18:00 on the planned date. ERP needs a read-only `timing_rule` on SIG Site, fed by the one-way SitesDB import, and the planner must book a fixed team-day for such sites. Full rule and steps: MASTER-ERP-INTEGRATION.md, "Critical sites: timing rule from RV80".
- **Gate before building:** confirm with the owner whether SitesDB's `critical` column holds the site code itself or an alias. Permissions: a new read-only Select field on SIG Site falls under the deployment permission guide (declared grant: none; field visibility only).


## Current reality — weekly field planner — 2026-10-25

Supersedes the planner statements earlier in this document where they differ. Source: ERP app `SIG_Warehouse`, branch `main`, releases through `317caf5`. Live checks on 2026-10-25 were read-only API reads plus one Administrator session.

**Live in ERP**
- **Page `/app/field-planner`** (SIG Operations; Field Ops, Projects User, Projects Manager, System Manager roles): cards, team-coloured map with a public-domain Saudi outline, street-map toggle, site search, site card on map pin or row click, trip tables and a not-placed list.
- **Candidates:** open Stage 2 and 3 field cycles. Excluded: Incident work (matched through the ERP Project name and family, not a fixed PO), recently visited cycles without HO or GCL (held 30 days), PM Hold and Remove, and office-only Stage 3.
- **PM decisions:** the list on each row, card and page offers blank, Must, Hold (30 days) and Remove. Each choice writes a line to the append-only log `SIG Plan Decision`. A new TCN cancels a Hold or Remove. Must lasts 14 days or until a visit is reported. The cycle's Planner Mark mirrors the current decision.
- **Continuity scheduler** (`sig_warehouse/sig_warehouse/continuity.py`): teams carry on from where they stopped, travel is counted, unfinished work continues next morning, and TCN windows are honoured. Live on 2026-10-25: 24 trips scheduled, 12 of 13 windows met, 3,757 km of overnight relocation counted, 0.08 s run. Before this release the plan placed trips in interchangeable team slots, which hid about 11,700 km of overnight moves.
- **Coordinates:** `site_latitude`, `site_longitude` and `geo_source` on SIG Site. Source is SitesDB (one-way copy, 1,966 sites written with zero read-back mismatches). Permissions: Projects User may read SIG Site (declared grant).
- **Excel:** `Field_Plan_<week>_*.xlsx` (Clusters, Schedule, Not scheduled) is generated by `ERPNext/scripts/planner_export_xlsx.py` from the same engine. Nothing is written to ERP by the export.

**Not yet live**
- Team bases are deliberately not modelled. Owner decision: teams start each day where they stopped.
- Per-team route blocks on the page (the scheduler returns them; the page still shows trips).
- Unhold and Restore on the cycle form.
- PM feedback: each PM's lapsed TCN sites with the nearest team.
- Team availability per day.
- Critical-site timing (RV80 forces 8 hours from midnight, and 06:00–18:00 for critical Incident sites). Staged in the MASTER doc, not built.
- Compute check: the scheduler's cost on Frappe Cloud was not measured after release. Baseline before the release was 0.00684 h of 2 h daily compute.
- Persona acceptance for SIG Field Ops and Projects User sessions is NOT TESTED. The permission snapshot tool does not cover the new SIG Plan Decision DocType; its roles were checked directly on the site.

**Canonical white paper:** moved to RV80 on 2026-10-25 (`RV80/Project Structure/canonical/white paper cp.md`). The SIGPC copy is archived.


## Current reality — field teams from Excel Setup — 2026-10-26

- **Teams list (Excel Setup, dataset `teams`, revision 9):** a team is its leader. Team name and phone come from the
  Employee record server-side, never typed. Six leaders are enabled (HR-EMP-00005, 00008, 00019, 00021, 00025, 00026);
  HR-EMP-00014 and HR-EMP-00045 are staged but disabled (no check-in or check-out in 14 days).
- **Starting positions:** each enabled team starts the plan from its leader's latest check-in or check-out site
  (`team_positions` in `field_planner.py`). A position older than 14 days is "Stale" and not used; no visit means "Unknown".
- **Team count:** enabled teams in Excel Setup set the team count; a Teams value typed on the page overrides it.
- **Release:** commit `1ac635c8` on `main` (tag `pre-teams-20261026` = previous `317caf5`). Frappe Cloud backup
  `dtu7oikn2m` taken before the release. Bench deploy and site update completed; site on `1ac635c8`.
- **Live check (read-only, 26-Oct):** 6 teams, 8 of 11 TCN windows met, travel 98.9 h, search 0.09 s. Earlier 12 of 13
  came from 5 slot teams with no starting point, so the comparison is not like-for-like; review tomorrow.
- **Open:** the team-start gap (check-ins not yet covering each leader's last day), daily re-plan, per-team route
  blocks, Unhold/Restore on the cycle form, PM feedback on lapsed TCN sites, persona checks for Field Ops and Projects User.


## Current reality — team archetype and map — 2026-10-26 (later)

- **Team archetype (Excel Setup, `teams`, revision 10):** each team row is `Project` (planned) or `Incident` (labelled,
  never planned). HR-EMP-00025 (Waqas) and HR-EMP-00021 (Imran) are `Incident`. The planner lists them as "Incident team · not planned".
- **Release:** commit `2f392a98` on `main` (tag `pre-archetype-20261026` = `1ac635c8`). Frappe Cloud backup `5967pchor2`.
  Bench deploy `09i52ktqst`, site update `ce7kug2c73`, site on `2f392a98`, stable.
- **Map:** sea-coloured background, rough neighbouring countries (outline only, not surveyed), taller box so south-coast
  sites stay on the map, and the 142 reference towns always shown in amber (Jeddah larger). The 142 stand in for
  municipality capitals; the full municipality list (about 285) still needs a source.
- **Open:** a km readout the user reported in the bottom-right of the map was not found in the drawing or street-map DOM on 26-Oct.


## Current reality — map scale and main towns — 2026-10-26 (later still)

- **Commits on `main`:** scale bar and neighbour removal (tag `pre-scalebar-20261026`), then `52821fe6` main towns only at normal zoom.
  Deployed as bench release `2ka1u2ns5i`; site on `52821fe6`, stable.
- **Scale bar:** bottom right, picks a round km length (5 to 500 km) for about a fifth of the visible width and updates on each zoom.
- **Neighbouring countries:** removed. Only the sea background and the Saudi outline remain.
- **Towns:** 27 main towns (Riyadh, Jeddah, Makkah, Madinah, Dammam and regional centres) are always shown; all other reference towns appear only when zoomed in.
- **Open:** the full municipality list (about 285) is still not in the data, so the main-town list is hand-picked.


## Current reality — planner integration repair — 2026-10-26

- **Release:** SIG Warehouse commit `ed35e177` on `main`; Frappe Cloud bench build `f1t349p6mn`; site update `b7tsqlh599`; production site is Active on the exact commit. Pre-release Cloud backup: `c0rso6cbbp` (Success).
- **Plan horizon:** default starts tomorrow using the ERP/Riyadh date and schedules five Saudi workdays (Sunday–Thursday), retaining later days for continuity and skipping Friday/Saturday.
- **Completed visits:** cycles with a `COMPLETED` `SIG Field Visit` are removed before clustering. This is per cycle; new scopes at the same physical site remain eligible. The Excel planner's separate 30-day visit hold is unchanged.
- **Integration:** Planner team position, posted-visit and session reads are limited to enabled Setup roster members and visible to the existing Planner role audience despite per-employee User Permissions. Site Visits' `get_visits` now checks its Operations audience server-side. The ERP Project selector uses `erp_project`, with agreement/PO compatibility for older cycles.
- **Interface:** responsive Operations links, role-aware Excel Setup link, stop workday, return-to-page refresh after 30 seconds, corrected distinct team/date capacity count, and TCN-window retention when a trip also contains unwindowed filler.
- **Permissions:** DocType/Page role matrices, User Permissions and Employee/HR access were unchanged. Before/after permission snapshots have zero added and zero removed grants (`ERPNext/backups/permission_release_field_planner_20261026_1345/`).
- **Not tested by owner instruction:** test suites, Desk route rendering, and ordinary-user acceptance for GM, PM/coordinator and outside-audience identities. Deployment/API readback confirms the revision and Active site, not those workflows.
- **Remaining work:** precise arrival-time route presentation and generation watermark are not part of this release. Distinguish “no visit” from “visit has no usable site coordinates.” Stale `UNRESOLVED_SITE` visit diagnostics remain for reconciliation in the existing intake system.


<a id="deferred-fixes-review"></a>
## Deferred: review local SIG Warehouse fixes against production — 2026-10-28

The local checkout at `ERPNext/SIG_Warehouse` was based on `c97714b`, about 140 commits behind production. Production is now on `b577cb1fd597264a2402e791ac5638d79e7f7737`. The 31 local Git status entries were not a safe release bundle: they mixed already-deployed files, stale versions that would remove current behavior, partial feature additions, and permission writers. The owner asked to record the likely intent for future development and then remove those local entries. Use this section as the handoff; start any future work from the then-current production source and reproduce the specific need before changing code.

### Do not retry or rebuild what is already live

- **Historical comparison superseded:** Client Collections progressed beyond the preview-only version described in the earlier 31-file review. A persistent draft and send workflow was deployed, but the two actual reminder attempts failed; see [current Collections status](#client-collections-status) and the priority index. Continue using existing Sales Invoices and a manually entered recipient.
- The field-visit page change that opens WhatsApp with the nearest `SITE-ID start` message and the public site lookup are already deployed. Do not redeploy the local duplicate.
- HR attendance page assets are already present in production, and the dashboard was separately deployed. Do not replace the live dashboard with the divergent local `attendance_dashboard.py` without first proving a new defect.
- SIG Verify's API, token, QR and event source files are already mostly present. The local registry delta is not grounds to redeploy the whole verification feature; inspect the exact missing document type or behavior first.
- SIG Letters also has substantial overlap with production. Continue only missing or materially changed letter assets/templates after comparing against the live source; the local directory also included generated `__pycache__` files, which are not release sources.

### Likely fixes worth reproducing and porting selectively

| Local item / likely purpose | Why it may matter | Future development guard |
|---|---|---|
| `sig_warehouse/sig_warehouse/field_feed.py` and `field_sessions.py`: recognize a site ID from known ERP sites when parsing WhatsApp start/end messages; reparse recent stored raw messages after parser improvement; send unresolved site sessions to review and refuse posting until resolved. | Could reduce manually correcting misattributed or site-less visits. | The local file is stale and drops current cycle-attribution diagnostics, CAPEX2 scope checks, and posting safeguards. Port only the parser/review improvement into current production code; keep all current checks. Reconcile affected sessions before posting any backfill. |
| `sig_warehouse/sig_warehouse/patches/v1_0/fix_asbuilt_terminal_behavior.py`: treat `ASBUILT_BOQ_GENERATED` as a milestone and close a cycle only on explicit `SITE_CLOSED`. | Likely fixes premature closeout that blocks further field evidence. | Confirm the current `register_evidence_event` Server Script still has the reported behavior; patch only that branch, fail closed if its source differs, then verify an As-Built event remains open and explicit closeout becomes terminal. |
| SIG Letters source/templates: reusable structured English/Arabic letters, block-based content and a standard print layout. | Could reduce repeatedly typing common client, authorization, warranty and release letters. | Compare the existing partial module and templates first. Port only missing templates/UI differences; review print output and letter permissions before deployment. |
| `sig_warehouse/sig_verify/registry.py` and `add_verify_token_fields.py`: expand which documents receive verifiable QR tokens. | Could extend document authenticity checks beyond the current registered set. | Determine the required document types and confirm the public verification response exposes no private invoice/customer data. Do not alter unrelated document hooks. |
| `restore_quotation_access.py`, `grant_humaira_supplier_item_maintenance.py`, and `grant_operations_payment_entry_drafts.py`: targeted Quotation, Item/Supplier and draft Payment Entry access. | These may correspond to previously reported blocked workflows. | Handle each only against a confirmed reproducer and current full standard/custom permission matrix. Role Profile changes and any Custom DocPerm additions require the permission regression gate; never ship them bundled with UI or automation work. |

### Do not transplant stale files wholesale

Local `hooks.py` removes current petty-cash guards, return-policy and PC-review schedulers, and current dashboard / JavaScript registrations. Local `patches.txt` omits current migration patches. Local `operations_workbench.py` is roughly 660 lines shorter than production; `field_feed.py` is roughly 109 lines shorter; the Arabic translation file drops 179 current rows. Local `dashboards.py`, `sites.py`, Site Visits JS, Operations workbench JS/CSS, and HR backend code also diverge from the deployed versions. These may contain isolated ideas, but require a specific problem statement and selective reimplementation from current source; do not retry the local files or the old checkout as a release.

The attendance, Client Collections preview, field lookup, field-visit release, and remaining persona/snapshot status are recorded in the [permission release evidence](../backups/permission_release_field_visit_b577cb1/release_gate.md). Future releases still require the normal access and persona gates; this deferral record does not certify workflow acceptance.


<a id="client-collections-status"></a>
## Client Collections: persistent reminder workflow deployed — 2026-10-28

**Status: deployed to `neosys.frappe.cloud` as `sig_warehouse` commit `48b03976b49e7dd1a6852bf43020df4b06cf7451`; functional, workflow and persona tests were explicitly deferred.** The previous modal-only preview is now a persistent `SIG Client Collection Draft` workflow. It uses existing submitted Sales Invoices and their live outstanding balances; no second invoice register is introduced. The operator enters the WhatsApp destination manually, chooses WhatsApp, email, or both, reviews/edits a saved bilingual-capable reminder, then explicitly sends. Drafts remain listed on Client Collections and open as normal ERP documents.

Each draft snapshots invoice, due-date, currency and balance data. Sending rechecks invoice read/print permissions and blocks if an invoice was paid or its balance/due date changed. The generated private PDFs comprise the reminder letter and each selected invoice; they are sent directly through the existing SIG WhatsApp Maytapi helper (no public file URL), or attached to a queued ERP email. Maytapi test mode redirects WhatsApp to the configured test number. Per-component delivery rows retain provider acceptance, message/queue references, failures, and retry counts so retries skip already accepted items. A provider `Queued` status is not represented as confirmed handset delivery.

### Source permission baseline and acceptance status

- Before this edit, `client-collections` Page roles and its server `_guard` were Accounts User, Accounts Manager and System Manager. Its invoice list and preview used the same roles, and the preview checked Sales Invoice `read`. Existing `SIG Letter` and `SIG Letter Template` DocType source permissions were System Manager only; this feature does not use those records or broaden them.
- New `SIG Client Collection Draft` source permissions grant read/write/create/print/report only to Accounts User, Accounts Manager and System Manager. Delete, submit, cancel and export are not granted. Two child tables inherit parent access and have no standalone audience. The Page role whitelist is unchanged. The send method repeats the role gate, checks draft write/print and each Sales Invoice read/print permission, and only acts after a user presses Send.
- Pre/post live snapshots show the existing `client-collections` Page roles unchanged. The new draft grants read/write/create/print/report only to Accounts User, Accounts Manager and System Manager; no delete, submit, cancel or export grant is present. The child tables have no standalone roles. Sales Invoice, Customer, Company and Currency access matrices did not change. The snapshot diff's three reported removals are only the three new DocTypes being `missing` in the before snapshot; all 99 additions belong to these newly installed DocTypes and their fields/declared permissions. See [release gate and permission evidence](../backups/permission_release_client_collections_20261028/release_gate.md).
- Actual authenticated Desk route rendering, User Permission/link-field behavior, actual Accounts User/Accounts Manager/System Manager workflows, a denied outside-role case, email queue behavior, Maytapi test-mode delivery, provider errors/retries, Arabic PDF rendering and real PDF attachments remain **NOT TESTED**, as requested. No user message was sent during deployment. Complete the mandatory persona and learning-loop checks before calling user acceptance verified.

The deployed module enables explicit delivery through the existing Maytapi helper or ERP email queue. Provider-accepted/queued status is not proof of handset delivery.

### Corrective release: make the send action visible — 2026-10-28

Production review showed that saved reminders had no obvious dispatch control. Commit `3e9206866d75795cc4087a34ce04113804bebe47` first registered a toolbar action, but browser review found it hidden in the `…` menu. Commit `bc62d30e2a3e2654ff69c0bd600e08cd45baf19b` then added a visible **Send Reminder** button directly on the saved draft form. This is the operator action that dispatches the reminder; the record itself intentionally remains a non-submittable draft, so ERP's generic Submit action is not the send mechanism.

The release completed as Cloud build `866k24s62i`, Site Update `8a3942q3tc`, active bench `bench-38491-000290-f1f`, with no pending app updates. The GPT in-app browser opened `CCREM-2026-00001` and confirmed the button is visible. The pre/post permission snapshot diff shows zero removals and only the declared `send_reminder_button` field addition; no access matrix changed. Actual ERP identity/role, Accounts persona workflows, confirmation, provider response, email, Maytapi, PDFs and retry behavior remain **NOT TESTED**. The button was not clicked and no message was sent. See [release gate](../backups/permission_release_client_collection_inline_send_20261028/release_gate.md). A recurring Press Source-detail 403 is logged under [PERM-20261027-02](permission_cases/PERM-20261027-02.md).


## Deferred employee account and task-app integrations

**Current source-of-truth boundary — 28 October 2026:** `Employee.custom_custody_account` is the ERP anchor used by petty-cash clearance. Am's `pc_employee_accounts` is a separate mirror; SNB import still posts through Am `erp_party` rather than resolving an immutable Employee ID and reading that Employee's linked account. Thus SIG PC is Employee-linked, but SNB and the full employee banking path are not yet unified. Keep unmatched, duplicate, or purpose-ambiguous beneficiary links in an exception queue; never auto-link by display-name similarity. Mohammed Algain remains a special deferred case. Sagheer's ledger key still carries the previous Muneeb label and requires a safe Finance-controlled rename/migration; Piran has no matching custody ledger and needs Finance approval before creation.

**Todoist — ERP task delivery (deployed 29 October; acceptance open):** SIG Warehouse `41cde77c429a88cf9231d08d51b8d235501e514e` is installed on active `neosys.frappe.cloud`; the `/app/app-connections` route shows the existing OAuth connection and Inbox project. Newly created ERP ToDos assigned to `9eskot9@gmail.com` and two explicit SNB conditions (failed ERP-import phases and rows skipped for review) enter the private outbox. The integration does not backfill old ToDos or send tracebacks/bank/beneficiary details; ERP remains authoritative and Todoist completion does not close ERP tasks. Snapshot evidence shows no existing access removal or role grant. No production task was created for acceptance; external delivery, retry/reconciliation and fresh actual-user workflow remain NOT TESTED. The SNB runner changes are local and uncommitted in the broader ERPNext checkout. Preserve SNB transaction/review records; do not route other Error Logs or historical runs automatically. See the [Todoist release gate](../backups/permission_release_todoist_task_delivery_20261029/release_gate.md) and [`SIG_Warehouse/docs/app_connections_todoist.md`](../SIG_Warehouse_todoist_20261028/docs/app_connections_todoist.md).

**Deferred HR follow-through:** Candidate Intake for Faizan Rasheed is not live; no onboarding request was sent and no employee or User was created. Verify his consent/identity path before contact. Finish the SNB/Employee identity map and compare every Am mirror row to the Employee link before claiming account coverage. Complete actual-user permission acceptance for changed HR and finance workflows; Administrator/API read-back is not persona acceptance.

**ERP release and reminder follow-up — 28 October 2026:** Commit `89d948c3ca369babb823f333e2e1f9e96c80b66b` was pushed and deployed to `neosys.frappe.cloud`; Site Update `dn1q3j2tin` succeeded on active bench `bench-38491-000291-f1f`. The pre-deployment backup `7gn2lan6nk` succeeded. The migration installed `planner_critical_status` and `planner_critical_source`; the ERP-only endpoint is deployed, while RV80 workbook sender changes remain deliberately deferred. Permission snapshots (`before.json`, `after.json`) compare 48 DocTypes, 19 Pages, 42 Workspaces, 22 Reports, 25 Role Profiles and 55 enabled users: **zero removals**, only the two declared read-only Custom Fields were added. No workflow/persona tests were run, as requested; affected audiences remain NOT TESTED.

**Maytapi acceptance remains unresolved:** live `CCREM-2026-00001` still reads `Sending`, Last Attempt `2026-10-28 21:09:46.487437`, blank Last Error. The earlier provider inspection found no matching send request or queue entry. Therefore provider acceptance is NOT EVIDENCED and client receipt is NOT VERIFIED. Do not count it as sent or automatically retry. Next: inspect/reconcile per-component state and provider logs, then make a controlled retry decision. The deployed queue change improves new sends and queue/worker error visibility; it does not reprocess this old attempt.
