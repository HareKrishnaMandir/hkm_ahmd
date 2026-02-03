app_name = "hkm_ahmd"
app_title = "HKM Ahmedabad"
app_publisher = "Hare Krishna Movement Ahmedabad"
app_description = "Dairy and Hotel Management"
app_email = "developer@harekrishnamandir.org"
app_license = "mit"
scheduler_events = {
    "daily":[
        "hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_requestor.amd_vehicle_requestor.reset_disabled_requestors",
        "hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_in_out_log.amd_vehicle_in_out_log.reset_vehicle_trip"
    ],
    "hourly": [
        "hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_assignment.amd_vehicle_assignment.check_vehicle_status_and_notify",
    ],
    "cron": {
        "0 17 * * *": [
            "hkm_ahmd.amd_dairy_management.api.create_orders.generate_daily_orders"
        ],
        "0 8 * * *": [
            "hkm_ahmd.amd_dairy_management.events.invoice.generate_subscription_invoices"
        ],
        "*/5 * * * *": [
            "hkm_ahmd.amd_vehicle_management.doctype.amd_vehicle_assignment.amd_vehicle_assignment.update_vehicle_status",
            "hkm_ahmd.tasks.vehicle_availability.update_vehicle_availability_status",
        ],
    }
}
# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "hkm_ahmd",
# 		"logo": "/assets/hkm_ahmd/logo.png",
# 		"title": "HKM Ahmedabad",
# 		"route": "/hkm_ahmd",
# 		"has_permission": "hkm_ahmd.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hkm_ahmd/css/hkm_ahmd.css"
# app_include_js = "/assets/hkm_ahmd/js/hkm_ahmd.js"

# include js, css files in header of web template
# web_include_css = "/assets/hkm_ahmd/css/hkm_ahmd.css"
# web_include_js = "/assets/hkm_ahmd/js/hkm_ahmd.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hkm_ahmd/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "hkm_ahmd/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "hkm_ahmd.utils.jinja_methods",
# 	"filters": "hkm_ahmd.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "hkm_ahmd.install.before_install"
# after_install = "hkm_ahmd.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "hkm_ahmd.uninstall.before_uninstall"
# after_uninstall = "hkm_ahmd.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "hkm_ahmd.utils.before_app_install"
# after_app_install = "hkm_ahmd.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "hkm_ahmd.utils.before_app_uninstall"
# after_app_uninstall = "hkm_ahmd.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hkm_ahmd.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"hkm_ahmd.tasks.all"
# 	],
# 	"daily": [
# 		"hkm_ahmd.tasks.daily"
# 	],
# 	"hourly": [
# 		"hkm_ahmd.tasks.hourly"
# 	],
# 	"weekly": [
# 		"hkm_ahmd.tasks.weekly"
# 	],
# 	"monthly": [
# 		"hkm_ahmd.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "hkm_ahmd.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hkm_ahmd.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "hkm_ahmd.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["hkm_ahmd.utils.before_request"]
# after_request = ["hkm_ahmd.utils.after_request"]

# Job Events
# ----------
# before_job = ["hkm_ahmd.utils.before_job"]
# after_job = ["hkm_ahmd.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"hkm_ahmd.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

