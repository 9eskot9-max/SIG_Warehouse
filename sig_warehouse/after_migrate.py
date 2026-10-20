"""Post-migrate reconciliation for SIG Warehouse's repeatable site invariants."""


def run():
    from sig_warehouse.sig_warehouse.permissions import (
        reconcile_payment_terms_template_permissions,
    )
    from sig_warehouse.sig_warehouse.return_closure import initialize_return_policy_start

    initialize_return_policy_start()
    reconcile_payment_terms_template_permissions()
