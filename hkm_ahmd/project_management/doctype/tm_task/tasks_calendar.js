frappe.views.calendar["TM Task"] = {
    field_map: {
        "start": "due_date",
        "end": "expected_date",
        "id": "name",
        "title": "title",
        "allday": "allday",
        "progress":"progress"
    },
    gantt: true,
};