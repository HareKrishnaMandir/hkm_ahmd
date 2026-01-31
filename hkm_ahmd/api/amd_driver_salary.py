import frappe
from frappe.utils import getdate, get_datetime

@frappe.whitelist()
def get_number_summary(vehicle_number, from_date, to_date):
    # Normalize dates
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # Use DATE ONLY here; append times later (fixes double time bug)
    from_date_str = from_date.strftime("%Y-%m-%d")
    to_date_str = to_date.strftime("%Y-%m-%d")

    settings = frappe.get_single("AMD Driver Salary Setting")

    # One fetch is enough
    vehicle_doc = frappe.get_doc("AMD Vehicle Details", vehicle_number)
    vehicle_model = (vehicle_doc.model or "auto").strip()            # keep a string
    fuel_type = (vehicle_doc.fuel_type or "CNG").strip()

    # Fuel rate by type
    if fuel_type.lower() == "petrol":
        fuel_rate = settings.petrol_rate or 0
    elif fuel_type.lower() == "diesel":
        fuel_rate = settings.diesel_rate or 0
    elif fuel_type.lower() == "cng":
        fuel_rate = settings.fuel_rate or 0
    else:
        frappe.throw(f"Invalid fuel type '{fuel_type}' for vehicle {vehicle_number}")

    if not fuel_rate:
        frappe.throw(f"Fuel rate not set for fuel type '{fuel_type}' in Salary Settings")

    extra_rate_per_hour = settings.extra_rate_per_hour or 90
    oil_rate = settings.oil_rate_per_10k_km or 1500

    # Rents by model (treat any 'auto' case-insensitively)
    is_auto = vehicle_model.lower() == "auto"                         # <<< KEY FLAG
    if is_auto:
        full_shift_rent = settings.full_shift_auto_rent_amount or 600
        half_shift_rent = settings.half_shift_auto_rent_amount or 300
        short_shift_rent = settings.short_shift_auto_rent_amount or 0
    else:
        full_shift_rent = settings.full_shift_rent or 1000
        half_shift_rent = settings.half_shift_rent or 500
        short_shift_rent = settings.short_shift_rent or 0

    # rate_per_km lookup (case-insensitive match on model)
    rate_per_km = 0
    for row in settings.rate_per_km or []:
        if (row.model or "").strip().lower() == vehicle_model.lower():
            rate_per_km = row.rate_per_km
            break
    if not rate_per_km:
        frappe.throw(f"Rate per KM not found for vehicle model '{vehicle_model}' in Salary Settings")

    # Attendance window (correct time strings)
    from_date_time = f"{from_date_str} 00:00:00"
    to_date_time = f"{to_date_str} 23:59:59"

    attendance_entries = frappe.get_all(
        "AMD Driver Attendance",
        filters={
            "vehicle_number": vehicle_number,
            "attendance_status": "Check-Out",
            "date": ["between", [from_date, to_date]],
            # "in_time": ["<=", to_date_time],
            # "out_time": [">=", from_date_time],
        },
        fields=["ot", "shift"],
    )

    extra_hours = 0.0
    rent_amount = 0.0
    for entry in attendance_entries:
        ot = float(entry.ot or 0)
        extra_hours += ot
        if entry.shift == "Full Shift":
            rent_amount += full_shift_rent
        elif entry.shift == "Half Shift":
            rent_amount += half_shift_rent
        elif entry.shift == "Short Shift":
            rent_amount += short_shift_rent

    # Vehicle logs within date range (use BETWEEN on DATE objects)
    vehicle_logs = frappe.get_all(
        "AMD Vehicle In-Out Log",
        filters={
            "vehicle_id": vehicle_number,
            "out_date": ["between", [from_date, to_date]],
        },
        fields=["total_km"],
    )

    total_km = sum(float((log.get("total_km") if isinstance(log, dict) else log.total_km) or 0) for log in vehicle_logs)

    # Oil amount: skip for Auto (this is your main issue)        <<< FIX
    if is_auto:
        oil_amount = 0.0
    else:
        oil_amount = (total_km / 10000.0) * oil_rate if total_km else 0.0

    # Base & extras
    base_salary = (total_km / rate_per_km) * fuel_rate if total_km else 0.0
    extra_salary = float(extra_hours) * float(extra_rate_per_hour)
    final_salary = base_salary + extra_salary + rent_amount + oil_amount

    return {
        "total_km": round(total_km, 2),
        "extra_hours": round(extra_hours, 2),
        "base_salary": round(base_salary, 2),
        "extra_salary": round(extra_salary, 2),
        "rent_amount": round(rent_amount, 2),
        "oil_amount": round(oil_amount, 2),
        "final_salary": round(final_salary, 2),
    }




def calculate_total_rent_days(driver_name, from_date, to_date):
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # --- Get vehicle info for this driver directly ---
    vehicle = frappe.db.get_value(
        "AMD Vehicle Details",
        {"driver_name": driver_name},
        ["license_plate_number", "model"],
        as_dict=True
    )

    model = vehicle.model if vehicle and vehicle.model else None

    # --- Fetch attendance records by Check-Out Date ---
    attendance_records = frappe.get_all(
        "AMD Driver Attendance",
        filters={
            # "driver_name": driver_name,
            "vehicle_number": vehicle.license_plate_number,
            "attendance_status": "Check-Out",
            "date": ["between", [from_date, to_date]]
        },
        fields=["date", "shift"],
        order_by="modified desc"
    )
    print(f"Attendance {attendance_records}")
    rent_days = {}

    for record in attendance_records:
        date = str(record.get("date"))
        shift = record.get("shift")

        # If already counted this date, skip (ensure 1 record per day)
        if date in rent_days:
            continue

        # Normalize spelling and case
        if model and model.strip().lower() == "auto":
            rent_days[date] = 1
        else:
            if shift == "Full Shift":
                rent_days[date] = 1
            elif shift == "Half Shift":
                rent_days[date] = 0.5
            elif shift == "Short Shift":
                rent_days[date] = 0
            else:
                rent_days[date] = 0

    return sum(rent_days.values())
