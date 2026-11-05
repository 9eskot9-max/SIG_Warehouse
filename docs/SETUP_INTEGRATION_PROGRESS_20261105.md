# Setup code release — 5 November 2026

Owner confirmed that Planner assigns a team to any eligible site within the selected mode. Planner supports two modes: **DC** and **Incident**. Team-to-Project rows are reference data only and do not restrict site eligibility.

This release is limited to the matching code work: include the selected stable `team_id` in Planner trip responses, clarify the DC label and team coverage meaning in Excel Setup, and keep team coverage in the historical/reference area. The change does not persist a generated plan or add another visibility/editor system. Existing role and roster behavior remains in force.

The owner deferred automatic PO/Project registration to the TAWAL–ERP integration and will review/fill ERP configuration after this code deployment. No PO integration, cycle-link rewrite, employee routing change, roster activation, or business-data write is included here. The People-model gate remains off.

The local Sheet Am Fetch Hub source calls `sig_warehouse.sig_operations.tawal_project_setup.sync_agreement_project`, but that module is absent from the production app source. The deployed Apps Script revision and its call path remain unconfirmed; reconcile that separately with the TAWAL–ERP integration work.

Live setup was previously revision 13, with nine Operations family members and three provisional TAWAL family defaults. Nine completed Projects were classified from unambiguous names; five Mobily/B2S legacy POs remain outside the current family model. Re-read the live setup before ERP configuration. See local `ERPNext/docs/setup_configuration_fill_20261105.md` for the configuration action and recovery references.

## Release acceptance

The change does not introduce permission writers, migration patches, or business data. The mandatory audience and route checks are still required after deployment. Unless individually evidenced in the release record, report the new Desk route rendering and actual-user/persona workflow as **NOT TESTED**; do not treat deployment success as acceptance.
