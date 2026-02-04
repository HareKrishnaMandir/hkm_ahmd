import frappe
from frappe import _

@frappe.whitelist()
def delete_my_account(customer_id: str):
    """
    Delete account using customer_id (called via API key auth)
    """

    if not customer_id:
        frappe.throw(_("Customer ID is required"))

    #  Fetch Customer
    if not frappe.db.exists("Customer", customer_id):
        frappe.throw(_("Customer not found"))

    customer = frappe.get_doc("Customer", customer_id)

    #  Get linked user email
    user_email = customer.email_id

    #  Delete Customer
    frappe.delete_doc("Customer", customer_id, force=1)

    #  Delete linked User (if exists)
    if user_email and frappe.db.exists("User", user_email):
        frappe.delete_doc("User", user_email, force=1)

    frappe.db.commit()

    return {
        "status": "success",
        "message": "Account deleted successfully"
    }

