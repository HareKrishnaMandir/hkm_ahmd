// Copyright (c) 2025, HKM Ahmedabad and contributors
// For license information, please see license.txt

// frappe.ui.form.on("AMD Driver Salary Slip", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("AMD Driver Salary Slip", {
    vehicle_number: function (frm) {
        fetch_number_summary(frm);
    },
    from_date: function (frm) {
        fetch_number_summary(frm);
    },
    to_date: function (frm) {
        fetch_number_summary(frm);
    },
    
});

function fetch_number_summary(frm) {
    if (frm.doc.vehicle_number && frm.doc.from_date && frm.doc.to_date) {
        frappe.call({
            method: "hkm_amd.api.amd_driver_salary.get_number_summary",
            args: {
                vehicle_number: frm.doc.vehicle_number,
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date
            },
            callback: function (r) {
                if (r.message) {
                    frm.set_value("total_km", r.message.total_km);
                    frm.set_value("extra_hours", r.message.extra_hours);
                    frm.set_value("base_salary", r.message.base_salary);
                    frm.set_value("extra_salary", r.message.extra_salary);
                    frm.set_value("rent_amount", r.message.rent_amount);
                    frm.set_value("oil_amount", r.message.oil_amount);
                    frm.set_value("final_salary", r.message.final_salary);
                }
            }
        });
    }
}
