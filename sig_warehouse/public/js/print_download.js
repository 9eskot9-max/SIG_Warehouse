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
            a.download = String(view.frm.doc.name).replace(/[\\/:*?"<>|]+/g, '-') + '.pdf';
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(href), 60000);
        } catch (e) {
            console.warn('SIG download fell back to browser tab', e);
            if (!window.open(url)) frappe.msgprint(__('Please enable pop-ups'));
        }
    }

    function relabel() {
        $('#page-print .page-actions button').each(function () {
            const $b = $(this);
            if ($b.text().trim() === 'PDF' || $b.text().trim() === __('PDF')) {
                $b.find('span').first().text(__('Download'));
                if (!$b.find('span').length) $b.text(__('Download'));
            }
        });
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
