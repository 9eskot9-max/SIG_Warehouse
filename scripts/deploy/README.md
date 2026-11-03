# Frappe Cloud deployment

This folder is the discoverable deployment entry point for SIG Warehouse. Production updates are performed through the Frappe Cloud bench build and site update/migration flow; pushing a GitHub commit does not itself update the site.

Before a release, use [Deployment and branches](../../docs/DEPLOYMENT_AND_BRANCHES.md) to confirm the installed app branch/hash and follow [Final release checklist](../../docs/FINAL_RELEASE_CHECKLIST.md).

Release sequence:

1. Identify exact site, bench, app branch and target revision.
2. Review source, permission writers, migrations and linked-record access.
3. Preserve backup/recovery evidence and complete the permission baseline.
4. Build the bench/app revision in Frappe Cloud.
5. Run site update/migrations and wait for terminal status.
6. Read back installed hashes, Active status and requested routes.
7. Complete fresh-session persona acceptance and record PASS / FAIL / NOT TESTED.

This repository does not currently contain a production deployment script. If a repeatable Press API launcher is added later, it must load credentials from an approved external secret store, accept explicit site/bench/revision targets, default to read-only/preflight behavior, and produce release evidence. Never commit API keys, secrets, site backups or customer/employee data.
