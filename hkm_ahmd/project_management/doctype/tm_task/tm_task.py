# Copyright (c) 2026, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

# import frappe
# from frappe.model.document import Document


# class TMTask(Document):
# 	pass
# Copyright (c) 2025, HKM Ahmedabad
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, today, getdate, nowdate, add_days, add_months, cint
import re
import json
import requests

# ======================================================
# CONSTANTS
# ======================================================

TASK_DOCTYPE = "TM Task"
PARENTFIELD = "timesheet_table"
TMUSER_DT = "TM User"

# ======================================================
# TIMER LOGIC
# ======================================================

def _child_dt():
    df = frappe.get_meta(TASK_DOCTYPE).get_field(PARENTFIELD)
    if not df or not df.options:
        frappe.throw(f"Field '{PARENTFIELD}' not found or options not set on {TASK_DOCTYPE}.")
    return df.options

def _child_has_is_running():
    try:
        return bool(frappe.get_meta(_child_dt()).get_field("is_running"))
    except Exception:
        return False

def _get_running_row_db(task_name, tm_user=None):
    child_dt = _child_dt()
    filters = {
        "parent": task_name,
        "parenttype": TASK_DOCTYPE,
        "parentfield": PARENTFIELD,
        "to_time": ["is", "not set"],
    }

    if tm_user:
        filters["user"] = tm_user

    if _child_has_is_running():
        filters["is_running"] = 1
        row = frappe.db.get_value(child_dt, filters, ["name", "from_time"], as_dict=True)
        if row:
            return row
        del filters["is_running"]

    return frappe.db.get_value(child_dt, filters, ["name", "from_time"], as_dict=True)

# ======================================================
# WHATSAPP API & NOTIFICATIONS
# ======================================================

def _digits_only_phone(phone):
    if not phone:
        return ""
    p = re.sub(r"\D", "", str(phone))
    if not p.startswith("91"):
        p = "91" + p
    return p

def send_template(to, template_name, variables, language_code="en"):
    API_URL = "https://graph.facebook.com/v19.0/263347100194101/messages"
    TOKEN = "EAAE76wtqkL8BO5ZB85fkPqXvkTZAjWhfuTuIBI5ql7ZCXZCSZBWZAMOcSkxwLkLNZCijiQkNWQ9SqkefaYj0KPamwUqJBVvYCjRzfQg5AuZBNAridzTPjxgY0OfDXvpQt0XL2X6smO4nXLkIEwCyJCBn3f0h3CtPLRJze3AX27I486l5qQ8bGAVIbAC0Y4s5KGbt"

    if not API_URL or not TOKEN:
        frappe.log_error("WhatsApp API URL / Token missing", "WA CONFIG ERROR")
        return

    to_clean = _digits_only_phone(to)
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_clean,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(v)} for v in variables],
                }
            ],
        },
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        if r.status_code not in (200, 201):
            frappe.log_error(
                title="WA SEND FAILED",
                message=f"Status: {r.status_code} | Template: {template_name} | Response: {r.text[:300]}"
            )
    except Exception:
        frappe.log_error(title="WA EXCEPTION", message=frappe.get_traceback())

def wa_send_task_to_dept_manager(doc):
    if doc.get_doc_before_save():
        return

    target_dept = doc.get("department")
    if not target_dept:
        return

    manager_name = frappe.db.get_value("TM User", {
        "department_name": target_dept,
        "is_manager": 1,
        "is_active": 1
    }, "name")

    if not manager_name:
        return

    manager_doc = frappe.get_doc("TM User", manager_name)

    if not manager_doc.mobile_no:
        return
    
    task_link = frappe.utils.get_url_to_form("TM Task", doc.name)

    send_template(
        to=manager_doc.mobile_no,
        template_name="task_creation",
        variables=[
            doc.title or doc.name,
            doc.full_name,
            doc.mobile_number,
            today(),
            task_link
        ],
    )

