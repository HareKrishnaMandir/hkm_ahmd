
import frappe
from frappe.utils import getdate, now_datetime, nowdate
from datetime import timedelta, date
from collections import defaultdict

# Config
ORDERS_DTYPE = "AMD Orders"
SUBS_DTYPE   = "AMD Customer Subscription"

# Orders
ORDERS_CUSTOMER       = "customer"
ORDERS_DELIVERY_DATE  = "delivery_date"
ORDERS_SOURCE         = "order_source"
ORDERS_ITEMS_CHILD    = "extra_items"    
ORDER_ITEM_FIELD      = "item"
ORDER_QTY_FIELD       = "quantity"

# Subscriptions
SUBS_CUSTOMER         = "customer"
SUBS_ACTIVE           = "active"
SUBS_STATUS           = "status"
SUBS_BILLING_TYPE     = "subscription_billing_type"

PRICE_LIST            = "Standard Selling"
LOG_PREFIX            = "[INV-SCHED]"

# Helpers
def _site_today() -> date:
    """Site-timezone 'today' to avoid UTC vs IST Monday mismatch."""
    return getdate(now_datetime())

def _norm(v: str) -> str:
    return (v or "").strip().lower()

def _last_week_window(today: date):
    """Last complete Mon..Sun before 'today'."""
    prev_monday = today - timedelta(days=today.weekday() + 7)
    prev_sunday = prev_monday + timedelta(days=6)
    return prev_monday, prev_sunday

def _last_month_window(today: date):
    """Full previous calendar month."""
    first_this = today.replace(day=1)
    last_prev  = first_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    return first_prev, last_prev

def _pick_child_field(odoc):
    """Use configured field if present; else auto-detect a table field with .item & .quantity."""
    if hasattr(odoc, ORDERS_ITEMS_CHILD):
        return ORDERS_ITEMS_CHILD
    for df in odoc.meta.get_table_fields():
        rows = getattr(odoc, df.fieldname, None) or []
        if rows:
            r0 = rows[0]
            if hasattr(r0, ORDER_ITEM_FIELD) and hasattr(r0, ORDER_QTY_FIELD):
                return df.fieldname
    return ORDERS_ITEMS_CHILD  # fallback

def _aggregate_items(order_names, child_field):
    agg = defaultdict(float)
    for name in order_names:
        d = frappe.get_doc(ORDERS_DTYPE, name)
        for r in getattr(d, child_field, []) or []:
            code = getattr(r, ORDER_ITEM_FIELD, None)
            qty  = float(getattr(r, ORDER_QTY_FIELD, 0) or 0)
            if code and qty > 0:
                agg[code] += qty
    return agg

def _filter_priced_items(item_qty: dict):
    """Return (priced_items_dict, missing_price_codes) using PRICE_LIST."""
    priced = {}
    missing = []
    for code, qty in item_qty.items():
        rate = frappe.db.get_value(
            "Item Price",
            {"item_code": code, "price_list": PRICE_LIST, "selling": 1},
            "price_list_rate",
        )
        if not rate or float(rate or 0) == 0:
            missing.append(code)
        else:
            priced[code] = qty
    return priced, missing

def _create_invoice(customer, item_qty, period_from, period_to, label):
    inv = frappe.new_doc("Sales Invoice")
    inv.customer         = customer
    inv.posting_date     = nowdate()
    inv.due_date         = nowdate()
    inv.set_posting_time = 1
    inv.company          = "Golden Lotus Foundation"
    inv.cost_head        = "Dairy"

    # Optional custom fields if they exist
    if hasattr(inv, "billing_period_from"):
        inv.billing_period_from = period_from
    if hasattr(inv, "billing_period_to"):
        inv.billing_period_to = period_to

    for item_code, qty in item_qty.items():
        rate = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": PRICE_LIST, "selling": 1},
            "price_list_rate",
        ) or 0
        if not rate or float(rate) == 0:
            frappe.logger().warning(f"{LOG_PREFIX} [{label}] Skip {item_code}: missing price in {PRICE_LIST}")
            continue
        inv.append("items", {"item_code": item_code, "qty": qty, "rate": rate})

    if not inv.items:
        return None

    inv.flags.ignore_permissions = True
    inv.save()
    inv.submit()
    return inv.name

