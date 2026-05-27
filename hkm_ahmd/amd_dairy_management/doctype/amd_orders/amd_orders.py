# import frappe
# from frappe.utils import getdate, now, add_days, now_datetime, flt, nowdate, get_datetime
# from frappe.model.document import Document


# MERGED_SUBSCRIPTION_MARKER = "[MERGED_SUBSCRIPTIONS]"


# class AMDOrders(Document):
#     def on_update(self):
#         # If marked Not Delivered, try to cancel invoice within 24 hours
#         if (self.order_status or "").strip().lower() == "not delivered":
#             self.cancel_sales_invoice_if_allowed()
#             return

#         # Create invoice only when order is completed + delivered
#         if (self.delivery_status or "").strip().upper() != "COMPLETED":
#             return

#         if (self.order_status or "").strip().lower() != "delivered":
#             return

#         source = (self.order_source or "").strip().lower()

#         # Instant invoice ONLY for App orders OR customers with BILLING TYPE = Daily
#         is_app = source == "app"
#         is_daily_billing = _customer_has_billing_type_ci(self.customer, "Daily")

#         if not (is_app or is_daily_billing):
#             frappe.logger().info(
#                 f"[NO-INSTANT] {self.name} src={source} cust={self.customer} → defer to scheduler."
#             )
#             return

#         # Prevent duplicate active invoice for this order
#         existing_invoice = frappe.db.get_value(
#             "Sales Invoice",
#             {"custom_order_reference": self.name, "docstatus": ["!=", 2]},
#             "name",
#         )
#         if existing_invoice:
#             return

#         create_sales_invoice_from_amd_order(self.name)

#     def cancel_sales_invoice_if_allowed(self):
#         sales_invoice_name = frappe.db.get_value(
#             "Sales Invoice",
#             {"custom_order_reference": self.name, "docstatus": 1},
#             "name",
#         )

#         if not sales_invoice_name:
#             frappe.logger().info(
#                 f"[CANCEL-SKIP] No submitted Sales Invoice found for order {self.name}"
#             )
#             return

#         inv = frappe.get_doc("Sales Invoice", sales_invoice_name)

#         created_on = get_datetime(inv.creation)
#         now_dt = now_datetime()
#         hours_passed = (now_dt - created_on).total_seconds() / 3600

#         if hours_passed > 24:
#             frappe.logger().info(
#                 f"[CANCEL-SKIP] Sales Invoice {inv.name} is older than 24 hours ({hours_passed:.2f} hrs)."
#             )
#             return

#         inv.flags.ignore_permissions = True
#         inv.cancel()

#         frappe.logger().info(
#             f"❌ Sales Invoice {inv.name} cancelled because order {self.name} marked Not Delivered within 24 hours."
#         )


# @frappe.whitelist()
# def generate_daily_orders(target_shift="Morning"):
#     """
#     Generate subscription orders.

#     Logic:
#     - Morning orders => for tomorrow
#     - Evening orders => for today
#     - One Subscription order per customer + shift + delivery_date
#     - If same customer has multiple valid subscriptions for same shift/date,
#       all items are merged into one order
#     - Re-running generator will not duplicate same subscription items
#     """
#     today = getdate()

#     target_shift = (target_shift or "Morning").strip()

#     if target_shift == "Evening":
#         delivery_date = today
#     else:
#         delivery_date = add_days(today, 1)

#     subscriptions = frappe.get_all(
#         "AMD Customer Subscription",
#         filters={
#             "active": 1,
#             "status": "Active",
#         },
#         fields=[
#             "name",
#             "customer",
#             "subscription_type",
#             "route",
#             "shift",
#             "is_alternate_days",
#         ],
#     )

#     for sub in subscriptions:
#         sub_doc = frappe.get_doc("AMD Customer Subscription", sub.name)

#         if not is_valid_shift(sub_doc.shift, target_shift):
#             continue

#         if not is_subscription_day(sub_doc, delivery_date, target_shift):
#             continue

#         create_or_update_subscription_order(sub_doc, delivery_date, target_shift)

#     frappe.db.commit()


# @frappe.whitelist()
# def create_app_order(customer, route, delivery_date, items, shift="Morning"):
#     """
#     Create an order directly from the mobile app.
#     App orders remain separate from subscription orders.
#     """
#     order = frappe.new_doc("AMD Orders")
#     order.customer = customer
#     order.route = route
#     order.order_date = getdate()
#     order.order_time = now()
#     order.delivery_date = getdate(delivery_date)
#     order.delivery_time = now()
#     order.delivery_status = "OUT"
#     order.order_status = "In Progress"
#     order.order_source = "App"

#     if has_field("AMD Orders", "shift"):
#         order.shift = shift

#     for row in items or []:
#         item_code = (row.get("item") or "").strip()
#         qty = flt_safe(row.get("quantity"))

#         if not item_code or qty <= 0:
#             continue

#         order.append("extra_items", {
#             "item": item_code,
#             "quantity": qty,
#         })

#     order.insert(ignore_permissions=True)
#     frappe.db.commit()
#     return order.name


# def create_or_update_subscription_order(sub_doc, delivery_date, target_shift):
#     """
#     Create one merged subscription order per:
#     customer + shift + delivery_date + order_source=Subscription

#     If order already exists, merge items into it.
#     If this subscription was already merged earlier, skip to avoid duplication.
#     """
#     order = get_existing_subscription_order(
#         customer=sub_doc.customer,
#         delivery_date=delivery_date,
#         target_shift=target_shift,
#     )

#     if not order:
#         order = frappe.new_doc("AMD Orders")
#         order.customer = sub_doc.customer
#         order.route = sub_doc.route
#         order.order_date = getdate()
#         order.order_time = now()
#         order.delivery_date = delivery_date
#         order.delivery_time = now()
#         order.delivery_status = "OUT"
#         order.order_status = "In Progress"
#         order.order_source = "Subscription"

#         if has_field("AMD Orders", "shift"):
#             order.shift = target_shift

#         # In merged-order logic, single subscription_reference is not reliable
#         if has_field("AMD Orders", "subscription_reference"):
#             order.subscription_reference = None

#         merge_subscription_items(order, sub_doc.child_table or [])
#         add_merged_subscription_name(order, sub_doc.name)

#         order.insert(ignore_permissions=True)
#         return order.name

#     # If this subscription is already merged in this order, do nothing
#     if subscription_already_merged(order, sub_doc.name):
#         return order.name

