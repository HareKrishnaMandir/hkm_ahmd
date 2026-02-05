# Copyright (c) 2025, HKM Ahmedabad and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate,add_to_date, get_time
from datetime import datetime, timedelta,time
from frappe import _


class AMDVehicleAssignment(Document):
    def validate(self):
        check_overlapping_assignments(self)
        
    def after_insert(self):
        if self.request_id:
            # OPTIONAL: prevent duplicate update
            current_status = frappe.db.get_value("AMD Vehicle Request", self.request_id, "status")
            if current_status != "Allocated":
                frappe.db.set_value("AMD Vehicle Request", self.request_id, "status", "Allocated")
                frappe.msgprint(f"Vehicle Request {self.request_id} marked as Allocated.")
	# def validate(self):
	# 	# if self.in_time and self.out_time:
	# 	# 	if self.in_time <= self.out_time:
	# 	# 		frappe.throw("In Time must be after Out Time.")
	# 	check_overlapping_assignments(self)
    # def after_insert(self):
    #     if self.request_id:
    #         current_status = frappe.db.get_value("AMD Vehicle Request", self.request_id, "status")
    #         if current_status != "Allocated":
    #             frappe.db.set_value("AMD Vehicle Reqeuest",self.request_id,"status","Allocated")
    #             frappe.msgprint(f"Vehicle Request {self.request_id} marked as Allocated")
# Helper to convert timedelta to time
def convert_timedelta_to_time(td):
	return (datetime.min + td).time()

def after_insert(self):
        if self.request_id:
            # OPTIONAL: prevent duplicate update
            current_status = frappe.db.get_value("AMD Vehicle Request", self.request_id, "status")
            if current_status != "Allocated":
                frappe.db.set_value("AMD Vehicle Request", self.request_id, "status", "Allocated")
                frappe.msgprint(f"Vehicle Request {self.request_id} marked as Allocated.")

# This function checks for overlapping vehicle assignments for the same driver or vehicle on the same date. It throws an error if any overlaps are found, ensuring that a driver or vehicle cannot be double-booked.
@frappe.whitelist()
def update_vehicle_status():
	now = now_datetime()
	

	assignments = frappe.get_all(
		"AMD Vehicle Assignment",
		filters={"date": getdate(now)},
		fields=["name", "vehicle_number", "in_time", "out_time", "date"]
	)
	
	for assignment in assignments:
		if not all([assignment.vehicle_number, assignment.in_time, assignment.out_time]):
			continue

		try:
			in_time = convert_timedelta_to_time(assignment.in_time)
			out_time = convert_timedelta_to_time(assignment.out_time)
			
		except Exception as e:
			frappe.log_error(f"Time conversion error in {assignment.name}: {str(e)}")
			continue

		in_dt = datetime.combine(assignment.date, in_time)
		
		out_dt = datetime.combine(assignment.date, out_time)
		
		vehicle = frappe.get_doc("AMD Vehicle Details", {"name": assignment.vehicle_number})

		if out_dt <= now <= in_dt:
			if vehicle.vehicle_status != "Assigned":
				vehicle.vehicle_status = "Assigned"
				vehicle.save(ignore_permissions=True)
		else:
			if vehicle.vehicle_status != "Available":
				vehicle.vehicle_status = "Available"
				vehicle.save(ignore_permissions=True,)
update_vehicle_status()
def convert_to_time(value):
    if isinstance(value, time):
        return value
    elif isinstance(value, timedelta):
        return (datetime.min + value).time()
    elif isinstance(value, str):
        try:
            return datetime.strptime(value, "%H:%M:%S").time()
        except ValueError:
            try:
                return datetime.strptime(value, "%H:%M").time()
            except ValueError:
                frappe.throw(f"Invalid time format: {value}")
    return value
# def validate(self):
# 	check_overlapping_assignments(self)
# 	if self.vehicle_number:
# 		vehicle = frappe.get_doc("AMD Vehicle Details", {"license_plate_number": self.vehicle_number})
# 		if vehicle.vehicle_status == "Assigned":
# 			frappe.throw(_("Vehicle {0} is already assigned to another requestor. Please choose another vehicle.").format(self.vehicle_number))

