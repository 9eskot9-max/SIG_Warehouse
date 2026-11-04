# Handoff baton — Codex and Claude take turns

One agent works on the production branch at a time. The owner can change the holder at any moment.

| Field | Value |
|---|---|
| Baton holder | **Codex** (taken from Claude after the 4 November deploy) |
| Next holder | **Claude** |
| Branch | `codex/sig-personal-home-v16` |
| Head when the baton was handed over | `aa84fd3` (live on `neosys.frappe.cloud`, bench `000026`) |
| Open items for the holder | Whatever the owner asks Codex for next. Do not schedule any Frappe Cloud update unless the owner says so. Benches `000024` and `000025` are unused. |
| Waiting on the owner | Weekly PM check per project family (families, recipients and project mapping). Six legacy Payment Entry drafts. 98 draft petty-cash journals. |

## Rules

1. Read this file first. If the baton is not yours, stop and tell the owner. Do not push.
2. Take the baton by editing this table in your first commit (holder = you). Give it back in your last commit (holder = the other agent, with the new head and open items).
3. One move = one task the owner asked for, finished and pushed. Do not start a second task inside a move.
4. Never deploy, schedule a Frappe Cloud update, or edit the Cloud benches unless the owner told you to in this move.
5. Add a row to `docs/DEPLOY_LOG.md` for every Cloud action, in the same last commit.
