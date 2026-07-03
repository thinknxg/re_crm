"""Scheduled jobs for re_crm."""

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime, nowdate

from re_crm.notifications import send_whatsapp


# ---------------------------------------------------------------- hourly

def lead_sla_escalation():
    settings = frappe.get_cached_doc("RE CRM Settings")
    breached = frappe.get_all(
        "RE Lead",
        filters={"status": "New", "sla_breached": 0,
                 "sla_due": ["<", now_datetime()]},
        fields=["name", "full_name", "mobile", "assigned_agent"])
    for lead in breached:
        frappe.db.set_value("RE Lead", lead.name, "sla_breached", 1)
        if settings.escalation_user:
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": settings.escalation_user, "type": "Alert",
                "document_type": "RE Lead", "document_name": lead.name,
                "subject": _("SLA breached: lead {0} ({1}) not contacted — agent {2}")
                           .format(lead.full_name, lead.mobile,
                                   lead.assigned_agent or _("unassigned")),
            }).insert(ignore_permissions=True)


def site_visit_reminders():
    """WhatsApp the client ~3h before the visit (fires once per visit)."""
    if not frappe.db.get_single_value("RE CRM Settings", "wa_visit_reminders"):
        return
    window_end = add_to_date(now_datetime(), hours=3)
    visits = frappe.get_all(
        "Site Visit",
        filters={"reminder_sent": 0, "outcome": ["in", ["", None]],
                 "visit_datetime": ["between", [now_datetime(), window_end]]},
        fields=["name", "deal", "unit", "visit_datetime", "client_mobile"])
    for visit in visits:
        if visit.client_mobile:
            unit_title = frappe.db.get_value("Unit", visit.unit, "unit_title") or visit.unit
            send_whatsapp(
                visit.client_mobile,
                _("Reminder: your property viewing at {0} is scheduled for {1}. "
                  "See you there!").format(
                    unit_title, get_datetime(visit.visit_datetime).strftime("%d %b, %I:%M %p")),
                reference_doctype="Site Visit", reference_name=visit.name)
        frappe.db.set_value("Site Visit", visit.name, "reminder_sent", 1)


# ---------------------------------------------------------------- daily

def release_expired_reservations():
    warn = frappe.db.get_single_value("RE CRM Settings", "wa_reservation_expiry")
    # Warn one day ahead
    if warn:
        expiring = frappe.get_all(
            "Reservation",
            filters={"docstatus": 1, "status": "Active",
                     "valid_till": add_days(nowdate(), 1)},
            fields=["name", "deal", "unit", "valid_till"])
        for res in expiring:
            mobile = frappe.db.get_value("RE Deal", res.deal, "mobile")
            if mobile:
                send_whatsapp(
                    mobile,
                    _("Your reservation {0} expires tomorrow ({1}). Please complete "
                      "the lease signing to secure the unit.").format(res.name, res.valid_till),
                    reference_doctype="Reservation", reference_name=res.name)
    # Release the expired
    for name in frappe.get_all("Reservation",
                               filters={"docstatus": 1, "status": "Active",
                                        "valid_till": ["<", nowdate()]},
                               pluck="name"):
        frappe.get_doc("Reservation", name).expire()


def rent_due_whatsapp_reminders():
    """Rides on re_core Rent Schedules: nudge tenants N days before due date."""
    settings = frappe.get_cached_doc("RE CRM Settings")
    if not settings.wa_rent_reminders:
        return
    target = add_days(nowdate(), int(settings.rent_reminder_days or 5))
    rows = frappe.db.sql(
        """
        SELECT ri.name, ri.due_date, ri.amount, rs.tenant
        FROM `tabRent Installment` ri
        JOIN `tabRent Schedule` rs ON rs.name = ri.parent
        WHERE ri.status IN ('Pending', 'Invoiced') AND ri.due_date = %s
          AND rs.status = 'Active'
        """, target, as_dict=True)
    for row in rows:
        tenant = frappe.db.get_value(
            "Tenant", row.tenant, ["tenant_name", "whatsapp_number", "mobile"],
            as_dict=True)
        number = tenant.whatsapp_number or tenant.mobile
        if number:
            send_whatsapp(
                number,
                _("Dear {0}, a rent installment of {1} is due on {2}. "
                  "Thank you!").format(tenant.tenant_name,
                                       frappe.utils.fmt_money(row.amount),
                                       row.due_date),
                reference_doctype="Rent Installment", reference_name=row.name)
