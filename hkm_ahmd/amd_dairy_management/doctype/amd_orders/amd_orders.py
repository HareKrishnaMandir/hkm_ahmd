import frappe
from frappe.utils import getdate, now, add_days, now_datetime
from frappe.model.document import Document


MERGED_SUBSCRIPTION_MARKER = "[MERGED_SUBSCRIPTIONS]"


class AMDOrders(Document):
    pass


@frappe.whitelist()
def generate_daily_orders(target_shift="Morning"):
    """
    Generate subscription orders for tomorrow.

    Merged logic:
    - One Subscription order per customer + shift + delivery_date
    - If same customer has multiple valid subscriptions for same shift/date,
      all items are merged into one order
    - Re-running generator will not duplicate same subscription items
    """
    today = getdate()
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

        delivery_day = (getattr(sub_doc, "delivery_day", None) or "").strip()
        weekday = delivery_date.strftime("%A")
        return weekday == delivery_day if delivery_day else False

    elif subscription_type == "Monthly":
        if is_subscription_paused_on(sub_doc, delivery_date):
            return False

        return delivery_date.day == 1

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