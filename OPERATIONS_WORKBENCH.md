# Operations Workbench

The Workbench projects stage work from existing evidence. It does not create a
second task ledger or mass-create native ToDos. Matching evidence closes the
matching stage task; a delay marks that same task for review. Site-cycle closure
is a separate PM/Coordinator action with a reason and recorded actor/time.

## Stage model

| Stage | Meaning in the Workbench |
|---|---|
| Scope & readiness | Current scope and prerequisites; manual Design, Survey, Access, and work-order request stay procedure-only. |
| Preparation | TCN, MIR, and Visit evidence. TCN/MIR belong to the Coordinator queue; Visit belongs to the PM queue. |
| Handover | After TCN + MIR + completed Visit, Tags and Photos are parallel Coordinator work. **As-Built Operational (Step 6c)** is separate parallel Warehouse work when a submitted site DN exists. The **As-Built BOQ file** is a separate PM task. |
| Completion documents | Independent evidence branches; only tasks with a verified source contract are projected. |
| Invoicing | Any applicable GCL/FIS/MGCL evidence starts this summary stage. A still-pending As-Built BOQ file follows the cycle here. Routine invoicing remains in ERP's invoice-sheet workflow. |
| Cycle closure | Explicit cycle-close action; As-Built evidence never closes a site cycle. |

The As-Built Operational task is read-only. One matching submitted site DN line
with `Stock Entry Detail.custom_return_closed = 1` closes it, even if another DN
for the site is still open. Zero returned quantity is not closure evidence.
This is distinct from the PM-owned As-Built BOQ file closed by
`ASBUILT_BOQ_GENERATED`.

## Access boundary

The current live field `custom_return_closed` is at Stock Entry permlevel 1.
The Workbench and the As-Built read model require both Stock Entry read access
and read access at that field's permlevel before returning its value. The
current Warehouse Manager path has the necessary existing read access. PM and
Coordinator Stock Viewer access does not include the level-1 field, so their
Workbench shows that Warehouse status is restricted instead of inferring
closure. No Page role, DocType permission, Role Profile, or user role is changed
by this release.

The existing Page role list also excludes the current Ramzan account, and it
does not have SIG Site Cycle read access. The Workbench does not grant those
permissions. Coordinator, Warehouse-user, and Arabic-session acceptance must be
recorded separately; a permission/configuration read is not user acceptance.

## Current coverage boundary

This update wires As-Built Operational into the existing task projection and
renames the HO-triggered summary to Invoicing. It does not claim full white
paper task coverage. Mapping/BOQ, RFI, Warranty, handover-document applicability,
and ERP invoice-sheet exceptions still need their authoritative source contracts
and task-opening rules confirmed before implementation.
