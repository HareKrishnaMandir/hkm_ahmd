import frappe
from hkm_ahmd.amd_dairy_management.utils.advance_allocation import (
    auto_allocate_payment_entry_doc_to_customer_invoices,
)


def payment_entry_before_submit(doc, method=None):
    try:
        result = auto_allocate_payment_entry_doc_to_customer_invoices(doc)
        frappe.logger().info(
            f"[PE-BEFORE-SUBMIT-AUTO-ALLOCATE] Payment Entry={doc.name} Result={result}"
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"[PE-BEFORE-SUBMIT-AUTO-ALLOCATE-FAILED] Payment Entry {doc.name}",
        )
        raise