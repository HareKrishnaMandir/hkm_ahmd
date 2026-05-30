# # Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
# # For license information, please see license.txt

# import frappe
# from frappe.model.document import Document
# from frappe.core.doctype.user.user import generate_keys


# class AMDCustomerRequest(Document):
#     def on_update(self):
#         old_doc = self.get_doc_before_save()

#         if self.status == "Approved" and old_doc and old_doc.status != "Approved":
#             created_user = None
#             created_customer = None
#             generated_api_key = None
#             generated_api_secret = None

#             # Send approval mail
#             if self.email:
#                 frappe.sendmail(
#                     recipients=[self.email],
#                     subject="Your Registration is Approved",
#                     message=f"""
#                         Hello {self.full_name},<br><br>
#                         Your registration request has been approved.<br>
#                         You can now log in to our app using your email: <b>{self.email}</b><br><br>
#                         Please check your inbox for another email to set your password.<br><br>
#                         Thanks,<br>
#                         Support Team
#                     """
#                 )
 
#             # Create User if not exists
#             if self.email and not frappe.db.exists("User", {"email": self.email}):
#                 user = frappe.get_doc({
#                     "doctype": "User",
#                     "email": self.email,
#                     "first_name": self.full_name,
#                     "mobile_no": self.mobile_number,
#                     "send_welcome_email": 1,
#                     "roles": [
#                         {"role": "Customer"}
#                     ]
#                 })
#                 user.insert(ignore_permissions=True)
#                 created_user = user.name

#                 # Generate API Key + Secret for newly created user
#                 generate_keys(user.name)

#                 # Reload user to get fresh values
#                 user.reload()

#                 generated_api_key = user.api_key
#                 generated_api_secret = user.get_password("api_secret")

#             else:
#                 # If user already exists, you can optionally fetch existing api_key
#                 existing_user = frappe.db.get_value("User", {"email": self.email}, "name")
#                 if existing_user:
#                     user_doc = frappe.get_doc("User", existing_user)

#                     # If api_key not present, generate it
#                     if not user_doc.api_key:
#                         generate_keys(user_doc.name)
#                         user_doc.reload()

#                     generated_api_key = user_doc.api_key
#                     # api_secret is encrypted; get_password will return it if available
#                     try:
#                         generated_api_secret = user_doc.get_password("api_secret")
#                     except Exception:
#                         generated_api_secret = None

#             # Create Customer if not exists
#             if self.email and not frappe.db.exists("Customer", {"custom_user": self.email}):
#                 customer = frappe.get_doc({
#                     "doctype": "Customer",
#                     "customer_name": self.full_name,
#                     "customer_type": "Individual",
#                     "customer_group": "Dairy Customers",
#                     "territory": "India",
#                     "custom_user": self.email,
#                     "custom_mobile_number": self.mobile_number,
#                     "custom_address": self.address,
#                     "gst_category": "Unregistered"
#                 })
#                 customer.insert(ignore_permissions=True)
#                 created_customer = customer.name

#             frappe.msgprint(
#                 f"✅ Approval email sent.<br>"
#                 f"User: {created_user or 'Already exists'}<br>"
#                 f"Customer: {created_customer or 'Already exists'}<br>"
#                 f"API Key: {generated_api_key or 'Not available'}<br>"
#                 f"API Secret: {generated_api_secret or 'Not available'}"
#             )
# Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.user.user import generate_keys
from frappe.contacts.doctype.address.address import get_address_display