#     # If route is blank in existing order, fill it
#     if not getattr(order, "route", None) and sub_doc.route:
#         order.route = sub_doc.route

#     merge_subscription_items(order, sub_doc.child_table or [])
#     add_merged_subscription_name(order, sub_doc.name)

#     order.flags.ignore_permissions = True
#     order.save()
#     return order.name


# def get_existing_subscription_order(customer, delivery_date, target_shift):
#     """
#     Find existing merged Subscription order for same customer + date + shift.
#     """
#     filters = {
#         "customer": customer,
#         "order_source": "Subscription",
#         "delivery_date": delivery_date,
#         "docstatus": ["!=", 2],
#     }

#     if has_field("AMD Orders", "shift"):
#         filters["shift"] = target_shift

#     existing_name = frappe.db.get_value("AMD Orders", filters, "name")
#     if existing_name:
#         return frappe.get_doc("AMD Orders", existing_name)

#     return None


# def merge_subscription_items(order, subscription_items):
#     """
#     Merge subscription items into AMD Order.
#     If same item already exists in order, quantity is increased.
#     """
#     for item in subscription_items:
#         item_code = (getattr(item, "item", None) or "").strip()
#         qty = flt_safe(getattr(item, "quantity", 0))

#         if not item_code or qty <= 0:
#             continue

#         existing_row = find_existing_item_row(order, item_code)

#         if existing_row:
#             existing_row.quantity = flt_safe(existing_row.quantity) + qty
#         else:
#             order.append("extra_items", {
#                 "item": item_code,
#                 "quantity": qty,
#             })


# def find_existing_item_row(order, item_code):
#     for row in (order.extra_items or []):
#         if (getattr(row, "item", None) or "").strip() == item_code:
#             return row
#     return None


# def is_valid_shift(subscription_shift, target_shift):
#     """
#     Morning run -> Morning + Both
#     Evening run -> Evening + Both
#     """
#     subscription_shift = (subscription_shift or "").strip()
#     target_shift = (target_shift or "").strip()

#     if subscription_shift == "Both":
#         return True

#     return subscription_shift == target_shift


# def is_subscription_day(sub_doc, delivery_date, target_shift=None):
#     """
#     Decide whether order should be generated for this delivery date.
#     """
#     subscription_type = (sub_doc.subscription_type or "").strip()

#     if subscription_type == "Daily":
#         return not is_subscription_paused_on(sub_doc, delivery_date)

#     elif subscription_type == "Weekly":
#         if is_subscription_paused_on(sub_doc, delivery_date):
#             return False

#         weekly_day = (getattr(sub_doc, "weekly_day", None) or "").strip()
#         if not weekly_day:
#             return False

#         weekday = delivery_date.strftime("%A")
#         return weekday == weekly_day

#     elif subscription_type == "Monthly":
#         if is_subscription_paused_on(sub_doc, delivery_date):
#             return False

#         monthly_date = cint_safe(getattr(sub_doc, "monthly_date", 0))
#         if monthly_date < 1 or monthly_date > 31:
#             return False

#         return delivery_date.day == monthly_date

#     elif subscription_type == "Alternate Days" or cint_safe(sub_doc.is_alternate_days) == 1:
#         return should_generate_alternate_order(sub_doc, delivery_date, target_shift)

#     return False


# def should_generate_alternate_order(sub_doc, delivery_date, target_shift=None):
#     """
#     Alternate-day logic in merged mode:

#     1. If current delivery_date is paused -> do not create
#     2. If previous delivery_date was paused -> create today
#     3. If previous day has COMPLETED + Delivered merged order for same
#        customer + shift -> skip today
#     4. Otherwise -> create today

#     NOTE:
#     Because orders are merged customer-wise, alternate tracking is also
#     evaluated customer + shift wise.
#     """
#     if is_subscription_paused_on(sub_doc, delivery_date):
#         return False

#     previous_delivery_date = add_days(delivery_date, -1)

#     if is_subscription_paused_on(sub_doc, previous_delivery_date):
#         return True

#     if alternate_order_exists_for_date(sub_doc, previous_delivery_date, target_shift):
#         return False

#     return True


# def alternate_order_exists_for_date(sub_doc, delivery_date, target_shift=None):
#     """
#     In merged-order mode, count previous day only if merged order for the same
#     customer + shift was actually completed and delivered.
#     """
#     filters = {
#         "customer": sub_doc.customer,
#         "order_source": "Subscription",
#         "delivery_date": delivery_date,
#         "delivery_status": "COMPLETED",
#         "order_status": "Delivered",
#     }

#     if has_field("AMD Orders", "shift") and target_shift in ("Morning", "Evening"):
#         filters["shift"] = target_shift

#     return bool(frappe.db.exists("AMD Orders", filters))


# def is_subscription_paused_on(sub_doc, target_date):
#     """
#     Checks pause/halt table for given date.
#     Supports:
#     - date
#     - from_date / to_date
#     - start_date / end_date
#     """
#     for row in (sub_doc.subscription_pause or []):
#         row_dict = row.as_dict()

#         single_date = row_dict.get("date")
#         from_date = row_dict.get("from_date") or row_dict.get("start_date")
#         to_date = row_dict.get("to_date") or row_dict.get("end_date")

#         if single_date and getdate(single_date) == target_date:
#             return True

#         if from_date and to_date:
#             if getdate(from_date) <= target_date <= getdate(to_date):
#                 return True

#     return False


# def subscription_already_merged(order, subscription_name):
#     merged_names = get_merged_subscription_names(order)
#     return subscription_name in merged_names


# def get_merged_subscription_names(order):
#     remarks = (getattr(order, "remarks", None) or "").strip()
#     if not remarks:
#         return set()

#     names = set()
#     for line in remarks.splitlines():
#         line = line.strip()
#         if line.startswith(MERGED_SUBSCRIPTION_MARKER):
#             raw = line.replace(MERGED_SUBSCRIPTION_MARKER, "", 1).strip()
#             if raw:
#                 names.update([x.strip() for x in raw.split(",") if x.strip()])

#     return names


# def add_merged_subscription_name(order, subscription_name):
#     names = get_merged_subscription_names(order)
#     names.add(subscription_name)
#     set_merged_subscription_names(order, names)


# def set_merged_subscription_names(order, names):
#     remarks = (getattr(order, "remarks", None) or "").strip()
#     lines = [line for line in remarks.splitlines() if line.strip()] if remarks else []

#     # Remove old marker line if present
#     lines = [line for line in lines if not line.strip().startswith(MERGED_SUBSCRIPTION_MARKER)]

