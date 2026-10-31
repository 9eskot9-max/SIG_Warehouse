"""Make a RESTORED COPY of production safe to run. Never run this on production.

A restored backup carries live credentials, queued emails and a live scheduler. Left alone, the
copy could send real WhatsApp messages, push real tasks to Todoist, call the AI providers or
submit real invoices to ZATCA. This script switches all of that off.

How to run (on the TRIAL site only, as Administrator): open Desk -> System Console (Python),
paste this whole file, set TRIAL_SITE below to the trial site's exact name, run it once with
APPLY = 0 (report only), read the report, then run again with APPLY = 1.

What it does when APPLY = 1:
  * turns the scheduler off (and pauses it in the site config);
  * deletes every stored secret (Password fields: WhatsApp/Maytapi, Todoist, OpenAI/Mistral,
    email accounts, ZATCA credentials, users' API secrets) but keeps users' login passwords;
  * disables email accounts, empties the unsent email queue, disables Webhooks,
    Notifications, Auto Email Reports and Email Digests;
  * turns ZATCA off for every Company (switch it back on only after onboarding the trial to the
    ZATCA sandbox/simulation environment, never with production credentials).
It does NOT touch business records. It is not undoable on the trial site: re-add secrets by hand
if a test needs one, using trial or sandbox credentials only.
"""
import frappe

TRIAL_SITE = ""  # <- type the trial site's exact name, e.g. "sig-v16-trial.frappe.cloud"
APPLY = 0        # 0 = report only, 1 = apply
PRODUCTION_SITES = {"neosys.frappe.cloud"}

site = frappe.local.site
if site in PRODUCTION_SITES:
    raise Exception(f"REFUSING to run on {site}: this is a production site.")
if TRIAL_SITE != site:
    raise Exception(f"Set TRIAL_SITE = {site!r} to confirm this is the trial copy.")

print(f"Site: {site}   mode: {'APPLY' if APPLY else 'REPORT ONLY'}")

KEEP = "not (`doctype` = 'User' and `fieldname` = 'password')"  # keep login passwords
secrets = frappe.db.sql(f"select `doctype`, `fieldname`, count(*) from `__Auth` where {KEEP} group by 1, 2", as_list=True)
print(f"\nStored secrets to delete: {sum(r[2] for r in secrets)}")
for doctype, fieldname, count in secrets:
    print(f"  {doctype}.{fieldname}: {count}")

for table, sets, where, label in [
    ("Email Account", "`enable_incoming` = 0, `enable_outgoing` = 0", "`enable_incoming` = 1 or `enable_outgoing` = 1", "email accounts"),
    ("Email Queue", "`status` = 'Error'", "`status` in ('Not Sent', 'Sending', 'Partially Sent')", "unsent emails"),
    ("Webhook", "`enabled` = 0", "`enabled` = 1", "webhooks"),
    ("Notification", "`enabled` = 0", "`enabled` = 1", "notifications"),
    ("Auto Email Report", "`enabled` = 0", "`enabled` = 1", "auto email reports"),
    ("Email Digest", "`enabled` = 0", "`enabled` = 1", "email digests"),
]:
    n = frappe.db.sql(f"select count(*) from `tab{table}` where {where}")[0][0]
    print(f"{label}: {n} to switch off")
    if APPLY and n:
        frappe.db.sql(f"update `tab{table}` set {sets} where {where}")

zatca_on = 0
if frappe.db.has_column("Company", "custom_enable_zatca_e_invoicing"):
    zatca_on = frappe.db.sql("select count(*) from `tabCompany` where `custom_enable_zatca_e_invoicing` = 1")[0][0]
    print(f"companies with ZATCA on: {zatca_on} to switch off")
    if APPLY and zatca_on:
        frappe.db.sql("update `tabCompany` set `custom_enable_zatca_e_invoicing` = 0")

scheduler_on = frappe.utils.cint(frappe.db.get_single_value("System Settings", "enable_scheduler"))
print(f"scheduler enabled: {scheduler_on}")

if APPLY:
    frappe.db.sql(f"delete from `__Auth` where {KEEP}")
    try:
        from frappe.utils.scheduler import disable_scheduler

        disable_scheduler()
    except Exception as exc:  # report, do not hide
        print("!! could not disable scheduler via System Settings:", exc)
    try:
        from frappe.installer import update_site_config

        update_site_config("pause_scheduler", 1)
    except Exception as exc:
        print("!! could not write pause_scheduler to site config (set it in Frappe Cloud's Site Config):", exc)
    frappe.db.commit()
    left = frappe.db.sql(f"select count(*) from `__Auth` where {KEEP}")[0][0]
    print(f"\nDONE. Remaining non-login secrets: {left}. Scheduler enabled: "
          f"{frappe.utils.cint(frappe.db.get_single_value('System Settings', 'enable_scheduler'))}")
    print("Next: also set pause_scheduler = 1 in Frappe Cloud's Site Config if the line above says it could not be written.")
else:
    print("\nReport only. Set APPLY = 1 and run again to apply.")
