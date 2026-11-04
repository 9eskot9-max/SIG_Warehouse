# Handoff baton — Codex and Claude take turns

One agent works on the production branch at a time. The owner can change the holder at any moment.

| Field | Value |
|---|---|
| Baton holder | **Codex** (taken from Claude after the 4 November deploy) |
| Next holder | **Claude** |
| Branch | `codex/employee-project-setup` (isolated topic branch from `codex/sig-personal-home-v16`) |
| Head when the baton was handed over | `620c69e` (source base; new employee setup change is not deployed) |
| Open items for the holder | Implement and stage Employee Project Assignment + Custom Setup navigation; document WhatsApp intake requirements and Faizan's redacted dry-run boundaries. Do not schedule a Frappe Cloud update unless the owner says so. |
| Waiting on the owner | Weekly PM check per project family (families, recipients and project mapping). Six legacy Payment Entry drafts. 98 draft petty-cash journals. |

## Rules

1. Read this file first. If the baton is not yours, stop and tell the owner. Do not push.
2. Take the baton by editing this table in your first commit (holder = you). Give it back in your last commit (holder = the other agent, with the new head and open items).
3. One move = one task the owner asked for, finished and pushed. Do not start a second task inside a move.
4. Never deploy, schedule a Frappe Cloud update, or edit the Cloud benches unless the owner told you to in this move.
5. Add a row to `docs/DEPLOY_LOG.md` for every Cloud action, in the same last commit.
