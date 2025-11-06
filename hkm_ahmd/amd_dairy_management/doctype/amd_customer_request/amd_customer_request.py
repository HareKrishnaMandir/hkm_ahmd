# Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AMDCustomerRequest(Document):
    def on_update(self):
        if self.status == "Approved" and self.get_doc_before_save():
            if self.get_doc_before_save().status != "Approved":

                frappe.sendmail(
                    recipients=[self.email],
                    subject="Your Registration is Approved ",
                    message=f"""
                    Hello {self.full_name},<br><br>
                    Your registration request has been approved.<br>
                    You can now log in to our app using your email: <b>{self.email}</b><br><br>
                    Please check your inbox for another email to set your password.<br><br>
                    Thanks,<br>
                    Support Team
                    """
                )

                created_user = None
                created_customer = None

                
                if not frappe.db.exists("User", {"email": self.email}):
                    user = frappe.get_doc({
                        "doctype": "User",
                        "email": self.email,
                        "first_name": self.full_name,
                        "mobile_no": self.mobile_number,
                        "send_welcome_email": 1,
                        "roles": [
                            {"role": "Customer"}  
                        ]
                    })
                    user.insert(ignore_permissions=True)
                    created_user = user.name

               
                if not frappe.db.exists("Customer", {"custom_user": self.email}):
                    customer = frappe.get_doc({
                        "doctype": "Customer",
                        "customer_name": self.full_name,
                        "customer_type": "Individual",
                        "custom_user": self.email,
                        "custom_mobile_number": self.mobile_number,
                        "custom_address": self.address,
                        "gst_category": "Unregistered"
                    })
                    customer.insert(ignore_permissions=True)
                    created_customer = customer.name

              
                frappe.msgprint(
                    f"✅ Approval email sent.<br>"
                    f"User: {created_user or 'Already exists'}<br>"
                    f"Customer: {created_customer or 'Already exists'}"
                )