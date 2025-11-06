# Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate
from frappe.model.document import Document


class AMDOrders(Document):
    def on_update(self):
        # Run only when order is actually completed/delivered
        if (self.delivery_status or "").strip().upper() != "COMPLETED":
            return
        if (self.order_status or "").strip().lower() != "delivered":
            return

        source = (self.order_source or "").strip().lower()

        # Instant invoice ONLY for App orders OR customers with BILLING TYPE = Daily
        is_app = source == "app"
        is_daily_billing = _customer_has_billing_type_ci(self.customer, "Daily")

        if not (is_app or is_daily_billing):
            # Weekly/Monthly should be billed by the scheduler
            frappe.logger().info(
                f"[NO-INSTANT] {self.name} src={source} cust={self.customer} → defer to scheduler."
            )
            return

        # Prevent duplicate invoice for this order
        if frappe.db.exists("Sales Invoice", {"order_reference": self.name}):
            return

        # Build invoice items from extra_items
        item_rows = []
        for row in (self.extra_items or []):
            if not (getattr(row, "item", None) and getattr(row, "quantity", 0)):
                continue

            rate = frappe.db.get_value(
                "Item Price",
                {"item_code": row.item, "price_list": "Standard Selling", "selling": 1},
                "price_list_rate",
            ) or 0

            # Skip if no rate found
            if float(rate) <= 0:
                frappe.logger().warning(f"[INSTANT] {self.name}: skipping {row.item} due to 0 rate.")
                continue

            item_rows.append({"item_code": row.item, "qty": row.quantity, "rate": rate})

        if not item_rows:
            frappe.logger().info(f"[INSTANT] {self.name}: no billable items; skipping invoice.")
            return

        # Create Sales Invoice
        inv = frappe.new_doc("Sales Invoice")
        inv.customer = self.customer
        inv.posting_date = nowdate()
        inv.due_date = nowdate()
        inv.set_posting_time = 1
        inv.order_reference = self.name  # your custom field to prevent duplicates

        # Optional: set billing window as the delivery date if you have these fields
        if hasattr(inv, "billing_period_from"):
            inv.billing_period_from = self.delivery_date
        if hasattr(inv, "billing_period_to"):
            inv.billing_period_to = self.delivery_date
        if hasattr(inv, "order_source") and self.order_source:
            inv.order_source = self.order_source

        for r in item_rows:
            inv.append("items", r)

        inv.flags.ignore_permissions = True
        inv.save()
        inv.submit()

        # Avoid msgprint on background/automated flows (can spam UI)
        frappe.logger().info(f"✅ Sales Invoice {inv.name} created for Order {self.name}")


def _customer_has_billing_type_ci(customer: str, billing_type: str) -> bool:
    """Case/space-insensitive check for subscription_billing_type."""
    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabAMD Customer Subscription`
        WHERE customer=%s AND active=1 AND status='Active'
          AND LOWER(TRIM(subscription_billing_type)) = LOWER(TRIM(%s))
        LIMIT 1
        """,
        (customer, billing_type),
        as_dict=True,
    )
    return bool(rows)
