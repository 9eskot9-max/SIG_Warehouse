# Operations Workbench

The Workbench projects stage work from existing evidence. It does not create a
second task ledger or mass-create native ToDos. Matching evidence closes the
matching stage task; a delay marks that same task for review. PMs and Coordinators
can close a cycle with a reason and recorded actor/time. Put that action on the
first normal task row for the cycle, or its Open cycles row when no task is
projected; do not create a separate closure-only row.

The Workbench's **Delivery stages** strip summarizes the signed-in user's
assigned Operations scope. The linked **Site Cycles** page (`/app/site-cycles`)
is a different view: it lists every open cycle across project scopes that the
signed-in user may read under normal Frappe permissions. It does not apply the
Workbench's employee roster filter. The page retains evidence history in the
selected-cycle panel, and its Excel export contains the same all-project cycle
pool plus the projected stage tasks. **Project Progress** remains the separate
evidence register and is not repurposed by this page.

Task owner labels use the approved short names (Sohil, Raheem, Gulzar, Arshad,
Imran, Waleed, Obed, Ramzan, Tahir). A list such as `Sohil / Raheem` names the
people responsible for that task category; the page does not add per-cycle ERP
assignments. The page canvas is neutral, with muted stage-specific accents.

## Stage model

| Stage | Meaning in the Workbench |
|---|---|
| 1 - Initial | Scope and Mapping/BOQ. Manual Design, Survey, Access, and work-order request stay procedure-only. |
| 2 - Plan | TCN, MIR, and Visit evidence. TCN/MIR belong to the Coordinator queue; Visit belongs to the PM queue. |
| 3 - Handover | After TCN + MIR + completed Visit, Tags and Photos are parallel Coordinator work. **As-Built Operational (Step 6c)** is separate parallel Warehouse work when a submitted site DN exists. Handover documents are independent evidence branches. |
| 4 - Invoicing | Applicable GCL/FIS/MGCL handover evidence advances the cycle here. The **As-Built BOQ file** remains a separate PM task in this stage. ERP invoice-sheet processing stays in ERPNext. |

`5 - Closed` is the terminal cycle state, not an active stage and not a stage-strip card. As-Built evidence never closes a site cycle. `Review due` is the status of the existing overdue task, not a stage.

The As-Built Operational task is read-only. One matching submitted site DN line
with `Stock Entry Detail.custom_return_closed = 1` closes it, even if another DN
for the site is still open. Zero returned quantity is not closure evidence.
This is distinct from the PM-owned As-Built BOQ file closed by
`ASBUILT_BOQ_GENERATED`.

## Access boundary

The cycle pages show the explicit As-Built Operational Open/Closed status to
anyone who can already see that cycle. The server reads only the status flag for
submitted outbound DN lines matching site keys from that user's permission-
visible, routed cycles; it does not grant Stock Entry read access or expose the
Stock Entry contents. DN source names are included in Excel only when a
permission-filtered Stock Entry list returns those records and the user already
has read access at the flag field's permlevel.
If the narrow status read fails, the pages say the status is unavailable and
the workbook marks the incomplete coverage instead of treating it as open or
closed. The Site Cycles Page declares the same four audience roles as the
Operations Workbench; it adds no DocType permission, Role Profile, or user role.
Live Page-role and linked-record access still require the pre/post-deployment
permission comparison and persona acceptance checks.

The existing Page role list also excludes the current Ramzan account, and it
does not have SIG Site Cycle read access. The Workbench does not grant those
permissions. Coordinator, Warehouse-user, and Arabic-session acceptance must be
recorded separately; a permission/configuration read is not user acceptance.

## Current coverage boundary

The current projection aligns the Workbench with the four ERP stages: Initial,
Plan, Handover, and Invoicing. Applicable HO evidence advances the cycle to
`4 - Invoicing`; it does not close the cycle. The task projection is
still partial against the white-paper catalog. Mapping/BOQ, RFI, Warranty,
handover-document applicability, and ERP invoice-sheet exceptions still need
their authoritative source contracts and task-opening rules confirmed.
