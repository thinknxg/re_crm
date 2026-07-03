import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

STAGES = ["New", "Contacted", "Site Visit Scheduled", "Negotiation",
          "Reservation", "Won", "Lost"]


class REDeal(Document):
    def validate(self):
        self.title = f"{self.tenant_name} — {self.unit or self.interest_type}"
        if self.pipeline_stage == "Won":
            self._validate_won()
        if self.pipeline_stage == "Lost" and not self.lost_reason:
            frappe.throw(_("Please record a Lost Reason."))

    def _validate_won(self):
        if not self.lease_contract:
            frappe.throw(_("A submitted Lease Contract is required to mark a deal Won."))
        docstatus, status = frappe.db.get_value(
            "Lease Contract", self.lease_contract, ["docstatus", "status"])
        if docstatus != 1:
            frappe.throw(_("Lease Contract {0} is not submitted.").format(self.lease_contract))

    def on_update(self):
        if self.pipeline_stage == "Won" and not self.commission_entry:
            entry = self._draft_commission()
            if entry:
                self.db_set("commission_entry", entry)
        if self.pipeline_stage == "Won" and self.reservation:
            if frappe.db.get_value("Reservation", self.reservation, "status") == "Active":
                frappe.db.set_value("Reservation", self.reservation, "status", "Converted")
        if self.pipeline_stage == "Won" and self.lead:
            frappe.db.set_value("RE Lead", self.lead, "status", "Converted")

    def _draft_commission(self):
        if not self.assigned_agent:
            return None
        agent = frappe.get_doc("RE Agent", self.assigned_agent)
        base = flt(frappe.db.get_value("Lease Contract", self.lease_contract,
                                       "total_contract_value")) or flt(self.expected_value)
        amount = compute_commission(agent, base)
        if not amount:
            return None
        entry = frappe.new_doc("Commission Entry")
        entry.agent = agent.name
        entry.deal = self.name
        entry.lease_contract = self.lease_contract
        entry.company = frappe.db.get_value("Lease Contract", self.lease_contract, "company")
        entry.base_amount = base
        entry.commission_amount = amount
        entry.insert(ignore_permissions=True)
        return entry.name


def compute_commission(agent, base):
    base = flt(base)
    if agent.commission_type == "Flat":
        return flt(agent.flat_amount)
    if agent.commission_type == "Percent":
        return flt(base * flt(agent.percent) / 100, 3)
    if agent.commission_type == "Tiered":
        for slab in agent.slabs:
            if flt(slab.from_amount) <= base <= flt(slab.to_amount):
                return flt(base * flt(slab.percent) / 100, 3)
        return 0
    return 0
