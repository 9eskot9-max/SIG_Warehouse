# SIG ERP: v15 vs v16 handover (1 Nov 2026)

## Where things are
| | Site | Version | State |
|---|---|---|---|
| Live today | `neosys.frappe.cloud` | v15 | Still running, scheduler on. Backup taken 1 Nov ~03:14 Riyadh. |
| New ERP | `neosys-v16-trial.frappe.cloud` | v16 (Frappe 16.54 / ERPNext 16.53 / HRMS 16.53) | Holds a full copy of production data from that backup. Scheduler OFF. |

**Why it still says "trial":** only the site *name* is the trial's. Frappe Cloud does not let anyone change a site's subdomain through the API or dashboard, so the name swap (`neosys` -> `neosys-old`, `neosys-v16-trial` -> `neosys`) must be done by Frappe support. Nothing else about it is a trial: it is the production data on v16. Until the swap and the steps below, v15 stays the system of record.

## Branches (GitHub 9eskot9-max/sig_warehouse, also sig_whatsapp, sig_qr_design, zatca_integration)
- `main` = v15 code (unchanged, still what the live v15 site runs).
- `v16-migration` = v16 code (zatca_integration: `sig-v16-phase2`). The v16 bench builds from these.
- After cutover: rename `main` -> `version-15`, `v16-migration` -> `main`, and change the bench branch in Frappe Cloud.
- Local work: develop on `v16-migration`; do not merge it into `main` while v15 is live. Fix bugs that exist in both on `main` first, then bring them across.

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
- Site config is NOT carried by a restore. The encryption key and custom keys (Todoist client id/secret, field-planner OpenAI key and flags, petty-cash archive token) were copied manually onto the v16 site. Redo this on any new restore.

## Verified (v15 live vs v16 copy)
Counts equal for MRs (484 / 428 submitted), invoices, payments, journals, stock, items, employees, projects, files, SIG site/cycle/visit/PC/evidence. Users (68), roles per user, role/module profiles, user permissions, custom permissions, custom doctypes (26), server (72) and client (21) scripts, print formats, reports, workflows, templates, settings: identical. All 19 SIG pages load. Colours (number cards, charts, workspaces) and user themes carried over.

## Pending before you rely on v16 only
1. **Name swap by Frappe support** (see above). Alternative: attach your own domain to v16.
2. **Fresh data at cutover.** The copy is from 1 Nov 03:14. Anything entered on v15 since is not in v16. At cutover: stop using v15, take a new backup, restore, Migrate, redo the config copy, re-run the count comparison.
3. **v15 scheduler/integrations must stop** when v16 goes live (WhatsApp/Maytapi, Todoist sync, ZATCA reporting) or messages will double. Not done yet (deliberately left on).
4. **Scheduler on v16** is off; turn it on only after (3).
5. **ZATCA:** company settings and the production device carried over, but one device can talk to ZATCA from one site only. After v15 is stopped, send one real invoice from v16 and confirm it clears. Ask Frappe to set the bench timezone to Asia/Riyadh (invoice-date rule 00:00-03:00).
6. **Not yet re-tested after the encryption-key copy:** email account, ZATCA, Todoist, Maytapi.
7. **External callers** pointing at the old address: Maytapi webhook, Todoist OAuth redirect, RV80-WH VBA, TX Manager. They keep working only if the name swap gives v16 the `neosys` address.
8. **Staff walkthrough** (planner, petty cash, purchasing, finance, MIR dispatch) and a login test per role.
9. **Rotate** the Frappe Cloud API key/secret and treat the copied encryption key as exposed in chat.
10. Keep v15 restorable (`neosys-old`) for two weeks as rollback.
