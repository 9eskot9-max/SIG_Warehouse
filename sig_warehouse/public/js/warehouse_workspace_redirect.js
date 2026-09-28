// Make the existing Warehouse Workspace sidebar entry open its role-aligned
// workbench. The original Workspace remains available from the workbench's
// "Original Warehouse Workspace" button for users who need the legacy view.
(() => {
    const nativeWorkspace = 'SIG Warehouse';
    const workbenchRoute = 'warehouse-workspace';
    const allowNativeOnceKey = 'sig_warehouse_allow_native_workspace_once';

    function routeWarehouseToWorkbench() {
        const route = frappe.get_route();
        if (route[0] !== 'Workspaces' || route[1] !== nativeWorkspace) return;

        if (window.sessionStorage.getItem(allowNativeOnceKey) === '1') {
            window.sessionStorage.removeItem(allowNativeOnceKey);
            return;
        }

        frappe.set_route(workbenchRoute);
    }

    frappe.router.on('change', routeWarehouseToWorkbench);
    routeWarehouseToWorkbench();
})();
