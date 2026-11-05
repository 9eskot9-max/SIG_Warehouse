# HR automation and employee setup master

**People setup — deployed 4 November 2026:** PR #79 adds People sections to the existing Excel Setup page. The employee work-group and petty-cash routing setup is separately stored in `SIG People Routing Setup`, not in workbook dataset configuration. The existing 58-row routing matrix, six reviewer rosters and two approved Incident additional-group exceptions were published as revision 1 (`people-setup-1`) on `neosys.frappe.cloud`, bench `bench-51251-000030-f1f`, SIG Warehouse `4d39efa`. The route and persisted revision were read back as Administrator. No Employee, User, exact Project assignment, Account, Journal Entry or petty-cash transaction records changed. Functional workflows, migration repeatability and HR/Projects/Finance non-admin acceptance are **NOT TESTED**. The setup does not update AM, create/link custody accounts, provision Users or payroll, or infer a specific Project from an operational group. See `docs/PEOPLE_SETUP_SCOPE.md` and [the deploy log](../../docs/DEPLOY_LOG.md).

**Earlier onboarding deployment — 4 November 2026:** Candidate Intake, Employee Project Assignment, Custom Setup and the HR inbox parser/fetcher were deployed in SIG Warehouse `7a37c9a` on bench `000027`. The current installation is its descendant `4d39efa` on bench `000030`. That earlier release did not run route, migration rehearsal or HR/Projects/Finance persona acceptance. No Candidate, Employee, User, payroll, bank/account or project-assignment data was changed, and no WhatsApp message was sent by deployment.
## 1. Purpose and ownership

ERPNext `Employee` remains the canonical employee record. Do not create a parallel employee registry in Excel or WhatsApp. Custom Setup is a navigation hub for related setup areas; it does not become a single spreadsheet of unrelated configuration.

| Setup concern | Authoritative record / owner | Rule |
|---|---|---|
| Employee identity and HR terms | Employee / HR | HR creates or edits the Employee only after identity and employment approval. Company defaults to the approved default company; employee does not choose it. Gender, designation, department, employment dates, and salary are HR-assigned/approved. |
| Employee ↔ project role | `SIG Employee Project Assignment` / HR and Projects Manager | One effective-dated ERP record per assignment. Project role and period are explicit; active Team Leader is unique per Project; historical assignments are ended, not deleted. |
| Employee onboarding readiness | Existing `SIG Employee Onboarding` / HR | Reuse its Employee link and its existing access, custody, bank, phone/WhatsApp and compliance checks. Do not create a second checklist or provision User/account/ledger merely because a checklist exists. |
| Login account and roles | User, Employee.user_id, Role Profile / HR + IT | Create/link only after approval. Check effective roles and role-profile re-derivation; employee edits may re-enable a linked User, so follow the permission snapshot/change gate. |
| Salary | Salary Structure Assignment and payroll records / HR + Finance | HR approval and effective date are prerequisites. Never infer payroll amount or create assignment from an employee's message. |
| Employee custody ledger | Employee.custom_custody_account → Account / Finance | Reuse the existing linked account where verified. Search the full chart and get Finance approval before a new ledger; never match by similar name alone. See [Finance employee setup](MASTER-FINANCE-AUTOMATION.md). |
| Employee phone mapping | Employee.cell_number / Employee-linked Contact; `SIG Field Reporter Map` as needed / HR + Operations | Normalize and verify the number; ensure it resolves uniquely before using WhatsApp or field feed. Avoid assigning a number to a second employee to fix a match. |
| Workbook and People setup | `SIG Excel Setup` / Operations, HR and Projects | Workbook datasets remain integration configuration; `teams` is the Field Planner leader roster, not project membership. The shared Excel Setup interface also exposes separately stored, permission-checked People records. Operational-group routing is not an exact Project assignment, and the published routing matrix does not replace Employee Project Assignment. |
| Dispatch and notifications | Existing dispatch recipient records and WhatsApp Inbox / Operations | Recipient mappings are independent and explicitly scoped. Sending messages requires approved channel/template, consent, and a deliberate send action. |

