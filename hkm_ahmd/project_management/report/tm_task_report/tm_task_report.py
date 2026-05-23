import frappe
from frappe import _


ASSIGN_TO_CHILD_DT = "TM Assign User"
ASSIGN_TO_PARENTFIELD = "assign_to"


def get_assign_to_link_field():
    """
    Finds the Link field inside TM Assign User child table automatically.
    Example possible fieldnames: user, assign_to, tm_user
    """
    meta = frappe.get_meta(ASSIGN_TO_CHILD_DT)

    for df in meta.fields:
        if df.fieldtype == "Link":
            return df.fieldname

    frappe.throw(_("No Link field found in {0}").format(ASSIGN_TO_CHILD_DT))


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Task / Group"),
            "fieldname": "title",
            "fieldtype": "Data",
            "width": 300
        },
        {
            "label": _("Task ID"),
            "fieldname": "task_id",
            "fieldtype": "Link",
            "options": "TM Task",
            "width": 160
        },
        {
            "label": _("Task Category"),
            "fieldname": "task_category",
            "fieldtype": "Link",
            "options": "TM Task Category",
            "width": 180
        },
        {
            "label": _("Assign To"),
            "fieldname": "assign_to",
            "fieldtype": "Data",
            "width": 220
        },
        {
            "label": _("From Department"),
            "fieldname": "from_department",
            "fieldtype": "Link",
            "options": "TM From Department",
            "width": 180
        },
        {
            "label": _("To Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "TM Departments",
            "width": 180
        },
        {
            "label": _("Assigned Full Name"),
            "fieldname": "full_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Assigned Date"),
            "fieldname": "assigned_date",
            "fieldtype": "Date",
            "width": 130
        },
        {
            "label": _("Expected Date"),
            "fieldname": "expected_date",
            "fieldtype": "Date",
            "width": 130
        },
        {
            "label": _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
            "width": 130
        },
        {
            "label": _("Priority"),
            "fieldname": "priority",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Overdue Status"),
            "fieldname": "overdue_status",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Total Working Hours"),
            "fieldname": "total_working_hours",
            "fieldtype": "Float",
            "width": 160
        },
        {
            "label": _("Time in Hours"),
            "fieldname": "hours_duration",
            "fieldtype": "Duration",
            "width": 140
        }
    ]


def get_data(filters):
    assign_to_link_field = get_assign_to_link_field()
    conditions = get_conditions(filters, assign_to_link_field)

    query = f"""
        SELECT
            t.name AS task_id,
            t.title AS title,
            t.tasks_list AS task_category,
            t.project AS project,

            t.from_department AS from_department,
            t.department AS department,

            t.full_name AS full_name,

            DATE(t.creation) AS assigned_date,
            t.expected_date AS expected_date,
            t.due_date AS due_date,

            t.priority AS priority,
            t.status AS status,

            CASE
                WHEN t.status IN ('Completed', 'Closed', 'Cancelled') THEN 'Closed'
                WHEN t.due_date IS NOT NULL AND t.due_date < CURDATE() THEN 'Overdue'
                WHEN t.expected_date IS NOT NULL AND t.expected_date < CURDATE() THEN 'Expected Date Overdue'
                ELSE 'Not Overdue'
            END AS overdue_status,

            t.total_working_hours AS total_working_hours,
            t.hours_duration AS hours_duration,

            (
                SELECT GROUP_CONCAT(atu.`{assign_to_link_field}` SEPARATOR ', ')
                FROM `tab{ASSIGN_TO_CHILD_DT}` atu
                WHERE
                    atu.parent = t.name
                    AND atu.parenttype = 'TM Task'
                    AND atu.parentfield = '{ASSIGN_TO_PARENTFIELD}'
            ) AS assign_to

        FROM
            `tabTM Task` t

        WHERE
            t.docstatus < 2
            {conditions}

        ORDER BY
            t.department,
            assign_to,
            t.status,
            t.due_date ASC
    """

    tasks = frappe.db.sql(query, filters, as_dict=True)

    return make_dynamic_grouped_data(tasks, filters)


def get_conditions(filters, assign_to_link_field):
    conditions = ""

    if filters.get("from_date"):
        conditions += " AND DATE(t.creation) >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND DATE(t.creation) <= %(to_date)s"

    if filters.get("tasks_list"):
        conditions += " AND t.tasks_list = %(tasks_list)s"

    if filters.get("hide_completed"):
        conditions += """
            AND t.status NOT IN ('Completed', 'Closed', 'Cancelled')
        """

    if filters.get("assign_to"):
        conditions += f"""
            AND EXISTS (
                SELECT 1
                FROM `tab{ASSIGN_TO_CHILD_DT}` atu_filter
                WHERE
                    atu_filter.parent = t.name
                    AND atu_filter.parenttype = 'TM Task'
                    AND atu_filter.parentfield = '{ASSIGN_TO_PARENTFIELD}'
                    AND atu_filter.`{assign_to_link_field}` = %(assign_to)s
            )
        """

    if filters.get("department"):
        conditions += " AND t.department = %(department)s"

    if filters.get("from_department"):
        conditions += " AND t.from_department = %(from_department)s"

    if filters.get("status"):
        conditions += " AND t.status = %(status)s"

    if filters.get("priority"):
        conditions += " AND t.priority = %(priority)s"

    if filters.get("overdue_status"):
        overdue_status = filters.get("overdue_status")

        if overdue_status == "Overdue":
            conditions += """
                AND t.status NOT IN ('Completed', 'Closed', 'Cancelled')
                AND t.due_date IS NOT NULL
                AND t.due_date < CURDATE()
            """

        elif overdue_status == "Expected Date Overdue":
            conditions += """
                AND t.status NOT IN ('Completed', 'Closed', 'Cancelled')
                AND t.expected_date IS NOT NULL
                AND t.expected_date < CURDATE()
            """

        elif overdue_status == "Not Overdue":
            conditions += """
                AND t.status NOT IN ('Completed', 'Closed', 'Cancelled')
                AND (
                    t.due_date IS NULL OR t.due_date >= CURDATE()
                )
                AND (
                    t.expected_date IS NULL OR t.expected_date >= CURDATE()
                )
            """

        elif overdue_status == "Closed":
            conditions += """
                AND t.status IN ('Completed', 'Closed', 'Cancelled')
            """

    return conditions


