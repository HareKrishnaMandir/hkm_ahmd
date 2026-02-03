// Copyright (c) 2025, HKM Ahmedabad and contributors
// For license information, please see license.txt

frappe.ui.form.on("AMD Vehicle Assignment", {
	refresh(frm) {
        if (frm.doc.status === "Approved" && !frm.doc.__islocal) {
            frm.add_custom_button("Cancel",() => {
                frappe.call({
                    method: "hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_assignment.amd_vehicle_assignment.send_driver_cancel_message",
                    args: {
                        docname:frm.doc.name
                    },
                    callback(r) {
                        if (!r.exc) {
                            frappe.msgprint("Driver cancellation message sent");
                            frm.set_value("status","Cancelled");
                            frm.save();
                            
                        } else {
                            frappe.msgprint("An error occurred.")
                        }
                    }  
                });
            });
        }
	},
    after_save(frm) {
        if (frm.doc.status === "Approved") {
            frappe.call({
                method: "hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_assignment.amd_vehicle_assignment.send_whatsapp_message",
                args: {
                    docname: frm.doc.name
                },
                callback(r) {
                    if (!r.exc) {
                        frappe.msgprint("WhatsApp message sent to driver and requestor.");
                    }
                }
            });
        }
    }
});


