// Role-aware navigation only. ERPNext documents and reports remain authoritative.
frappe.pages['finance-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Finance'),
        single_column: true
    });
    page.add_inner_button(__('Original Accounting Workspace'), () => {
        window.sessionStorage.setItem('sig_finance_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG Accounting');
    });

    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const direction = language.startsWith('ar') ? 'rtl' : 'ltr';
    const root = $('<main class="sig-finance-home"></main>')
        .attr('dir', direction)
        .attr('lang', language)
        .appendTo(page.main);

    const daily = [
        {title: __('Payment entries'), description: __('Review receipts, supplier payments, and their invoice allocations.'), icon: 'exchange', doctype: 'Payment Entry', route: ['List', 'Payment Entry', 'List']},
        {title: __('Sales invoices'), description: __('Review customer invoices and collection status.'), icon: 'file-text', doctype: 'Sales Invoice', route: ['List', 'Sales Invoice', 'List']},
        {title: __('Purchase invoices'), description: __('Review supplier invoices after the purchasing and receipt handoff.'), icon: 'file-text-o', doctype: 'Purchase Invoice', route: ['List', 'Purchase Invoice', 'List']},
        {title: __('Journal entries'), description: __('Review controlled accounting entries; draft first and submit with authority.'), icon: 'book', doctype: 'Journal Entry', route: ['List', 'Journal Entry', 'List']}
    ];

    const control = [
        {title: __('General Ledger'), description: __('Trace posted balances to their source vouchers.'), doctype: 'GL Entry', report: 'General Ledger', route: ['query-report', 'General Ledger']},
        {title: __('Trial Balance'), description: __('Check debit and credit balances for the selected period.'), doctype: 'GL Entry', report: 'Trial Balance', route: ['query-report', 'Trial Balance']},
        {title: __('Profit and Loss'), description: __('Review income and expense performance.'), doctype: 'GL Entry', report: 'Profit and Loss Statement', route: ['query-report', 'Profit and Loss Statement']},
        {title: __('Balance Sheet'), description: __('Review assets, liabilities, and equity.'), doctype: 'GL Entry', report: 'Balance Sheet', route: ['query-report', 'Balance Sheet']}
    ];

    const collections = [
        {title: __('Sales Register'), doctype: 'Sales Invoice', report: 'Sales Register', route: ['query-report', 'Sales Register']},
        {title: __('Sales Invoice Trends'), doctype: 'Sales Invoice', report: 'Sales Invoice Trends', route: ['query-report', 'Sales Invoice Trends']},
        {title: __('Accounts Receivable'), doctype: 'Sales Invoice', report: 'Accounts Receivable', route: ['query-report', 'Accounts Receivable']}
    ];

    const payables = [
        {title: __('Purchase Register'), doctype: 'Purchase Invoice', report: 'Purchase Register', route: ['query-report', 'Purchase Register']},
        {title: __('Purchase Invoice Trends'), doctype: 'Purchase Invoice', report: 'Purchase Invoice Trends', route: ['query-report', 'Purchase Invoice Trends']},
        {title: __('Accounts Payable'), doctype: 'Purchase Invoice', report: 'Accounts Payable', route: ['query-report', 'Accounts Payable']}
    ];

    const review = [
        {title: __('Draft payments queue'), description: __('Review draft payment entries before approval or posting.'), doctype: 'Payment Entry', report: 'SIG Finance Draft Payments Queue', route: ['query-report', 'SIG Finance Draft Payments Queue']},
        {title: __('Bank transactions'), description: __('Review statement evidence before matching or reconciliation.'), doctype: 'Bank Transaction', route: ['List', 'Bank Transaction', 'List']}
    ];

    const specialist = [
        {title: __('SIG Petty Cash'), description: __('Open the separate evidence, clearance, and finance handoff workspace.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager', 'SIG Finance Viewer', 'SIG PC Clearance'], route: ['Workspaces', 'SIG Petty Cash']},
        {title: __('ZATCA Integrations'), description: __('Review tax-compliance evidence linked to the source invoice.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], route: ['Workspaces', 'ZATCA Integrations']}
    ];

    const references = [
        {title: __('Chart of accounts'), description: __('Reference the account hierarchy; setup remains a controlled finance task.'), doctype: 'Account', route: ['List', 'Account', 'List']},
        {title: __('Cost centers'), description: __('Reference financial responsibility and reporting dimensions.'), doctype: 'Cost Center', route: ['List', 'Cost Center', 'List']}
    ];

    function canOpen(item) {
        if (item.roleAny && !item.roleAny.some((role) => frappe.user.has_role(role))) return false;
        if (!item.doctype) return true;
        if (!frappe.model.can_read(item.doctype)) return false;
        if (!item.report) return true;
        const reportGrants = frappe.boot?.user?.can_get_report;
        if (Array.isArray(reportGrants) && !reportGrants.includes(item.doctype)) return false;
        const reports = frappe.boot?.allowed_reports;
        if (Array.isArray(reports)) {
            return reports.some((report) => (typeof report === 'string' ? report : report.name) === item.report);
        }
        if (reports && typeof reports === 'object') return item.report in reports;
        return false;
    }

    function card(item, compact = false) {
        const icon = item.icon
            ? `<span class="sig-finance-icon" aria-hidden="true"><i class="fa fa-${item.icon}"></i></span>`
            : '';
        const detail = item.description
            ? `<span class="sig-finance-detail">${frappe.utils.escape_html(item.description)}</span>`
            : '';
        return `<button type="button" class="sig-finance-card ${compact ? 'sig-finance-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route))}">
            <span class="sig-finance-card-top">${icon}<i class="fa fa-external-link sig-finance-open" aria-hidden="true"></i></span>
            <span class="sig-finance-card-title">${frappe.utils.escape_html(item.title)}</span>${detail}
        </button>`;
    }

    function section(title, description, items, compact = true) {
        const available = items.filter(canOpen);
        if (!available.length) return '';
        return `<section class="sig-finance-section">
            <div class="sig-finance-section-heading"><h2>${frappe.utils.escape_html(title)}</h2>
                <p>${frappe.utils.escape_html(description)}</p></div>
            <div class="sig-finance-grid ${compact ? 'sig-finance-grid-compact' : ''}">${available.map((item) => card(item, compact)).join('')}</div>
        </section>`;
    }

    root.html(`<header class="sig-finance-header">
            <div><div class="sig-finance-eyebrow">${__('SIG Finance')}</div>
                <h1>${__('Finance workbench')}</h1>
                <p>${__('Daily finance work, backed by ERPNext records and accounting controls.')}</p>
            </div><span class="sig-finance-header-mark" aria-hidden="true"><i class="fa fa-line-chart"></i></span>
        </header>
        ${section(__('Daily finance work'), __('Open the source documents used for customer, supplier, payment, and journal work.'), daily, false)}
        ${section(__('Financial control'), __('Core statements and ledger traceability. Each report keeps its own filters.'), control)}
        ${section(__('Sales and collections'), __('Customer billing and receivable review, including the Tawal customer lane.'), collections)}
        ${section(__('Purchasing and payables'), __('Supplier invoice review after the Purchase Order and receipt handoff.'), payables)}
        ${section(__('Reconciliation and evidence'), __('Review source evidence before matching, approval, or posting.'), review)}
        ${section(__('Specialist finance lanes'), __('Separate controlled workspaces for petty cash and tax-compliance evidence.'), specialist)}
        ${section(__('Reference and setup'), __('Use less-frequent finance masters and reporting references.'), references)}
        <p class="sig-finance-footnote">${__('This page is navigation only. It does not create or post accounting entries; document, workflow, and report permissions remain enforced by ERPNext.')}</p>`);

    root.find('.sig-finance-card').on('click', function () {
        let route;
        try { route = JSON.parse($(this).attr('data-route')); }
        catch (e) { return; }
        if (Array.isArray(route) && route.length) frappe.set_route(...route);
    });
};
