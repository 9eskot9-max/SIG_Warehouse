# v16 production follow-up fixes — 1 November 2026

Audit findings are being staged against the revisions installed on
`neosys.frappe.cloud`. The invoice wording was removed directly from the live
Print Format on 1 November; the app patch below makes the change repeatable in
future deployments. The other app changes are in open draft [SIG Warehouse PR
#68](https://github.com/9eskot9-max/SIG_Warehouse/pull/68) and [ZATCA PR
#1](https://github.com/9eskot9-max/ZATCA_Integration/pull/1); neither is merged
or deployed.
Previously generated invoice PDFs and historical invoice records have not been
rewritten. The one ZATCA canary invoice remains deferred until the owner runs it
after cutover.

## Source changes started

| Item | Finding | Staged work | Acceptance |
|---|---|---|---|
| Invoice transfer instruction | “Quote {{ doc.name }} on your transfer.” appeared in the live SIG Tax Invoice (Infographic) format and in the PDF of SIG-SINV-26-133. | Removed from the live Print Format through the ERP API; exact record read-back succeeded and a read-only render of SIG-SINV-26-133 no longer contains the text. Local source includes a guarded, idempotent patch that removes only that line in future deployments and refuses an unfamiliar template. Previously generated PDFs and attachments stay as issued. | System Manager API render: PASS. Fresh Desk preview and representative invoice-user acceptance: NOT TESTED. Evidence: `ERPNext/backups/invoice_reference_removal_20261101/`. |
| Print toolbar Share | The JS asset is deployed, but the live v16 toolbar's icon-only PDF control is not recognized by the script, so Share is not inserted. | PR #68 extends PDF action discovery to accessible labels / icon metadata; preserves the original icon when relabeling; and cache-busts the asset. | NOT TESTED in the live browser after build and deploy. |
| Buyer VAT fallback | V15 permits `Customer.tax_id` as fallback when `custom_vat_number` is blank; the deployed v16 ZATCA XML path uses only `custom_vat_number`. | Add a shared VAT resolver and use it for the emitted buyer VAT. | NOT TESTED with a customer populated only in `tax_id`; ZATCA canary remains deferred. |
| Non-JSON FATOORA responses | Deployed v16 response paths call `.json()` directly; v15 retains status, content type and a bounded response preview when parsing fails. | Restore defensive response parsing for transaction logging and status handling. | NOT TESTED against malformed / empty sandbox responses. |
| Already-imported legacy invoices | V15 marks the legacy classification immutable and bypasses ZATCA generation/resend for flagged invoices. Deployed v16 source lacks those guards. | Restore only the protection for records already carrying `custom_is_legacy_import`; no historical import/resend flow is being added. | NOT TESTED on a flagged existing invoice; confirm live field and record state before deployment. |

## Investigation / release follow-ups

| Item | Current state | Required next evidence |
|---|---|---|
| Empty invoice `SAR NaN` | Reproduced after VAT defaults load; no fix is in the deployed release. | Trace the v16 outstanding/tax calculation owner and prepare a scoped fix; fresh unsaved-form acceptance by affected invoice roles. |
| ZATCA Workspace audience | V16 fixture has an empty role list; navigation visibility is separate from DocType authorization. | Confirm whether broad tile visibility is intended; check affected audience access without changing permissions by inference. |
| Canonical ZATCA branch | Installed B2B clearance gate is present in the deployed revision, while the canonical `sig-v16-phase2` branch is behind it and PR #1 remains draft. | Reconcile source branches before the next build so the next deployment cannot drop the gate. |
| Permission and user acceptance | The prior access audit has unresolved Agriculture Manager/User role loss; affected non-admin workflows remain NOT TESTED. | Continue the existing permission incident and mandatory persona gate. Do not call access fixed from Administrator/API read-back. |

## Deployment gate

Follow `ERPNext/docs/deployment_permission_guide.md`, the permission regression
mandate in `ERPNext/docs/erpnext_final_implementation_plan.md`, and the access
regression gate in `ERPNext/docs/erpnext_learning_loop.md`. For these template,
client-script and ZATCA changes, record affected audiences and relevant current
access, retain full matrices, compare after migration, and complete fresh-session
persona checks. Failures or unperformed acceptance remain FAIL / NOT TESTED.
