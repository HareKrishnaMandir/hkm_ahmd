// Copyright (c) 2025, HKM Ahmedabad and contributors
// For license information, please see license.txt

// frappe.ui.form.on("AMD Vehicle Requestor", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("AMD Vehicle Requestor", {
    disable: function(frm) {
        if (frm.doc.disable) {
            // ✅ When checked, set to Irregular
            frm.set_value("requestor_type", "Irregular");
        } else {
            // ✅ When unchecked, set to Regular
            frm.set_value("requestor_type", "Regular");
        }
    }
});
