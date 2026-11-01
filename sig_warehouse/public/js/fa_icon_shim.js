// Frappe v16 no longer ships Font Awesome, so the workbenches' <i class="fa fa-NAME"> icons rendered
// blank. This swaps each one for the matching Lucide symbol that v16 already loads.
(function () {
	if (window.__sig_fa_shim) return;
	window.__sig_fa_shim = true;
	const MAP = {
		"book": "book-open", "calendar": "calendar", "calendar-check-o": "calendar-check", "clock-o": "clock",
		"columns": "columns-3", "cubes": "box", "envelope": "mail", "exchange": "arrow-left-right",
		"exclamation-triangle": "triangle-alert", "external-link": "external-link", "file-text": "file-text",
		"file-text-o": "file-text", "id-card": "id-card", "inbox": "inbox", "life-ring": "life-buoy",
		"line-chart": "chart-line", "list-alt": "list", "refresh": "refresh-cw", "rotate-right": "rotate-cw",
		"shopping-cart": "shopping-cart", "ticket": "ticket", "truck": "truck", "undo": "undo-2",
		"user-circle-o": "circle-user", "users": "users",
	};
	function swap(el) {
		const m = /(?:^|\s)fa-([a-z0-9-]+)/.exec(el.className || "");
		const id = m && MAP[m[1]];
		if (!id || !el.parentNode) return;
		const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
		svg.setAttribute("viewBox", "0 0 24 24");
		svg.setAttribute("fill", "none");
		svg.setAttribute("stroke", "currentColor");
		svg.setAttribute("stroke-width", "2");
		svg.setAttribute("stroke-linecap", "round");
		svg.setAttribute("stroke-linejoin", "round");
		svg.setAttribute("aria-hidden", "true");
		svg.style.cssText = "width:1.1em;height:1.1em;vertical-align:-0.15em;flex:none";
		const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
		use.setAttribute("href", "#icon-" + id);
		svg.appendChild(use);
		el.replaceWith(svg);
	}
	function scan(root) {
		if (root.nodeType !== 1) return;
		if (root.matches && root.matches("i.fa")) swap(root);
		root.querySelectorAll && root.querySelectorAll("i.fa").forEach(swap);
	}
	new MutationObserver((muts) => muts.forEach((m) => m.addedNodes.forEach(scan))).observe(document.documentElement, {childList: true, subtree: true});
	document.addEventListener("DOMContentLoaded", () => scan(document.body));
})();
