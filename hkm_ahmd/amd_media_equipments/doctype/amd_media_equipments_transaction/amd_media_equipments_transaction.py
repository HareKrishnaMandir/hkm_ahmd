# Copyright (c) 2026, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

# import frappe
                  
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class AMDMediaEquipmentsTransaction(Document):

    def validate(self):
        """ Validate child table entries and check equipment existence. """
        if not self.item:
            frappe.throw(_("Please add at least one row in the Equipment Details table."))

        for row in self.item:
            if not row.media_equipment:
                frappe.throw(_("The 'Media Equipment' field is required for all rows in the Equipment Details table."))

            # Fetch Equipment
            equipment = frappe.get_value(
                "AMD Media Equipments",
                row.media_equipment,
                ["name", "status"],
                as_dict=True
            )

            if not equipment:
                frappe.throw(_(f"No equipment found with ID: {row.media_equipment}"))

    def before_save(self):
        """ Automatically fill the return date if not provided when status is 'Return' """
        if self.status == "Return" and not self.return_date:
            self.return_date = nowdate()
            self.db_set("return_date", self.return_date)  # Store return date in DB

    def on_update(self):
        """ Update the equipment's status after the transaction is updated """
        for row in self.item:
            if not row.media_equipment:
                continue  # Skip if not set

            equipment = frappe.get_doc("AMD Media Equipments", row.media_equipment)

            if self.status == "Issue":
                if equipment.status == "Available":
                    equipment.status = "Issued"
                    equipment.save(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.msgprint(_(f"Equipment '{equipment.name}' has been successfully issued."))
                else:
                    frappe.throw(_(f"Equipment '{equipment.name}' is already issued."))

            elif self.status == "Return":
                if equipment.status == "Issued":
                    equipment.status = "Available"
                    equipment.save(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.msgprint(_(f"Equipment '{equipment.name}' has been successfully returned and is now available."))
                else:
                    frappe.throw(_(f"Equipment '{equipment.name}' cannot be returned as it is already available."))