#     marker_line = "{0} {1}".format(
#         MERGED_SUBSCRIPTION_MARKER,
#         ",".join(sorted(names))
#     )

#     lines.append(marker_line)
#     order.remarks = "\n".join(lines)


# def generate_morning_orders():
#     generate_daily_orders(target_shift="Morning")


# def generate_evening_orders():
#     generate_daily_orders(target_shift="Evening")


# def run_dynamic_order_schedulers():
#     """
#     Runs every hour from hooks.py.
#     Checks AMD Dairy Management Settings and triggers
#     morning/evening order generation when hour matches.
#     """
#     settings = frappe.get_cached_doc("AMD Dairy Management Settings")

#     morning_hour = parse_scheduler_hour(
#         getattr(settings, "orders_morning_schedular", None)
#     )
#     evening_hour = parse_scheduler_hour(
#         getattr(settings, "orders_evening_schedular", None)
#     )

#     current_hour = now_datetime().hour

#     frappe.logger().info(
#         "[ORDER-SCHEDULER] current_hour={0}, morning_hour={1}, evening_hour={2}".format(
#             current_hour, morning_hour, evening_hour
#         )
#     )

#     if morning_hour is not None and current_hour == morning_hour:
#         frappe.logger().info("[ORDER-SCHEDULER] Running Morning Orders")
#         generate_morning_orders()

#     if evening_hour is not None and current_hour == evening_hour:
#         frappe.logger().info("[ORDER-SCHEDULER] Running Evening Orders")
#         generate_evening_orders()


# # =========================
# # DYNAMIC SALES INVOICE RATE LOGIC
# # =========================

# def get_customer_default_price_list(customer):
#     """
#     Dynamically get Customer.default_price_list.
#     Fallback to Standard Selling if blank.
#     """
#     price_list = frappe.db.get_value("Customer", customer, "default_price_list")
#     return (price_list or "Standard Selling").strip()


# def get_item_price_from_price_list(item_code, price_list, uom=None):
#     """
#     Get selling price from Item Price using given price list.
#     First try with UOM if available, then fallback without UOM.
#     Latest modified/creation wins.
#     """
#     filters = {
#         "item_code": item_code,
#         "price_list": price_list,
#         "selling": 1,
#     }

#     if uom:
#         rows = frappe.get_all(
#             "Item Price",
#             filters={**filters, "uom": uom},
#             fields=["name", "price_list_rate"],
#             order_by="modified desc, creation desc",
#             limit=1,
#         )
#         if rows:
#             return flt(rows[0].price_list_rate)

#     rows = frappe.get_all(
#         "Item Price",
#         filters=filters,
#         fields=["name", "price_list_rate"],
#         order_by="modified desc, creation desc",
#         limit=1,
#     )
#     if rows:
#         return flt(rows[0].price_list_rate)

#     return 0.0


# def get_item_standard_rate(item_code):
#     """
#     Last fallback from Item.standard_rate
#     """
#     standard_rate = frappe.db.get_value("Item", item_code, "standard_rate")
#     return flt(standard_rate)


# def get_dynamic_item_rate(customer, item_code, uom=None):
#     """
#     Fully dynamic rate resolution:
#     1. Customer.default_price_list
#     2. Standard Selling
#     3. Item.standard_rate
#     """
#     customer_price_list = get_customer_default_price_list(customer)

#     rate = get_item_price_from_price_list(item_code, customer_price_list, uom=uom)
#     if rate > 0:
#         return {
#             "price_list": customer_price_list,
#             "rate": rate,
#             "source": "customer_price_list",
#         }

#     fallback_rate = get_item_price_from_price_list(item_code, "Standard Selling", uom=uom)
#     if fallback_rate > 0:
#         return {
#             "price_list": customer_price_list,
#             "rate": fallback_rate,
#             "source": "standard_selling",
#         }

#     item_standard_rate = get_item_standard_rate(item_code)
#     return {
#         "price_list": customer_price_list,
#         "rate": item_standard_rate,
#         "source": "item_standard_rate",
#     }


# @frappe.whitelist()
# def create_sales_invoice_from_amd_order(order_name):
#     """
#     Create Sales Invoice from AMD Order using:
#     - old instant invoice logic
#     - dynamic customer price list logic
#     """
#     order = frappe.get_doc("AMD Orders", order_name)

#     if not order.customer:
#         frappe.throw("Customer is required")

#     # Prevent duplicate active invoice for this order
#     existing_invoice = frappe.db.get_value(
#         "Sales Invoice",
#         {"custom_order_reference": order.name, "docstatus": ["!=", 2]},
#         "name",
#     )
#     if existing_invoice:
#         return existing_invoice

#     # Dynamic settings
#     settings = frappe.get_cached_doc("AMD Dairy Management Settings")
#     company = settings.company
#     cost_head = settings.cost_head
#     warehouse = settings.warehouse
#     default_sales_income_account = settings.default_sales_income_account

#     if not company:
#         frappe.throw("Company is missing in AMD Dairy Management Settings")

#     customer_price_list = get_customer_default_price_list(order.customer)

#     # Build invoice items from extra_items
#     item_rows = []
#     for row in (order.extra_items or []):
#         item_code = (getattr(row, "item", None) or "").strip()
#         qty = flt(getattr(row, "quantity", 0))

#         if not item_code or qty <= 0:
#             continue

#         item_doc = frappe.get_cached_doc("Item", item_code)
#         uom = item_doc.stock_uom

#         price_data = get_dynamic_item_rate(
#             customer=order.customer,
#             item_code=item_code,
#             uom=uom,
#         )
#         rate = flt(price_data["rate"])

#         if rate <= 0:
#             frappe.logger().warning(
#                 f"[INSTANT] {order.name}: skipping {item_code} due to 0 rate."
#             )
#             continue

#         item_row = {
#             "item_code": item_code,
#             "item_name": item_doc.item_name,
#             "description": item_doc.description,
#             "uom": uom,
#             "stock_uom": uom,
#             "qty": qty,
#             "price_list_rate": rate,
#             "rate": rate,
#             "amount": flt(rate) * qty,
#         }

#         if warehouse:
#             item_row["warehouse"] = warehouse

#         if default_sales_income_account:
#             item_row["income_account"] = default_sales_income_account

#         item_rows.append(item_row)

#     if not item_rows:
#         frappe.logger().info(f"[INSTANT] {order.name}: no billable items; skipping invoice.")
#         return

