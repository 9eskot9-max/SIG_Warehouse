# Handoff baton — Codex and Claude take turns

One agent works on the production branch at a time. The owner can change the holder at any moment.

| Field | Value |
|---|---|
| Baton holder | **Claude** (rebuild and deploy of the Sales Invoice and cleanup changes) |
| Next holder | **Codex** |
| Branch | `codex/sig-personal-home-v16` |
| Head when the baton was taken | `a03c88f` |
| Open items for the holder | Rebuild from the branch head with SIG Warehouse only; deploy after the new bench is Active; add a `docs/DEPLOY_LOG.md` row. |
| Waiting on the owner | Weekly PM check per project family (families, recipients and project mapping). Six legacy Payment Entry drafts. 98 draft petty-cash journals. |

## Rules

1. Read this file first. If the baton is not yours, stop and tell the owner. Do not push.
2. Take the baton by editing this table in your first commit (holder = you). Give it back in your last commit (holder = the other agent, with the new head and open items).
3. One move = one task the owner asked for, finished and pushed. Do not start a second task inside a move.
4. Never deploy, schedule a Frappe Cloud update, or edit the Cloud benches unless the owner told you to in this move.
5. Add a row to `docs/DEPLOY_LOG.md` for every Cloud action, in the same last commit.
