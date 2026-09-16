# SIG Warehouse

ERP-native warehouse workbench (dispatch, returns, custody) for ERPNext, replacing WH's
Excel/VBA system per `ERPNext/docs/erpnext_final_implementation_plan.md` §9A.9.

**Status, 2026-09-16: live for real operational use.** All four warehouses (Jizan, Qasim,
Makkah, Riyadh) have an ACTIVE Stage 4 cutover — ERP is the sole stock writer, the legacy WH
Excel/VBA workbook is retired from writing. Dispatch (`Issue` button on a Material Request, or
the Kanban board's card menu), returns/custody declaration, and cancel-remaining-demand are all
real, audited, idempotent endpoints. Still open: the historical starting balance has 1,102
unreconciled rows against the legacy workbook (Stage 5 gate 3) — see
`ERPNext/docs/erpnext_final_implementation_plan.md` §9A.10 for the full statement before treating
current ERP stock as reconciled to the unit.

This app is the permanent home for the transactional writers (`sig_dispatch_mr`,
`sig_declare_disposition`) and the lifecycle hooks that keep MR dispatch-state derived
fields correct on every native ERPNext submit/cancel/amend - not just the two custom
endpoints. See §9A.9 "Writer placement" for why this is a bench app rather than more
sandboxed Server Scripts.

Deploy pattern: same as `sig_whatsapp` (`ERPNext/scripts/deploy_sig_whatsapp_bench.ps1`,
retargeted). Requires this app connected to the Frappe Cloud bench via its own GitHub
repo first - a one-time manual step, same as `sig_whatsapp`'s original setup.
