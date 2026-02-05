// Copyright (c) 2025, HKM Ahmedabad and contributors
// For license information, please see license.txt

// frappe.ui.form.on("AMD Vehicle Bulk Assignment", {
// 	refresh(frm) {

// 	},
// });
// vehile bulk assignment 
frappe.ui.form.on('AMD Vehicle Bulk Assignment', {
    date: function(frm) {
        if (frm.doc.date) {
            frappe.call({
                method: 'hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_bulk_assignment.amd_vehicle_bulk_assignment.get_preacher_assignments_by_date',
                args: {
                    date: frm.doc.date
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table('alloted_vehicle_for_regular_requestor');
                        frm.clear_table('alloted_vehicle');

                        // Populate Regular Requestors
                        if (r.message.regular && r.message.regular.length) {
                            r.message.regular.forEach(item => {
                                let row = frm.add_child('alloted_vehicle_for_regular_requestor');
                                row.requestor = item.requestor;
                                row.driver_name = item.driver_name;
                                row.mobile_number = item.mobile_number;
                                row.vehicle_number = item.vehicle_number;
                                row.model = item.vehicle_model;
                                row.date = item.date;
                                row.out_time = item.out_time;
                                row.in_time = item.in_time;
                            });
                        }

                        // Populate Irregular Requestors
                        if (r.message.irregular && r.message.irregular.length) {
                            r.message.irregular.forEach(item => {
                                let row = frm.add_child('alloted_vehicle');
                                row.requestor = item.requestor;
                                row.date = item.date;
                                row.out_time = item.out_time;
                                row.in_time = item.in_time;
                                row.model = item.model;
                                row.remarks = item.remarks;
                                row.vehicle_request_id = item.vehicle_request_id;
                            });
                        }

                        frm.refresh_field('alloted_vehicle_for_regular_requestor');
                        frm.refresh_field('alloted_vehicle');
                    } else {
                        frappe.msgprint('No assignments found for selected date.');
                    }
                }
            });
        }
    },

    refresh: function(frm) {
        frm.add_custom_button('Create Vehicle Assignments', function() {
            frappe.call({
                method: 'hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_bulk_assignment.amd_vehicle_bulk_assignment.create_vehicle_assignments',
                args: {
                    bulk_assignment_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message === "success") {
                        frappe.msgprint("✅ Vehicle Assignments created successfully.");
                    } else {
                        frappe.msgprint("❌ Error: " + r.message);
                    }
                }
            });
        });
    }
});
