# Field Planner weekly comments — local implementation

Status: developed locally; not deployed or accepted by actual users. This is separate from the older `SIG PM Weekly Review` job and its three outgoing messages. Nothing sends WhatsApp messages or changes that job's settings.

- The Planner shows three fields for the signed-in employee: last week summary, this week plan, and comment on the ERP plan.
- A new period starts Sunday at 19:00 Asia/Riyadh. Periods are computed server-side, independently of the browser's time zone. Prior saved periods remain in the employee's history; no records are deleted. The page warns rather than discarding unsaved text at the cutoff.
- Each record is bound to the unique active Employee linked to the authenticated User. The endpoint requires the existing Projects Manager or System Manager role, Planner access and Employee read access. Employees cannot choose another employee in the request; an administrator can read records through the restricted DocType. Confirm the actual PMs hold the required roles before release; no role is granted here. Concurrent saves use a lock and a modified-time check; a request from an expired period is rejected.
- Long cycle storage names are retained in links and identifiers, while the Planner's visible scope labels and map tooltips show the PO and date. DC and Incident planning logic is unchanged.
- The table and service need a normal app migration. No Planner role, Employee permission, User Permission or role profile is changed here. Verify actual PM identities, Employee-link visibility and read/write boundaries in fresh sessions after an owner-authorized deployment. Check other Planner audiences and route rendering; record acceptance as PASS / FAIL / NOT TESTED.
- The new comments are not automatically submitted to PMs' managers, sent by WhatsApp, used to change the plan, or converted into site decisions. The user has not specified a manager review screen or notification workflow.
