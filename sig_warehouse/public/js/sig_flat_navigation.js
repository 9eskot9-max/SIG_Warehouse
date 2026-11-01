// Replace the module link list only while a SIG landing page is open.
(() => {
    const pages = ['sig-hub', 'operations-workbench', 'finance-workbench', 'hr-workbench', 'warehouse-workspace', 'pc-invoice-review', 'pc-transaction-status'];
    const destinations = [
        ['Operations', 'operations-workbench', '🏗️'],
        ['Finance', 'finance-workbench', '💵'],
        ['HR', 'hr-workbench', '👥'],
        ['Warehouse', 'warehouse-workspace', '📦'],
        ['Petty Cash', 'pc-invoice-review', '👛']
    ];
    let permitted = null;
    let request = null;

    function activePage() {
        const parts = (frappe.get_route() || []).map((part) => String(part).toLowerCase());
        return pages.find((name) => parts.includes(name)) || null;
    }
    function loadDestinations() {
        if (!request) {
            request = frappe.call({ method: 'sig_warehouse.sig_warehouse.hub.get_cards' })
                .then((response) => {
                    permitted = ((response && response.message) || []).flatMap((g) => g.cards || []);
                    return permitted;
                }).catch(() => { request = null; return null; });
        }
        return request;
    }
    function refresh() {
        const current = activePage();
        $('body').removeClass('sig-flat-navigation');
        $('.sig-flat-links').remove();
        if (!current) return;
        loadDestinations().then((cards) => {
            if (!cards || activePage() !== current) return;
            const container = $('.body-sidebar-top').first();
            if (!container.length) return;
            container.find('.sig-flat-links').remove();
            const nav = $('<nav class="sig-flat-links" aria-label="SIG"></nav>').appendTo(container);
            function add(label, route, isCurrent, icon) {
                const button = $('<button type="button" class="sig-flat-link"></button>')
                    .attr({ 'aria-label': __(label), title: __(label) })
                    .text(icon).appendTo(nav);
                if (isCurrent) button.attr('aria-current', 'page');
                button.on('click', () => frappe.set_route(route));
            }
            add('My Page', ['sig-hub'], current === 'sig-hub', '🏠');
            destinations.forEach(([label, name, icon]) => {
                const entry = cards.find((item) => item.route && item.route[0] === name);
                if (entry) add(label, entry.route, current === name || (name === 'pc-invoice-review' && current === 'pc-transaction-status'), icon);
            });
            if ((frappe.user_roles || []).includes('System Manager')) {
                add('Setup', ['setup', 'home'], false, '⚙️');
            }
            $('body').addClass('sig-flat-navigation');
        });
    }
    frappe.ready(() => {
        frappe.router.on('change', () => {
            refresh();
            setTimeout(refresh, 250);
        });
        refresh();
    });
})();