class AMDCustomerRequest(Document):
    def on_update(self):
        old_doc = self.get_doc_before_save()

        if self.status == "Approved" and old_doc and old_doc.status != "Approved":
            created_user = None
            created_customer = None
            generated_api_key = None
            generated_api_secret = None
            customer_name = None

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

                # Generate API Key + Secret
                generate_keys(user.name)
                user.reload()

                generated_api_key = user.api_key

                try:
                    generated_api_secret = user.get_password("api_secret")
                except Exception:
                    generated_api_secret = None

            else:
                existing_user = frappe.db.get_value(
                    "User",
                    {"email": self.email},
                    "name"
                )

                if existing_user:
                    user_doc = frappe.get_doc("User", existing_user)

                    if not user_doc.api_key:
                        generate_keys(user_doc.name)
                        user_doc.reload()

                    generated_api_key = user_doc.api_key

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
                customer_name = customer.name

            else:
                customer_name = frappe.db.get_value(
                    "Customer",
                    {"custom_user": self.email},
                    "name"
                )

            # Create Address and Contact
            if customer_name:
                address_name, contact_name = self.create_address_and_contact(customer_name)
            else:
                address_name = None
                contact_name = None

            frappe.msgprint(
                f"✅ Customer request approved successfully.<br><br>"
                f"User: {created_user or 'Already exists'}<br>"
                f"Customer: {created_customer or customer_name or 'Not created'}<br>"
                f"Address: {address_name or 'Not created'}<br>"
                f"Contact: {contact_name or 'Not created'}<br>"
                f"API Key: {generated_api_key or 'Not available'}<br>"
                f"API Secret: {generated_api_secret or 'Not available'}"
            )

    def create_address_and_contact(self, customer_name):
        customer = frappe.get_doc("Customer", customer_name)

        address_name = self.create_customer_address(customer)
        contact_name = self.create_customer_contact(customer, address_name)

        update_values = {}

        if address_name:
            address_doc = frappe.get_doc("Address", address_name)

            update_values["customer_primary_address"] = address_name
            update_values["primary_address"] = get_address_display(address_doc.as_dict())

        if contact_name:
            update_values["customer_primary_contact"] = contact_name
            update_values["mobile_no"] = self.mobile_number
            update_values["email_id"] = self.email

        if update_values:
            frappe.db.set_value("Customer", customer.name, update_values)

        return address_name, contact_name

    def create_customer_address(self, customer):
        if not self.address:
            return None

        existing_address = frappe.db.sql(
            """
            SELECT parent
            FROM `tabDynamic Link`
            WHERE parenttype = 'Address'
              AND parentfield = 'links'
              AND link_doctype = 'Customer'
              AND link_name = %s
            LIMIT 1
            """,
            customer.name,
            as_dict=True
        )

        if existing_address:
            return existing_address[0].parent

        address = frappe.get_doc({
            "doctype": "Address",
            "address_title": self.full_name or customer.customer_name,
            "address_type": "Billing",

            "address_line1": self.address,
            "city": self.city or "",
            "state": self.state or "",
            "country": self.country or "India",
            "pincode": self.pincode or "",

            "phone": self.mobile_number,
            "email_id": self.email,
            "is_primary_address": 1,
            "is_shipping_address": 1,

            "links": [
                {
                    "link_doctype": "Customer",
                    "link_name": customer.name,
                    "link_title": customer.customer_name
                }
            ]
        })

        address.insert(ignore_permissions=True)
        return address.name

    def create_customer_contact(self, customer, address_name=None):
        existing_contact = frappe.db.sql(
            """
            SELECT parent
            FROM `tabDynamic Link`
            WHERE parenttype = 'Contact'
              AND parentfield = 'links'
              AND link_doctype = 'Customer'
              AND link_name = %s
            LIMIT 1
            """,
            customer.name,
            as_dict=True
        )

        if existing_contact:
            return existing_contact[0].parent

        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": self.full_name or customer.customer_name,
            "full_name": self.full_name or customer.customer_name,
            "email_id": self.email,
            "mobile_no": self.mobile_number,
            "phone": self.mobile_number,
            "address": address_name,
            "is_primary_contact": 1,
            "email_ids": [
                {
                    "email_id": self.email,
                    "is_primary": 1
                }
            ] if self.email else [],
            "phone_nos": [
                {
                    "phone": self.mobile_number,
                    "is_primary_mobile_no": 1
                }
            ] if self.mobile_number else [],
            "links": [
                {
                    "link_doctype": "Customer",
                    "link_name": customer.name,
                    "link_title": customer.customer_name
                }
            ]
        })

        contact.insert(ignore_permissions=True)
        return contact.name