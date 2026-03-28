frappe.listview_settings['AMD Bash Books'] = {
    get_indicator: function(doc) {
        if (doc.status === "Issued") {
            return [__("Issued"), "red", "status,=,Issued"];
        } else if (doc.status === "Available") {
            return [__("Available"), "green", "status,=,Available"];
        }
    }
};