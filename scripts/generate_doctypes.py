#!/usr/bin/env python3
"""re_crm DocType JSON generator. Controllers are hand-maintained."""
import json, os, re

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE = "RE CRM"
DOCTYPE_DIR = os.path.join(APP_ROOT, "re_crm", "re_crm", "doctype")
TS = "2026-01-01 00:00:00.000000"

STAGES = "New\nContacted\nSite Visit Scheduled\nNegotiation\nReservation\nWon\nLost"


def scrub(n): return re.sub(r"[\s-]+", "_", n.strip().lower())


def f(fieldname, fieldtype="Data", label=None, **kw):
    d = {"fieldname": fieldname, "fieldtype": fieldtype,
         "label": label or fieldname.replace("_", " ").title()}
    d.update(kw); return d


def sb(fieldname, label="", **kw): return f(fieldname, "Section Break", label, **kw)
def cb(i): return f(f"col_break_{i}", "Column Break", "")


def perm(role, **kw):
    base = {"role": role, "read": 1, "write": 1, "create": 1, "email": 1,
            "print": 1, "report": 1, "export": 1, "share": 1}
    base.update(kw); return base


SALES_PERMS = [
    perm("RE Manager", delete=1, submit=1, cancel=1, amend=1),
    perm("RE Sales Manager", delete=1, submit=1, cancel=1, amend=1),
    perm("RE Sales Agent"),
    perm("System Manager", delete=1, submit=1, cancel=1, amend=1),
]


