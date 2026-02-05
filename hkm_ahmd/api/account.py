import frappe
from frappe import _

@frappe.whitelist()
def delete_my_account(customer_id: str):
    if not customer_id:
        frappe.throw(_("Customer ID is required"))

    if not frappe.db.exists("Customer", customer_id):
        frappe.throw(_("Customer not found"))

    customer = frappe.get_doc("Customer", customer_id)

    # 1) Clear only the 5 fields
    customer.custom_delivery_route = None
    customer.custom_fixed_billing_status = None
    customer.custom_user = None
    customer.custom_address = None
    customer.custom_mobile_number = None
    customer.save(ignore_permissions=True)

    #  2) Disable the linked User (do NOT delete)
    user_email = customer.email_id
    if user_email and frappe.db.exists("User", user_email):
        user = frappe.get_doc("User", user_email)
        user.enabled = 0
        user.save(ignore_permissions=True)

        # 3) Logout / invalidate session tokens
        frappe.db.sql("DELETE FROM `tabSessions` WHERE user=%s", user_email)
        frappe.db.sql("DELETE FROM `tabOAuth Bearer Token` WHERE user=%s", user_email)

    frappe.db.commit()

    return {
        "status": "success",
        "message": "Account deleted (data cleared + user disabled)"
    }