def check_overlapping_assignments(doc):
	driver_name = frappe.get_doc("AMD Drivers Details",doc.driver_name,"driver_name")
	if not (doc.driver_name and doc.vehicle_number and doc.out_time and doc.in_time and doc.date):
		return
	driver_conflicts = frappe.db.get_all(
        "AMD Vehicle Assignment",
        filters={
            "driver_name": doc.driver_name,
            "date": doc.date,
            "name": ["!=",doc.name],
            "status":"Approved",
        },
        fields = ["name","out_time","in_time"]
    )
	for d in driver_conflicts:
		if time_overlap(doc.out_time, doc.in_time, d.out_time, d.in_time):
			frappe.throw(
				f"Driver <b>{doc.driver_name}</b> is already assigned between {d.out_time} and {d.in_time} in assignment: {d.name}"
            )
			
	vehicle_conflicts = frappe.db.get_all(
		"AMD Vehicle Assignment",
		filters = {
			"vehicle_number": doc.vehicle_number,
			"date": doc.date,
			"name": ["!=",doc.name],
			"status": "Approved"
        },
		fields = ["name","out_time","in_time"]
    )
	for v in vehicle_conflicts:
		if time_overlap(doc.out_time,doc.in_time,v.out_time,v.in_time):
			frappe.throw(
				f"Vehicle <b>{doc.vehicle_number}</b> is already assigned between {v.out_time} and {v.in_Time}"
            )
			
def time_overlap(start1, end1, start2, end2):
    start1 = convert_to_time(start1)
    end1 = convert_to_time(end1)
    start2 = convert_to_time(start2)
    end2 = convert_to_time(end2)

    return (
        start1 <= end2 and end1 >= start2
        if all([start1, end1, start2, end2]) else False
    )
#for sending whatsapp message to driver and requestor vehicle and driver details on approval of vehicle assignment.
@frappe.whitelist()
def send_whatsapp_message(docname):
    if not docname:
        return {"status": "error","message": "Assignment name is required."}
    
    try:
        api_url = "https://graph.facebook.com/v19.0/263347100194101/messages"
        doc = frappe.get_doc("AMD Vehicle Assignment", docname)
        if doc.requestor == "Other":
            requestor_phone = doc.other_requestor
            requestor_name = doc.other_requestor_name
        else:
            requestor_phone = frappe.get_value("AMD Vehicle Requestor", doc.requestor, "phone_number")
            requestor_name = doc.requestor
        access_token = "EAAE76wtqkL8BO5ZB85fkPqXvkTZAjWhfuTuIBI5ql7ZCXZCSZBWZAMOcSkxwLkLNZCijiQkNWQ9SqkefaYj0KPamwUqJBVvYCjRzfQg5AuZBNAridzTPjxgY0OfDXvpQt0XL2X6smO4nXLkIEwCyJCBn3f0h3CtPLRJze3AX27I486l5qQ8bGAVIbAC0Y4s5KGbt"
        
        
        if doc.other_driver_name is None:     
            driver_name = frappe.get_value("AMD Drivers Details",doc.driver_name,"driver_name")
            mobile_number = doc.mobile_number
        else:
            driver_name = doc.other_driver_name
            mobile_number = doc.other_mobile_number
        vehicle_number = frappe.get_value("AMD Vehicle Details",doc.vehicle_number, "license_plate_number")
        if not requestor_phone:
            return {"status": "error","message": "Requestor phone number not found"}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        requestor_payload = json.dumps(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"+91{requestor_phone}",
                "type": "template",
                "template" :{
                    "name" : "vehicle_requestor",
                    "language" : {"code": "en"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text", "text":  f"*{driver_name}*"
                                },
                                {
                                    "type": "text", "text": f"*{mobile_number}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.date}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.out_time}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.in_time}*"
                                },
                                {
                                    "type": "text", "text": f"*{vehicle_number}*"
                                },
                            ]
                        },
                    ]
                }
            },
        )
		
        requestor_response = requests.request("POST", api_url, headers=headers, data=requestor_payload)
        if not doc.mobile_number:
            return {"status": "error","message": "Driver phone number not found."}
        
        driver_payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"+91{mobile_number}",
            "type": "template",
            "template": {
                "name": "driver_message",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text", "text": f"*{requestor_name}*"
                            },
                            {
                                "type": "text", "text": f"*{doc.out_time}*"
                            },
                            {
                                "type": "text", "text": f"*{requestor_phone}*"
                            },
                        ]
                    }
                ]
            }
        })
        driver_response = requests.request("POST", api_url,headers = headers,data= driver_payload)
        return {"status": "success", "message": "Message sent."}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Whatsapp send failed.")
        frappe.msgprint(f"{docname}:{str(e)}")
        return {"status": "error", "message": str(e)}
