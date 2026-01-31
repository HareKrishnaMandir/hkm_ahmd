# Copyright (c) 2025, HKM Ahmedabad and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_assignment.amd_vehicle_assignment import send_whatsapp_message

class AMDVehicleBulkAssignment(Document):
	pass

@frappe.whitelist()
def get_preacher_assignments_by_date(date):
    regular_assignments = []
    irregular_assignments = []

    # Step 1: Fetch requestors from AMD Vehicle Request with selected date
    preacher_list = frappe.get_all("AMD Vehicle Request", filters={"date": date}, fields=["requestor"])

    for entry in preacher_list:
        requestor = entry.requestor
        details = fetch_vehicle_details(requestor, date)
        details["requestor"] = requestor

        if details.get("status") == "created":
            regular_assignments.append(details)
        elif details.get("status") == "skipped":
            irregular_assignments.append(details)

    # Step 2: Add Regular requestors from AMD Vehicle Requestor if not already added
    regular_requestors = frappe.get_all("AMD Vehicle Requestor", filters={"requestor_type": "Regular"}, fields=["requestor", "driver_name", "vehicle_number", "in_time", "out_time"])

    for req in regular_requestors:
        if req.requestor not in [a["requestor"] for a in regular_assignments]:
            driver_info = frappe.get_value("AMD Drivers Details", {"driver_name": req.driver_name}, ["mobile_number"], as_dict=True)
            vehicle_info = frappe.get_value("AMD Vehicle Details", {"license_plate_number": req.vehicle_number}, ["model"], as_dict=True)

            regular_assignments.append({
                "status": "created",
                "requestor": req.requestor,
                "driver_name": req.driver_name,
                "mobile_number": driver_info.mobile_number if driver_info else "",
                "vehicle_number": req.vehicle_number,
                "vehicle_model": vehicle_info.model if vehicle_info else "",
                "date": date,
                "out_time": req.out_time,
                "in_time": req.in_time
            })

    # Return both lists separately so frontend can populate 2 tables
    return {
        "regular": regular_assignments,
        "irregular": irregular_assignments
    }

def fetch_vehicle_details(requestor, date):
    requestor_data = frappe.get_value(
        "AMD Vehicle Requestor",
        {"requestor": requestor},
        ["requestor_type", "driver_name"],
    )

    if not requestor_data:
        return {"status": "error", "message": "No Vehicle Requestor found"}

    requestor_type, driver_identifier = requestor_data

    vehicle_request = frappe.get_value(
        "AMD Vehicle Request",
        {"requestor": requestor, "date": date, "status": "pending"},
        ["date", "out_time", "in_time", "model", "remarks", "name"],
        as_dict=True,
    )

    if vehicle_request:
        # Put all explicit requests (even by regular requestors) in irregular table
        return {
            "status": "skipped",
            "date": vehicle_request.date,
            "out_time": vehicle_request.out_time,
            "in_time": vehicle_request.in_time,
            "model": vehicle_request.model,
            "remarks": vehicle_request.remarks,
            "vehicle_request_id": vehicle_request.name,
        }

    # No explicit request found, so normal regular assignment logic
    if requestor_type == "Irregular":
        return {"status": "error", "message": "No Vehicle Request found"}

    driver_info = frappe.get_value(
        "AMD Drivers Details",
        {"driver_name": driver_identifier},
        ["driver_name", "mobile_number"],
        as_dict=True,
    )

    vehicle = frappe.get_value(
        "AMD Vehicle Details",
        {"driver_name": driver_identifier},
        ["model", "license_plate_number"],
        as_dict=True,
    )

    return {
        "status": "created",
        "driver_name": driver_info.driver_name if driver_info else "",
        "mobile_number": driver_info.mobile_number if driver_info else "",
        "vehicle_number": vehicle.license_plate_number if vehicle else "",
        "vehicle_model": vehicle.model if vehicle else "",
        "date": date,
        "out_time": None,
        "in_time": None,
    }


@frappe.whitelist()
def create_vehicle_assignments(bulk_assignment_name):
    doc = frappe.get_doc("AMD Vehicle Bulk Assignment", bulk_assignment_name)

    if not doc:
        return "Bulk Assignment not found"

    for row in list(doc.alloted_vehicle):
        try:
            vehicle_request = frappe.get_doc("AMD Vehicle Request", row.vehicle_request_id)
            assignment = frappe.new_doc("AMD Vehicle Assignment")
            assignment.request_id = vehicle_request.name
            assignment.requestor = row.requestor
            assignment.driver_name = row.driver_name
            assignment.mobile_number = row.mobile_number
            assignment.vehicle_number = row.vehicle_number
            assignment.model = row.model
            assignment.date = row.date
            assignment.out_time = row.out_time
            assignment.in_time = row.in_time
            assignment.remarks = row.remarks
            assignment.status = "Approved"
            assignment.insert()
            frappe.db.commit()
            send_whatsapp_message(assignment.name)
            row.delete()
        except Exception as e:
            frappe.log_error(f"Failed to create assignment for {row.requestor}: {str(e)}")
            continue

    for row in list(doc.alloted_vehicle_for_regular_requestor):
        try:
            if not row.driver_name:
                continue
            assignment = frappe.new_doc("AMD Vehicle Assignment")
            assignment.request_id = ""
            assignment.requestor = row.requestor
            assignment.driver_name = row.driver_name
            assignment.mobile_number = row.mobile_number
            assignment.vehicle_number = row.vehicle_number
            assignment.model = row.model
            assignment.date = row.date
            assignment.out_time = row.out_time
            assignment.in_time = row.in_time
            assignment.remarks = ""
            assignment.status = "Approved"
            assignment.insert()
            frappe.db.commit()
            send_whatsapp_message(assignment.name)
            row.delete()
        except Exception as e:
            frappe.log_error(f"Failed to create assignment for {row.requestor}: {str(e)}")
            continue

    doc.save()
    return "success"
