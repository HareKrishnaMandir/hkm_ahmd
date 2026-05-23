frappe.query_reports["TM Task Report"] = {
    tree: true,
    name_field: "title",
    parent_field: "parent_row",
    initial_depth: 2,

    filters: [
        {
            fieldname: "from_date",
            label: __("Assigned From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("Assigned To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "tasks_list",
            label: __("Task Category"),
            fieldtype: "Link",
            options: "TM Task Category"
        },
        {
            fieldname: "assign_to",
            label: __("Assign To"),
            fieldtype: "Link",
            options: "TM User"
        },
        {
            fieldname: "department",
            label: __("To Department"),
            fieldtype: "Link",
            options: "TM Departments"
        },
        {
            fieldname: "from_department",
            label: __("From Department"),
            fieldtype: "Link",
            options: "TM From Department"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nNot Started\nAcknowledged\nEditing\nUnder Review\nPrinting\nBilling\nCompleted\nClosed\nWorking On\nHOLD\nHold\nPlanned\nApproval & review\nOrdered\nReplacement\nRepair\nReceived\nIT asset entry\nIssue/Install\nERP asset entry\nCancelled\nRecorded"
        },
        {
            fieldname: "priority",
            label: __("Priority"),
            fieldtype: "Select",
            options: "\nP4\nP3\nP2\nP1"
        },
        {
            fieldname: "overdue_status",
            label: __("Overdue Status"),
            fieldtype: "Select",
            options: "\nOverdue\nExpected Date Overdue\nNot Overdue\nClosed"
        },
        {
            fieldname: "hide_completed",
            label: __("Hide Completed Tasks"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "group_by",
            label: __("Group By"),
            fieldtype: "Select",
            default: "Department Wise Assign To",
            options: "\nDepartment Wise Assign To\nTo Department\nFrom Department\nTask Category\nAssign To\nStatus\nPriority\nAssigned Person\nAssigned Date\nExpected Date\nDue Date\nOverdue Status"
        }
    ]
};