def make_dynamic_grouped_data(tasks, filters):
    group_by = filters.get("group_by") or "Department Wise Assign To"

    if group_by == "Department Wise Assign To":
        return make_department_assign_to_grouped_data(tasks)

    group_field_map = {
        "To Department": "department",
        "From Department": "from_department",
        "Task Category": "task_category",
        "Assign To": "assign_to",
        "Status": "status",
        "Priority": "priority",
        "Assigned Person": "full_name",
        "Assigned Date": "assigned_date",
        "Expected Date": "expected_date",
        "Due Date": "due_date",
        "Overdue Status": "overdue_status"
    }

    group_field = group_field_map.get(group_by, "department")

    grouped = {}

    for task in tasks:
        group_value = task.get(group_field) or "Not Set"
        group_label = f"{group_by}: {group_value}"

        if group_label not in grouped:
            grouped[group_label] = []

        grouped[group_label].append(task)

    data = []
    total_groups = len(grouped)

    for index, (group_label, group_tasks) in enumerate(grouped.items()):
        data.append(make_group_row(group_label))

        for task in group_tasks:
            data.append(make_task_row(task, group_label, 1))

        if index < total_groups - 1:
            data.append(make_blank_row())

    return data


def make_department_assign_to_grouped_data(tasks):
    grouped = {}

    for task in tasks:
        department = task.get("department") or "Not Set"
        assign_to = task.get("assign_to") or "Not Assigned"

        if department not in grouped:
            grouped[department] = {}

        if assign_to not in grouped[department]:
            grouped[department][assign_to] = []

        grouped[department][assign_to].append(task)

    data = []
    total_departments = len(grouped)

    for dept_index, (department, assign_groups) in enumerate(grouped.items()):
        department_row_id = f"Department: {department}"

        data.append({
            "title": department,
            "parent_row": "",
            "indent": 0,
            "task_id": "",
            "task_category": "",
            "assign_to": "",
            "from_department": "",
            "department": department,
            "full_name": "",
            "assigned_date": "",
            "expected_date": "",
            "due_date": "",
            "priority": "",
            "status": "",
            "overdue_status": "",
            "total_working_hours": "",
            "hours_duration": "",
            "is_group": 1
        })

        for assign_to, group_tasks in assign_groups.items():
            assign_row_id = f"{department_row_id} - Assign To: {assign_to}"

            data.append({
                "title": assign_to,
                "parent_row": department_row_id,
                "indent": 1,
                "task_id": "",
                "task_category": "",
                "assign_to": assign_to,
                "from_department": "",
                "department": department,
                "full_name": "",
                "assigned_date": "",
                "expected_date": "",
                "due_date": "",
                "priority": "",
                "status": "",
                "overdue_status": "",
                "total_working_hours": "",
                "hours_duration": "",
                "is_group": 1
            })

            for task in group_tasks:
                data.append(make_task_row(task, assign_row_id, 2))

        if dept_index < total_departments - 1:
            data.append(make_blank_row())

    return data


def make_group_row(group_label):
    return {
        "title": group_label,
        "parent_row": "",
        "indent": 0,
        "task_id": "",
        "task_category": "",
        "assign_to": "",
        "from_department": "",
        "department": "",
        "full_name": "",
        "assigned_date": "",
        "expected_date": "",
        "due_date": "",
        "priority": "",
        "status": "",
        "overdue_status": "",
        "total_working_hours": "",
        "hours_duration": "",
        "is_group": 1
    }


def make_task_row(task, parent_row, indent):
    return {
        "title": task.get("title") or task.get("task_id"),
        "parent_row": parent_row,
        "indent": indent,

        "task_id": task.get("task_id"),
        "task_category": task.get("task_category"),
        "assign_to": task.get("assign_to"),
        "from_department": task.get("from_department"),
        "department": task.get("department"),
        "full_name": task.get("full_name"),
        "assigned_date": task.get("assigned_date"),
        "expected_date": task.get("expected_date"),
        "due_date": task.get("due_date"),
        "priority": task.get("priority"),
        "status": task.get("status"),
        "overdue_status": task.get("overdue_status"),
        "total_working_hours": task.get("total_working_hours"),
        "hours_duration": task.get("hours_duration")
    }


def make_blank_row():
    return {
        "title": "",
        "parent_row": "",
        "indent": 0,
        "task_id": "",
        "task_category": "",
        "assign_to": "",
        "from_department": "",
        "department": "",
        "full_name": "",
        "assigned_date": "",
        "expected_date": "",
        "due_date": "",
        "priority": "",
        "status": "",
        "overdue_status": "",
        "total_working_hours": "",
        "hours_duration": ""
    }