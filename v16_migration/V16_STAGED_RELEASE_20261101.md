# v16 staged release and deployment guide

Status: STAGED ONLY, 1 November 2026. Production `neosys.frappe.cloud` was last verified on v15; the v16 trial is separate. Confirm current live status and exact revisions again before deployment.

## Staged app changes

[Draft PR #68](https://github.com/9eskot9-max/SIG_Warehouse/pull/68) combines the Excel Setup PM repair (#67), dispatch field access (#66), ready-MR feed correction (#64), and HR default-export review (#65). These PRs overlap; do not merge them all unchanged. The combined candidate passed 29 focused local tests on its published revision, but has not been deployed, migrated or accepted as a real user. It does not fix the empty Sales Invoice NaN display or resolve the ZATCA branch safeguard differences. Do not represent this as a complete or approved production release.

The feed currently uses `frappe.get_all`, and the proposed status change exposes additional records to existing callers. Review and enforce the intended audience and record scope before enabling the change. HR and dispatch permission changes also require review of roles, downstream writers, actual permission matrices and representative-user workflows. Follow the deployment permission guide and incident cases in the ERP workspace, including real migration repeatability and access snapshots; testing after production deployment alone does not satisfy those requirements.

## PM for WO-2026-0037 / Capex PO 10001274

The last recorded production read showed both Project and active default assignment as Muhammad Jawad Khan; RV80 holds a temporary PO-specific Hazem override. Re-read current ERP data before changing it. Do not run RV80 Sync From ERP first, since it could overwrite the temporary override. After the PM fix has been deployed and accepted, open Excel Setup > Projects / PO setup, select Hazem A Najjar for the PO, confirm the mismatch checkbox if one is shown, and save. Read back the Project default and active assignment and verify both identify Hazem. Then run RV80 Sync From ERP and confirm that PO 10001274 still shows Hazem; check shared builder aliases are unaffected.

## Cutover outline

1. Finish release scope, version pinning and the permission and feed review; rehearse the actual production-site upgrade path on a restored copy and record migration repeatability and representative-user acceptance. The owner's small live ZATCA invoice test remains after cutover.
2. Agree the cutover window, stop conflicting writers/schedulers, take a fresh supported database, files and configuration backup, and verify the recovery and rollback procedure. Preserve the encryption key and current production data.
3. Upgrade the existing `neosys.frappe.cloud` site using the approved v16 branches and pinned app revisions through Frappe Cloud. Verify the exact site, bench, pipeline and migration result; don't assume the trial database or its newly onboarded device automatically moves with an in-place upgrade.
4. Verify real user logins and permissions, Desk routes and linked forms, ERP PM records, RV80 workbook, WH/TX Manager, Todoist and WhatsApp. Restore only the intended external writers, ensuring a single production writer per integration. Perform the owner-planned small live ZATCA invoice test only after cutover.

RV80 source already points to `neosys.frappe.cloud`; the installed workbook has not been independently compiled or accepted against v16. Keep incomplete checks marked NOT TESTED, rather than treating source presence or a successful build as proof of operation.
