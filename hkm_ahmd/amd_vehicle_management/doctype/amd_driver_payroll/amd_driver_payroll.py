
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from hkm_ahmd.api.amd_driver_salary import get_number_summary


class AMDDriverPayroll(Document):
    def before_save(self):
        if not self.slip_generate_date:
            self.slip_generate_date = nowdate()

    def validate(self):
        # Only fill once, when creating new Payroll
        if self.is_new() and self.from_date and self.to_date:
            self.fill_driver_salary_slips()

    def fill_driver_salary_slips(self):
        # Add all enabled vehicles initially
        active_vehicles = frappe.get_all(
            "AMD Vehicle Details",
            filters={"enabled": 1},
            fields=["name"]
        )

        for vehicle in active_vehicles:
            self.append("drivers_salary_slips", {
                "license_plate_number": vehicle.name
            })


@frappe.whitelist()
# Function to generate salary slips for all drivers in the payroll
def generate_salary_slips(name):
    doc = frappe.get_doc("AMD Driver Payroll", name)

    if not doc.from_date or not doc.to_date:
        frappe.throw("Please select From Date and To Date before generating salary slips.")

    if not doc.drivers_salary_slips:
        frappe.throw("Please save the document first to populate drivers list.")

    created_slips = []

    for row in doc.drivers_salary_slips:
        if not row.license_plate_number:
            continue

        # Check if Salary Slip already exists
        exists = frappe.db.exists("AMD Driver Salary Slip", {
            "vehicle_number": row.license_plate_number,
            "from_date": doc.from_date,
            "to_date": doc.to_date
        })

        if exists:
            frappe.msgprint(f"Slip already exists for vehicle {row.license_plate_number}. Skipping.")
            continue

        try:
            summary = get_number_summary(
                vehicle_number=row.license_plate_number,
                from_date=doc.from_date,
                to_date=doc.to_date
            )

            slip = frappe.new_doc("AMD Driver Salary Slip")
            slip.vehicle_number = row.license_plate_number
            slip.from_date = doc.from_date
            slip.to_date = doc.to_date
            slip.posting_date = doc.slip_generate_date

            slip.total_km = summary.get("total_km", 0)
            slip.extra_hours = summary.get("extra_hours", 0)
            slip.base_salary = summary.get("base_salary", 0)
            slip.extra_salary = summary.get("extra_salary", 0)
            slip.rent_amount = summary.get("rent_amount", 0)
            slip.oil_amount = summary.get("oil_amount", 0)
            slip.final_salary = summary.get("final_salary", 0)

            slip.insert(ignore_permissions=True)
            created_slips.append(slip.name)

        except Exception as e:
            frappe.msgprint(f"Error for {row.license_plate_number}: {str(e)}")

    if created_slips:
        frappe.msgprint(f"Created Salary Slips: {', '.join(created_slips)}")
    else:
        frappe.msgprint("No new Salary Slips were created.")
