// Route role-facing SIG workspace slugs to their focused app-owned workbenches.
(() => {
    const workspaces = {
        'sig-warehouse': {
            route: 'warehouse-workspace',
            allowNativeOnceKey: 'sig_warehouse_allow_native_workspace_once'
        },
        'sig-accounting': {
            route: 'finance-workbench',
            allowNativeOnceKey: 'sig_finance_allow_native_workspace_once'
        },
        'sig-hr': {
            route: 'hr-workbench',
            allowNativeOnceKey: 'sig_hr_allow_native_workspace_once'
        },
        // "SIG - My Work" is open to every user, but its replacement Page is limited to the Employee roles.
        // roleAny keeps users without those roles (finance, warehouse, ops staff) on the native workspace
        // instead of sending them to a Page they cannot open.
        'sig-my-work': {
            route: 'employee-workbench',
            allowNativeOnceKey: 'sig_my_work_allow_native_workspace_once',
            roleAny: ['Employee', 'Employee Self Service', 'HR User', 'HR Manager', 'System Manager']
        }
    };

    function normalize(value) {
        return String(value || '')
            .trim()
            .toLowerCase()
            .replace(/[\s_]+/g, '-')
            .replace(/-+/g, '-');
    }

    function getWorkspaceTarget() {
        const route = frappe.get_route() || [];
        const candidates = [];

        if (String(route[0] || '').toLowerCase() === 'workspaces' && route[1]) {
            candidates.push(route[1]);
        }
        if (route[0]) candidates.push(route[0]);

        // Workspace routes may be reported as a DocType route or just its URL
        // slug depending on how Desk reached the page. The URL is the stable
        // fallback for direct loads and sidebar clicks.
        const match = window.location.pathname.match(/^\/app\/([^/]+)/i);
        if (match) candidates.push(decodeURIComponent(match[1]));

        for (const candidate of candidates) {
            const target = workspaces[normalize(candidate)];
            if (target) return target;
        }
        return null;
    }

    function routeToWorkbench() {
        const target = getWorkspaceTarget();
        if (!target) return;
        if (target.roleAny && !target.roleAny.some((role) => frappe.user.has_role(role))) return;

        if (window.sessionStorage.getItem(target.allowNativeOnceKey) === '1') {
            window.sessionStorage.removeItem(target.allowNativeOnceKey);
            return;
        }

        if (normalize(frappe.get_route()?.[0]) === normalize(target.route)) return;
        frappe.set_route(target.route);
    }

    frappe.router.on('change', routeToWorkbench);
    routeToWorkbench();
})();
