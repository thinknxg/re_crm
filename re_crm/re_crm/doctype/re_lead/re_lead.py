import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime


class RELead(Document):
    def validate(self):
        self._validate_mobile()
        if self.status != "New" and not self.first_contacted_on:
            self.first_contacted_on = now_datetime()

    def _validate_mobile(self):
        digits = (self.mobile or "").strip().lstrip("+").replace(" ", "")
        if not (digits.isdigit() and 7 <= len(digits) <= 15):
            frappe.throw(_("Mobile number {0} does not look valid.").format(self.mobile))

    def after_insert(self):
        settings = frappe.get_cached_doc("RE CRM Settings")
        if settings.sla_minutes:
            self.db_set("sla_due", add_to_date(now_datetime(),
                                               minutes=int(settings.sla_minutes)))
        if settings.auto_assign_leads and not self.assigned_agent:
            agent = _next_agent(settings)
            if agent:
                self.db_set("assigned_agent", agent)
                self._notify_agent(agent)
        if settings.wa_lead_auto_reply:
            from re_crm.notifications import send_whatsapp
            send_whatsapp(
                self.mobile,
                _("Hi {0}, thanks for your inquiry! One of our property consultants "
                  "will contact you shortly.").format(self.full_name),
                reference_doctype=self.doctype, reference_name=self.name)

    def _notify_agent(self, agent):
        user = frappe.db.get_value("RE Agent", agent, "user")
        if not user:
            return
        frappe.get_doc({
            "doctype": "Notification Log", "for_user": user, "type": "Assignment",
            "document_type": self.doctype, "document_name": self.name,
            "subject": _("New lead assigned: {0} ({1})").format(self.full_name, self.mobile),
        }).insert(ignore_permissions=True)

    @frappe.whitelist()
    def make_deal(self):
        if self.deal:
            frappe.throw(_("Deal {0} already exists for this lead.").format(self.deal))
        deal = frappe.new_doc("RE Deal")
        deal.lead = self.name
        deal.tenant_name = self.full_name
        deal.mobile = self.mobile
        deal.assigned_agent = self.assigned_agent
        deal.unit = self.unit_of_interest
        deal.interest_type = self.interest_type
        deal.expected_value = self.budget_max or self.budget_min
        deal.pipeline_stage = "Contacted" if self.first_contacted_on else "New"
        deal.insert()
        self.db_set("deal", deal.name)
        self.db_set("status", "Converted")
        return deal.name


def _next_agent(settings):
    """Round-robin over active agents in the assignment pool."""
    pool = frappe.get_all("RE Agent",
                          filters={"is_active": 1, "in_assignment_pool": 1},
                          order_by="name asc", pluck="name")
    if not pool:
        return None
    last = settings.last_assigned_agent
    nxt = pool[(pool.index(last) + 1) % len(pool)] if last in pool else pool[0]
    frappe.db.set_single_value("RE CRM Settings", "last_assigned_agent", nxt)
    return nxt
