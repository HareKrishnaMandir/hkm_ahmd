# Copyright (c) 2025, HKM Ahmedabad and contributors
# For license information, please see license.txt
import json
import frappe, requests
from frappe.model.document import Document

class AMDVehicleRequest(Document):
    def after_insert(self):
        send_request_message(self.name)
    def validate(self):
        # Logic based on requestor_type
        if self.request_type == "Pickup":
            self.in_time = None  

        elif self.request_type == "Drop":
            self.out_time = None  

        elif self.request_type == "Both":
            pass

        if self.request_type == "Pickup" and not self.out_time:
            frappe.throw("Please enter Pickup Time in 'Out Time' field.")

        if self.request_type == "Drop" and not self.in_time:
            frappe.throw("Please enter Drop Time in 'In Time' field.")

        if self.request_type == "Both" and (not self.in_time or not self.out_time):
            frappe.throw("Please enter both Pickup and Drop Time.")

    # def validate(self):
    #     if self.out_time and self.in_time:
    #         if self.in_time <= self.out_time:
    #             frappe.throw("In Time must be after Out Time.")
@frappe.whitelist()
def send_request_message(docname):
    if not docname:
        return{"status": "error","message": "Request name is required."}
    try:
        api_url = "https://graph.facebook.com/v19.0/263347100194101/messages"
        doc = frappe.get_doc("AMD Vehicle Request", docname)
        
        if doc.requestor == "Other":
            requestor_phone = doc.other_requestor
            requestor_name = doc.other_requestor_name
        else:
            requestor_phone = frappe.get_value("AMD Vehicle Requestor", doc.requestor, "phone_number")
            requestor_name = doc.requestor

        
        access_token = "EAAE76wtqkL8BO5ZB85fkPqXvkTZAjWhfuTuIBI5ql7ZCXZCSZBWZAMOcSkxwLkLNZCijiQkNWQ9SqkefaYj0KPamwUqJBVvYCjRzfQg5AuZBNAridzTPjxgY0OfDXvpQt0XL2X6smO4nXLkIEwCyJCBn3f0h3CtPLRJze3AX27I486l5qQ8bGAVIbAC0Y4s5KGbt"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        request_payload = json.dumps(
            {
                "messaging_product":"whatsapp",
                "recipient_type": "individual",
                "to": "+916351011883",
                "type": "template",
                "template": {
                    "name": "vehicle_request_form",
                    "language": {"code":"en"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text", "text":  f"*{requestor_name}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.date}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.request_type}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.out_time}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.in_time}*"
                                },
                                {
                                    "type": "text", "text": f"*{doc.model}*"
                                },
                            ]
                        }
                    ]
                }
            }
        )
        request_response = requests.request("POST", api_url, headers=headers,data=request_payload)
        # print(f"Payload {request_payload}")
        # print(f"Response is: {request_response}")
        # frappe.msgprint(f"Status Code: {request_response.status_code}")
        # print(f"Response: {request_response.text}")
    except Exception as e:
        frappe.msgprint(f"{docname}:{str(e)}")
        print("In except")