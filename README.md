# SIG Warehouse

SIG Warehouse is the ERPNext app for Warehouse, Operations, Finance, HR and related workbenches. It owns its app code, pages, doctypes, patches and hooks; ERP records and live configuration remain in the ERP site.

## Current release

The production site and installed app revisions are recorded in [MASTER.md](MASTER.md) and [Deployment and branches](docs/DEPLOYMENT_AND_BRANCHES.md). GitHub branch contents are not proof of a live deployment. Verify the exact bench and installed hashes in Frappe Cloud before a release.

## Start here

- [ERP integration master](docs/MASTER-ERP-INTEGRATION.md): current system map and operating boundaries.
- [Final release checklist](docs/FINAL_RELEASE_CHECKLIST.md): permission, migration and real-user acceptance gate.
- [Deployment and branches](docs/DEPLOYMENT_AND_BRANCHES.md): installed app refs and release sequence.
- [Deployment runbook](scripts/deploy/README.md): how Frappe Cloud builds and updates this app.
- [Operations Workbench](OPERATIONS_WORKBENCH.md): current page behavior and access boundaries.

## Deploying

A push to GitHub is not a deployment. Frappe Cloud builds the configured app branches, then the site update runs migrations. Follow the deployment runbook and final release checklist. This repository does not store Cloud API secrets or site backups.
