// Copyright (c) 2026, Hare Krishna Movement Ahmedabad and contributors
// For license information, please see license.txt

// frappe.ui.form.on("AMD Bash Books Transaction", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('AMD Bash Book Transaction', {
    status: function(frm) {
        // Show Return Date field only when status is "Return"
        frm.toggle_display('return_date', frm.doc.status === 'Return');
    },
    refresh: function(frm) {
        // Ensure Return Date visibility on form load
        frm.trigger('status');
    }
});