#     # Create Sales Invoice
#     inv = frappe.new_doc("Sales Invoice")
#     inv.customer = order.customer
#     inv.posting_date = nowdate()
#     inv.due_date = nowdate()
#     inv.company = company
#     inv.set_posting_time = 1
#     inv.selling_price_list = customer_price_list
#     inv.custom_order_reference = order.name

#     if cost_head and hasattr(inv, "cost_head"):
#         inv.cost_head = cost_head

#     if warehouse and hasattr(inv, "set_warehouse"):
#         inv.set_warehouse = warehouse

#     if default_sales_income_account and hasattr(inv, "default_sales_income_account"):
#         inv.default_sales_income_account = default_sales_income_account

#     if hasattr(inv, "billing_period_from"):
#         inv.billing_period_from = order.delivery_date

#     if hasattr(inv, "billing_period_to"):
#         inv.billing_period_to = order.delivery_date

#     if hasattr(inv, "order_source") and order.order_source:
#         inv.order_source = order.order_source

#     for r in item_rows:
#         inv.append("items", r)

#     inv.flags.ignore_permissions = True
#     inv.save()
#     inv.submit()

#     frappe.logger().info(f"✅ Sales Invoice {inv.name} created for Order {order.name}")
#     return inv.name


# def _customer_has_billing_type_ci(customer: str, billing_type: str) -> bool:
#     rows = frappe.db.sql(
#         """
#         SELECT name
#         FROM `tabAMD Customer Subscription`
#         WHERE customer=%s
#           AND active=1
#           AND status='Active'
#           AND LOWER(TRIM(subscription_billing_type)) = LOWER(TRIM(%s))
#         LIMIT 1
#         """,
#         (customer, billing_type),
#         as_dict=True,
#     )
#     return bool(rows)


# def parse_scheduler_hour(value):
#     """
#     Accepts:
#     - 4
#     - 04
#     - 4:00
#     - 04:00
#     - 04:00:00
#     """
#     if value is None or value == "":
#         return None

#     value = str(value).strip()

#     try:
#         if value.isdigit():
#             hour = int(value)
#             return hour if 0 <= hour <= 23 else None

#         if ":" in value:
#             hour = int(value.split(":")[0])
#             return hour if 0 <= hour <= 23 else None

#     except Exception:
#         frappe.logger().warning(
#             "[ORDER-SCHEDULER] Invalid scheduler value: {0}".format(value)
#         )

#     return None


# def cint_safe(value):
#     try:
#         return int(value or 0)
#     except Exception:
#         return 0


# def flt_safe(value):
#     try:
#         return float(value or 0)
#     except Exception:
#         return 0.0


# def has_field(doctype, fieldname):
#     meta = frappe.get_meta(doctype)
#     return fieldname in [df.fieldname for df in meta.fields]

import frappe
from frappe.utils import getdate, now, add_days, now_datetime, flt, nowdate, get_datetime
from frappe.model.document import Document
import json


