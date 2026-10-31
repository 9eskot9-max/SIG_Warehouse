// SIG Hub: one front door to every SIG interface the signed-in user may open.
frappe.pages['sig-hub'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: '', single_column: true });
    $(wrapper).find('.page-head').hide();
    const root = $('<main class="sig-hub"></main>').appendTo(page.main);
    root.append(`<header class="sig-hub-head"><div class="sig-hub-kicker">SIG</div>
        <h1>${__('SIG hub')}</h1>
        <p>${__('Every SIG workbench you can open, in one place. Each opens the same ERP records and permissions as before.')}</p></header>`);
    const body = $('<div class="sig-hub-body"></div>').appendTo(root);
    body.text(__('Loading...'));
    frappe.call({ method: 'sig_warehouse.sig_warehouse.hub.get_cards' }).then((r) => {
        body.empty();
        const groups = (r && r.message) || [];
        if (!groups.length) {
            body.append(`<p class="sig-hub-empty">${__('No SIG interface is available for your roles. Ask an administrator for access.')}</p>`);
            return;
        }
        groups.forEach((g) => {
            const section = $(`<section class="sig-hub-section"><h2></h2><div class="sig-hub-grid"></div></section>`).appendTo(body);
            section.find('h2').text(__(g.group));
            g.cards.forEach((c) => {
                const card = $(`<a class="sig-hub-card" href="#"><strong></strong><span></span></a>`).appendTo(section.find('.sig-hub-grid'));
                card.find('strong').text(__(c.label));
                card.find('span').text(__(c.description));
                card.on('click', (e) => { e.preventDefault(); frappe.set_route(c.route); });
            });
        });
    });
};
