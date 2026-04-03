import frappe
from frappe.utils import flt


def auto_allocate_payment_entry_doc_to_customer_invoices(doc) -> dict:
    """
    Payment Type = Receive ,Party Type = Customer ,Cost Head = Dairy

    It appends outstanding Sales Invoice references to the same draft Payment Entry before submit, so normal ERPNext submit logic handles the actual reconciliation.
    This does NOT affect other Payment Entries.
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

    available = flt(doc.paid_amount or doc.unallocated_amount)
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
    # We do NOT filter Sales Invoice by cost_head here, to avoid failures
    # on ERPs where that field may not exist or may be blank.
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

    # If references are already present, keep them and avoid duplicates.
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

        existing_ref = None
        for ref in (doc.references or []):
            if (
                ref.reference_doctype == "Sales Invoice"
                and ref.reference_name == invoice_name
            ):
                existing_ref = ref
                break

        if existing_ref:
            existing_ref.allocated_amount = flt(existing_ref.allocated_amount) + allocate_now
        else:
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