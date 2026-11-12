// Keep the five existing SIG apps in Frappe's icon dock as the main navigation.
// On SIG landing/workbench pages, remove the extra workspace-link sidebar.
(() => {
    const pages = [
        'sig-hub',
        'operations-workbench',
        'finance-workbench',
        'hr-workbench',
        'warehouse-workspace',
        'snb-movement-router',
        'pc-invoice-review',
        'pc-transaction-status'
    ];
    const logoUrl = '/assets/sig_warehouse/images/sig-mark.png';

    function applyBrand() {
        if (!document.body) return;
        document.body.classList.add('sig-logo-only');
        const logo = document.querySelector('.shell-header .header-logo img');
        if (logo && !logo.getAttribute('src')?.endsWith('/sig-mark.png')) {
            logo.setAttribute('src', logoUrl);
            logo.setAttribute('alt', 'SIG');
        }
        const header = document.querySelector('a.shell-header');
        if (header) header.setAttribute('aria-label', 'SIG');
    }

    function applyPageNavigation() {
        if (!document.body) return;
        const route = frappe.get_route() || [];
        const active = route.some((part) => pages.includes(String(part).toLowerCase()));
        document.body.classList.toggle('sig-flat-navigation', active);
    }

    function refresh() {
        applyBrand();
        applyPageNavigation();
    }

    // App include scripts run as soon as Desk loads on v16; `frappe.ready` is
    // not available here. The router event handles later SPA navigation.
    frappe.router.on('change', () => {
        refresh();
        setTimeout(refresh, 250);
    });
    refresh();
    setTimeout(refresh, 250);

    // The shell header can be re-rendered after an app/route switch.
    new MutationObserver(applyBrand).observe(document.documentElement, {
        childList: true,
        subtree: true
    });
})();
