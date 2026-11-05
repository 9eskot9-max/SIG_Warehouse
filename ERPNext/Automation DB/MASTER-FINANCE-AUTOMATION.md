# SIG Finance Automation — Employee Setup Integration

**People setup — deployed 4 November 2026:** PR #79 adds employee work-group and petty-cash review-group settings to the existing Excel Setup interface. The 58-row matrix, six reviewer rosters and two approved Incident additional-group exceptions were published to `SIG People Routing Setup` revision 1 (`people-setup-1`) on SIG Warehouse `4d39efa`, bench `bench-51251-000030-f1f`. The employee's existing `custom_custody_account` can be displayed where permitted, but the routing setup neither creates, relinks nor reconciles accounts. AM's separate employee-account and bank-beneficiary mappings remain in AM. Finance must continue verifying account, company and beneficiary evidence through existing controls. The route and revision were read back as Administrator; Finance persona and transaction workflows are **NOT TESTED**. No finance or employee records were changed by publishing this config.

**Safety release — 5 November 2026:** PR #81 deployed a read-only freeze for People routing on SIG Warehouse `5104e97`, bench `bench-51251-000031-f1f`. Existing petty-cash routing, permissions, employee/account links and finance records were left unchanged. The deployment permission snapshot showed no additions or removals in captured layers. Finance and non-admin persona workflows and migration repeatability remain **NOT TESTED**; no Finance behavior is accepted by this deployment alone. See [the deploy log](../../docs/DEPLOY_LOG.md).

**Status checked 4 November 2026:** this finance integration note is in the SIG Warehouse GitHub source and is included in deployed source `4d39efa` on active bench `bench-51251-000030-f1f` (site update `0kb4f0p4ru`). Frappe, ERPNext and HRMS were unchanged. Live workflow, migration and Finance persona acceptance are **NOT TESTED**.
## Purpose and control boundary

Finance participates in employee setup through approved financial relationships, not by creating a second employee registry. ERPNext `Employee` is the canonical person record. Candidate Intake stages HR-approved terms and employee-provided non-sensitive details; it is not a payroll, bank, ledger or payment instruction.

No onboarding message or parser may create or submit `Journal Entry`, `Payment Entry`, `Employee Advance`, `Expense Claim`, `Salary Structure Assignment`, Bank Account, or Chart of Accounts records. Finance must review the source evidence and approve each relation or transaction through the owning ERP workflow. Source capture and matching can prepare a proposal or draft only where an existing approved automation expressly permits it.

## Employee-linked finance records

| Concern | Authoritative record | Finance control |
|---|---|---|
| Employee petty-cash/custody ledger | `Employee.custom_custody_account` → ERPNext `Account` | Reuse only the verified linked Account. Finance checks company, account type, currency, group/leaf status, naming policy and existing ledger balance before linking or creating anything. Never choose an Account by similar employee name. |
| Journal Entry employee attribution | Native Journal Entry account lines plus Employee reference where supported by the configured flow | Preserve the approved account and Employee link together. Ambiguous employee/account matches go to review; never create GL rows directly or submit from onboarding. |
| Petty Cash sender / employee mapping | `SIG PC Sender Staging.employee` and the approved PC mapping | Require a unique, reviewed Employee match. A reused phone or duplicate sender row is an exception; do not reassign historical receipts based on a name match. |
| Payroll | Salary Structure Assignment and payroll documents | HR owns approved salary terms and effective dates; Finance/payroll validates the applicable structure and payroll period. Candidate Intake salary is not a payroll record and must not trigger an assignment. |
| Employee bank details / beneficiary | Approved secure evidence and the governed bank/beneficiary master | Do not accept IBAN, account number, ID, OTP or document images in WhatsApp. Secure upload is not implemented in the current onboarding release. Until an approved secure channel is available, Finance/HR handle bank evidence outside Candidate Intake and record no unverified beneficiary link. |
| Advances and expenses | Native Employee Advance and Expense Claim | Use the ERP employee link and normal approval/settlement process. Do not infer an advance, reimbursement or GL posting from an onboarding answer. |
| Employee access | `User`, `Employee.user_id`, Role Profile and User Permissions | Access provisioning is a separate HR/IT change with effective-role checks; finance mappings do not grant ERP roles. |
| Employee ↔ project membership | `SIG Employee Project Assignment` | Projects Manager approval governs membership and dates. A project assignment does not create a cost-centre, ledger, budget or payroll relationship. |

## Onboarding handoff to Finance

1. HR opens Candidate Intake with the person's basic name and verified official WhatsApp number. HR assigns gender, designation, department, manager, default Company and approved employment terms. The employee cannot choose Company or salary.
2. WhatsApp consent and structured `EMP-DATA` replies stage only allowlisted non-sensitive values. Duplicate phones and conflicting Employee/User/Contact/reporter/PC mappings block the case for HR review.
3. HR verifies identity and approves Employee creation. No finance record is created by conversion.
4. If custody or petty-cash use is required, Finance verifies the employee's need and existing Chart of Accounts relationship, then approves/link the correct Account using the supported Employee workflow. If no valid Account exists, Finance decides whether policy permits a new leaf Account and confirms its company, parent, currency, naming and opening/transaction implications first.
5. Payroll, bank beneficiary, employee advance/expense, Petty Cash mapping and project membership proceed as distinct records with their own evidence and owners. Each step records Pending, Done, Exception or Not Applicable and links the resulting ERP document.
6. Before enabling employee finance activity, reconcile the Employee link, Account, cost centre where applicable, verified phone and any downstream mappings. Check duplicates and historical transactions; never replay old receipts to make a new mapping appear complete.

## Status and acceptance

- Candidate Intake, Employee Project Assignment and Custom Setup source is deployed. No Candidate, Employee, User, salary, Account, bank-beneficiary or exact Project-assignment data changed by deployment. The separate People routing configuration was published as revision 1; no WhatsApp message was sent by deployment.
- Secure ID/bank upload, payroll assignment, User provisioning, Finance custody-account workflow, AM account/beneficiary mapping and retention review remain follow-up work, not completed onboarding automation.
- The Administrator route and persisted revision were confirmed; functional route behavior, migration rehearsal, permission snapshots and fresh-session HR/Projects/Finance persona acceptance are **NOT TESTED**. Do not describe those workflows as accepted.
- Faizan Rasheed already has a reported Employee/User and his phone collides with another Faizan sender/employee relationship. Reconcile identity and phone ownership live before creating an intake, sending a message, changing a mapping, or creating any financial relationship. His exact Capex project and approved assignment remain unconfirmed.

See [HR automation master](MASTER-HR-AUTOMATION.md), [ERP integration master](MASTER-ERP-INTEGRATION.md), [Employee Setup design](../../docs/EMPLOYEE_SETUP_AND_ONBOARDING.md), and [release record](../../docs/DEPLOY_LOG.md).