def wa_send_status_to_managers(doc):
    before = doc.get_doc_before_save()
    if not before or before.status == doc.status:
        return

    managers = frappe.get_all(
        TMUSER_DT, 
        filters={"is_manager": 1, "is_active": 1, "department_name": doc.department},
        fields=["mobile_no", "full_name"],
    )

    assignees = ", ".join(
        frappe.get_value(TMUSER_DT, r.tm_user, "full_name")
        for r in doc.get("assign_to") or []
        if r.tm_user
    ) or "Not Assigned"

    for mgr in managers:
        if not mgr.mobile_no:
            continue

        send_template(
            to=mgr.mobile_no,
            template_name="task_status_update",
            variables=[
                doc.status,                                     
                doc.title or doc.name,                          
                assignees,                                      
                frappe.utils.get_url_to_form("TM Task", doc.name), 
            ],
        )


# ======================================================
# TM TASK DOCTYPE CLASS
# ======================================================

class TMTask(Document):
    def onload(self):
        row = _get_running_row_db(self.name)
        self.set_onload("timer_from_time", row.from_time if row else None)

    def validate(self):
        if not _child_has_is_running():
            return
        for r in self.get(PARENTFIELD) or []:
            r.is_running = 1 if (r.from_time and not r.to_time) else 0

    def before_save(self):
        if self.status in ["Completed", "Closed"]:
            self.custom_overdue_status = "Completed"
            
        elif self.expected_date:
            today_date = getdate(nowdate())
            expected = getdate(self.expected_date)
            
            delta = (expected - today_date).days
            if delta > 0:
                self.custom_overdue_status = "On Track"
            elif delta == 0:
                self.custom_overdue_status = "Due Today"
            elif delta >= -3:
                self.custom_overdue_status = "Overdue"
            elif delta >= -7:
                self.custom_overdue_status = "Seriously Overdue"
            else:
                self.custom_overdue_status = "Severely Delayed"
                   
    def before_insert(self):
        self._validate_expected_date()       
    
    def _validate_expected_date(self):
        if not self.expected_date:
            return
        
        today_date = getdate(nowdate())
        selected_date = getdate(self.expected_date)

        if selected_date <= today_date:
            frappe.throw(
                title="Invalid Expected Date",
                msg=f"The Expected Date <b>({self.expected_date})</b> cannot be "
                    f"Today or in the Past. Please select a future date."

            )
            
    def on_update(self):
        # 1. Fire WhatsApp Notifications
        wa_send_task_to_dept_manager(self)
        wa_send_status_to_managers(self)

        # ==========================================================
        # SMART RECURRING ENGINE: Instant Reset vs. Early Completion
        # ==========================================================
        if self.is_recurring == 1 and self.status == "Completed" and self.has_value_changed("status"):
            
            today_date = getdate(nowdate())
            task_due_date = getdate(self.due_date)

            # 1. Figure out what the next chronological day SHOULD be (e.g., Friday)
            next_target = get_strictly_next_date(self, task_due_date)

            # 2. SCENARIO: Late or On-Time Completion
            # If today is Friday (or later), the target has arrived. 
            # We instantly reset it so the user can start tracking time immediately.
            if today_date >= next_target:
                self.db_set("due_date", next_target)
                self.db_set("expected_date",next_target)
                self.db_set("status", "Not Started")
                
                # Clear timesheets for the new cycle
                frappe.db.sql("DELETE FROM `tabTimesheet Table` WHERE parent = %s", self.name)
                
                frappe.msgprint(
                    title="Task Instantly Reset",
                    msg=f"Because you completed this on (or after) the next target day, the system instantly generated the next cycle (Due: {next_target}).",
                    indicator="orange"
                )
            
            # 3. SCENARIO: Early Completion
            # If today is Wed, and the target is Fri (today_date >= next_target is False)
            # It skips the reset block entirely! The task peacefully stays "Completed".
            # The midnight cron job (run_recurring_tasks) will wake it up on Friday.

        if self.get("project"):
            update_project_metrics(self.project)