MERGED_SUBSCRIPTION_MARKER = "[MERGED_SUBSCRIPTIONS]"


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

        # If invoice_pending is checked, do not auto-create Sales Invoice
        if has_field("AMD Orders", "invoice_pending") and cint_safe(getattr(self, "invoice_pending", 0)) == 1:
            frappe.logger().info(
                f"[INVOICE-PENDING-SKIP] {self.name} customer={self.customer} → invoice_pending checked. Auto invoice skipped."
            )
            return

        # Safety check: if Customer is Manually Billing, do not create invoice
        if is_customer_manual_billing(self.customer):
            if has_field("AMD Orders", "invoice_pending"):
                frappe.db.set_value("AMD Orders", self.name, "invoice_pending", 1)

            frappe.logger().info(
                f"[MANUAL-BILLING-SKIP] {self.name} customer={self.customer} → Customer is Manually Billing. Auto invoice skipped."
            )
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
            {"custom_order_reference": self.name, "docstatus": ["!=", 2]},
            "name",
        )
        if existing_invoice:
            return

        create_sales_invoice_from_amd_order(self.name)

    def cancel_sales_invoice_if_allowed(self):
        sales_invoice_name = frappe.db.get_value(
            "Sales Invoice",
            {"custom_order_reference": self.name, "docstatus": 1},
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


@frappe.whitelist()
def generate_daily_orders(target_shift="Morning"):
    """
    Generate subscription orders.

    Logic:
    - Morning orders => for tomorrow
    - Evening orders => for today
    - One Subscription order per customer + shift + delivery_date
    - If same customer has multiple valid subscriptions for same shift/date,
      all items are merged into one order
    - Re-running generator will not duplicate same subscription items
    """
    today = getdate()

    target_shift = (target_shift or "Morning").strip()

    if target_shift == "Evening":
        delivery_date = today
    else:
        delivery_date = add_days(today, 1)

    subscriptions = frappe.get_all(
        "AMD Customer Subscription",
        filters={
            "active": 1,
            "status": "Active",
        },
        fields=[
            "name",
            "customer",
            "subscription_type",
            "route",
            "shift",
            "is_alternate_days",
        ],
    )

    for sub in subscriptions:
        sub_doc = frappe.get_doc("AMD Customer Subscription", sub.name)

        if not is_valid_shift(sub_doc.shift, target_shift):
            continue

        if not is_subscription_day(sub_doc, delivery_date, target_shift):
            continue

        create_or_update_subscription_order(sub_doc, delivery_date, target_shift)

    frappe.db.commit()


@frappe.whitelist()
def create_app_order(customer, route, delivery_date, items, shift="Morning"):
    """
    Create an order directly from the mobile app.
    App orders remain separate from subscription orders.

    Manual Billing Customer:
    - invoice_pending = 1
    - no Sales Invoice auto-created on delivery
    """
    order = frappe.new_doc("AMD Orders")
    order.customer = customer
    order.route = route
    order.order_date = getdate()
    order.order_time = now()
    order.delivery_date = getdate(delivery_date)
    order.delivery_time = now()
    order.delivery_status = "OUT"
    order.order_status = "In Progress"
    order.order_source = "App"

    set_invoice_pending_based_on_customer(order, customer)

    if has_field("AMD Orders", "shift"):
        order.shift = shift

    for row in items or []:
        item_code = (row.get("item") or "").strip()
        qty = flt_safe(row.get("quantity"))

        if not item_code or qty <= 0:
            continue

        order.append("extra_items", {
            "item": item_code,
            "quantity": qty,
        })

    order.insert(ignore_permissions=True)
    frappe.db.commit()
    return order.name


def create_or_update_subscription_order(sub_doc, delivery_date, target_shift):
    """
    Create one merged subscription order per:
    customer + shift + delivery_date + order_source=Subscription

    If order already exists, merge items into it.
    If this subscription was already merged earlier, skip to avoid duplication.

    Manual Billing Customer:
    - invoice_pending = 1
    - no Sales Invoice auto-created on delivery
    """
    order = get_existing_subscription_order(
        customer=sub_doc.customer,
        delivery_date=delivery_date,
        target_shift=target_shift,
    )

    if not order:
        order = frappe.new_doc("AMD Orders")
        order.customer = sub_doc.customer
        order.route = sub_doc.route
        order.order_date = getdate()
        order.order_time = now()
        order.delivery_date = delivery_date
        order.delivery_time = now()
        order.delivery_status = "OUT"
        order.order_status = "In Progress"
        order.order_source = "Subscription"

        set_invoice_pending_based_on_customer(order, sub_doc.customer)

        if has_field("AMD Orders", "shift"):
            order.shift = target_shift

        # In merged-order logic, single subscription_reference is not reliable
        if has_field("AMD Orders", "subscription_reference"):
            order.subscription_reference = None

        merge_subscription_items(order, sub_doc.child_table or [])
        add_merged_subscription_name(order, sub_doc.name)

        order.insert(ignore_permissions=True)
        return order.name

    # If this subscription is already merged in this order, do nothing
    if subscription_already_merged(order, sub_doc.name):
        return order.name

    # If route is blank in existing order, fill it
    if not getattr(order, "route", None) and sub_doc.route:
        order.route = sub_doc.route

    merge_subscription_items(order, sub_doc.child_table or [])
    add_merged_subscription_name(order, sub_doc.name)

    # Refresh invoice_pending based on Customer billing type
    set_invoice_pending_based_on_customer(order, sub_doc.customer)

    order.flags.ignore_permissions = True
    order.save()
    return order.name


def get_existing_subscription_order(customer, delivery_date, target_shift):
    """
    Find existing merged Subscription order for same customer + date + shift.
    """
    filters = {
        "customer": customer,
        "order_source": "Subscription",
        "delivery_date": delivery_date,
        "docstatus": ["!=", 2],
    }

    if has_field("AMD Orders", "shift"):
        filters["shift"] = target_shift

    existing_name = frappe.db.get_value("AMD Orders", filters, "name")
    if existing_name:
        return frappe.get_doc("AMD Orders", existing_name)

    return None


def merge_subscription_items(order, subscription_items):
    """
    Merge subscription items into AMD Order.
    If same item already exists in order, quantity is increased.
    """
    for item in subscription_items:
        item_code = (getattr(item, "item", None) or "").strip()
        qty = flt_safe(getattr(item, "quantity", 0))

        if not item_code or qty <= 0:
            continue

        existing_row = find_existing_item_row(order, item_code)

        if existing_row:
            existing_row.quantity = flt_safe(existing_row.quantity) + qty
        else:
            order.append("extra_items", {
                "item": item_code,
                "quantity": qty,
            })


def find_existing_item_row(order, item_code):
    for row in (order.extra_items or []):
        if (getattr(row, "item", None) or "").strip() == item_code:
            return row
    return None


def is_valid_shift(subscription_shift, target_shift):
    """
    Morning run -> Morning + Both
    Evening run -> Evening + Both
    """
    subscription_shift = (subscription_shift or "").strip()
    target_shift = (target_shift or "").strip()

    if subscription_shift == "Both":
        return True

    return subscription_shift == target_shift


def is_subscription_day(sub_doc, delivery_date, target_shift=None):
    """
    Decide whether order should be generated for this delivery date.
    """
    subscription_type = (sub_doc.subscription_type or "").strip()

    if subscription_type == "Daily":
        return not is_subscription_paused_on(sub_doc, delivery_date)

    elif subscription_type == "Weekly":
        if is_subscription_paused_on(sub_doc, delivery_date):
            return False

        weekly_day = (getattr(sub_doc, "weekly_day", None) or "").strip()
        if not weekly_day:
            return False

        weekday = delivery_date.strftime("%A")
        return weekday == weekly_day

    elif subscription_type == "Monthly":
        if is_subscription_paused_on(sub_doc, delivery_date):
            return False

        monthly_date = cint_safe(getattr(sub_doc, "monthly_date", 0))
        if monthly_date < 1 or monthly_date > 31:
            return False

        return delivery_date.day == monthly_date

    elif subscription_type == "Alternate Days" or cint_safe(sub_doc.is_alternate_days) == 1:
        return should_generate_alternate_order(sub_doc, delivery_date, target_shift)

    return False


def should_generate_alternate_order(sub_doc, delivery_date, target_shift=None):
    """
    Alternate-day logic in merged mode:

    1. If current delivery_date is paused -> do not create
    2. If previous delivery_date was paused -> create today
    3. If previous day has COMPLETED + Delivered merged order for same
       customer + shift -> skip today
    4. Otherwise -> create today

    NOTE:
    Because orders are merged customer-wise, alternate tracking is also
    evaluated customer + shift wise.
    """
    if is_subscription_paused_on(sub_doc, delivery_date):
        return False

    previous_delivery_date = add_days(delivery_date, -1)

    if is_subscription_paused_on(sub_doc, previous_delivery_date):
        return True

    if alternate_order_exists_for_date(sub_doc, previous_delivery_date, target_shift):
        return False

    return True


def alternate_order_exists_for_date(sub_doc, delivery_date, target_shift=None):
    """
    In merged-order mode, count previous day only if merged order for the same
    customer + shift was actually completed and delivered.
    """
    filters = {
        "customer": sub_doc.customer,
        "order_source": "Subscription",
        "delivery_date": delivery_date,
        "delivery_status": "COMPLETED",
        "order_status": "Delivered",
    }

    if has_field("AMD Orders", "shift") and target_shift in ("Morning", "Evening"):
        filters["shift"] = target_shift

    return bool(frappe.db.exists("AMD Orders", filters))


def is_subscription_paused_on(sub_doc, target_date):
    """
    Checks pause/halt table for given date.
    Supports:
    - date
    - from_date / to_date
    - start_date / end_date
    """
    for row in (sub_doc.subscription_pause or []):
        row_dict = row.as_dict()

        single_date = row_dict.get("date")
        from_date = row_dict.get("from_date") or row_dict.get("start_date")
        to_date = row_dict.get("to_date") or row_dict.get("end_date")

        if single_date and getdate(single_date) == target_date:
            return True

        if from_date and to_date:
            if getdate(from_date) <= target_date <= getdate(to_date):
                return True

    return False


def subscription_already_merged(order, subscription_name):
    merged_names = get_merged_subscription_names(order)
    return subscription_name in merged_names


def get_merged_subscription_names(order):
    remarks = (getattr(order, "remarks", None) or "").strip()
    if not remarks:
        return set()

    names = set()
    for line in remarks.splitlines():
        line = line.strip()
        if line.startswith(MERGED_SUBSCRIPTION_MARKER):
            raw = line.replace(MERGED_SUBSCRIPTION_MARKER, "", 1).strip()
            if raw:
                names.update([x.strip() for x in raw.split(",") if x.strip()])

    return names


def add_merged_subscription_name(order, subscription_name):
    names = get_merged_subscription_names(order)
    names.add(subscription_name)
    set_merged_subscription_names(order, names)


def set_merged_subscription_names(order, names):
    remarks = (getattr(order, "remarks", None) or "").strip()
    lines = [line for line in remarks.splitlines() if line.strip()] if remarks else []

    # Remove old marker line if present
    lines = [line for line in lines if not line.strip().startswith(MERGED_SUBSCRIPTION_MARKER)]

    marker_line = "{0} {1}".format(
        MERGED_SUBSCRIPTION_MARKER,
        ",".join(sorted(names))
    )

    lines.append(marker_line)
    order.remarks = "\n".join(lines)


def generate_morning_orders():
    generate_daily_orders(target_shift="Morning")


def generate_evening_orders():
    generate_daily_orders(target_shift="Evening")


def run_dynamic_order_schedulers():
    """
    Runs every hour from hooks.py.
    Checks AMD Dairy Management Settings and triggers
    morning/evening order generation when hour matches.
    """
    settings = frappe.get_cached_doc("AMD Dairy Management Settings")

    morning_hour = parse_scheduler_hour(
        getattr(settings, "orders_morning_schedular", None)
    )
    evening_hour = parse_scheduler_hour(
        getattr(settings, "orders_evening_schedular", None)
    )

    current_hour = now_datetime().hour

    frappe.logger().info(
        "[ORDER-SCHEDULER] current_hour={0}, morning_hour={1}, evening_hour={2}".format(
            current_hour, morning_hour, evening_hour
        )
    )

    if morning_hour is not None and current_hour == morning_hour:
        frappe.logger().info("[ORDER-SCHEDULER] Running Morning Orders")
        generate_morning_orders()

    if evening_hour is not None and current_hour == evening_hour:
        frappe.logger().info("[ORDER-SCHEDULER] Running Evening Orders")
        generate_evening_orders()


# =========================
# CUSTOMER DAIRY BILLING LOGIC
# =========================

def get_customer_dairy_invoice_billing(customer):
    """
    Customer custom field:
    custom_dairy_invoice_billing

    Options:
    - Auto Billing
    - Manually Billing

    Default fallback:
    - Auto Billing
    """
    if not customer:
        return "Auto Billing"

    billing_type = frappe.db.get_value(
        "Customer",
        customer,
        "custom_dairy_invoice_billing"
    )

    return (billing_type or "Auto Billing").strip()


def is_customer_manual_billing(customer):
    """
    Returns True if Customer billing is Manually Billing.
    """
    billing_type = get_customer_dairy_invoice_billing(customer)
    return billing_type.lower() == "manually billing"


def set_invoice_pending_based_on_customer(order, customer):
    """
    If Customer is Manually Billing:
    - AMD Orders.invoice_pending = 1

    If Customer is Auto Billing:
    - AMD Orders.invoice_pending = 0

    This prevents auto Sales Invoice creation for manual billing customers.
    """
    if not has_field("AMD Orders", "invoice_pending"):
        return

    if is_customer_manual_billing(customer):
        order.invoice_pending = 1
    else:
        order.invoice_pending = 0


# =========================
# DYNAMIC SALES INVOICE RATE LOGIC
# =========================

def get_customer_default_price_list(customer):
    """
    Dynamically get Customer.default_price_list.
    Fallback to Standard Selling if blank.
    """
    price_list = frappe.db.get_value("Customer", customer, "default_price_list")
    return (price_list or "Standard Selling").strip()


def get_item_price_from_price_list(item_code, price_list, uom=None):
    """
    Get selling price from Item Price using given price list.
    First try with UOM if available, then fallback without UOM.
    Latest modified/creation wins.
    """
    filters = {
        "item_code": item_code,
        "price_list": price_list,
        "selling": 1,
    }

    if uom:
        rows = frappe.get_all(
            "Item Price",
            filters={**filters, "uom": uom},
            fields=["name", "price_list_rate"],
            order_by="modified desc, creation desc",
            limit=1,
        )
        if rows:
            return flt(rows[0].price_list_rate)

    rows = frappe.get_all(
        "Item Price",
        filters=filters,
        fields=["name", "price_list_rate"],
        order_by="modified desc, creation desc",
        limit=1,
    )
    if rows:
        return flt(rows[0].price_list_rate)

    return 0.0


def get_item_standard_rate(item_code):
    """
    Last fallback from Item.standard_rate
    """
    standard_rate = frappe.db.get_value("Item", item_code, "standard_rate")
    return flt(standard_rate)


def get_dynamic_item_rate(customer, item_code, uom=None):
    """
    Fully dynamic rate resolution:
    1. Customer.default_price_list
    2. Standard Selling
    3. Item.standard_rate
    """
    customer_price_list = get_customer_default_price_list(customer)

    rate = get_item_price_from_price_list(item_code, customer_price_list, uom=uom)
    if rate > 0:
        return {
            "price_list": customer_price_list,
            "rate": rate,
            "source": "customer_price_list",
        }

    fallback_rate = get_item_price_from_price_list(item_code, "Standard Selling", uom=uom)
    if fallback_rate > 0:
        return {
            "price_list": customer_price_list,
            "rate": fallback_rate,
            "source": "standard_selling",
        }

    item_standard_rate = get_item_standard_rate(item_code)
    return {
        "price_list": customer_price_list,
        "rate": item_standard_rate,
        "source": "item_standard_rate",
    }


@frappe.whitelist()
def create_sales_invoice_from_amd_order(order_name):
    """
    Create Sales Invoice from AMD Order using:
    - old instant invoice logic
    - dynamic customer price list logic

    Manual Billing protection:
    - If AMD Orders.invoice_pending = 1, invoice will not be created.
    - If Customer.custom_dairy_invoice_billing = Manually Billing, invoice will not be created.
    """
    order = frappe.get_doc("AMD Orders", order_name)

    if not order.customer:
        frappe.throw("Customer is required")

    # Do not create invoice if invoice_pending is checked
    if has_field("AMD Orders", "invoice_pending") and cint_safe(getattr(order, "invoice_pending", 0)) == 1:
        frappe.logger().info(
            f"[INVOICE-PENDING-SKIP] {order.name}: invoice_pending checked. Sales Invoice not created."
        )
        return None

    # Do not create invoice if Customer is Manually Billing
    if is_customer_manual_billing(order.customer):
        if has_field("AMD Orders", "invoice_pending"):
            frappe.db.set_value("AMD Orders", order.name, "invoice_pending", 1)

        frappe.logger().info(
            f"[MANUAL-BILLING-SKIP] {order.name}: Customer {order.customer} is Manually Billing. Sales Invoice not created."
        )
        return None

    # Prevent duplicate active invoice for this order
    existing_invoice = frappe.db.get_value(
        "Sales Invoice",
        {"custom_order_reference": order.name, "docstatus": ["!=", 2]},
        "name",
    )
    if existing_invoice:
        return existing_invoice

    # Dynamic settings
    settings = frappe.get_cached_doc("AMD Dairy Management Settings")
    company = settings.company
    cost_head = settings.cost_head
    warehouse = settings.warehouse
    default_sales_income_account = settings.default_sales_income_account

    if not company:
        frappe.throw("Company is missing in AMD Dairy Management Settings")

    customer_price_list = get_customer_default_price_list(order.customer)

    # Build invoice items from extra_items
    item_rows = []
    for row in (order.extra_items or []):
        item_code = (getattr(row, "item", None) or "").strip()
        qty = flt(getattr(row, "quantity", 0))

        if not item_code or qty <= 0:
            continue

        item_doc = frappe.get_cached_doc("Item", item_code)
        uom = item_doc.stock_uom

        price_data = get_dynamic_item_rate(
            customer=order.customer,
            item_code=item_code,
            uom=uom,
        )
        rate = flt(price_data["rate"])

        if rate <= 0:
            frappe.logger().warning(
                f"[INSTANT] {order.name}: skipping {item_code} due to 0 rate."
            )
            continue

        item_row = {
            "item_code": item_code,
            "item_name": item_doc.item_name,
            "description": item_doc.description,
            "uom": uom,
            "stock_uom": uom,
            "qty": qty,
            "price_list_rate": rate,
            "rate": rate,
            "amount": flt(rate) * qty,
        }

        if warehouse:
            item_row["warehouse"] = warehouse

        if default_sales_income_account:
            item_row["income_account"] = default_sales_income_account

        item_rows.append(item_row)

    if not item_rows:
        frappe.logger().info(f"[INSTANT] {order.name}: no billable items; skipping invoice.")
        return None

    # Create Sales Invoice
    inv = frappe.new_doc("Sales Invoice")
    inv.customer = order.customer
    inv.posting_date = nowdate()
    inv.due_date = nowdate()
    inv.company = company
    inv.set_posting_time = 1
    inv.selling_price_list = customer_price_list
    inv.custom_order_reference = order.name

    if cost_head and hasattr(inv, "cost_head"):
        inv.cost_head = cost_head

    if warehouse and hasattr(inv, "set_warehouse"):
        inv.set_warehouse = warehouse

    if default_sales_income_account and hasattr(inv, "default_sales_income_account"):
        inv.default_sales_income_account = default_sales_income_account

    if hasattr(inv, "billing_period_from"):
        inv.billing_period_from = order.delivery_date

    if hasattr(inv, "billing_period_to"):
        inv.billing_period_to = order.delivery_date

    if hasattr(inv, "order_source") and order.order_source:
        inv.order_source = order.order_source

    for r in item_rows:
        inv.append("items", r)

    inv.flags.ignore_permissions = True
    inv.save()
    inv.submit()

    frappe.logger().info(f"✅ Sales Invoice {inv.name} created for Order {order.name}")
    return inv.name


def _customer_has_billing_type_ci(customer: str, billing_type: str) -> bool:
    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabAMD Customer Subscription`
        WHERE customer=%s
          AND active=1
          AND status='Active'
          AND LOWER(TRIM(subscription_billing_type)) = LOWER(TRIM(%s))
        LIMIT 1
        """,
        (customer, billing_type),
        as_dict=True,
    )
    return bool(rows)


def parse_scheduler_hour(value):
    """
    Accepts:
    - 4
    - 04
    - 4:00
    - 04:00
    - 04:00:00
    """
    if value is None or value == "":
        return None

    value = str(value).strip()

    try:
        if value.isdigit():
            hour = int(value)
            return hour if 0 <= hour <= 23 else None

        if ":" in value:
            hour = int(value.split(":")[0])
            return hour if 0 <= hour <= 23 else None

    except Exception:
        frappe.logger().warning(
            "[ORDER-SCHEDULER] Invalid scheduler value: {0}".format(value)
        )

    return None


def cint_safe(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def flt_safe(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def has_field(doctype, fieldname):
    meta = frappe.get_meta(doctype)
    return fieldname in [df.fieldname for df in meta.fields]




@frappe.whitelist()
def get_manual_billing_customers_for_invoice():
    """
    Get customers whose custom_dairy_invoice_billing = Manually Billing
    and who have at least one delivered order with invoice_pending = 1.
    """

    frappe.only_for(("AMD App Order Creator", "System Manager"))

    rows = frappe.db.sql(
        """
        SELECT DISTINCT
            c.name,
            c.customer_name,
            c.custom_mobile_number,
            c.custom_delivery_route
        FROM `tabCustomer` c
        INNER JOIN `tabAMD Orders` o
            ON o.customer = c.name
        WHERE IFNULL(c.custom_dairy_invoice_billing, '') = 'Manually Billing'
          AND IFNULL(o.invoice_pending, 0) = 1
          AND o.order_status = 'Delivered'
          AND o.delivery_status = 'COMPLETED'
          AND o.docstatus != 2
        ORDER BY c.customer_name ASC
        """,
        as_dict=True,
    )

    return rows


@frappe.whitelist()
def get_pending_invoice_orders(customer):
    """
    Get delivered AMD Orders for selected manual billing customer.
    Only orders where invoice_pending = 1.
    """

    frappe.only_for(("AMD App Order Creator", "System Manager"))

    if not customer:
        frappe.throw("Customer is required")

    customer_billing = frappe.db.get_value(
        "Customer",
        customer,
        "custom_dairy_invoice_billing",
    )

    if (customer_billing or "").strip() != "Manually Billing":
        frappe.throw("Selected customer is not Manually Billing customer")

    orders = frappe.get_all(
        "AMD Orders",
        filters={
            "customer": customer,
            "invoice_pending": 1,
            "order_status": "Delivered",
            "delivery_status": "COMPLETED",
            "docstatus": ["!=", 2],
        },
        fields=[
            "name",
            "customer",
            "delivery_date",
            "delivery_time",
            "route",
            "shift",
            "order_source",
        ],
        order_by="delivery_date desc, creation desc",
        limit_page_length=500,
    )

    for order in orders:
        full_order = frappe.get_doc("AMD Orders", order.name)
        order["items"] = []

        for row in full_order.extra_items or []:
            item_code = (row.item or "").strip()
            qty = flt(row.quantity)

            if not item_code or qty <= 0:
                continue

            item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code

            order["items"].append({
                "item": item_code,
                "item_name": item_name,
                "quantity": qty,
            })

    return orders


@frappe.whitelist()
def create_manual_sales_invoices_from_orders(order_names):
    """
    Create Sales Invoice for selected AMD Orders.

    Important:
    - Only for orders with invoice_pending = 1
    - Only for Manually Billing customers
    - Creates one Sales Invoice per AMD Order
    - After invoice is created, invoice_pending is unchecked
    """

    frappe.only_for(("AMD App Order Creator", "System Manager"))

    if isinstance(order_names, str):
        try:
            order_names = json.loads(order_names)
        except Exception:
            frappe.throw("Invalid order_names format")

    if not order_names or not isinstance(order_names, list):
        frappe.throw("Please select at least one order")

    created_invoices = []
    skipped_orders = []

    for order_name in order_names:
        try:
            invoice_name = create_manual_sales_invoice_from_single_order(order_name)

            if invoice_name:
                created_invoices.append({
                    "order": order_name,
                    "sales_invoice": invoice_name,
                })
            else:
                skipped_orders.append({
                    "order": order_name,
                    "reason": "Invoice not created",
                })

        except Exception as e:
            skipped_orders.append({
                "order": order_name,
                "reason": str(e),
            })

    frappe.db.commit()

    return {
        "created": created_invoices,
        "skipped": skipped_orders,
    }


def create_manual_sales_invoice_from_single_order(order_name):
    """
    Force-create Sales Invoice for manual billing pending order.
    This does not call create_sales_invoice_from_amd_order(),
    because that function skips invoice_pending/manual billing orders.
    """

    order = frappe.get_doc("AMD Orders", order_name)

    if not order.customer:
        frappe.throw(f"Customer missing in order {order.name}")

    customer_billing = frappe.db.get_value(
        "Customer",
        order.customer,
        "custom_dairy_invoice_billing",
    )

    if (customer_billing or "").strip() != "Manually Billing":
        frappe.throw(f"Customer {order.customer} is not Manually Billing")

    if not getattr(order, "invoice_pending", 0):
        frappe.throw(f"Order {order.name} is not invoice pending")

    if (order.order_status or "").strip() != "Delivered":
        frappe.throw(f"Order {order.name} is not Delivered")

    if (order.delivery_status or "").strip() != "COMPLETED":
        frappe.throw(f"Order {order.name} is not COMPLETED")

    existing_invoice = frappe.db.get_value(
        "Sales Invoice",
        {
            "custom_order_reference": order.name,
            "docstatus": ["!=", 2],
        },
        "name",
    )

    if existing_invoice:
        frappe.db.set_value("AMD Orders", order.name, "invoice_pending", 0)
        return existing_invoice

    settings = frappe.get_cached_doc("AMD Dairy Management Settings")

    company = settings.company
    cost_head = settings.cost_head
    warehouse = settings.warehouse
    default_sales_income_account = settings.default_sales_income_account

    if not company:
        frappe.throw("Company is missing in AMD Dairy Management Settings")

    customer_price_list = get_customer_default_price_list(order.customer)

    item_rows = []

    for row in order.extra_items or []:
        item_code = (row.item or "").strip()
        qty = flt(row.quantity)

        if not item_code or qty <= 0:
            continue

        item_doc = frappe.get_cached_doc("Item", item_code)
        uom = item_doc.stock_uom

        price_data = get_dynamic_item_rate(
            customer=order.customer,
            item_code=item_code,
            uom=uom,
        )

        rate = flt(price_data.get("rate"))

        if rate <= 0:
            frappe.throw(f"Rate missing for item {item_code} in order {order.name}")

        item_row = {
            "item_code": item_code,
            "item_name": item_doc.item_name,
            "description": item_doc.description,
            "uom": uom,
            "stock_uom": uom,
            "qty": qty,
            "price_list_rate": rate,
            "rate": rate,
            "amount": rate * qty,
        }

        if warehouse:
            item_row["warehouse"] = warehouse

        if default_sales_income_account:
            item_row["income_account"] = default_sales_income_account

        item_rows.append(item_row)

    if not item_rows:
        frappe.throw(f"No billable items found in order {order.name}")

    inv = frappe.new_doc("Sales Invoice")
    inv.customer = order.customer
    inv.posting_date = nowdate()
    inv.due_date = nowdate()
    inv.company = company
    inv.set_posting_time = 1
    inv.selling_price_list = customer_price_list
    inv.custom_order_reference = order.name

    if cost_head and hasattr(inv, "cost_head"):
        inv.cost_head = cost_head

    if warehouse and hasattr(inv, "set_warehouse"):
        inv.set_warehouse = warehouse

    if default_sales_income_account and hasattr(inv, "default_sales_income_account"):
        inv.default_sales_income_account = default_sales_income_account

    if hasattr(inv, "billing_period_from"):
        inv.billing_period_from = order.delivery_date

    if hasattr(inv, "billing_period_to"):
        inv.billing_period_to = order.delivery_date

    if hasattr(inv, "order_source") and order.order_source:
        inv.order_source = order.order_source

    for item in item_rows:
        inv.append("items", item)

    inv.flags.ignore_permissions = True
    inv.insert(ignore_permissions=True)
    inv.submit()

    frappe.db.set_value("AMD Orders", order.name, "invoice_pending", 0)

    frappe.logger().info(
        f"[MANUAL-INVOICE] Sales Invoice {inv.name} created from AMD Order {order.name}"
    )

    return inv.name