# Copyright (c) 2025, HKM Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime
from hkm_ahmd.api.amd_driver_salary import get_number_summary

# This class represents the AMD Driver Salary Slip document. It calculates the total rent days before saving and validates the required fields before saving the document. 
# It also fetches the number summary based on the vehicle number and date range to populate the salary details.
class AMDDriverSalarySlip(Document):
    def before_save(self):
        if self.driver_name and self.from_date and self.to_date:
            self.total_rent_days = frappe.call(
                "hkm_ahmd.api.amd_driver_salary.calculate_total_rent_days",
                driver_name=self.driver_name,
                from_date=self.from_date,
                to_date=self.to_date
            )

    def validate(self):
        if not self.vehicle_number or not self.from_date or not self.to_date:
            frappe.throw("Please select Vehicle Number, From Date, and To Date")

        summary = get_number_summary(
            vehicle_number=self.vehicle_number,
            from_date=self.from_date,
            to_date=self.to_date
        )

        self.total_km = summary.get("total_km", 0)
        self.extra_hours = summary.get("extra_hours", 0)
        self.base_salary = summary.get("base_salary", 0)
        self.extra_salary = summary.get("extra_salary", 0)
        self.rent_amount = summary.get("rent_amount", 0)
        self.oil_amount = summary.get("oil_amount", 0)
        self.final_salary = summary.get("final_salary", 0)

   