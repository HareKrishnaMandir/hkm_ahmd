import frappe
from frappe.utils import flt


def auto_allocate_payment_entry_doc_to_customer_invoices(doc) -> dict:
    """
    Payment Type = Receive, Party Type = Customer, Cost Head = Dairy

    Behavior:
    1. If Sales Invoice references are already present (for example selected from app),
       DO NOT auto-allocate again.
    2. If no references are present, treat it like advance payment and auto-allocate
       against customer's outstanding Sales Invoices.
    """
    if not doc:
        return {"ok": False, "reason": "missing_doc"}

    if doc.docstatus == 2:
        return {"ok": False, "reason": "payment_entry_cancelled"}

    if doc.payment_type != "Receive":
        return {
            "ok": True,
            "reason": "not_receive_payment",
            "payment_entry": doc.name,
            "allocated": 0.0,
            "remaining_unallocated": flt(doc.unallocated_amount or doc.paid_amount or 0),
            "sales_invoices": [],
        }

    if doc.party_type != "Customer" or not doc.party:
        return {
            "ok": True,
            "reason": "not_customer_payment",
            "payment_entry": doc.name,
            "allocated": 0.0,
            "remaining_unallocated": flt(doc.unallocated_amount or doc.paid_amount or 0),
            "sales_invoices": [],
        }

    settings = frappe.get_cached_doc("AMD Dairy Management Settings")
    settings_cost_head = (settings.cost_head or "").strip()
    doc_cost_head = (getattr(doc, "cost_head", "") or "").strip()

    if not settings_cost_head or doc_cost_head != settings_cost_head:
        return {
            "ok": True,
            "reason": "cost_head_not_matching_settings",
            "payment_entry": doc.name,
            "allocated": 0.0,
            "remaining_unallocated": flt(doc.unallocated_amount or doc.paid_amount or 0),
            "sales_invoices": [],
        }

    # If app/user already selected Sales Invoice references,
    # do NOT auto-allocate again.
    
    existing_invoice_refs = [
        ref for ref in (doc.references or [])
        if ref.reference_doctype == "Sales Invoice" and ref.reference_name
    ]

    if existing_invoice_refs:
        if hasattr(doc, "set_missing_ref_details"):
            try:
                doc.set_missing_ref_details(force=True)
            except TypeError:
                doc.set_missing_ref_details()

        if hasattr(doc, "set_amounts"):
            doc.set_amounts()

        return {
            "ok": True,
            "reason": "references_already_present_skip_auto_allocate",
            "payment_entry": doc.name,
            "allocated": sum(flt(ref.allocated_amount) for ref in existing_invoice_refs),
            "remaining_unallocated": flt(doc.unallocated_amount),
            "sales_invoices": [
                {
                    "sales_invoice": ref.reference_name,
                    "allocated": flt(ref.allocated_amount),
                }
                for ref in existing_invoice_refs
            ],
        }

    available = flt(doc.unallocated_amount or doc.paid_amount)
    if available <= 0:
        return {
            "ok": True,
            "reason": "no_amount_available",
            "payment_entry": doc.name,
            "allocated": 0.0,
            "remaining_unallocated": available,
            "sales_invoices": [],
        }

    # Fetch only submitted unpaid invoices for same customer.
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "customer": doc.party,
            "docstatus": 1,
            "outstanding_amount": [">", 0],
        },
        fields=["name", "outstanding_amount", "posting_date", "creation"],
        order_by="posting_date asc, creation asc",
    )

    if not invoices:
        return {
            "ok": True,
            "reason": "no_outstanding_invoices",
            "payment_entry": doc.name,
            "allocated": 0.0,
            "remaining_unallocated": available,
            "sales_invoices": [],
        }

    total_allocated = 0.0
    used_invoices = []

    for row in invoices:
        if available <= 0:
            break

        invoice_name = row.get("name")
        remaining = flt(row.get("outstanding_amount"))

        if not invoice_name or remaining <= 0:
            continue

        allocate_now = min(available, remaining)
        if allocate_now <= 0:
            continue

        doc.append(
            "references",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice_name,
                "allocated_amount": allocate_now,
            },
        )

        available -= allocate_now
        total_allocated += allocate_now
        used_invoices.append(
            {
                "sales_invoice": invoice_name,
                "allocated": allocate_now,
            }
        )

    if hasattr(doc, "set_missing_ref_details"):
        try:
            doc.set_missing_ref_details(force=True)
        except TypeError:
            doc.set_missing_ref_details()

    if hasattr(doc, "set_amounts"):
        doc.set_amounts()

    return {
        "ok": True,
        "reason": "allocation_done",
        "payment_entry": doc.name,
        "allocated": total_allocated,
        "remaining_unallocated": flt(doc.unallocated_amount),
        "sales_invoices": used_invoices,
    } 