# ======================================================
# RECURRING TASKS ENGINE (STRICT LOGIC)
# ======================================================

def get_strictly_next_date(task, current_due_date):
    """
    LOGIC: Finds the exact chronological next target date based on the setup, 
    without trying to artificially fast-forward through time.
    """
    interval = cint(task.recurrence_interval) or 1
    
    if task.recurrence_type == "Daily":
        # Hand off to the checkbox scanner
        return get_next_daily_checked_date(current_due_date, task, interval)
        
    elif task.recurrence_type == "Weekly":
        return add_days(current_due_date, 7 * interval)
            
    elif task.recurrence_type == "Monthly":
        return add_months(current_due_date, interval)
        
    return add_days(current_due_date, interval)

def get_next_daily_checked_date(current_date, task, interval):
    """
    LOGIC: Scans the 7 checkboxes day-by-day. If an interval of 1 is set, it finds the 
    very next checked day chronologically. 
    """
    weekday_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    # Failsafe: If the user forgot to check ANY boxes, just behave like a normal daily task.
    has_checked_days = any(task.get(day) for day in weekday_fields)
    if not has_checked_days:
        return add_days(current_date, interval)
        
    next_date = current_date
    valid_days_found = 0
    
    # Move day-by-day until we find the required number of checked boxes.
    while valid_days_found < interval:
        next_date = add_days(next_date, 1)          
        day_index = next_date.weekday()             
        field_name = weekday_fields[day_index]      
        
        if task.get(field_name):                    
            valid_days_found += 1                   
            
    return next_date