## 2. Employee project assignment (source implementation)

`SIG Employee Project Assignment` stores Employee, Project, project role, start/end dates, status, source and approval metadata. It is a SIG HR-owned DocType and the Custom Setup hub links to it. Records are independently permissioned for HR and Projects audiences. The hub is navigation only; it does not grant DocType or linked-record permissions.

Rules in source:

- `Draft → Active` requires Projects Manager or System Manager and captures approver/time. HR Manager can prepare the Draft but cannot approve project membership.
- Only an Active Employee and a non-completed/non-cancelled Project can have an Active assignment.
- End Date cannot precede Start Date. Active assignment has no End Date; Ended assignment gets an end date and remains in immutable history. Unapproved Drafts can be Cancelled.
- Overlapping periods for the same Employee + Project + role are rejected. A Project may have only one active Team Leader; end the former assignment before activating a replacement.
- Active cannot return to Draft, and closed assignment history cannot be edited or deleted.
- Notes are for business references only; the form warns against identity and bank information.

This record is intentionally not a field on Employee: one employee can move between projects, hold multiple roles, and retain assignment history. It is also separate from `SIG Planner Position` (latest travel starting location) and the workbook `teams` roster (planner team leaders).

## 3. WhatsApp preboarding design

### 3.1 HR starts the case

HR prepares a restricted candidate intake with the proposed employee's name, verified official WhatsApp/mobile phone, HR-assigned gender, designation, department, approved manager, and proposed salary with currency and pay period. Company is assigned from the ERP global default. HR may select a Project, role and start date; conversion then creates a **Draft** `SIG Employee Project Assignment` for Projects Manager approval. The proposed salary remains an HR-approved intake value and is not yet a payroll record.

Before contact, HR confirms the phone belongs to the intended person, documents the permitted contact/processing basis, checks there is no existing Employee/Candidate identity conflict, and previews the message. A matching sender number or a WhatsApp reply does not by itself prove identity or consent to create an ERP account.

### 3.2 Employee reply format

The source sends an explanatory WhatsApp message first and waits for `YES` to confirm the number and consent. It then sends the instruction message and template as two separate messages. In the template, `EMP-DATA`, every label and its value are separate lines. The employee replaces the value line directly below each label; they keep the exact order and use `NOT_PROVIDED` or `USE_SECURE_FORM` instead of removing rows. The parser accepts only the fixed labels and order; invalid/duplicate/unknown rows go to correction or HR review.

**Instruction message:**

> Please fill in the next message. Keep EMP-DATA and each field label on its own line, and put your answer on the line directly below that label. Keep the field order. Use NOT_PROVIDED if an item does not apply or you do not know it. Keep USE_SECURE_FORM for private details; HR will provide the secure form when needed. Do not send an ID, IBAN, password, PIN, OTP, bank login, or document photo in WhatsApp. Reply STOP to end messages.

**Template message (sent separately):**

```text
EMP-DATA
Case ID
CI-2026-00001
Full Legal Name (as on ID)
NOT_PROVIDED
Preferred Name
NOT_PROVIDED
Official Mobile Number
NOT_PROVIDED
Email for ERP Contact/Login
NOT_PROVIDED
Date of Birth
USE_SECURE_FORM
Nationality
USE_SECURE_FORM
National ID / Iqama Number
USE_SECURE_FORM
ID Expiry Date
USE_SECURE_FORM
Saudi IBAN (for payroll, if applicable)
USE_SECURE_FORM
Bank Account Holder Name
USE_SECURE_FORM
Current Address (if required by HR)
USE_SECURE_FORM
Emergency Contact Name / Phone / Relationship (if required by HR)
USE_SECURE_FORM
```

Employee replies as fixed label/value lines, for example (fictional data):

