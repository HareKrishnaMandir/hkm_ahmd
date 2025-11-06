// Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
// For license information, please see license.txt

frappe.query_reports["Tomorrows`s Dairy Orders"] = {
	"filters": [
		 {
            fieldname: "route",
            label: __("Route"),
            fieldtype: "Link",
            options: "AMD Delivery Route",
            reqd: 0,
        },
        {
            fieldname: "delivery_status",
            label: __("Delivery Status"),
            fieldtype: "Select",
            options: ["", "OUT", "COMPLETED"],
        },

	]
};
