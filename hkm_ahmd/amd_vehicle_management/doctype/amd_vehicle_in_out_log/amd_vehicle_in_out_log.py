# Copyright (c) 2025, HKM Ahmedabad and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe.model.document import Document
from frappe.utils import getdate,today
class AMDVehicleInOutLog(Document):
    # def after_insert(self):
    #     if self.status == "Out":
    #         update_count(self)
    #calculate total km
    def validate(self):
        if self.in_km and self.out_km:
            try:
                in_km = float(self.in_km)
                out_km = float(self.out_km)
                self.total_km = in_km - out_km
            except ValueError:
                frappe.throw("IN KM and OUT KM must be valid numbers")


@frappe.whitelist()
def reset_vehicle_trip():
    vehicles = frappe.get_all("AMD Vehicle Details", fields=["name"])
    for v in vehicles:
        frappe.db.set_value("AMD Vehicle Details",v.name, {
            "total_trips":0
        })