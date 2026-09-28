// Route role-facing SIG workspaces to their focused workbenches. Each original
// Workspace remains available through the workbench's native-workspace button.
(() => {
    const workspaces = {
        'SIG Warehouse': {
            route: 'warehouse-workspace',
            allowNativeOnceKey: 'sig_warehouse_allow_native_workspace_once'
        },
        'SIG Accounting': {
            route: 'finance-workbench',
            allowNativeOnceKey: 'sig_finance_allow_native_workspace_once'
        }
    };

    function routeToWorkbench() {
        const route = frappe.get_route();
        if (route[0] !== 'Workspaces' || !workspaces[route[1]]) return;
        const target = workspaces[route[1]];

        if (window.sessionStorage.getItem(target.allowNativeOnceKey) === '1') {
            window.sessionStorage.removeItem(target.allowNativeOnceKey);
            return;
        }

        frappe.set_route(target.route);
    }

    frappe.router.on('change', routeToWorkbench);
    routeToWorkbench();
})();
