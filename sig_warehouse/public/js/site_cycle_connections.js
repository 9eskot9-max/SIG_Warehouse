// Add the resolved SIG Site master to Site Cycle's Connections panel.
// Custom DocTypes skip Frappe's override_doctype_dashboards hook in v15, so
// this app-owned form enhancement supplies the connection until metadata adoption.
(() => {
	if (typeof frappe === "undefined" || !frappe.ui?.form) return;
	if (window.__sig_site_cycle_connections_loaded) return;
	window.__sig_site_cycle_connections_loaded = true;

	const DOCTYPE = "SIG Site Cycle";
	const SITE_DOCTYPE = "SIG Site";
	const GROUP = __("Field Ops");

	function getFieldOpsColumn(frm, $dashboard) {
		const $area = frm.dashboard.links_area.body;
		const $column = $area
			.find(".form-link-title")
			.filter(function () {
				const label = $(this).text().trim();
				return label === GROUP || label === "Field Ops";
			})
			.first()
			.closest(".col-md-4");
		if ($column.length) return $column;

		let $documents = $dashboard.find(".form-documents").first();
		if (!$documents.length) {
			$documents = $('<div class="form-documents"></div>').appendTo($dashboard);
		}
		let $row = $documents.find(".row").first();
		if (!$row.length) $row = $('<div class="row"></div>').appendTo($documents);
		const $newColumn = $('<div class="col-md-4"></div>').appendTo($row);
		$('<div class="form-link-title"></div>').text(GROUP).appendTo($newColumn);
		return $newColumn;
	}

	function makeConnectionItem($column) {
		const $prototype = $column.find(".document-link").first();
		if ($prototype.length) return $prototype.clone(false, false);
		return $('<div class="document-link"><div class="document-link-badge"><a href="#" class="badge-link"></a></div></div>');
	}

	function markUnavailable(frm, $item, docName, siteId, message) {
		if (frm.doc?.name !== docName || $item.attr("data-site-id") !== siteId) return;
		$item.removeAttr("data-site-record data-site-checking");
		$item.find(".badge-link").first().attr({
			"aria-disabled": "true",
			title: message,
		}).addClass("text-muted");
	}

	function openSiteFromItem($item) {
		const siteName = $item.attr("data-site-record");
		if (siteName) frappe.set_route("Form", SITE_DOCTYPE, siteName);
	}

	function addSiteToGroup(frm) {
		const $dashboard = frm.dashboard?.transactions_area;
		if (!$dashboard?.length || frm.is_new()) return;

		const $area = frm.dashboard.links_area.body;
		$area.find('[data-sig-site-connection="1"]').remove();

		const doc = frm.doc || {};
		const siteId = String(doc.site_id || doc.site_key || doc.site || "").trim();
		if (!siteId) return;

		const $column = getFieldOpsColumn(frm, $dashboard);
		let $item = $column.find('.document-link[data-doctype="SIG Site"]').first();
		const isNativeItem = Boolean($item.length);
		if (!isNativeItem) {
			$item = makeConnectionItem($column);
			$item.attr("data-doctype", SITE_DOCTYPE).attr("data-sig-site-connection", "1");
			$item.find(".count, .open-notification, .btn-new").remove();
			$column.append($item);
		}

		const docName = doc.name;
		const label = `${__("SIG Site ID")}: ${siteId}`;
		$item.attr("data-site-id", siteId).attr("data-site-checking", "1").removeAttr("data-site-record");
		$item.find(".badge-link").first().text(`${__("SIG Site ID")}: ${siteId}`).attr({
			href: "#",
			"aria-label": label,
			"aria-disabled": "true",
			title: __("Checking SIG Site access…"),
		}).addClass("text-muted");

		if (!isNativeItem) {
			$item.find(".badge-link").first().on("click", (event) => {
				event.preventDefault();
				event.stopPropagation();
				openSiteFromItem($item);
			});
		}

		frm.dashboard.links_area.show();
		frm.dashboard.show();

		if (!frappe.model.can_read(SITE_DOCTYPE)) {
			markUnavailable(frm, $item, docName, siteId, __("You do not have read access to SIG Site."));
			return;
		}

		const filters = doc.site ? { name: doc.site } : { site_id: siteId };
		frappe.db
			.get_value(SITE_DOCTYPE, filters, "name")
			.then((result) => {
				if (frm.doc?.name !== docName || $item.attr("data-site-id") !== siteId) return;
				const siteName = result?.message?.name;
				if (!siteName) {
					markUnavailable(frm, $item, docName, siteId, __("No SIG Site master is registered for this ID yet."));
					return;
				}
				$item.attr("data-site-record", siteName);
				$item.find(".badge-link").first().attr({
					"aria-disabled": "false",
					title: __("Open SIG Site and its history."),
				}).removeClass("text-muted");
				$item.removeAttr("data-site-checking");
			})
			.catch(() =>
				markUnavailable(
					frm,
					$item,
					docName,
					siteId,
					__("SIG Site access could not be verified. Refresh and try again.")
				)
			);
	}

	const Dashboard = frappe.ui.form.Dashboard;
	if (Dashboard?.prototype && !Dashboard.prototype.__sig_site_cycle_open_override) {
		const originalOpenDocumentList = Dashboard.prototype.open_document_list;
		Dashboard.prototype.open_document_list = function ($link, showOpen) {
			if (this.frm?.doctype === DOCTYPE && $link.attr("data-doctype") === SITE_DOCTYPE) {
				openSiteFromItem($link);
				return false;
			}
			return originalOpenDocumentList.call(this, $link, showOpen);
		};
		Dashboard.prototype.__sig_site_cycle_open_override = true;
	}

	frappe.ui.form.on(DOCTYPE, {
		refresh(frm) {
			addSiteToGroup(frm);
		},
	});
})();