# This function is called when a vehicle assignment is cancelled. It updates the assignment status to "Cancelled", sets the vehicle status to "Available", and sends a WhatsApp message to both the driver and requestor notifying them of the cancellation.
@frappe.whitelist(allow_guest=True)
def send_driver_cancel_message(docname):
    try:
        api_url = "https://graph.facebook.com/v19.0/263347100194101/messages"
        doc = frappe.get_doc("AMD Vehicle Assignment",docname)
        #vehicle_status = frappe.get_doc("AMD Vehicle Details", doc.vehicle_number,ignore_permissions=True)
        if doc.requestor == "Other":
            requestor_phone = doc.other_requestor
            requestor_name = doc.other_requestor_name

        else:
            requestor_phone = frappe.get_value("AMD Vehicle Requestor", doc.requestor, "phone_number")
            requestor_name = doc.requestor
        # vehicle_status.vehicle_status = "Available"
        # vehicle_status.save(ignore_permissions=True)
        access_token = "EAAE76wtqkL8BO5ZB85fkPqXvkTZAjWhfuTuIBI5ql7ZCXZCSZBWZAMOcSkxwLkLNZCijiQkNWQ9SqkefaYj0KPamwUqJBVvYCjRzfQg5AuZBNAridzTPjxgY0OfDXvpQt0XL2X6smO4nXLkIEwCyJCBn3f0h3CtPLRJze3AX27I486l5qQ8bGAVIbAC0Y4s5KGbt"

        if doc.other_driver_name is None:
            driver_mobile_number = doc.mobile_number
            driver_name = doc.driver_name
        else:
            driver_mobile_number = doc.other_mobile_number
            driver_name = doc.other_driver_name
                
        if not driver_mobile_number:
            return {"status": "error", "message": "Driver phone number not found."}
        headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        recipient_numbers = [
             f"{driver_mobile_number}",
             "6351011883",
             "9904407517"
        ]
        for number in recipient_numbers:
            driver_cancel_payload = json.dumps({
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": f"+91{number}",
                    "type": "template",
                    "template": {
                        "name": "driver_message",
                        "language": {"code": "en"},
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text", "text": f"*{requestor_name}*"
                                    },
                                    {
                                        "type": "text", "text": "*Cancelled*"
                                    },
                                    {
                                        "type": "text", "text": f"*{requestor_phone}*"
                                    },
                                ]
                            }
                        ]
                    }
                })
            driver_cancel_response = requests.request("POST", api_url, headers=headers, data=driver_cancel_payload)


        requestor_cancel_payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"+91{requestor_phone}",
                "type": "template",
                "template": {
                    "name": "vehicle_requestor",
                    "language": {"code": "en"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text", "text":  f"*{driver_name}*"
                                },
                                {
                                    "type": "text", "text": f"*{driver_mobile_number}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.date}*"
                                },
                                {
                                    "type": "text", "text": "*Cancelled*"
                                },
                                {
                                    "type": "text", "text": "*Cancelled*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.vehicle_number}*"
                                },
                            ]
                        },
                    ]
                }
            })
        requestor_cancel_response = requests.request("POST", api_url, headers=headers, data=requestor_cancel_payload)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "whatsapp send failed.")
        frappe.msgprint(f"{docname}:{str(e)}")
        return {"status": "error","message": str(e)}
# This function cancels a vehicle assignment by updating its status to "Cancelled" and setting the associated vehicle's status to "Available". It also sends a WhatsApp message to both the driver and requestor notifying them of the cancellation.
@frappe.whitelist(allow_guest=True)
def cancel_assignment_and_send_message(docname):
    try:
        doc = frappe.get_doc("AMD Vehicle Assignment", docname)
        if doc.status == "Cancelled":
            return "Assignment is already marked as Cancelled"
        frappe.db.set_value("AMD Vehicle Details", doc.vehicle_number,"vehicle_status","Available",update_modified=False)
        frappe.db.set_value("AMD Vehicle Assignment", docname, "status", "Cancelled", update_modified=False)
        # vehicle_status = frappe.get_doc(
		# "AMD Vehicle Details", doc.vehicle_number,ignore_permissions=True)
        # vehicle_status.vehicle_status = "Available"
        # vehicle_status.save(ignore_permissions=True)
        # Update status to Cancelled
        frappe.db.commit()

        # Call existing message method
        frappe.call("hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_assignment.amd_vehicle_assignment.send_driver_cancel_message", docname=docname)

        return f"Assignment '{docname}' marked as Cancelled and WhatsApp message sent."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Cancel and WhatsApp Failed")
        return f"Error: {str(e)}"