```text
EMP-DATA
Case ID
CI-2026-00001
Full Legal Name (as on ID)
Sami Example Ali
Preferred Name
Sami
Official Mobile Number
+966500000000
Email for ERP Contact/Login
sami@example.invalid
Date of Birth
USE_SECURE_FORM
Nationality
USE_SECURE_FORM
National ID / Iqama Number
USE_SECURE_FORM
ID Expiry Date
USE_SECURE_FORM
Saudi IBAN (for payroll, if applicable)
USE_SECURE_FORM
Bank Account Holder Name
USE_SECURE_FORM
Current Address (if required by HR)
USE_SECURE_FORM
Emergency Contact Name / Phone / Relationship (if required by HR)
USE_SECURE_FORM
```

The ID-number prefix convention requested by HR is a *classification hint*: starting digit `1` maps to Saudi National ID and `2` maps to Resident/Iqama. Candidate Intake stores only the first digit entered by HR from reviewed secure ID evidence, then derives the category. `Other` routes to Compliance Review. This does not verify the ID itself or determine nationality; HR compares the secure document and approved source. The full ID number stays out of WhatsApp and the Candidate Intake.

### 3.3 Parser, review and account creation gates

The staged receive path:

1. Reads the Maytapi Inbox sheet and accepts only inbound one-to-one text messages; normalizes sender phone and matches exactly one open case. Ambiguous/unmatched traffic is ignored rather than guessed or linked.
2. Requires `YES` before sending the follow-up template. `STOP` closes the case. It detects `EMP-DATA`, validates exact line order, and stages only allowlisted non-sensitive values.
3. Stores message ID/time/category/result receipts, not the message body. ID, DOB, nationality, IBAN, address and emergency contact accept only `USE_SECURE_FORM`; accidental ID/bank content routes the case to privacy review. Email/phone/name values are held in the HR-only intake record.
4. Checks phone collisions against Employee, User, Contact, reporter maps and sender staging. Collisions block messaging or require HR review; an Employee collision cannot be cleared to permit a second Employee. Never attaches historical receipts based on name similarity.
5. Requires HR to verify identity, select default Company/Department/Designation/manager, confirm gender, and enter positive proposed salary + currency/pay period before approval. This is an HR decision, not employee-provided terms. Approval checks consent, number confirmation, and duplicate status.
6. Creates only an Employee after explicit HR approval. Optional Project/role/date in the case creates a Draft assignment which a Projects Manager must approve. User, Salary Structure Assignment, custody Account, Contact, Field Reporter Map and dispatch recipient remain separate gated records/actions.
7. Runs the inbox fetch hourly. Outbound messages are explicit HR button actions; the first is only a neutral confirmation request. Maytapi message text/ID is checked before the send is recorded, and each message step has a five-minute retry throttle. Provider/log privacy, secure-form delivery, retention, and persona permissions still need review before production.
8. Requires pre/post permission snapshots and fresh-session HR/Projects/Finance acceptance. A successful API or message send is not persona acceptance.

The live parser rejects IBAN/ID through WhatsApp and requests `USE_SECURE_FORM`. The separate secure upload is **not yet implemented**, so protected identity/bank evidence must remain an HR follow-up until an approved channel and its privacy, retention and access audit are in place.

## 4. Faizan Rasheed trial case

Use Faizan as a non-persisting acceptance case to demonstrate the onboarding workflow, not as permission to create a duplicate employee or assign him to an assumed Capex project. Prior read-only reconciliation reported an existing Active Employee (`HR-EMP-00067`) and linked User, and an existing sender staging row for a phone ending in `4408`; the phone also appeared on the separate Faizan Haneef record. The intake duplicate detector should block contact while that Employee collision is unresolved. Recheck facts live before any action. The historical receipts must remain attached to their current staging state unless explicitly reconciled by owner-approved identity evidence.

The prior record review did not establish all mandatory setup facts: the correct Capex Project, approved Designation/Department/manager, salary amount/currency/pay period/effective date, confirmed gender, verified legal ID/type, IBAN/bank evidence, personal email, emergency contact, a unique official phone, compliance validity, approved project role/start date, and HR/Finance approval. Do not guess any missing value. A team-leader designation or Capex role is not a project assignment until a specific Project and dates are chosen and approved.

