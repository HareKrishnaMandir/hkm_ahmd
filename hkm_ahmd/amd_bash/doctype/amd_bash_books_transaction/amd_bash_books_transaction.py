# Copyright (c) 2026, Hare Krishna Movement Ahmedabad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
class AMDBashBooksTransaction(Document):

    def before_save(self):
        if not hasattr(self, 'books'):
            frappe.throw("Field 'books' not found in BASHBookTransaction document")
        # Handle book status and return date based on transaction type
			
        # Fetch the linked book document
        book = frappe.get_doc("AMD Bash Books", self.books)

        if self.status == "Issue":
            if book.status == "Available":
                # Update book status to "Issued"
                book.status = "Issued"
                book.save()
            else:
                frappe.throw(f"The book '{book.title}' is already issued.")

        elif self.status == "Return":
            # Automatically fill the return date if not provided
            if not self.return_date:
               self.return_date = nowdate()

            if book.status == "Issued":
                # Update book status to "Available"
                book.status = "Available"
                book.save()
            else:
                frappe.throw(f"The book '{book.title}' is not currently issued.")
