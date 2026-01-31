# Copyright (c) 2025, HKM Ahmedabad and contributors
# For license information, please see license.txt



import frappe
from frappe.model.document import Document

class AMDCancelRequest(Document):
    def after_insert(self):
        if self.requestor:
            # Fetch the AMD Vehicle Requestor record
            requestor_doc = frappe.get_doc("AMD Vehicle Requestor", self.requestor)

            # Set disable and date range
            requestor_doc.disable = 1
            requestor_doc.disable_from = self.disable_from
            requestor_doc.disable_to = self.disable_to

            # Set Requestor Type to Irregular
            requestor_doc.requestor_type = "Irregular"

            # Save the updated requestor
            requestor_doc.save()
            frappe.msgprint(f"Requestor '{self.requestor}' disabled from {self.disable_from} to {self.disable_to} and marked as Irregular.")