Trial acceptance should be a redacted form/API dry-run with synthetic IBAN/identity values: verify duplicate detection blocks this case, field parsing and correction states, sender matching, missing-value handling, consent and STOP paths, project-assignment draft and one-active-Team-Leader guard, approval state, history retention, permission denial and no-write paths. Do not send a message or create/update Employee, User, salary, Account or assignment records during the dry-run.

## 5. Release and acceptance status

Candidate Intake, Employee Project Assignment and Custom Setup first deployed in `7a37c9a` on bench `000027`; the current deployed descendant is `4d39efa` on bench `000030`. The People routing revision was separately published as described above. A prior synthetic parser/overlap dry-run is recorded in the PR. No Frappe integration check, migration rehearsal, or actual-user role/persona acceptance was run for these releases. Mark these **NOT TESTED**. No post-deployment permission snapshots were captured. At minimum check System Manager, HR Manager, HR User, Projects Manager and Projects User, plus linked Employee/Project read access, in fresh authenticated sessions before claiming release acceptance.

The Candidate Intake form, explicit WhatsApp confirmation/instruction/template sender, Maytapi inbox fetcher, strict EMP-DATA parser, HR review/approval and Employee conversion are deployed but not accepted. A secure upload form, identity-document review, payroll Salary Structure Assignment, User provisioning, Finance custody-account workflow, contact/mapping workflow, retention settings, and full user-persona validation remain open. See the [concise Employee Setup implementation note](../../docs/EMPLOYEE_SETUP_AND_ONBOARDING.md).


## Employee project and Operations configuration — staging gap, 4 November 2026

**OPEN — not implemented or migrated.** The live Excel Setup **Employee project assignments** table was observed empty. The published People routing revision 1 contains 58 existing employee work-group / petty-cash review rows, six reviewer groups and two approved Incident exceptions; it does not establish each employee's exact ERP Project or complete employee setup. The deployed Operations workbench still uses the code-owned `OPS_ROSTER`, `OPS_OWNER_NAMES`, `WAREHOUSE_USERS` and `WAREHOUSE_OWNER_NAMES` for scope, role and display; its task-audience logic has not been switched to People setup. The seven observed Field Reporter Map rows are existing phone-to-Employee records used by field-feed/site-visit logic. Do not claim the full employee/project migration is complete.

Stage the following work in the existing Excel Setup People interface:

1. Inventory actual employee/project relationships and related settings across current ERP Project/PM assignments, Operations roster and aliases, Field Planner teams, Field Reporter Map, published PC routing/reviewer exceptions, Employee/User/custody links and relevant AM mappings. Record the owning source, identity, scope, dates and consumer; distinguish exact ERP Project from operating family and planner roster. Reconcile duplicates, conflicts, missing dates and phone collisions instead of guessing. Preserve existing records and assignments.
2. Prepare a reviewable per-employee migration manifest with verified Employee IDs, exact Projects where evidenced, operational family/role and display alias, PC review group/exceptions and existing linked records. Keep unknowns explicit; do not infer exact Projects, payroll, account or access grants. Preserve the existing PM/coordinator and Warehouse memberships and their intentional differences from PC reviewer rosters.
3. Develop configuration and migration in the owning app, integrated into the existing People setup. Replace hardcoded Operations routing and display lookups with validated configured records; connect each consumer to its correct source. Preserve existing PC behavior, fallback and exceptions, Field Reporter Map consumers, project- and role-specific semantics, history, authorization and a recovery path. An operational group alone is not an exact Project assignment.
4. Before release, compare old and new effective routing and task audiences for all affected people and scopes, review grants and removals, rehearse migration and repeatability on a recoverable copy, and record HR, Projects, Operations and Finance persona acceptance using the permission regression gate. Record PASS / FAIL / NOT TESTED. Do not treat an Administrator page render or saved configuration as end-to-end acceptance. Missing evidence or unresolved identity/scope must remain review items.

This entry stages future implementation; no employee, project, routing, access or financial record was changed by documenting it.
