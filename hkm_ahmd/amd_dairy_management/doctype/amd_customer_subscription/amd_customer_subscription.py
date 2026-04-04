# Copyright (c) 2025, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AMDCustomerSubscription(Document):
    def validate(self):
        self.set_alternate_days_flag()

    def set_alternate_days_flag(self):
        subscription_type = (self.subscription_type or "").strip()

        if subscription_type == "Alternate Days":
            self.is_alternate_days = 1
        else:
            self.is_alternate_days = 0