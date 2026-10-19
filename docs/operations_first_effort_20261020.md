# Operations evidence repair — 20 October 2026

## Scope

Owner requested an immediate BAS/visit repair, with Initial/Mapping development deferred to 20 November and the tag publisher to 21 October. This app branch stages the ERP portion. No permission, roster, accounting, stock or historical cycle reclassification changes are included.

- Replace tuple assignments in the shared evidence-stage body with ordinary assignments. Frappe's Server Script sandbox lacks `_unpack_sequence_`; a real ZRW022 pending-visit retry reproduced that exact failure. The new migration rewrites only the existing embedded body, idempotently, without reconciling historical stages.
- Record a short fixed error-log title, the original exception in the body, and raise failed feed runs so the scheduler cannot label them successful. Continue processing the other pending records after a record failure.
- Add Live load transfer/SIG `120363025557580310@g.us` as `ticpx2`, labelled Capex2 in Site Visits, with Sohil as PM and Capex as its Operations family. Preserve commercial BA/Project identity; the discussion label is not authority to substitute a different BA. Hold known cross-family scope conflicts rather than merging into Incident/Colocation.
- Recognize existing site suffixes such as ZMK549R11 without stripping them to the base site.
- Use the same Start/End visit structure for Capex2. Owner confirmed Before/After posts must not become inferred visits; retrospective visits remain later review.
- Offer System Manager a **dry-run by default**, group-specific recent import to avoid resetting the global Inbox cursor. It uses a 72-hour window plus one day of Start context, stable source message keys and the normal session pipeline. Explicit apply stores messages/sessions only; normal Live posting handles eligible completed visits. No forced posting of old/auto-closed sessions.
- Show Tags as ongoing coordinator work in active Plan/Handover for Capex/Colocation, without waiting for TCN+MIR+Visit. Keep Initial tasks unchanged. Tags evidence, HO/Invoicing or terminal closure suppresses it as appropriate. The tag publisher is not implemented in this release.
- Do not send internal generator/module names as field-feed source metadata. Keep operational attribution and stable keys.

## Live narrow repair already applied

Production remains app `2175bd7`. Only the four unsupported tuple assignments in live `register_evidence_event` were expanded after before-snapshot and exact-source comparison. The replacement is exactly what this branch's migration writes. The live script was read back and matched.

ZRW022's actual 19 October 18:46–18:50 visit posted to `ZRW022|NA|20260727`; sessions_completed moved from 2 to 3. Repeating the normal post command returned `already_posted`. A normal feed run at 20 October 00:20 Riyadh returned OK, zero failures, cursor 33604. Site Visits visibly showed ZRW022 as Posted under the existing `m.waled@sigtele.com` impersonated session. This is not fresh actual-user acceptance.

The branch's Capex2 mapping, parser, Tags and logging changes have **not** been deployed by that live script repair. BAS sources are separate workbook imports, also not proved by an app migration.

## Verification

Local regressions: 7 first-effort tests, 13 session tests, 34 existing Workbench tests PASS. The first-effort test **executes** all principal stage branches under RestrictedPython without an unpack guard; compile-only validation previously missed the production failure. The prepared full writer rewrite is idempotent. No Permissions JSON, Page roles, hooks or fixtures are changed.

Before/after narrow-repair snapshots: 14 Pages, 42 Workspaces, 22 Reports, 36 effective DocTypes, 25 Role Profiles, 55 enabled System Users. Zero additions/removals; raw 590 Custom DocPerm rows and 121 User Permissions unchanged, as were captured standard matrices, field contracts, roles and navigation. These comparisons do not replace persona tests.

| Audience | Narrow repair / staged release acceptance |
|---|---|
| Integration identity `9eskot9@gmail.com` | PASS for actual pending-visit acceptance, repeat protection and normal feed run. New BAS per-person runtime remains NOT TESTED. |
| Coordinator | Existing impersonated Waleed session rendered Site Visits and Posted ZRW022. Fresh direct identity/workflow NOT TESTED. |
| PM | Fresh direct workflow NOT TESTED. |
| Warehouse Ramzan/Tahir | Fresh workflow NOT TESTED; no stock/return command or permission changed. |
| Finance User/Manager, Operations Admin Hamid, HR, Employee/viewers | Captured access configuration unchanged; fresh basic access NOT TESTED. Financial/HR/employee workflows outside this behavior change; do not claim their acceptance. |

## Deferred / next release

1. Deploy this app branch through the permission guide, including source-writer review and fresh persona checks. Run Capex2 import in preview first; the current recent source contains media/Before/After and unpaired Ends, so no completed visits may be force-created.
2. Import corrected BAS EvidenceCore/EvErpSend into actual RV80 and SIGPC workbooks, compile and verify a real authorized TCN: proposed visit date in the TCN marker, actual recorded time, correct operator/machine/version and optional plan/stream data.
3. Tag publisher on 21 October. Initial/Mapping adoption and development on 20 November.
4. Prepare As-Built Operational backlog baseline and dispatch-driven reopening/10-day closure. Do not rewrite Warehouse return flags merely to clear Operations. The existing per-DN policy remains independent.
5. Complete invoice → Site/Cycle linkage/closure using the actual ERP invoice BAS/API; resolve cross-family identity candidates separately. No accounting submit/cancel or retrospective visit publication in this release.
