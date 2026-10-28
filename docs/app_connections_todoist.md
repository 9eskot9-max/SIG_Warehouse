# ERP tasks in Todoist

## Current production setup — 29 October 2026

The `/app/app-connections` page and per-user OAuth connection are deployed on
`neosys.frappe.cloud` in SIG Warehouse commit `d8b5165bad418fd78e4d464cd52afbdd983e44a2`.
ERP user `9eskot9@gmail.com` authorized the existing **SIG ERP Automation for Todoist**
app and selected the **Inbox** project. The Todoist developer page reports one authorized
user. The OAuth scopes are `data:read,task:add`: the app can read projects/tasks and add
tasks; it cannot edit or complete existing Todoist tasks.

The task-delivery implementation in this worktree is **not yet deployed**. Until its
release is complete, connecting the account alone does not forward ERP tasks.

## Task delivery behavior in this change

- Newly inserted ERP `ToDo` records assigned to `9eskot9@gmail.com` create one durable
  `SIG Todoist Outbox` row and are queued for the user's selected project. Other users'
  tasks are not exported. Existing ToDos are not backfilled.
- The ToDo description is converted from HTML to plain text, bounded to 500 characters,
  and redacts credentials, email addresses, long phone/account-like numbers and IBAN-like
  identifiers. Only the ToDo ID and its ERP route are included as the description/link;
  linked-record contents and attachments are not exported.
- The SNB runner sends only two explicit issue categories to ERP: failed `import_erpnext`
  phases and import rows skipped for review. The ERP endpoint accepts only those categories,
  a validated run ID and a bounded skipped-row count from the API identity
  `9eskot9@gmail.com`. It creates an ERP ToDo assigned to that user and an outbox row.
  Tracebacks, bank/beneficiary data, transaction details and report contents are not sent.
- Each outbox row has a unique source key. Delivery runs asynchronously, stores the
  Todoist task ID and status, retries known rate-limit/transient cases, and leaves uncertain
  remote outcomes in **Unknown** for reconciliation instead of blindly replaying them.
  The App Connections page shows the user's latest delivery results.
- Delivery is one way. ERP remains authoritative. Completing, editing or deleting a task
  in Todoist does not change or close its ERP ToDo/issue. No historical task backfill or
  issue auto-closure is performed.

## Access and data boundaries

- The existing App Connections Page keeps its deployed `All` role. Server methods require
  an enabled signed-in System User and return only that user's connection and delivery rows.
- The outbox DocType has no direct role permissions. Internal hooks and background workers
  access it with server-side permission bypass; no user-facing outbox route is added.
- The SNB issue intake additionally requires the exact ERP user `9eskot9@gmail.com` and
  ignores client-supplied task text. The local runner reads existing ERP API credentials
  from the ignored secret file at runtime and never logs them.
- The selected Todoist project is an ERP-side default for task destination, not a restriction
  on what the OAuth grant can access. Disconnecting removes ERP's stored tokens; revoke the
  app separately in Todoist integrations settings to end provider-side access.

## Release and acceptance record

The permission snapshot must include `SIG App Connection`, `SIG Todoist Outbox` and `ToDo`
in both effective and source DocType coverage. The declared permission delta for this
feature is no change to the existing Page or ToDo matrices and a new outbox DocType with no
role grants. Confirm the new DocType installs with an empty permission list; inspect the
new ToDo hook and SNB endpoint as permission writers. Required actual-user acceptance is
the fresh `9eskot9@gmail.com` session opening App Connections and confirming a newly created
ToDo is queued/delivered to Inbox. Do not create production test work without authorization.
Arabic route behavior, ordinary non-target user visibility, retries, timeout reconciliation
and real delivery remain NOT TESTED until evidenced.

The user's live OAuth authorization and project selection are confirmed. The delivery
feature itself remains pending its code deployment and actual-user task-flow acceptance.

Todoist API: [official API v1 documentation](https://developer.todoist.com/api/v1/).
