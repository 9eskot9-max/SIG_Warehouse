# Deploy log — SIG ERP (neosys.frappe.cloud)

One row per production action. Times are Frappe Cloud times (UTC as shown in the dashboard). Add the row in the same
pull request that changes the deployed commit, or in the commit that records the deploy. Never edit an old row;
add a correction row instead.

Columns: **When** · **Who** · **Action** · **Bench** · **SIG Warehouse commit** · **Cloud IDs** · **Result** · **Notes**

| When (UTC) | Who | Action | Bench | SIG Warehouse | Cloud IDs | Result | Notes |
|---|---|---|---|---|---|---|---|
| 2026-11-01 | Owner + Claude | v16 cutover (in-place Version Upgrade of the production site) | bench-51251 | v16 staging branches | pipeline `3rkb1ujufv`, migrate `62obfopq6d` | Success | Hostname kept. Details in `v16_migration/` and the master. |
| 2026-11-04 02:57 | Claude (for owner) | Site update to the no-visit controller fix | bench-51251-000017 | `8db19e9` | build `d58fpng1p6`, update `1cfnf6kqub` | Success | Two earlier attempts rolled back: a missing controller file, and a site update scheduled before the new bench was Active. |
| 2026-11-04 16:07 | Claude (for owner) | Site update: Excel Setup links, no-visit message (Off), weekly PM check (Off) | bench-51251-000018 | `76927313` | build `ck3k6m7r7f`, update `0r3ck2fqno` | Success | Frappe and HRMS updates left out on purpose. |
| 2026-11-04 17:28 | Not recorded by Claude (owner or Codex) | Site update | not recorded | not recorded | update `fb079l4e72` | Success | Found in Cloud on 4 November; no commit recorded. |
| 2026-11-04 17:52 | Not recorded by Claude (owner or Codex) | Site update | not recorded | not recorded | update `9oq8ebg0bg` | Success | Found in Cloud on 4 November; no commit recorded. |
| 2026-11-04 18:54 | Owner via Codex (Cloud dashboard) | Site update to intake item changes | bench-51251-000023 | `c8f71c4` | pipeline `3roheu9glr`, update `6t76uuin7k` | Success | Includes the intake item-family commits (`13faa51`, `cf544c5`, `162a323`, `5fe31ca`); the catalogue default patch ran (Item field `custom_wh_catalogue`, default 1). Does **not** include the Sales Invoice change (`ce468a7`) or the cleanup patch (`7489d1e`). Codex recorded the Cloud Apps page as still showing `6ce8da3`; the API read of installed apps on 4 November shows `c8f71c4`, so that page was stale. |

## Open at the time of this log

- Bench `bench-51251-000024` is Active and is built from `7489d1e`. That commit contains a Field Planner weekly PM panel that the owner did not ask for (removed in `b246ace`). The site shows "Update Available" because of this bench. **Do not schedule the update from it.** Rebuild from a branch head that includes `b246ace` first.
- Not yet deployed: Sales Invoice tidy-up (`ce468a7`), Journal Entry and related cleanup patch (`advanced_cleanup_v1`).

## Row template

| When (UTC) | Who | Action | Bench | SIG Warehouse | Cloud IDs | Result | Notes |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD HH:MM | name | what changed and why | bench-… | commit (8 chars) | build …, update … | Success / Failure / Recovered | rollback commit if any |