def run_recurring_tasks():
    """
    LOGIC: This is the Midnight Cron Job. It ONLY looks for tasks that were completed 
    early and are sleeping. If their target day has finally arrived, it wakes them up.
    """
    today_date = getdate(nowdate())
    
    # Find sleeping tasks that were finished early
    tasks = frappe.get_all(
        TASK_DOCTYPE,  
        filters={"is_recurring": 1, "status": "Completed"},
        fields=["name", "due_date", "recurrence_end_date", "recurrence_type", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    )

    for r in tasks:
        task = frappe.get_doc(TASK_DOCTYPE, r.name)  

        if task.recurrence_end_date and getdate(task.recurrence_end_date) < today_date:
            continue

        # 1. Figure out what day this task is supposed to wake up
        next_target = get_strictly_next_date(task, getdate(task.due_date))
        
        # 2. If today is finally the target day (or somehow later), Wake It Up!
        if today_date >= next_target:
            task.due_date = next_target
            task.expected_date = next_target
            task.status = "Not Started"
            
            # Clear old timer data for the fresh day
            task.set("timesheet_table", []) 
            
            # Save it so it appears fresh on the dashboard
            task.flags.ignore_assign_to = True
            task.save(ignore_permissions=True)

    frappe.db.commit()


# ======================================================
# START / STOP TIMERS 
# ======================================================
    
@frappe.whitelist()
def get_running_timer(task):
    tm_user = _get_tm_user_name(frappe.session.user)
    row = _get_running_row_db(task, tm_user=tm_user)
    return {"from_time": row.from_time if row else None}

def _get_tm_user_name(system_user: str) -> str | None:
    return frappe.db.get_value(
        TMUSER_DT,
        {"user": system_user, "is_active": 1},
        "name"
    )

@frappe.whitelist()
def start_timer(task, activity_type):
    tm_user = _get_tm_user_name(frappe.session.user)
    if not tm_user:
        frappe.throw("No active TM User found for the logged-in user.")

    active_timer = frappe.db.sql("""
        SELECT parent 
        FROM `tabTimesheet Table`
        WHERE user = %s 
          AND (to_time IS NULL OR to_time = '')
        LIMIT 1
    """, (tm_user,), as_dict=True)

    if active_timer:
        running_task = active_timer[0].parent
        if running_task == task:
            frappe.throw("You already have a timer running on this task.")
        else:
            frappe.throw(
                title="Concurrent Timer Blocked",
                msg=f"You cannot start a new timer. You currently have an active timer running on task: <b>{running_task}</b>.<br><br>Please go stop that timer first."
            )

    doc = frappe.get_doc(TASK_DOCTYPE, task)
    doc.append(PARENTFIELD, {
        "activity_type": activity_type,
        "from_time": now_datetime(),
        "user": tm_user,
        "is_running": 1,
    })

    doc.flags.ignore_assign_to = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return True

@frappe.whitelist()
def stop_timer(task, paused_seconds=None, force_user=None):
    if force_user:
        if frappe.session.user != "Administrator":
            frappe.throw("Security Violation: You do not have permission to force-stop another user's timer.")
        tm_user = force_user
    else:
        tm_user = _get_tm_user_name(frappe.session.user)
        if not tm_user:
            frappe.throw("No active TM User found for the logged-in user.")

    doc = frappe.get_doc(TASK_DOCTYPE, task)
    doc.reload()

    has_flag = _child_has_is_running()
    db_row = _get_running_row_db(task, tm_user=tm_user)

    row = None
    if db_row:
        for r in doc.get(PARENTFIELD) or []:
            if r.name == db_row.name:
                row = r
                break

    if not row:
        for r in reversed(doc.get(PARENTFIELD) or []):
            if (r.get("from_time") and not r.get("to_time") and r.get("user") == tm_user):
                row = r
                break

    if not row:
        frappe.throw("No running timer found for your user on this task.")

    started = get_datetime(row.from_time)
    ended = now_datetime()  
    
    MAX_SECONDS = 14400 
    
    total_elapsed_seconds = (ended - started).total_seconds()
    paused_secs = max(0, float(paused_seconds)) if paused_seconds is not None else 0.0
    worked_seconds = max(0.0, total_elapsed_seconds - paused_secs)

    if worked_seconds >= MAX_SECONDS:
        final_worked_seconds = MAX_SECONDS
        from frappe.utils import add_to_date
        row.to_time = add_to_date(row.from_time, seconds=MAX_SECONDS + paused_secs)
    else:
        final_worked_seconds = worked_seconds
        row.to_time = ended

    row.hours = round(final_worked_seconds / 3600.0, 2)

    if has_flag:
        row.is_running = 0

    total_worked = sum(float(rr.get("hours") or 0) for rr in doc.get(PARENTFIELD) or [])
    if hasattr(doc, "total_working_hours"):
        doc.total_working_hours = decimal_to_hhmm(total_worked)
    
    doc.flags.ignore_assign_to = True    
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"hours": row.hours, "total_working_hours": doc.total_working_hours}

def decimal_to_hhmm(decimal_hours):
    try:
        decimal_hours = float(decimal_hours or 0)
    except Exception:
        return 0.0
    
    h = int(decimal_hours)
    m = int(round((decimal_hours - h) * 60))

    if m == 60:
        h += 1
        m = 0

    return float(f"{h}.{m:02d}")


# ======================================================
# SYSTEM AUTOMATIONS (Snapshots & Midnight Tasks)
# ======================================================

def auto_update_overdue_statuses():
    open_tasks = frappe.get_all(
        "TM Task", 
        filters={
            "status": ["not in", ["Completed", "Closed"]],
            "expected_date": ["is", "set"] 
        }
    )
    
    for task in open_tasks:
        try:
            doc = frappe.get_doc("TM Task", task.name)
            doc.flags.ignore_assign_to = True
            doc.save(ignore_permissions=True)
        except frappe.exceptions.MandatoryError as e:
            frappe.logger().warning(f"[TM Task] Skipped {task.name} during midnight update due to missing mandatory field.")
            continue
        except Exception as e:
            frappe.logger().error(f"[TM Task] Failed to auto-update task {task.name}: {str(e)}")
            continue
    
    completed_tasks = frappe.get_all(
        "TM Task",
        filter={
            "status": ["in", ["Completed","Closed"]],
            "custom_overdue_status": ["!=", "Completed"]
        }
    )
    
    for task in completed_tasks:
        try:
            frappe.db.set_value("TM Task", task.name, "custom_overdue_status", "Completed")            
        except Exception as e:
            frappe.logger().error(f"[TM Task] Failed to update overdue status for completed task {task.name}: {str(e)}")
            continue
  
    frappe.db.commit()
    frappe.logger().info(
        f"[TM Task] Midnight status update completed. "
        f"Active: {len(open_tasks)}, Completed/Closed fixed: {len(completed_tasks)}"
    )

