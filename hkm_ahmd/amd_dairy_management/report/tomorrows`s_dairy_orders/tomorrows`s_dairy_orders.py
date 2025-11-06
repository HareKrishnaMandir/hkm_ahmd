# Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

def execute(filters=None):
    columns = [
        {"label": "Item", "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": "Total Quantity", "fieldname": "total_qty", "fieldtype": "Float", "width": 150},
        {"label": "No. of Orders", "fieldname": "order_count", "fieldtype": "Int", "width": 120},
    ]

    tomorrow = add_days(today(), 1)

    conditions = "o.delivery_date = %s AND o.docstatus < 2"
    values = [tomorrow]

    # ✅ Add Route filter if selected
    if filters and filters.get("route"):
        conditions += " AND o.route = %s"
        values.append(filters.get("route"))

    data = frappe.db.sql(f"""
        SELECT 
            oi.item AS item,
            SUM(oi.quantity) AS total_qty,
            COUNT(DISTINCT o.name) AS order_count
        FROM 
            `tabAMD Orders` AS o
        JOIN 
            `tabAMD Order Item` AS oi ON oi.parent = o.name
        WHERE 
            {conditions}
        GROUP BY 
            oi.item
        ORDER BY 
            oi.item
    """, tuple(values), as_dict=True)

    return columns, data
