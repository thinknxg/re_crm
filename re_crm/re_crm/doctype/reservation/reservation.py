import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class Reservation(Document):
    def validate(self):
        if getdate(self.valid_till) < getdate(nowdate()):
            frappe.throw(_("Valid Till cannot be in the past."))
        unit_prop = frappe.db.get_value("Unit", self.unit, ["status", "property"],
                                        as_dict=True)
        if self.docstatus == 0 and unit_prop.status != "Vacant":
            frappe.throw(_("Unit {0} is {1}; only Vacant units can be reserved.")
                         .format(self.unit, unit_prop.status))
        self.company = frappe.db.get_value("Property", unit_prop.property, "company")

    def on_submit(self):
        self.db_set("status", "Active")
        frappe.db.set_value("Unit", self.unit, "status", "Reserved")
        pe = self._receive_booking_fee()
        if pe:
            self.db_set("payment_entry", pe)

    def _receive_booking_fee(self):
        """Record the booking fee as an unallocated receipt against the client's
        Customer (on lease conversion it nets off the first rent invoice)."""
        account = frappe.db.get_single_value("RE CRM Settings", "booking_fee_account")
        if not (account and flt(self.booking_fee) > 0):
            return None
        tenant_name = frappe.db.get_value("RE Deal", self.deal, "tenant_name")
        customer = frappe.db.get_value("Customer", {"customer_name": tenant_name})
        if not customer:
            return None  # fee stays tracked on the reservation until a Customer exists
        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.company = self.company
        pe.party_type = "Customer"
        pe.party = customer
        pe.paid_amount = self.booking_fee
        pe.received_amount = self.booking_fee
        pe.paid_to = account
        pe.reference_no = self.name
        pe.reference_date = nowdate()
        pe.insert(ignore_permissions=True)
        pe.submit()
        return pe.name

    def on_cancel(self):
        self.db_set("status", "Cancelled")
        self._release_unit()

    def _release_unit(self):
        if frappe.db.get_value("Unit", self.unit, "status") == "Reserved":
            frappe.db.set_value("Unit", self.unit, "status", "Vacant")

    def expire(self):
        """Called by the daily scheduler."""
        self.db_set("status", "Expired")
        self._release_unit()
        agent = frappe.db.get_value("RE Deal", self.deal, "assigned_agent")
        user = agent and frappe.db.get_value("RE Agent", agent, "user")
        if user:
            frappe.get_doc({
                "doctype": "Notification Log", "for_user": user, "type": "Alert",
                "document_type": self.doctype, "document_name": self.name,
                "subject": _("Reservation {0} on unit {1} expired — unit released.")
                           .format(self.name, self.unit),
            }).insert(ignore_permissions=True)