def auto_stop_overdue_timers():
    from frappe.utils import time_diff_in_seconds, now_datetime

    running_timers = frappe.db.sql("""
        SELECT parent, name, from_time, user 
        FROM `tabTimesheet Table` 
        WHERE to_time IS NULL OR to_time = ''
    """, as_dict=True)

    now = now_datetime()
    
    for row in running_timers:
        if not row.get("from_time"):
            continue

        elapsed = time_diff_in_seconds(now, row.from_time)
        
        # 4 hours = 14400 seconds
        if elapsed >= 14400:
            try:
                stop_timer(row.parent, paused_seconds=0, force_user=row.user) 
                frappe.logger().info(f"Auto-stopped zombie timer {row.name} on Task {row.parent}")
            except Exception as e:
                frappe.log_error(f"Failed to auto-stop timer {row.name}: {str(e)}", "Timer Auto-Stop Error")

def update_project_metrics(project_name):
    if not project_name:
        return
    
    task_stats = frappe.db.sql("""
        SELECT
            COUNT(name) as total_tasks,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_tasks
        FROM `tabTM Task`
        WHERE project = %s
    """, (project_name,), as_dict=True)[0]
    
    total_tasks = task_stats.get("total_tasks") or 0
    completed_tasks = task_stats.get("completed_tasks") or 0
    
    progress = 0.0
    if total_tasks > 0:
        progress = round((completed_tasks / total_tasks)* 100, 2)
    
    hours_data = frappe.db.sql("""
        SELECT SUM(ts.hours) as raw_total
        FROM `tabTimesheet Table` ts
        JOIN `tabTM Task` t ON ts.parent = t.name
        WHERE t.project = %s
    """, (project_name,), as_dict=True)[0]
    
    row_hours = hours_data.get("raw_total") or 0.0
    formatted_hours = decimal_to_hhmm(row_hours)
    
    target_doctype = "TM Projects" 
    frappe.db.set_value(target_doctype, project_name, {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress": progress,
        "total_working_hours": formatted_hours
    })

    frappe.db.commit()

# ======================================================
# TASKS SNAPSHOT
# ======================================================

def take_morning_snapshot():
    snapshot_date = getdate(today())

    tasks = frappe.db.sql("""
        SELECT
            t.name          AS task_name,
            t.status        AS status,
            t.department    AS department,
            GROUP_CONCAT(DISTINCT a.tm_user SEPARATOR ', ') AS assigned_to,
            GROUP_CONCAT(DISTINCT ts.activity_type SEPARATOR ', ') AS activity_type
        FROM `tabTM Task` t
        LEFT JOIN `tabTM Assign User` a
            ON a.parent = t.name
            AND a.parentfield = 'assign_to'
            AND a.parenttype = 'TM Task'
        LEFT JOIN `tabTimesheet Table` ts
            ON ts.parent = t.name
            AND ts.parentfield = 'timesheet_table'
            AND ts.parenttype = 'TM Task'
            AND DATE(ts.from_time) = CURDATE()
        WHERE
            t.due_date = CURDATE()
            AND t.department IS NOT NULL
        GROUP BY t.name
    """, as_dict=True)

    if not tasks:
        frappe.logger().info("[TM Task Snapshot] No tasks due today.")
        return

    dept_map = {}
    for task in tasks:
        dept = task.department
        if dept not in dept_map:
            dept_map[dept] = []
        dept_map[dept].append(task)

    for department, dept_tasks in dept_map.items():
        existing = frappe.db.exists("TM Tasks Snapshots", {
            "department": department,
            "due_date": snapshot_date
        })
        if existing:
            continue

        doc = frappe.new_doc("TM Tasks Snapshots")
        doc.department = department
        doc.due_date   = snapshot_date

        for task in dept_tasks:
            doc.append("tasks_table", {
                "tasks":                 task.task_name,
                "status":                task.status or "",
                "assigned_to":           task.assigned_to or "",
                "activity_type":         task.activity_type or "",
                "hours":                 0.0,
                "updated_status":        "",
                "updated_assigned_to":   "",
                "updated_due_date":      None,
                "updated_activity_type": ""
            })

        doc.insert(ignore_permissions=True)
        frappe.logger().info(f"[TM Task Snapshot] Morning snapshot created for {department}: {len(dept_tasks)} tasks.")

    frappe.db.commit()

