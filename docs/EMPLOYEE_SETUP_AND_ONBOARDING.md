# Employee setup and WhatsApp onboarding

This note summarizes the source implementation and rollout boundary. The detailed record ownership, privacy rules, Faizan trial case and open requirements are in [the HR automation master](../ERPNext/Automation%20DB/MASTER-HR-AUTOMATION.md).

## Custom Setup model

`Custom Setup` is an ERP navigation hub. It links:

- Restricted **Candidate Intake** for a pre-employee WhatsApp request and HR review.
- Native **Employee** records and existing onboarding readiness checks.
- **SIG Employee Project Assignment** for effective-dated employee/project roles.
- **Workbook Setup** (`SIG Excel Setup`) for RV80/SIGPC integration data.

The workbook `teams` data is only the Field Planner leader roster. It is not project membership. Employee↔Project relationships live in ERP rows, with date periods, role, source, approval, and audit history. An active Team Leader is unique per Project; overlapping assignments for the same employee, project and role are rejected. End old assignments instead of deleting them.

## Candidate process

1. HR enters the candidate name, official WhatsApp/mobile, HR-assigned gender, Designation, Department, manager (if applicable), positive proposed salary, currency/pay period, default Company, and joining date when approved. Candidate intake is restricted to HR Manager/System Manager. Company comes from ERP's global default.
2. The system checks phone collisions across Employee, User, Contact, reporter mapping and sender-staging records. Conflicts block outreach. HR confirms a candidate's contact basis and uses the explicit WhatsApp action; it does not send on case creation.
3. The first WhatsApp message asks the person to reply `YES` or `STOP`. After `YES`, the system sends an instruction message and then the `EMP-DATA` template as two separate messages.
4. The template starts with `EMP-DATA`. Every field label is on its own line and its answer is on the line below it. The case ID and all field rows must remain in order. The inbox fetcher accepts inbound one-to-one text and stores only receipt metadata, parsed safe values and outcome, not the original message body.
5. The parser stages allowed values for HR review. ID, date of birth, nationality, IBAN, address and emergency-contact values must stay `USE_SECURE_FORM`; the separate secure-upload channel is not implemented. Accidental sensitive data is quarantined for privacy review. HR enters the first digit of verified ID from secure evidence: `1` maps to Saudi National ID, `2` to Resident/Iqama, other to Compliance Review. This is a category hint only; it does not verify identity or set nationality.
6. HR reviews identity, candidate fields, consent, and phone collisions, then approves. The conversion action creates only the Employee. If HR selected a Project/role/start date, conversion also creates a **Draft** Employee Project Assignment; a Projects Manager must approve it.
7. User account, Role Profile, Salary Structure Assignment, custody ledger, bank details, Contact, Field Reporter Map, dispatch recipient and employee notifications remain separately controlled steps. The proposed salary in intake does not itself post payroll.

### Exact line layout

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

The HR instruction before this template tells the employee to copy it, keep each label/value on separate lines, use `NOT_PROVIDED` when unknown/not applicable, keep `USE_SECURE_FORM` for protected information, and reply `STOP` to end contact.

## Faizan trial boundary

The prior read-only check reported Faizan Rasheed already has Employee `HR-EMP-00067` and a linked User; a sender-staging phone also appears against another Faizan Employee. The intake flow must therefore block a new candidate path and must not create a duplicate Employee or reassign sender receipts. Recheck live records before any action. His precise Capex Project, HR terms, salary basis, verified ID/bank data, and approved project assignment were not established. Use redacted synthetic values for parser/route dry-run; do not contact him or write live records as part of this source development.

## Current state

Candidate Intake, parser/fetcher, project assignment DocType, Custom Setup page and HR Workbench links were deployed on 4 November 2026 in SIG Warehouse commit `7a37c9a`, bench `bench-51251-000027-f1f`; the Cloud site update succeeded and the site is Active. No live route check, migration rehearsal or role/persona acceptance was run; these remain **NOT TESTED**. No Candidate/Employee/User/payroll/account/project-assignment data was changed and no WhatsApp message was sent. Secure upload, payroll assignment, User provisioning, Finance account setup, message/log/retention review, and fresh-session permission checks remain open. Follow the [Final Release Checklist](FINAL_RELEASE_CHECKLIST.md) and permission-regression instructions before claiming release acceptance.
