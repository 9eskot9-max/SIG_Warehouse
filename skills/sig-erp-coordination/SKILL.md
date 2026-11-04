---
name: sig-erp-coordination
description: Use before changing the SIG ERP repository (SIG_Warehouse) or deploying to neosys.frappe.cloud. Rules for Codex, Claude and the owner taking turns on one production branch, the handoff baton, the deploy procedure and the deploy log.
---

# SIG ERP: Codex, Claude and owner coordination

Repository: `9eskot9-max/SIG_Warehouse`. Production source branch: `codex/sig-personal-home-v16`. Production site:
`neosys.frappe.cloud` (Frappe Cloud bench group `bench-51251`). Full guide: `docs/CODEX_CLAUDE_COORDINATION.md`.
Status files: `docs/HANDOFF.md`, `docs/DEPLOY_LOG.md`, `docs/DEPLOYMENT_AND_BRANCHES.md`, and the master in `ERPNext/Automation DB/`.

## Turn-taking (one Codex move, then one Claude move)
1. `git fetch origin`, then read `docs/HANDOFF.md`. If the baton holder is not you, stop and tell the owner.
2. In your first commit set yourself as holder. In your last commit hand the baton to the other agent, with the new head and the open items.
3. One move is one owner-requested task, finished and pushed. Never start a second task inside the same move.

## Before you change anything
- Check the production head and the open pull requests. List commits since the last deploy: every commit on the production branch goes live with the next build.
- Never force-push. Never rewrite pushed history. If a hook asks for a rewrite, stop and ask the owner.
- `patches.txt` is append-only; on a conflict keep both lines. Never edit a patch that has already run on production.
- A new DocType needs its controller `.py` file. A new patch, DocType, dock, workspace or fixture needs a migrate.
- Run `git push` without `-q` and read the last line. A rejected push must not be reported as done.

## Deploy only when the owner says so (Frappe Cloud, not GitHub)
1. Confirm the commit list since the last deploy is what the owner expects.
2. Take a site backup.
3. Fetch the latest app update, then build with only the apps that changed. Leave out Frappe and HRMS unless the owner asks.
4. Wait until the new bench is Active, then schedule the site update with backups on. Scheduling earlier picks the old bench.
5. If the update reports Recovered or Failure, read the failing migrate step; Frappe has rolled back.
6. Verify the installed commit with the installed-apps API (the dashboard Apps page can be stale), the site status, and the pages touched.
7. Add a row to `docs/DEPLOY_LOG.md`. Tag the deployed commit `live/YYYY-MM-DD-<8 chars>` if the owner has approved tags.

## Record, do not guess
Dashboard views can be stale and some API reads are blocked. Write what was read, from where, and when. Mark anything not tested as NOT TESTED.
