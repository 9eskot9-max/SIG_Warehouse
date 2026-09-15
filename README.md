# SIG Warehouse

ERP-native warehouse workbench (dispatch, returns, custody) for ERPNext, replacing WH's
Excel/VBA system per `ERPNext/docs/erpnext_final_implementation_plan.md` §9A.9.

This app is the permanent home for the transactional writers (`sig_dispatch_mr`,
`sig_declare_disposition`) and the lifecycle hooks that keep MR dispatch-state derived
fields correct on every native ERPNext submit/cancel/amend - not just the two custom
endpoints. See §9A.9 "Writer placement" for why this is a bench app rather than more
sandboxed Server Scripts.

Deploy pattern: same as `sig_whatsapp` (`ERPNext/scripts/deploy_sig_whatsapp_bench.ps1`,
retargeted). Requires this app connected to the Frappe Cloud bench via its own GitHub
repo first - a one-time manual step, same as `sig_whatsapp`'s original setup.
