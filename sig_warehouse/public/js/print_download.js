// Print view: turn the "PDF" button into "Download".
// Stock Frappe opens the generated PDF in a new browser tab (the server sends it inline, so
// Edge/Chrome show their viewer). Here the same endpoint with the same selections (format,
// language, letterhead) is fetched and saved as <document name>.pdf. The Print button is left
// untouched. If anything fails, fall back to Frappe's original behaviour.
(() => {
    const MARK = '__sig_download_patched';

    function build_url(view) {
        const fmt = view.get_print_format ? view.get_print_format() : {};
        if (fmt && fmt.print_format_builder_beta) {
            return '/api/method/frappe.utils.weasyprint.download_pdf?' + new URLSearchParams({
                doctype: view.frm.doc.doctype,
                name: view.frm.doc.name,
                print_format: fmt.name,
                letterhead: view.get_letterhead()
            });
        }
        return frappe.urllib.get_full_url(
            '/api/method/frappe.utils.print_format.download_pdf?' +
            'doctype=' + encodeURIComponent(view.frm.doc.doctype) +
            '&name=' + encodeURIComponent(view.frm.doc.name) +
            '&format=' + encodeURIComponent(view.selected_format()) +
            '&no_letterhead=' + (view.with_letterhead() ? '0' : '1') +
            '&letterhead=' + encodeURIComponent(view.get_letterhead()) +
            '&settings=' + encodeURIComponent(JSON.stringify(view.additional_settings)) +
            (view.lang_code ? '&_lang=' + view.lang_code : '')
        );
    }

    async function download(view) {
        const url = build_url(view);
        try {
            frappe.show_alert({ message: __('Preparing download...'), indicator: 'blue' });
            const res = await fetch(url, { credentials: 'same-origin' });
            const type = res.headers.get('content-type') || '';
            if (!res.ok || type.indexOf('pdf') === -1) throw new Error('HTTP ' + res.status + ' ' + type);
            const blob = await res.blob();
            const a = document.createElement('a');
            const href = URL.createObjectURL(blob);
            a.href = href;
            a.download = file_name(view.frm.doc);
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(href), 60000);
        } catch (e) {
            console.warn('SIG download fell back to browser tab', e);
            if (!window.open(url)) frappe.msgprint(__('Please enable pop-ups'));
        }
    }

    // "<document name> . <party name>.pdf", e.g. "SIG-SINV-26-118 . Client Name.pdf".
    // Falls back to the bare document name when the document has no party field.
    const PARTY_FIELDS = ['customer_name', 'supplier_name', 'party_name', 'employee_name',
        'customer', 'supplier', 'party'];
    function clean(s) {
        return String(s || '').replace(/[\\/:*?"<>|\u0000-\u001f]+/g, '-').replace(/\s+/g, ' ')
            .trim().replace(/[. ]+$/, '');
    }
    function file_name(doc) {
        const party = PARTY_FIELDS.map(f => doc[f]).find(v => v && typeof v === 'string');
        const base = clean(doc.name) + (party ? ' . ' + clean(party) : '');
        return base.slice(0, 150) + '.pdf';
    }

    // Download becomes the single blue (primary) button at the far right; Print stays but turns
    // neutral and sits to its left.
    function relabel() {
        const $actions = $('#page-print .page-actions');
        const label = (b) => $(b).text().trim();
        const $print = $actions.find('button').filter((i, b) => label(b) === 'Print' || label(b) === __('Print')).first();
        let $dl = $actions.find('button').filter((i, b) => ['PDF', 'Download', __('PDF'), __('Download')].includes(label(b))).first();
        if (!$dl.length) return;
        if (label($dl) !== __('Download')) {
            const $s = $dl.find('span').first();
            if ($s.length) $s.text(__('Download')); else $dl.text(__('Download'));
        }
        $dl.removeClass('btn-default btn-secondary').addClass('btn-primary');
        if ($print.length && !$print.is($dl)) {
            $print.removeClass('btn-primary primary-action').addClass('btn-default');
            if ($dl.prev()[0] !== $print[0] || $dl.parent()[0] !== $print.parent()[0]) $print.after($dl);
        }
    }

    function patch() {
        const cls = frappe.ui.form && frappe.ui.form.PrintView;
        if (!cls) return false;
        if (!cls.prototype[MARK]) {
            cls.prototype.render_pdf = function () { download(this); };
            cls.prototype[MARK] = true;
        }
        relabel();
        return true;
    }

    function on_route() {
        const route = frappe.get_route() || [];
        if (route[0] !== 'print') return;
        let tries = 0;
        const t = setInterval(() => {
            tries += 1;
            if ((patch() && $('#page-print .page-actions button').length) || tries > 50) clearInterval(t);
        }, 200);
    }

    $(document).on('page-change', on_route);
    $(on_route);
})();
