"""Refresh the SIG Letter format for the reminder masthead and seed its template."""

from sig_warehouse.sig_warehouse.patches.v1_0.install_sig_letters import _install_print_format, _seed_templates


def execute():
    _seed_templates()
    _install_print_format()
