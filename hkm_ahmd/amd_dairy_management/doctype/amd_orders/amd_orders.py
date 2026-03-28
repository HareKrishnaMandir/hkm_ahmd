
import frappe
from frappe.utils import nowdate, now_datetime, get_datetime
from frappe.model.document import Document


class AMDOrders(Document):
    def on_update(self):
        # If marked Not Delivered, try to cancel invoice within 24 hours
        if (self.order_status or "").strip().lower() == "not delivered":
            self.cancel_sales_invoice_if_allowed()
            return

        # Create invoice only when order is completed + delivered
        if (self.delivery_status or "").strip().upper() != "COMPLETED":
            return

        if (self.order_status or "").strip().lower() != "delivered":
            return

        source = (self.order_source or "").strip().lower()

        # Instant invoice ONLY for App orders OR customers with BILLING TYPE = Daily
        is_app = source == "app"
        is_daily_billing = _customer_has_billing_type_ci(self.customer, "Daily")

        if not (is_app or is_daily_billing):
            frappe.logger().info(
                f"[NO-INSTANT] {self.name} src={source} cust={self.customer} → defer to scheduler."
            )
            return

        # Prevent duplicate active invoice for this order
        existing_invoice = frappe.db.get_value(
            "Sales Invoice",
            {"order_reference": self.name, "docstatus": ["!=", 2]},
            "name",
        )
        if existing_invoice:
            return

        # Dynamic settings
        settings = frappe.get_cached_doc("AMD Dairy Management Settings")
        company = settings.company
        cost_head = settings.cost_head
        warehouse = settings.warehouse
        default_sales_income_account = settings.default_sales_income_account

        if not company:
            frappe.throw("Company is missing in AMD Dairy Management Settings")

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

            if float(rate) <= 0:
                frappe.logger().warning(
                    f"[INSTANT] {self.name}: skipping {row.item} due to 0 rate."
                )
                continue

            item_row = {
                "item_code": row.item,
                "qty": row.quantity,
                "rate": rate,
            }

            if warehouse:
                item_row["warehouse"] = warehouse

            if default_sales_income_account:
                item_row["income_account"] = default_sales_income_account

            item_rows.append(item_row)

        if not item_rows:
            frappe.logger().info(f"[INSTANT] {self.name}: no billable items; skipping invoice.")
            return

        # Create Sales Invoice
        inv = frappe.new_doc("Sales Invoice")
        inv.customer = self.customer
        inv.posting_date = nowdate()
        inv.due_date = nowdate()
        inv.company = company
        inv.set_posting_time = 1
        inv.order_reference = self.name

        if cost_head and hasattr(inv, "cost_head"):
            inv.cost_head = cost_head

        if warehouse and hasattr(inv, "set_warehouse"):
            inv.set_warehouse = warehouse

        if default_sales_income_account and hasattr(inv, "default_sales_income_account"):
            inv.default_sales_income_account = default_sales_income_account

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

        frappe.logger().info(f"✅ Sales Invoice {inv.name} created for Order {self.name}")

    def cancel_sales_invoice_if_allowed(self):
        sales_invoice_name = frappe.db.get_value(
            "Sales Invoice",
            {"order_reference": self.name, "docstatus": 1},
            "name",
        )

        if not sales_invoice_name:
            frappe.logger().info(
                f"[CANCEL-SKIP] No submitted Sales Invoice found for order {self.name}"
            )
            return

        inv = frappe.get_doc("Sales Invoice", sales_invoice_name)

        created_on = get_datetime(inv.creation)
        now_dt = now_datetime()
        hours_passed = (now_dt - created_on).total_seconds() / 3600

        if hours_passed > 24:
            frappe.logger().info(
                f"[CANCEL-SKIP] Sales Invoice {inv.name} is older than 24 hours ({hours_passed:.2f} hrs)."
            )
            return

        inv.flags.ignore_permissions = True
        inv.cancel()

        frappe.logger().info(
            f"❌ Sales Invoice {inv.name} cancelled because order {self.name} marked Not Delivered within 24 hours."
        )


def _customer_has_billing_type_ci(customer: str, billing_type: str) -> bool:
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