def take_evening_snapshot():
    snapshot_date = getdate(today())

    snapshot_docs = frappe.get_all(
        "TM Tasks Snapshots",
        filters={"due_date": snapshot_date},
        fields=["name", "department"]
    )

    if not snapshot_docs:
        frappe.logger().warning("[TM Task Snapshot] No morning snapshots found for today.")
        return

    for snap in snapshot_docs:
        doc = frappe.get_doc("TM Tasks Snapshots", snap.name)

        task_ids = [row.tasks for row in doc.tasks_table if row.tasks]
        if not task_ids:
            continue

        current_tasks = frappe.db.sql("""
            SELECT
                t.name          AS task_name,
                t.due_date      AS due_date,
                t.status        AS status,
                GROUP_CONCAT(DISTINCT a.tm_user SEPARATOR ', ') AS assigned_to,
                GROUP_CONCAT(DISTINCT ts.activity_type SEPARATOR ', ') AS activity_type
            FROM `tabTM Task` t
            LEFT JOIN `tabTM Assign User` a
                ON a.parent = t.name
                AND a.parentfield = 'assign_to'
                AND a.parenttype = 'TM Task'
            LEFT JOIN `tabTimesheet Table` ts
                ON ts.parent = t.name
                AND ts.parentfield = 'timesheet_table'
                AND ts.parenttype = 'TM Task'
                AND DATE(ts.from_time) = CURDATE()
            WHERE t.name IN %(task_ids)s
            GROUP BY t.name
        """, {"task_ids": task_ids}, as_dict=True)
        
        current_map = {t.task_name: t for t in current_tasks}

        hours_data = frappe.db.sql("""
            SELECT parent as task_name, SUM(hours) as total_hours
            FROM `tabTimesheet Table`
            WHERE DATE(from_time) = %(snapshot_date)s AND parent IN %(task_ids)s
            GROUP BY parent
        """, {
            "snapshot_date": snapshot_date, 
            "task_ids": task_ids
        }, as_dict=True)
        
        hours_map = {d.task_name: d.total_hours for d in hours_data}

        for row in doc.tasks_table:
            current = current_map.get(row.tasks)
            if not current:
                continue

            if current.status != row.status:
                row.updated_status = current.status
            
            if (current.assigned_to or "") != (row.assigned_to or ""):
                row.updated_assigned_to = current.assigned_to or ""

            if getdate(current.due_date) != snapshot_date:
                row.updated_due_date = current.due_date

            if (current.activity_type or "") != (row.activity_type or ""):
                row.updated_activity_type = current.activity_type or ""

            raw_decimal_hours = float(hours_map.get(row.tasks, 0.0))
            row.hours = decimal_to_hhmm(raw_decimal_hours)

        doc.save(ignore_permissions=True)
        frappe.logger().info(f"[TM Task Snapshot] Evening snapshot updated for {snap.department}.")

    frappe.db.commit()