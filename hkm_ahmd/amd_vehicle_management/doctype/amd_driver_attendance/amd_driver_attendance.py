# # Copyright (c) 2025, HKM Ahmedabad and contributors
# # For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import time_diff_in_hours, date_diff
class AMDDriverAttendance(Document):
    pass
    def get_duration(self):
        if self.in_time and self.out_time:
            # if self.date == self.in_date:
            duration = time_diff_in_hours((self.out_time), (self.in_time))
            frappe.msgprint(f'Duration {duration}')
            return duration
            # else:
            #     day_diff = date_diff(str(self.in_date) , str(self.date))
            #     frappe.msgprint(f"Duration is:{day_diff}")     
            #     print()           
        else:
            return None
    def before_save(self):
        if self.attendance_status == "Check-Out":
            duration = self.get_duration()
            if duration is not None:
                self.duration = duration

                # Overtime logic
                if self.duration > 10:
                    extra_hours = self.duration - 10

                    # Only count if at least 1 full extra hour completed
                    if extra_hours >= 1:
                        whole_hours = int(extra_hours)   # completed full hours
                        minutes = (extra_hours - whole_hours) * 60

                        # Round OT based on minutes
                        if minutes >= 45:
                            ot_fraction = 1
                        elif minutes >= 30:
                            ot_fraction = 0.5
                        else:
                            ot_fraction = 0

                        self.ot = whole_hours + ot_fraction
                    else:
                        self.ot = 0
                else:
                    self.ot = 0

                # Shift classification
                if self.duration <= 5:
                    self.shift = "Short Shift"
                elif 5 < self.duration < 9.5:
                    self.shift = "Half Shift"
                elif self.duration >= 9.5:
                    self.shift = "Full Shift"