def _best_billing_type_per_customer():
    """Pick highest cadence if multiple subs exist: Daily<Weekly<Monthly."""
    subs = frappe.get_all(
        SUBS_DTYPE,
        filters={SUBS_ACTIVE: 1, SUBS_STATUS: "Active"},
        fields=[SUBS_CUSTOMER, SUBS_BILLING_TYPE],
    )
    if not subs:
        return {}
    priority = {"daily": 1, "weekly": 2, "monthly": 3}
    best = {}
    for s in subs:
        cust = s[SUBS_CUSTOMER]
        bt   = _norm(s[SUBS_BILLING_TYPE] or "monthly")
        if cust not in best or priority.get(bt, 99) < priority.get(best[cust], 99):
            best[cust] = bt
    return best

def _process_period(customers: set, date_from: date, date_to: date, label: str, dry_run: bool):
    """For each customer, collect subscription orders in window and create invoice."""
    created = []
    for customer in customers:
        # fetch all orders in range, then keep only Subscription ones
        orders = frappe.get_all(
            ORDERS_DTYPE,
            filters={ORDERS_CUSTOMER: customer, ORDERS_DELIVERY_DATE: ["between", [date_from, date_to]]},
            fields=["name", ORDERS_SOURCE, ORDERS_DELIVERY_DATE],
            order_by=f"{ORDERS_DELIVERY_DATE} asc",
        )
        orders = [o for o in orders if _norm(o.get(ORDERS_SOURCE)) == "subscription"]
        if not orders:
            continue

        probe = frappe.get_doc(ORDERS_DTYPE, orders[0]["name"])
        child_field = _pick_child_field(probe)

        item_qty = _aggregate_items([o["name"] for o in orders], child_field)
        if not item_qty:
            continue

        priced, missing = _filter_priced_items(item_qty)
        if missing:
            frappe.logger().warning(f"{LOG_PREFIX} [{label}] {customer}: missing prices in {PRICE_LIST}: {missing}")
        if not priced:
            continue

        if dry_run:
            frappe.logger().info(f"{LOG_PREFIX} DRY RUN → would create invoice for {customer} ({date_from}→{date_to})")
            continue

        inv_name = _create_invoice(customer, priced, date_from, date_to, label)
        if inv_name:
            created.append(inv_name)
            frappe.logger().info(f"{LOG_PREFIX} ✅ {inv_name} for {customer} ({date_from}→{date_to})")
    return created

# MAIN (same function name)
@frappe.whitelist()
def generate_subscription_invoices(assume_date: str | None = None, dry_run: int = 0):
    """
    Run daily.
    - If Monday: create invoices for Weekly subscriptions for last Mon–Sun.
    - If 1st:    create invoices for Monthly subscriptions for previous month.
    Testing:
      bench --site <site> execute path.to.generate_subscription_invoices --kwargs '{"assume_date":"2025-10-20","dry_run":1}'
    """
    # Resolve 'today'
    today = getdate(assume_date) if assume_date else _site_today()
    do_weekly  = (today.weekday() == 0)   # Monday
    do_monthly = (today.day == 1)         # 1st

    frappe.logger().info(f"{LOG_PREFIX} today={today} weekly={do_weekly} monthly={do_monthly}")
    if not (do_weekly or do_monthly):
        frappe.logger().info(f"{LOG_PREFIX} Not an anchor day; exiting.")
        return {"today": str(today), "ran": False, "reason": "not_anchor_day"}

    best = _best_billing_type_per_customer()
    if not best:
        frappe.logger().info(f"{LOG_PREFIX} No active subscriptions.")
        return {"today": str(today), "ran": False, "reason": "no_active_subscriptions"}

    weekly_customers  = {c for c, bt in best.items() if bt == "weekly"} if do_weekly else set()
    monthly_customers = {c for c, bt in best.items() if bt == "monthly"} if do_monthly else set()

    created = []
    if weekly_customers:
        wf, wt = _last_week_window(today)
        created += _process_period(weekly_customers, wf, wt, label="weekly", dry_run=bool(int(dry_run)))
    if monthly_customers:
        mf, mt = _last_month_window(today)
        created += _process_period(monthly_customers, mf, mt, label="monthly", dry_run=bool(int(dry_run)))

    return {
        "today": str(today),
        "weekly_customers": len(weekly_customers),
        "monthly_customers": len(monthly_customers),
        "created": created,
        "dry_run": bool(int(dry_run)),
        "ran": True,
    }
