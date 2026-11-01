# v16 production upgrade: open fixes and acceptance

Recorded 1 November 2026. **Status: NOT READY.** This document records findings and required work; it does not implement, deploy, or verify the fixes. Production `neosys.frappe.cloud` remains on v15. The intended method is Frappe Cloud Version Upgrade of that existing site using its current production database, after the checks below. Do not assume a successful simulation or an Administrator page load is full acceptance.

## Actual versions reviewed

- Trial `neosys-v16-trial.frappe.cloud`: Frappe 16.54.0, ERPNext 16.53.0, HRMS 16.53.0; SIG Warehouse `v16-migration` at `1229f4f`; ZATCA `sig-v16-phase2` at `cbc271a`.
- Production SIG Warehouse `main` at `59c7ce3`; ZATCA `sig-v15-phase2-base` at `25454a7`.
- On review, SIG Warehouse's `v16-migration` branch had moved beyond the installed trial revision with documentation commits. Verify and pin the exact revisions before building; review every pending change.

## Release blockers and required actions

### 1. Preserve ZATCA production safeguards

Production branch commit `a921f14` adds legacy invoice protection: it prevents a flagged historical invoice entering ZATCA generation/resend and validates the flag's immutability. The reviewed v16 app source at `cbc271a` contains no references to `custom_is_legacy_import` or `is_legacy_import`, including its central `generate_einvoice` and `resend_einvoice` paths and hooks. The restored trial has 341 invoices with the legacy flag. Trial Server Scripts and Client Scripts were also searched for those identifiers with no matches. This is a source finding; it is not a live attempt to submit or resend an invoice.

**Required:** compare production's complete legacy guard and all entry points against v16, port any missing protections into the v16 ZATCA branch, and test validation, submit, individual resend and bulk resend with representative flagged documents without contacting the live authority. Confirm the classification cannot be changed after creation and that historical invoices never enter signing, the hash chain, transactions, or external requests.

Production has an `enforce_b2b_clearance_on_submit` hook; that symbol is absent in the reviewed v16 app. Determine whether the v16 vendor flow provides equivalent enforcement, including rejected, non-JSON and network-failure responses, and preserve the approved production behavior if it does not. A missing symbol alone does not establish the result of a rejected invoice. Review the diverged production-only commits, including buyer VAT/address fallback, error handling and workspace restrictions. The handover reports normal simulation invoices passed; this does not test these boundaries. Use sandbox/simulation and approved credentials, never production signing credentials for test submissions.

The v16 app's `ZATCA` Workspace fixture and trial record are public with no role whitelist. The separately named `ZATCA Integrations` Workspace has Accounts Manager, Accounts User, Finance Manager and System Manager roles. Review intended visibility and effective authorization; navigation alone does not prove a permission grant or denial.

### 2. Warehouse dispatch field access

Trial case `PERM-20261101-01`: impersonated Hamid (`hamid.j@sigtele.com`, Operations Admin profile with Warehouse Manager and Stock User) opened Warehouse Workbench → Dispatch materials. The `SIG Dispatch Queue` Kanban failed: `You do not have permission to access field: Material Request.custom_dispatch_stage`.

Trial metadata: `custom_dispatch_stage` is a read-only Select at permlevel 1 and the board groups on it. Material Request effective level-1 read is granted to System Manager and Stock Manager; Hamid has neither. The trial currently has 11 Custom DocPerm rows for Material Request; only this parent field is at level 1. The local field setup mirror is `ERPNext/scripts/hr/sig_warehouse_workbench_custom_fields.json`.

**Required:** determine approved warehouse audiences, inspect the complete standard and custom matrices, related child fields, Role Profiles and User Permissions. Implement a narrowly scoped, repeatable source-owned correction preserving the entire approved matrix. A sparse Custom DocPerm list can replace standard permissions; do not create one assuming it merely adds a role. Compare snapshots and test the real dispatch board and linked workflow as each affected audience. Current acceptance: **FAIL**; fix and repeatability **NOT TESTED**.

### 3. Warehouse-ready MIR feed

Trial `sig_list_ready_mrs` filters by old `custom_sync_status` values. MIRs 1197–1206 and 1208 are present on trial as submitted, unsent and `PARTIALLY_CONFIRMED`, so the current filter excludes them. The prepared local mirror `ERPNext/scripts/hr/sig_list_ready_mrs_server_script.json` differs from trial in the two status-filter expressions and retains submitted status, source identifier and `custom_sent_to_wh=0` gates.

**Required:** review the caller audiences and all permission layers before exposing additional records. Deploy a version-controlled, repeatable correction to the trial; verify the 11 appear exactly once through the intended feed with a representative warehouse user, without importing or issuing them. Preserve other intended filters, duplicate safety and permissions. Deploy to production only through the permission and release gate. **NOT DEPLOYED / NOT ACCEPTED.**

### 4. Sales Invoice empty-form display

An Administrator's new v16 invoice showed `SAR NaN` for outstanding after defaults loaded without a priced item. Selecting a customer and item cleared the amount; quantity 1 and rate SAR 100 gave SAR 15 tax and SAR 115 outstanding on the unsaved form. Nothing was saved or submitted.

**Required:** identify and fix the empty-form calculation/display cause, compare against v15 and v16 app scripts, and check fresh forms under affected users, linked-record lookups, taxes and populated totals. Do not send test invoices to the production ZATCA environment. The populated unsaved example is a limited pass, not end-to-end acceptance.

## Cutover gates

1. Review all permission writers, migration order, complete standard/custom DocPerm matrices, roles, profiles, User Permissions, field levels, Pages, Reports and Workspaces. Capture before/after snapshots and review additions as well as removals. Follow `ERPNext/docs/deployment_permission_guide.md` and the learning-loop access gate in the local workspace. Actual-user acceptance is required; Administrator/API success is not a substitute.
2. Rehearse the **existing production-site Version Upgrade** on a restored copy where feasible; this differs from merely restoring a v15 backup to an already-v16 bench. Review patches and fixtures, rerun the setup/migration path for repeatability and keep a written rollback.
3. Inventory any trial-only database settings and the newly onboarded trial ZATCA device. Decide explicitly what must be preserved or recreated; the trial database will not replace the existing production database during an in-place version upgrade.
4. Freeze production writers and scheduled integrations for cutover; take and verify a fresh recoverable database, files and site-configuration backup. Coordinate scheduler, WhatsApp/Maytapi, Todoist, ZATCA and other external writers so only one site acts on production systems.
5. After upgrading `neosys.frappe.cloud`, verify the actual Desk routes, user roles and linked forms in fresh sessions, the authorized warehouse workflow, ZATCA sandbox boundaries and production device configuration, and RV80 read-only sync before any separately authorized live transaction. Record PASS / FAIL / NOT TESTED for every audience and workflow. Keep rollback available.

RV80 source already targets `https://neosys.frappe.cloud`; keeping that site name does not require a hostname change. Its installed workbook, API authentication as real users and end-to-end workflows remain to be verified.
