# App Connections: Todoist

Local development only. Page: `/app/app-connections`, owned by SIG Operations.
It connects each authenticated System User through Todoist OAuth and lets them choose
a project. It does not yet synchronize ToDos or Operations stage work.

## Current OAuth setup state — 2026-10-28

- The Todoist developer app **SIG ERP Automation for Todoist** exists under the
  `9eskot9` Todoist account. Its service URL and the HTTPS ERP callback below are
  configured in Todoist. Todoist reports zero authorized users; OAuth consent has
  not been granted.
- `/app/app-connections` was checked on production and returns **Page app-connections
  not found**. The page, DocType and backend are local only; there are no production
  Todoist credentials or connection records configured.
- The OAuth client secret appeared in the browser accessibility output during setup.
  Before entering any credential into ERP, the account owner must reset the secret
  in Todoist and use only the new secret. Do not copy the previously displayed value.
  The reset is an owner handoff because it changes an authentication credential.
- The local authorization request is limited to `data:read,task:add`. Before OAuth
  consent, present those scopes and the specific account access to the user. Do not
  authorize until the app is deployed, its replacement secret is safely configured,
  and the consent request is reviewed.

## Setup for a later release

1. Keep the existing Todoist app registration, confirm the callback and minimum scopes,
   and use the freshly rotated secret. Do not create a duplicate app registration.
2. Register the exact HTTPS callback
   `https://neosys.frappe.cloud/api/method/sig_warehouse.sig_operations.app_connections.callback`.
3. Set `todoist_client_id` and `todoist_client_secret` in Frappe site configuration
   using the hosting platform's secret-management mechanism. Never commit either value.
   Ensure Frappe's configured public host resolves to the registered HTTPS site.
4. Migrate the app to install the Page and SIG App Connection DocType. The new DocType
   has no directly granted roles; server methods identify the current System User and
   access only that user's record. Frappe Password fields protect tokens at rest.
5. Complete the permission regression gate and actual-user acceptance before release.
   New Page audience: authenticated System Users (Page role All; endpoints reject
   guests and Website Users). No existing permissions or workspaces are changed.
   Baseline, migration repeatability, role/linked workflow, OAuth callback, token
   refresh, disconnect and Arabic acceptance: NOT TESTED against a Frappe site.

The local OAuth request uses the narrower `data:read,task:add` scopes: project
listing needs read access and the planned SNB error notification needs task creation.
It does not request full `data:read_write` access. Selecting a project is an ERP-side
preference, not a Todoist-enforced restriction. Disconnect deletes the locally stored
credentials; users should also revoke ERP's access from Todoist's integrations settings
if they want provider-side revocation.

Task synchronization must be designed and implemented separately: bind ERP and
Todoist IDs, retry safely, account for Todoist's one-assignee rule, and preserve
evidence-based closure of Operations stage tasks. A connected account alone does
not create or synchronize tasks.

## Integration error routing requested 28 October 2026

**Status: design only; not deployed or active.** The owner wants selected ERP
integration failures to appear as Todoist tasks in the account connected by ERP
user `9eskot9@gmail.com`. Production read-back did not find `SIG App Connection`.
The local connection page has no task writer or error-routing implementation.
The owner selected **SNB-to-ERP automation errors** as the first category; do not
route every Error Log or historical error automatically.

The existing `run_snb_agent.mjs` records `import_erpnext` phase failures and
`erp_skipped` counts in the local agent run report. A skipped count can coexist
with an otherwise successful phase. The local pure adapter
`ERPNext/scripts/snb/todoist_issue_candidates.mjs` derives sanitized candidates
for these two conditions and ignores dry-run and plan-only reports; its three
local checks pass. Its hash deduplicates the same category within the same run,
not the same transaction across different runs. It is not wired to the runner,
ERP, an outbox, or Todoist. Transaction-level deduplication needs the SNB row's
stable idempotency key and reconciliation against the existing unresolved queue.

1. Install the connection page and DocType through the normal release and access
   gate. Register a Todoist OAuth application and configure its credentials in
   protected site configuration. The owner signs in to ERP as the intended
   System User, authorizes their own Todoist account and selects the destination
   project. Do not store a personal token or OAuth secret in source control.
2. Add a durable ERP integration-issue record with a stable source/event key,
   category, occurrence count, last-seen time, owner, status, Todoist task ID,
   last delivery result and retry/review state. The ERP issue is authoritative;
   selecting a Todoist project does not change source-system permissions.
3. Register explicit adapters for the selected integration failures. Create or
   update one issue per stable key, and send only a short sanitized summary and
   an ERP link. Do not send tracebacks, credentials, customer data, bank data,
   invoice content or private attachment URLs to Todoist.
4. Use an asynchronous, idempotent outbox. Persist the Todoist task ID and remote
   result; repeated errors update the existing issue. Treat timeouts after a
   possible remote write as **unknown** and reconcile before retrying, rather
   than silently creating a duplicate. Surface failed or disconnected delivery
   in ERP. No historical backfill or automatic closure is implied.
5. Define access, allowed categories, ownership and resolution behavior in ERP;
   closing a Todoist task must not silently mark a financial or operational
   source event resolved. Verify the actual ERP user and Todoist account,
   OAuth lifecycle, project selection, retry and role boundaries before use.

Todoist's current API uses `/api/v1/tasks`; see the
[Todoist API documentation](https://developer.todoist.com/api/v1/).
