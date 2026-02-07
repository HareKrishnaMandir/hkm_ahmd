import frappe
from frappe.utils import now_datetime, format_date
from datetime import datetime, timedelta

def send_unchecked_out_vehicle_alert():
    # ✅ Get previous date
    previous_date = now_datetime().date() - timedelta(days=1)
    formatted_date = format_date(previous_date, "d MMMM yyyy")
    start_of_day = datetime.combine(previous_date, datetime.min.time())  # 00:00:00
    end_of_day = datetime.combine(previous_date, datetime.max.time())    # 23:59:59.999999

    # ✅ Get Check-In records from AMD Driver Attendance for previous day
    checkins_yesterday = frappe.get_all(
        "AMD Driver Attendance",
        filters={
            "attendance_status": "Check-In",
            "creation": ["between", [start_of_day, end_of_day]]
        },
        fields=["name", "driver_name", "vehicle_number", "creation"]
    )

    # ✅ Get all AMD Vehicle In-Out Log records with Status = "Out" from previous day
    out_logs_yesterday = frappe.get_all(
        "AMD Vehicle In-Out Log",
        filters={
            "status": "Out",
            "creation": ["between", [start_of_day, end_of_day]]
        },
        fields=["name", "vehicle", "driver_name", "status", "creation"]
    )

    # ✅ If no records for Check-In and Out on previous day → don't send email
    if not checkins_yesterday and not out_logs_yesterday:
        frappe.logger().info("✅ No vehicles were left checked-in or out yesterday.")
        return

    # ✅ Prepare dynamic filter URL date format
    filter_date = previous_date.strftime("%Y-%m-%d")

    # ✅ Construct dynamic list view URLs with date filter
    attendance_link = (
        f"https://hkmerp.in/app/amd-driver-attendance/view/list"
        f"?creation=%5B%22Between%22%2C%5B%22{filter_date}%22%2C%22{filter_date}%22%5D%5D"
        f"&attendance_status=Check-In"
    )

    out_log_link = (
        f"https://hkmerp.in/app/amd-vehicle-in-out-log/view/list"
        f"?creation=%5B%22Between%22%2C%5B%22{filter_date}%22%2C%22{filter_date}%22%5D%5D"
        f"&status=Out"
    )

    # ✅ Compose email message
    message = "<p>Hare Krishna,</p>"

    if checkins_yesterday:
        message += f"""
        <p>🔴 Some vehicles are still <strong>Checked-In</strong> on <strong>{formatted_date}</strong> in 
        <strong>AMD Driver Attendance</strong>.</p>
        <p><a href="{attendance_link}" target="_blank">Click here to view Check-In records</a>.</p>
        """

    if out_logs_yesterday:
        message += f"""
        <p>🔴 Some vehicles are still marked as <strong>Status = Out</strong> in 
        <strong>AMD Vehicle In-Out Log</strong> on <strong>{formatted_date}</strong>.</p>
        <p><a href="{out_log_link}" target="_blank">Click here to view Out records</a>.</p>
        """

    message += """
    <p>Please ensure all vehicles are properly Checked-Out or marked as In before day-end.</p>
    <p>Regards,<br>ERP System – Hare Krishna Mandir</p>
    """

    subject = f"🚗 Vehicle Out / Check-In Alert – {formatted_date}"

    sender_email = frappe.get_value("Email Account", {"email_id": "hkma.erp@gmail.com"}, "email_id")

    frappe.sendmail(
        recipients=["haresh.vaghela@harekrishnamandir.org","ajay.padhya@harekrishnamandir.org"],
        subject=subject,
        message=message,
        sender=sender_email or None
    )


