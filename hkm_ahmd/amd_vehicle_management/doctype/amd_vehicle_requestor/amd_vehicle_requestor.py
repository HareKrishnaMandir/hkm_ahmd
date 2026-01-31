# Copyright (c) 2025, HKM Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, getdate
from frappe.model.document import Document

class AMDVehicleRequestor(Document):
    pass

def reset_disabled_requestors():
    today = getdate(nowdate())

    requestors = frappe.get_all("AMD Vehicle Requestor", 
        filters={
            "disable": 1,
            "disable_to": ["<", today]
        },
        fields=["name"]
    )

    for r in requestors:
        doc = frappe.get_doc("AMD Vehicle Requestor", r.name)
        doc.disable = 0
        doc.disable_from = None
        doc.disable_to = None

        # ✅ Automatically change requestor_type to "Regular"
        if doc.requestor_type == "Irregular":
            doc.requestor_type = "Regular"

        doc.save(ignore_permissions=True)
        frappe.db.commit()