def dt(name, fields, autoname=None, is_submittable=0, istable=0, issingle=0,
       title_field=None, perms=None, search_fields=None):
    doc = {
        "actions": [], "allow_rename": 0, "autoname": autoname or "",
        "creation": TS, "doctype": "DocType", "editable_grid": 1, "engine": "InnoDB",
        "field_order": [x["fieldname"] for x in fields], "fields": fields,
        "index_web_pages_for_search": 0, "is_submittable": is_submittable,
        "issingle": issingle, "istable": istable, "links": [],
        "modified": TS, "modified_by": "Administrator", "module": MODULE,
        "name": name, "owner": "Administrator",
        "naming_rule": "Expression" if (autoname or "").startswith("format:") else "",
        "permissions": [] if istable else (perms or SALES_PERMS),
        "sort_field": "modified", "sort_order": "DESC", "states": [], "track_changes": 1,
    }
    if title_field: doc["title_field"] = title_field
    if search_fields: doc["search_fields"] = search_fields
    folder = os.path.join(DOCTYPE_DIR, scrub(name))
    os.makedirs(folder, exist_ok=True)
    init = os.path.join(folder, "__init__.py")
    if not os.path.exists(init): open(init, "w").close()
    with open(os.path.join(folder, f"{scrub(name)}.json"), "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True); fh.write("\n")
    print(f"  wrote {name}")


def gen_lead_source():
    dt("Lead Source RE", autoname="field:source_name",
       fields=[f("source_name", "Data", reqd=1, unique=1)],
       perms=[perm("RE Manager", delete=1), perm("RE Sales Manager")])


def gen_re_lead():
    dt("RE Lead",
       autoname="format:RELD-{YYYY}-{#####}",
       title_field="full_name",
       search_fields="full_name,mobile,email",
       fields=[
           sb("who_sb", "Lead"),
           f("full_name", "Data", reqd=1, in_list_view=1),
           f("mobile", "Data", options="Phone", reqd=1, in_list_view=1),
           f("email", "Data", options="Email"),
           cb(1),
           f("status", "Select", default="New", in_list_view=1, in_standard_filter=1,
             options="New\nContacted\nQualified\nConverted\nDisqualified"),
           f("source", "Link", options="Lead Source RE", in_standard_filter=1),
           f("assigned_agent", "Link", options="RE Agent", in_standard_filter=1),
           sb("interest_sb", "Interest"),
           f("interest_type", "Select", options="Rent\nBuy", default="Rent"),
           f("preferred_property_type", "Select",
             options="\nApartment\nVilla\nOffice\nShop\nWarehouse\nLand"),
           f("preferred_location", "Data"),
           cb(2),
           f("budget_min", "Currency"),
           f("budget_max", "Currency"),
           f("unit_of_interest", "Link", options="Unit",
             description="Set automatically by portal inquiries"),
           sb("sla_sb", "SLA", collapsible=1),
           f("first_contacted_on", "Datetime", read_only=1),
           f("sla_due", "Datetime", read_only=1),
           f("sla_breached", "Check", read_only=1),
           cb(3),
           f("deal", "Link", options="RE Deal", read_only=1),
           sb("notes_sb", ""),
           f("notes", "Small Text"),
       ])


def gen_commission_slab():
    dt("Commission Slab", istable=1, fields=[
        f("from_amount", "Currency", reqd=1, in_list_view=1),
        f("to_amount", "Currency", reqd=1, in_list_view=1),
        f("percent", "Percent", reqd=1, in_list_view=1),
    ])


def gen_re_agent():
    dt("RE Agent",
       autoname="format:AGT-{###}",
       title_field="agent_name",
       fields=[
           sb("who_sb", "Agent"),
           f("agent_name", "Data", reqd=1, in_list_view=1),
           f("user", "Link", options="User", reqd=1, unique=1,
             description="Desk user this agent logs in as"),
           f("employee", "Link", options="Employee"),
           cb(1),
           f("mobile", "Data", options="Phone"),
           f("is_active", "Check", default=1, in_list_view=1),
           f("in_assignment_pool", "Check", default=1,
             label="Include in Round-Robin"),
           sb("plan_sb", "Commission Plan"),
           f("commission_type", "Select", default="Percent",
             options="Flat\nPercent\nTiered", in_list_view=1),
           f("flat_amount", "Currency",
             depends_on="eval:doc.commission_type=='Flat'"),
           f("percent", "Percent", label="Percent of Contract Value",
             depends_on="eval:doc.commission_type=='Percent'"),
           f("slabs", "Table", options="Commission Slab",
             depends_on="eval:doc.commission_type=='Tiered'"),
       ],
       perms=[perm("RE Manager", delete=1), perm("RE Sales Manager"),
              perm("RE Sales Agent", write=0, create=0)])


def gen_re_deal():
    dt("RE Deal",
       autoname="format:DEAL-{YYYY}-{####}",
       title_field="title",
       search_fields="lead,tenant_name,unit",
       fields=[
           sb("deal_sb", "Deal"),
           f("title", "Data", read_only=1, hidden=1),
           f("lead", "Link", options="RE Lead", in_list_view=1),
           f("tenant_name", "Data", label="Client Name", reqd=1, in_list_view=1),
           f("mobile", "Data", options="Phone"),
           cb(1),
           f("pipeline_stage", "Select", options=STAGES, default="New",
             in_list_view=1, in_standard_filter=1),
           f("assigned_agent", "Link", options="RE Agent", in_standard_filter=1),
           f("expected_close", "Date"),
           sb("what_sb", "Interest"),
           f("unit", "Link", options="Unit", in_list_view=1),
           f("interest_type", "Select", options="Rent\nBuy", default="Rent"),
           cb(2),
           f("expected_value", "Currency"),
           f("probability", "Percent", default=25),
           sb("closure_sb", "Closure", collapsible=1),
           f("reservation", "Link", options="Reservation", read_only=1),
           f("lease_contract", "Link", options="Lease Contract",
             description="Required to move the deal to Won"),
           cb(3),
           f("commission_entry", "Link", options="Commission Entry", read_only=1),
           f("lost_reason", "Small Text",
             depends_on="eval:doc.pipeline_stage=='Lost'"),
           sb("notes_sb", ""),
           f("notes", "Small Text"),
       ])


def gen_site_visit():
    dt("Site Visit",
       autoname="format:SV-{#####}",
       fields=[
           f("deal", "Link", options="RE Deal", reqd=1, in_list_view=1),
           f("unit", "Link", options="Unit", reqd=1, in_list_view=1),
           f("visit_datetime", "Datetime", reqd=1, in_list_view=1),
           f("agent", "Link", options="RE Agent", in_list_view=1),
           f("client_mobile", "Data", options="Phone", read_only=1,
             fetch_from="deal.mobile"),
           f("outcome", "Select", in_standard_filter=1,
             options="\nInterested\nConsidering\nNot Interested\nNo Show"),
           f("feedback", "Small Text"),
           f("reminder_sent", "Check", read_only=1, hidden=1),
       ])


def gen_reservation():
    dt("Reservation",
       autoname="format:RSV-{#####}",
       is_submittable=1,
       fields=[
           sb("res_sb", "Reservation"),
           f("deal", "Link", options="RE Deal", reqd=1, in_list_view=1),
           f("unit", "Link", options="Unit", reqd=1, in_list_view=1),
           f("company", "Link", options="Company", read_only=1),
           cb(1),
           f("booking_fee", "Currency", reqd=1, in_list_view=1),
           f("valid_till", "Date", reqd=1, in_list_view=1),
           f("status", "Select", default="Draft", read_only=1, allow_on_submit=1,
             in_standard_filter=1,
             options="Draft\nActive\nConverted\nExpired\nCancelled"),
           sb("fin_sb", "Payment", collapsible=1),
           f("payment_entry", "Link", options="Payment Entry", read_only=1,
             allow_on_submit=1, no_copy=1),
           f("amended_from", "Link", options="Reservation", read_only=1,
             no_copy=1, print_hide=1),
       ])


def gen_commission_entry():
    dt("Commission Entry",
       autoname="format:COM-{#####}",
       is_submittable=1,
       fields=[
           sb("com_sb", "Commission"),
           f("agent", "Link", options="RE Agent", reqd=1, in_list_view=1),
           f("deal", "Link", options="RE Deal", reqd=1, in_list_view=1),
           f("lease_contract", "Link", options="Lease Contract"),
           f("company", "Link", options="Company", read_only=1),
           cb(1),
           f("base_amount", "Currency", read_only=1,
             description="Contract value the plan was applied to"),
           f("commission_amount", "Currency", reqd=1, in_list_view=1),
           f("status", "Select", default="Draft", read_only=1, allow_on_submit=1,
             options="Draft\nApproved\nPaid", in_standard_filter=1),
           sb("post_sb", "Posting", collapsible=1),
           f("journal_entry", "Link", options="Journal Entry", read_only=1,
             allow_on_submit=1, no_copy=1),
           f("remarks", "Small Text"),
           f("amended_from", "Link", options="Commission Entry", read_only=1,
             no_copy=1, print_hide=1),
       ],
       perms=[perm("RE Manager", delete=1, submit=1, cancel=1, amend=1),
              perm("RE Sales Manager", submit=1, cancel=1, amend=1),
              perm("Accounts User", submit=1),
              perm("RE Sales Agent", write=0, create=0)])


def gen_crm_settings():
    dt("RE CRM Settings", issingle=1, fields=[
        sb("assign_sb", "Lead Assignment"),
        f("auto_assign_leads", "Check", default=1),
        f("last_assigned_agent", "Link", options="RE Agent", read_only=1, hidden=1),
        cb(1),
        f("sla_minutes", "Int", default=60,
          description="First-contact SLA for new leads"),
        f("escalation_user", "Link", options="User",
          description="Notified on SLA breach"),
        sb("fees_sb", "Accounts"),
        f("booking_fee_account", "Link", options="Account",
          description="Account booking fees are received into (per default company)"),
        cb(2),
        f("commission_expense_account", "Link", options="Account"),
        f("commission_payable_account", "Link", options="Account"),
        sb("wa_sb", "WhatsApp Triggers"),
        f("wa_lead_auto_reply", "Check", default=1, label="Lead Auto-Reply"),
        f("wa_visit_reminders", "Check", default=1, label="Site Visit Reminders (T-3h)"),
        cb(3),
        f("wa_reservation_expiry", "Check", default=1,
          label="Reservation Expiry Warnings"),
        f("wa_rent_reminders", "Check", default=0,
          label="Rent Due Reminders (uses re_core schedules)"),
        f("rent_reminder_days", "Int", default=5,
          description="Send rent reminder this many days before due date"),
    ], perms=[perm("RE Manager"), perm("RE Sales Manager"), perm("System Manager")])


def gen_whatsapp_settings():
    dt("WhatsApp Settings", issingle=1, fields=[
        f("enabled", "Check"),
        f("provider", "Select", options="Meta Cloud API", default="Meta Cloud API"),
        f("phone_number_id", "Data",
          description="Meta WhatsApp Business phone number ID"),
        f("access_token", "Password"),
        f("default_country_code", "Data", default="+968"),
        f("api_version", "Data", default="v19.0"),
    ], perms=[perm("RE Manager"), perm("System Manager")])


def gen_whatsapp_log():
    dt("WhatsApp Message Log",
       autoname="format:WAM-{#####}",
       fields=[
           f("to_number", "Data", reqd=1, in_list_view=1),
           f("message", "Small Text", in_list_view=1),
           f("status", "Select", default="Queued", in_list_view=1,
             in_standard_filter=1, options="Queued\nSent\nFailed\nSkipped"),
           f("reference_doctype", "Data"),
           f("reference_name", "Data"),
           f("response", "Small Text", read_only=1),
       ],
       perms=[perm("RE Manager", delete=1), perm("RE Sales Manager", write=0, create=0),
              perm("System Manager", delete=1)])


if __name__ == "__main__":
    os.makedirs(DOCTYPE_DIR, exist_ok=True)
    init = os.path.join(DOCTYPE_DIR, "__init__.py")
    if not os.path.exists(init): open(init, "w").close()
    for gen in (gen_lead_source, gen_re_lead, gen_commission_slab, gen_re_agent,
                gen_re_deal, gen_site_visit, gen_reservation, gen_commission_entry,
                gen_crm_settings, gen_whatsapp_settings, gen_whatsapp_log):
        gen()
    print("Done.")
