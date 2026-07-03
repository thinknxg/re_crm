import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class CommissionEntry(Document):
    def on_submit(self):
        self.db_set("status", "Approved")
        je = self._post_journal_entry()
        if je:
            self.db_set("journal_entry", je)

    def on_cancel(self):
        self.db_set("status", "Draft")

    def _post_journal_entry(self):
        settings = frappe.get_cached_doc("RE CRM Settings")
        expense = settings.commission_expense_account
        payable = settings.commission_payable_account
        if not (expense and payable and self.company):
            return None
        je = frappe.new_doc("Journal Entry")
        je.company = self.company
        je.posting_date = nowdate()
        je.user_remark = _("Commission for deal {0}, agent {1}").format(self.deal, self.agent)
        je.append("accounts", {"account": expense,
                               "debit_in_account_currency": self.commission_amount})
        je.append("accounts", {"account": payable,
                               "credit_in_account_currency": self.commission_amount})
        je.insert(ignore_permissions=True)
        je.submit()
        return je.name

    @frappe.whitelist()
    def mark_paid(self):
        if self.docstatus != 1 or self.status != "Approved":
            frappe.throw(_("Only Approved commissions can be marked Paid."))
        self.db_set("status", "Paid")
        return self.status
