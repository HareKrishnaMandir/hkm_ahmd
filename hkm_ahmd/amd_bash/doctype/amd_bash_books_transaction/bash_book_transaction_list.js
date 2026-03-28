frappe.listview_settings['AMD Bash Book Transaction'] = {
    get_indicator: function(doc) {
        if (doc.status === 'Issue') {
            return [__("Issue"), "red", "status,=,Issue"];
        } else if (doc.status === "Return") {
            return [__("Return"), "blue", "status,=,Return"];
        }
    }
};