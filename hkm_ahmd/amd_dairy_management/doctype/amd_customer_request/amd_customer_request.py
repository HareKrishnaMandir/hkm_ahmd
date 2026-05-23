# Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.user.user import generate_keys


class AMDCustomerRequest(Document):
    def on_update(self):
        old_doc = self.get_doc_before_save()

        if self.status == "Approved" and old_doc and old_doc.status != "Approved":
            created_user = None
            created_customer = None
            generated_api_key = None
            generated_api_secret = None

            # Send approval mail
            if self.email:
                frappe.sendmail(
                    recipients=[self.email],
                    subject="Your Registration is Approved",
                    message=f"""
                        Hello {self.full_name},<br><br>
                        Your registration request has been approved.<br>
                        You can now log in to our app using your email: <b>{self.email}</b><br><br>
                        Please check your inbox for another email to set your password.<br><br>
                        Thanks,<br>
                        Support Team
                    """
                )

            # Create User if not exists
            if self.email and not frappe.db.exists("User", {"email": self.email}):
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

                # Generate API Key + Secret for newly created user
                generate_keys(user.name)

                # Reload user to get fresh values
                user.reload()

                generated_api_key = user.api_key
                generated_api_secret = user.get_password("api_secret")

            else:
                # If user already exists, you can optionally fetch existing api_key
                existing_user = frappe.db.get_value("User", {"email": self.email}, "name")
                if existing_user:
                    user_doc = frappe.get_doc("User", existing_user)

                    # If api_key not present, generate it
                    if not user_doc.api_key:
                        generate_keys(user_doc.name)
                        user_doc.reload()

                    generated_api_key = user_doc.api_key
                    # api_secret is encrypted; get_password will return it if available
                    try:
                        generated_api_secret = user_doc.get_password("api_secret")
                    except Exception:
                        generated_api_secret = None

            # Create Customer if not exists
            if self.email and not frappe.db.exists("Customer", {"custom_user": self.email}):
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": self.full_name,
                    "customer_type": "Individual",
                    "customer_group": "Dairy Customers",
                    "territory": "India",
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
                f"Customer: {created_customer or 'Already exists'}<br>"
                f"API Key: {generated_api_key or 'Not available'}<br>"
                f"API Secret: {generated_api_secret or 'Not available'}"
            )