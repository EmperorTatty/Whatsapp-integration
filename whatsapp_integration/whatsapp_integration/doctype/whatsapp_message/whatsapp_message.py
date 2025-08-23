# Copyright (c) 2024, Upeosoft and contributors
# For license information, please see license.txt

import frappe
from frappe.model.naming import getseries
from datetime import datetime
from frappe.model.document import Document


class WhatsappMessage(Document):
	def autoname(self):
		date_obj = datetime.strptime(self.date, '%Y-%m-%d')
		year_month_day = date_obj.strftime('%Y/%m/%d')
		prefix = f"{self.subject}_{year_month_day}"
		series_number = getseries(prefix, 3)
		self.name = f"{prefix}_{series_number}"


	