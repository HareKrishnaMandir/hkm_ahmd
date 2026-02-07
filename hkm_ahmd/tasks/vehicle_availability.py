import frappe

def update_vehicle_availability_status():
    vehicles = frappe.get_all("AMD Vehicle Details", fields=["name", "vehicle_status", "status", "driver_name"])

    for vehicle in vehicles:
        if not vehicle.driver_name:
            frappe.db.set_value("AMD Vehicle Details", vehicle.name, "availability_status", "Unavailable")
            continue

        attendance_status = frappe.db.get_value("AMD Driver Attendance", {
            "driver_name": vehicle.driver_name
        }, "attendance_status")

        if (
            vehicle.vehicle_status == "Available" and
            vehicle.status == "In" and
            attendance_status == "Check-In"
        ):
            new_status = "Available"
        else:
            new_status = "Unavailable"

        frappe.db.set_value("AMD Vehicle Details", vehicle.name, "availability_status", new_status)
