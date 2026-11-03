# Daily no-visit WhatsApp message

Send-only. Each evening, field staff with no visit recorded today get one personal WhatsApp asking for the site and activity, or the reason. Replies are read by the coordinator; AI reading is a later phase. Nothing here writes a visit, session or business record.

**Who:** Active Employees with a phone who had a field visit or session in the last N days (default 14), plus anyone in "Also message". Skipped: "Never message", approved leave, holidays, anyone with a visit, session or WhatsApp field report today, anyone already messaged today.

**When:** the hourly scheduler job `sig_warehouse.sig_operations.no_visit_nudge.run_scheduled` sends after the configured hour (default 19:00 Riyadh) until 23:59. One message per person per day and mode, tracked in `SIG No Visit Nudge`; every send also lands in `Maytapi Message Log`.

**Controls (SIG Field Ops Settings, section "No-visit message"):** mode Off (default) / Test (all messages go to the Maytapi test number, prefixed with the person's name) / Live; send hour; look-back days; include and exclude lists. The form has "Preview no-visit message" and "Send test to test number" buttons (System Manager or Operations Manager).

**Rollout:** Preview, read the list with the coordinator, run a Test, then switch mode to Live. Maytapi `test_mode` still redirects everything to the test number.