def timedelta_to_time(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return time(hour=hours, minute=minutes, second=seconds)

def check_vehicle_status_and_notify():
    current_datetime = now_datetime()
    current_date = getdate(current_datetime)
    current_time = get_time(current_datetime)

    print(f"Current date : {current_date}")
    print(f"Current time : {current_time}")

    assignments = frappe.get_all(
        "AMD Vehicle Assignment",
        filters={"date": current_date,"status": "Approved"},
        fields=["name", "out_time", "in_time", "vehicle_number", "requestor"]
    )

    for assignment in assignments:
        doc = frappe.get_doc("AMD Vehicle Assignment", assignment.name)

        if not doc.out_time or not doc.in_time:
            continue

        # Handle case where out_time/in_time are timedelta instead of time
        out_time = doc.out_time
        in_time = doc.in_time

        if isinstance(out_time, timedelta):
            out_time = timedelta_to_time(out_time)
        if isinstance(in_time, timedelta):
            in_time = timedelta_to_time(in_time)

        out_time_dt = datetime.combine(current_date, out_time)
        in_time_dt = datetime.combine(current_date, in_time)
        now_dt = datetime.combine(current_date, current_time)

        time_diff = in_time_dt - out_time_dt
        print(f"{doc.name} time difference: {time_diff}")

        # Skip if trip duration is <= 2.5 hours
        if time_diff <= timedelta(hours=2, minutes=30):
            print(f"{doc.name} time diff {time_diff}. Skipping...")
            continue

        print("Outside time difference if-statement")

        out_time_plus_1hr = out_time_dt + timedelta(hours=1)
        print(f"Out plus 1 hr: {out_time_plus_1hr}")

        if out_time_dt < now_dt < in_time_dt and now_dt > out_time_plus_1hr:
            print("Inside range condition")

            requestor_details = frappe.get_value(
                "AMD Vehicle Requestor",
                doc.requestor,
                ["phone_number", "requestor_type"],
                as_dict=True
            )

            if not requestor_details or requestor_details.requestor_type != "Irregular":
                continue
            vehicle_status = frappe.get_value(
                "AMD Vehicle Details",
                {"name": doc.vehicle_number},
                ["status", "vehicle_status", "availability_status"],
                as_dict=True
            )
  
            # vehicle_status = frappe.get_value(
            #     "AMD Vehicle Details",
            #     {"name": doc.vehicle_number, "date": current_date},
            #     ["status", "vehicle_status", "availability_status"],
            #     as_dict=True
            # )

            if (
                vehicle_status and
                vehicle_status.status == "In" and
                vehicle_status.vehicle_status == "Assigned"
            ):
                try:
                    api_url = "https://graph.facebook.com/v19.0/263347100194101/messages"
                    access_token = "EAAE76wtqkL8BO5ZB85fkPqXvkTZAjWhfuTuIBI5ql7ZCXZCSZBWZAMOcSkxwLkLNZCijiQkNWQ9SqkefaYj0KPamwUqJBVvYCjRzfQg5AuZBNAridzTPjxgY0OfDXvpQt0XL2X6smO4nXLkIEwCyJCBn3f0h3CtPLRJze3AX27I486l5qQ8bGAVIbAC0Y4s5KGbt"

                    if not requestor_details.phone_number:
                        frappe.log_error("Requestor phone number not found.")
                        continue

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {access_token}"
                    }

                    cancel_payload = json.dumps({
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": f"{requestor_details.phone_number}",
                        "type": "template",
                        "template": {
                            "name": "cancel_vehicle_request",
                            "language": {"code": "en"},
                            "components": [
                                {
                                    "type": "button",
                                    "sub_type": "url",
                                    "index": "0",
                                    "parameters": [
                                        {
                                            "type": "text",
                                            "text": f"{doc.name}"
                                        }
                                    ]
                                }
                            ]
                        }
                    })

                    response = requests.post(api_url, headers=headers, data=cancel_payload)
                    print(f"Notification sent. Response: {response.status_code} {response.text}")

                except Exception as e:
                    frappe.log_error(f"Error sending WhatsApp message: {str(e)}")


                