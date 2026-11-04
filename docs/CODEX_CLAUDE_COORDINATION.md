# Working together: Codex, Claude and the owner

Purpose: two agents and one owner change the same repository and the same production site. This guide keeps their
work from colliding and keeps a clear record of what is live.

## 0. Active agent (owner decision, 4 November 2026)

The owner currently uses Codex for repository and deployment work; Claude is not in the active rotation. `docs/HANDOFF.md` records the active agent and open work. The owner may reassign the work at any time. The portable version of these rules is `skills/sig-erp-coordination/SKILL.md`.

## 1. Roles

- **Owner** (Mohammed): decides what goes live, merges pull requests, says "deploy", and is the only person who
  schedules a Frappe Cloud site update unless the owner has asked an agent to do it for one named change.
- **Codex** and **Claude**: write code and docs on their own topic branches, open pull requests, and never deploy on
  their own initiative. Each agent starts a session by reading this guide, `docs/DEPLOYMENT_AND_BRANCHES.md` and
  `docs/DEPLOY_LOG.md`.

## 2. Branches

- Production source (what Frappe Cloud builds): `codex/sig-personal-home-v16` today. Plan: rename to `production/v16`.
  Nobody commits to it directly. Changes arrive by merged pull request.
- Codex work: `codex/<topic>`. Claude work: `claude/<topic>`. Owner work: `owner/<topic>` or straight to production
  only for documents the owner has said are the owner's.
- One writer per branch. Two agents never push to the same branch at the same time.
- Do not force-push a branch that has been pushed. Do not rewrite history on production. If a hook asks for a
  rewrite, stop and ask the owner.

## 3. Before you start

1. `git fetch origin` and check the production head: `git log --oneline -5 origin/codex/sig-personal-home-v16`.
2. Read the open pull requests and the last rows of `docs/DEPLOY_LOG.md`.
3. Say in the pull request which files you expect to touch. If another open pull request touches the same files,
   stop and tell the owner.

## 4. While you work

- Keep to one topic per branch. Small commits, each with a clear message.
- `patches.txt` is append-only. Add your line at the end of the section. On a conflict, keep both lines.
  Never edit a patch that has already run on production; add a new patch.
- Any change that adds a DocType, a patch, a dock, a workspace or a fixture needs a migrate, so say so in the pull request.
- Each Frappe Cloud build takes the **branch head**, not a commit you chose. Before asking for a build, list
  the commits since the last deploy: `git log --oneline <last-deployed>..origin/codex/sig-personal-home-v16`.
  Every commit in that list goes live with the build.
- Git identity for agent commits: committer `Claude <noreply@anthropic.com>` (set per repository). Do not change
  the author of existing commits.

## 5. Pull requests

- Title: what changes for the user. Body: files touched, patches added, whether a migrate is needed, and the
  test commands run.
- Agents do not merge their own pull requests. The owner merges.
- Close stale drafts as soon as their content is on production. An open draft tells the next reader that work is pending.

## 6. Deploying (owner says "deploy")

1. Confirm the commit list since the last deploy (section 4) is exactly what the owner expects.
2. Take a backup of the site.
3. Build from the branch: fetch the latest app update, then build with **only** the apps that changed. Do not
   include Frappe or HRMS updates unless the owner asks.
4. Wait until the new bench is **Active**. Do not schedule the site update while the bench is still installing:
   the update picks whichever bench is active at scheduling time.
5. Schedule the site update with backups on. Wait for a terminal result.
6. If the result is Recovered or Failure, read the failing step first (the migrate log). Frappe rolls back on failure.
7. Verify: installed app commit, the site's Active status, and the Desk pages the change touches.
8. Add a row to `docs/DEPLOY_LOG.md` in a pull request, or in a commit on the branch.
9. Tag the deployed commit `live/YYYY-MM-DD-<8 chars>` so the change history on GitHub shows what was live when.

## 7. Failures we have already hit (do not repeat)

- A site update scheduled while the new bench was still installing used the old bench, and migrate failed.
- A DocType without its controller `.py` file fails the migrate with "Module import failed".
- A push rejected by the remote was reported as successful because the command hid the error. Run push without `-q`
  and read the last line.
- A combined "deploy and update" call failed its pre-release checks; build and update separately.
- Frappe Cloud's image registry timed out on one server. Retry after a few minutes.
- Remote history changed while local work was still unpushed. Rebase onto the remote branch; never force.

## 8. When agents disagree

Write the disagreement in the pull request. The owner decides. Until the owner decides, the production branch stays
as it is.
