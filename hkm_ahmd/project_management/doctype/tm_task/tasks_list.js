console.log("Tasks list js loaded");

frappe.listview_settings["TM Task"] = {
	add_fields: ["status"],

	get_indicator: function (doc) {
		return [__(doc.status || "Not Started"), "gray", "status,=," + (doc.status || "Not Started")];
	},

	refresh: function () {
		setTimeout(() => {
			try {
				apply_task_status_colors();
			} catch (e) {
				console.log("Task status color error:", e);
			}
		}, 500);
	},

	onload: function () {
		setTimeout(() => {
			try {
				apply_task_status_colors();
			} catch (e) {
				console.log("Task status color error:", e);
			}
		}, 500);
	}
};

function apply_task_status_colors() {
	const colorMap = {
		"Not Started": { bg: "#f3f4f6", color: "#6b7280" },
		"Acknowledged": { bg: "#fef3c7", color: "#b45309" },
		"Editing": { bg: "#dbeafe", color: "#1d4ed8" },
		"Under Review": { bg: "#ffedd5", color: "#c2410c" },
		"Printing": { bg: "#fce7f3", color: "#be185d" },
		"Billing": { bg: "#f3e8ff", color: "#7e22ce" },
		"Completed": { bg: "#dcfce7", color: "#15803d" },
		"Closed": { bg: "#fee2e2", color: "#dc2626" },
		"Working On": { bg: "#dbeafe", color: "#1d4ed8" },
		"HOLD": { bg: "#ffedd5", color: "#c2410c" },
		"Hold": { bg: "#ffedd5", color: "#c2410c" },
		"Planned": { bg: "#dbeafe", color: "#1e3a8a" },
		"Approval & review": { bg: "#dcfce7", color: "#15803d" },
		"Ordered": { bg: "#fee2e2", color: "#dc2626" },
		"Replacement": { bg: "#dbeafe", color: "#1d4ed8" },
		"Repair": { bg: "#fef3c7", color: "#b45309" },
		"Received": { bg: "#fce7f3", color: "#be185d" },
		"IT asset entry": { bg: "#dcfce7", color: "#15803d" },
		"Issue/Install": { bg: "#ffedd5", color: "#c2410c" },
		"ERP asset entry": { bg: "#f3e8ff", color: "#7e22ce" },
		"Cancelled": { bg: "#fee2e2", color: "#dc2626" },
		"Recorded": { bg: "#fef3c7", color: "#b45309" }
	};

	document.querySelectorAll(".indicator-pill").forEach((pill) => {
		const text = (pill.textContent || "").trim();
		const colors = colorMap[text];

		if (!colors) return;

		pill.style.backgroundColor = colors.bg;
		pill.style.color = colors.color;
		pill.style.border = `1px solid ${colors.bg}`;
		pill.style.fontWeight = "500";
	});
}