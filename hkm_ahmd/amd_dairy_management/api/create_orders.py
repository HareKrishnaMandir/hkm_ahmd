
import frappe
from frappe.utils import getdate, now, add_days

@frappe.whitelist()
def generate_daily_orders():
    """
    Generate orders automatically from active subscriptions.
    Each subscription creates a separate order (order_source = Subscription).
    """
    today = getdate()
    tomorrow = add_days(today, 1)

    subscriptions = frappe.get_all(
        "AMD Customer Subscription",
        filters={"active": 1},
        fields=["name", "customer", "subscription_type", "route"]
    )
    
    for sub in subscriptions:
        # Skip if today is not a valid subscription day
        if not is_subscription_day(sub.subscription_type, today):
            continue

        # Load subscription details & items
        sub_doc = frappe.get_doc("AMD Customer Subscription", sub.name)
        subscription_items = sub_doc.child_table

        # ⚡ Always create a fresh order (do not merge with App orders)
        order = frappe.new_doc("AMD Orders")
        order.customer = sub.customer
        order.route = sub.route
        order.order_date = today
        order.order_time = now()
        order.delivery_date = tomorrow
        order.delivery_time = now()
        order.delivery_status = "OUT"
        order.order_status = "In Progress"
        order.order_source = "Subscription"   

        # Add subscription items
        for item in subscription_items:
            order.append("extra_items", {
                "item": item.item,
                "quantity": item.quantity
            })

        order.insert()

    frappe.db.commit()


@frappe.whitelist()
def create_app_order(customer, route, delivery_date, items):
    """
    Create an order directly from the mobile app.
    This keeps App orders separate from Subscription orders.

    Args:
        customer (str): Customer ID
        route (str): Delivery route
        delivery_date (str): Date string (YYYY-MM-DD)
        items (list[dict]): [{"item": "ITEM-001", "quantity": 2}, ...]

    Returns:
        str: Order name
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

    for row in items:
        order.append("extra_items", {
            "item": row.get("item"),
            "quantity": row.get("quantity")
        })

    order.insert()
    frappe.db.commit()
    return order.name


def get_extra_items_for_customer(customer, date):
    """
    Placeholder function for fetching extra items from the app.
    Not needed anymore since app should call create_app_order().
    """
    return []


def is_subscription_day(subscription_type, date, sub_doc=None):
    """
    Check if today is a valid subscription day based on subscription type.
    """
    weekday = date.strftime("%A")

    if subscription_type == "Daily":
        return True
    elif subscription_type == "Weekly":
        if sub_doc and sub_doc.delivery_day:
            return weekday == sub_doc.delivery_day
        return False
    elif subscription_type == "Monthly":
        return date.day == 1
    elif subscription_type == "Alternate Days":
        return date.day % 2 == 0
    return False
