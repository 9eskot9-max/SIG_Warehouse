# People model cutover review — 5 November 2026

This review supports the People-model release candidate. The source gate is now enabled; production remains inactive until a scoped release. The live access audience has not been tested as affected users, so this is not a claim of verified activation.

## Evidence and scope

- On 5 November, the Cloud dashboard showed `neosys.frappe.cloud` Active. The supported Visit Site handoff opened an authenticated ERP session; the User form showed the `Administrator` record. The current Excel Setup rendered published revision 13.
- The live revision 13 has nine enabled Operations family rows: three each for Capex, Incident and 5G / Colocation. Their Employee IDs match the three existing hardcoded Operations names for each family (Sohail, Ghlzar, Sultan; Raheem, Sohail, Arshad; Imran, Waleed, Obed). No Project replacement rows were present in the Operations-member table. The live gate was off at inspection; this release candidate turns it on in source.
- The nine current Operations members each resolve to an Active Employee with a linked User in the live Employees view. User roles/effective access were not audited, and no representative non-admin task workflow was run.
- The live Planner configuration has six enabled flexible teams and six current leader membership rows. They match the six enabled legacy Planner leaders by Employee ID; two disabled legacy rows are not enabled in the flexible list. All staged leader periods begin 5 November. This is a roster match, not permission/persona acceptance.
- The Employee Project Assignment table displays EPA-00579–00587, all `Cancelled`; there are no active assignments in the displayed result. They are historical mistakes and should remain cancelled. Do not derive exact Employee–Project assignments from the PC work-group values; Operations family work is already represented by its separate team-membership table.
- The live PC-routing editor still displays the Employee routing matrix and reviewer groups. This review did not publish or alter PC routing. The local 66-row employee snapshot and revision-2 routing snapshot are historical only; use fresh live reads for any employee/User/account migration.
- `OPS_ROSTER` remains the effective Operations source when `PEOPLE_MODEL_ACTIVE` is false. `WAREHOUSE_USERS` has a separate early path and requires its own access review.
- Historical revision-12 and Employee inventory snapshots are not used to assert current roles or coverage. The live revision-13 roster was checked; the older snapshots' employee counts and disabled legacy labels are historical context only.

## Material behavior change in this release

The legacy roster differentiates `pm` and `co` for role-specific task audiences. The configured family-team adapter labels all family members as shared Operations members: they can see family tasks regardless of `pm`/`co` role, and a Project exception replaces the entire family team. This follows the owner's direction that a family's Operations team shares its cycle work. It changes application-level task visibility, not native ERP roles or DocType permissions. Cycle evidence and close authorization remain separate.

With the currently matched members, the shared audience specifically adds PM-category task visibility for the former coordinator-only employees and coordinator-category visibility for the former PM-only employees in each family. It does not add a native ERP role or DocType permission. The `WAREHOUSE_USERS` early branch remains a separate hardcoded path even when the feature gate is on; treat Warehouse visibility as a separate migration/acceptance item, not as automatically converted by these nine rows.

The owner also chose that Planner may assign any eligible site within its DC or Incident mode. Project coverage is reference data and must not become a Planner eligibility filter. Flexible-team leader changes and the saved weekly snapshot do not mean that dynamically generated plans are persisted.

## Remaining readiness items

1. Actual-user acceptance for newly shared Operations task queues was not performed at the owner's request. Record affected-user checks as NOT TESTED; do not claim verified access. No native role or DocType permission changes are included.
2. Warehouse stays on the separate hardcoded `WAREHOUSE_USERS` path. Its scope is not changed by the People gate and needs a separate future decision/review.
3. PC inheritance, overrides and reviewer/Finance scope are independent of this gate and remain separate configuration/acceptance work. Do not copy historical routing snapshots back to production.
4. No Project replacement team rows exist. Family defaults apply to all family projects until exceptions are configured; exact employee-to-project assignments must not be inferred from PC-family clues.
5. Nine erroneous Employee Project Assignments EPA-00579–00587 are cancelled and retained. The local controller change ignores Cancelled records during overlap checks while preserving overlap checks for Draft, Active and Ended periods. The native workflow has not been accepted by users.

6. Planner history continuity fix: on the first People-model cutover, the existing leader membership is dated from cutover day even though that leader's earlier visits/manual positions already define the team's last-known location. The local adapter now treats the earliest membership as the legacy team's historical origin only when its Employee ID and team label match the enabled legacy Planner roster. Later leader changes remain date-bounded. This has focused unit coverage; it is not deployed.

Persisted Planner plans and automatic new-PO registration are deferred. Historical evidence is not to be rewritten. No production data or native permissions were changed by this review.
