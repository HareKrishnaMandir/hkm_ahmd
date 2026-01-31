// Copyright (c) 2025, HKM Ahmedabad and contributors
// For license information, please see license.txt

frappe.ui.form.on("AMD Vehicle Request", {
	refresh(frm) {

        if (frm.doc.status === "Pending"){
            frm.add_custom_button('Allocate',function() {
                frappe.model.with_doctype('AMD Vehicle Assignment', function() {
                    let doc = frappe.model.get_new_doc('AMD Vehicle Assignment');

                    doc.requestor = frm.doc.requestor;
                    doc.model = frm.doc.model;
                    doc.vehicle_request = frm.doc.name;
                    doc.request_id = frm.doc.name;

                    if (frm.doc.requestor === "Other") {
                        doc.other_requestor = frm.doc.other_requestor;
                        doc.other_requestor_name = frm.doc.other_requestor_name
                    }

                    // Assign time/date fields explicitly
                    doc.out_time = frm.doc.out_time || null;
                    doc.in_time = frm.doc.in_time || null;
                    doc.date = frm.doc.date || null;
                frappe.set_route('Form','AMD Vehicle Assignment',doc.name);
            });
        });
    }
	},
});
