// Copyright (c) 2025, HKM Ahmedabad and contributors
// For license information, please see license.txt

// frappe.ui.form.on("AMD Driver Payroll", {
// 	refresh(frm) {

// 	},
// });
// Button to generate salary slips for the driver payroll
frappe.ui.form.on('AMD Driver Payroll', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Generate Salary Slips'), function() {
                frappe.call({
                    method: 'hkm_ahmd.amd_vehicle_management.doctype.amd_driver_payroll.amd_driver_payroll.generate_salary_slips',
                    args: {
                        name: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});