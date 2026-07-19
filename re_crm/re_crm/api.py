import frappe
from frappe import _


# ─────────────────────────────────────────────
# LEAD SOURCES
# ─────────────────────────────────────────────
@frappe.whitelist()
def get_lead_sources():
    return frappe.get_all("Lead Source RE", fields=["name", "source_name"], order_by="source_name asc")


# ─────────────────────────────────────────────
# COMMISSION ENTRIES
# ─────────────────────────────────────────────
@frappe.whitelist()
def get_commission_entries(agent=None, deal=None, status=None):
    filters = {}
    if agent:
        filters["agent"] = agent
    if deal:
        filters["deal"] = deal
    if status:
        filters["status"] = status

    total_draft = frappe.db.count("Commission Entry", {"status": "Draft"})
    total_approved = frappe.db.count("Commission Entry", {"status": "Approved"})
    total_paid = frappe.db.count("Commission Entry", {"status": "Paid"})

    rows = frappe.get_all(
        "Commission Entry",
        filters=filters,
        fields=["name", "agent", "deal", "lease_contract", "company", "base_amount",
                "commission_amount", "status", "journal_entry", "remarks"],
        order_by="modified desc",
        limit_page_length=200,
    )

    return {
        "stats": {"draft": total_draft, "approved": total_approved, "paid": total_paid},
        "rows": rows,
    }


@frappe.whitelist()
def create_commission_entry(agent, base_amount, commission_amount, deal=None,
                             lease_contract=None, company=None, remarks=None):
    doc = frappe.get_doc({
        "doctype": "Commission Entry",
        "agent": agent,
        "deal": deal,
        "lease_contract": lease_contract,
        "company": company,
        "base_amount": base_amount,
        "commission_amount": commission_amount,
        "status": "Draft",
        "remarks": remarks,
    }).insert()
    return {"name": doc.name}


@frappe.whitelist()
def update_commission_status(name, status):
    doc = frappe.get_doc("Commission Entry", name)
    doc.status = status
    doc.save()
    return {"name": doc.name, "status": doc.status}


# ─────────────────────────────────────────────
# COMMISSION SLABS (child table on RE Agent via 'slabs')
# ─────────────────────────────────────────────
@frappe.whitelist()
def get_commission_slabs(agent):
    doc = frappe.get_doc("RE Agent", agent)
    return [
        {
            "name": row.name,
            "from_amount": row.from_amount,
            "to_amount": row.to_amount,
            "percent": row.percent,
        }
        for row in doc.slabs
    ]


@frappe.whitelist()
def set_commission_slabs(agent, slabs):
    # slabs: JSON list of {from_amount, to_amount, percent}
    if isinstance(slabs, str):
        slabs = frappe.parse_json(slabs)
    doc = frappe.get_doc("RE Agent", agent)
    doc.set("slabs", [])
    for row in slabs:
        doc.append("slabs", row)
    doc.save()
    return {"agent": agent, "slabs_count": len(doc.slabs)}


# ─────────────────────────────────────────────
# WHATSAPP MESSAGE LOG
# ─────────────────────────────────────────────
@frappe.whitelist()
def get_whatsapp_logs(reference_doctype=None, reference_name=None, status=None):
    filters = {}
    if reference_doctype:
        filters["reference_doctype"] = reference_doctype
    if reference_name:
        filters["reference_name"] = reference_name
    if status:
        filters["status"] = status

    rows = frappe.get_all(
        "WhatsApp Message Log",
        filters=filters,
        fields=["name", "to_number", "message", "status", "reference_doctype",
                "reference_name", "response"],
        order_by="creation desc",
        limit_page_length=200,
    )
    return {"rows": rows}


# ─────────────────────────────────────────────
# AGENTS LIST (for pickers)
# ─────────────────────────────────────────────
@frappe.whitelist()
def get_agents_list():
    return frappe.get_all("RE Agent", fields=["name", "agent_name"], order_by="agent_name asc")


# ─────────────────────────────────────────────
# RE LEAD — CREATE (CRM "New Inquiry")
# ─────────────────────────────────────────────
@frappe.whitelist()
def create_lead(full_name, mobile, email=None, source=None, assigned_agent=None,
                 interest_type=None, preferred_property_type=None, preferred_location=None,
                 budget_min=None, budget_max=None, unit_of_interest=None):
    doc = frappe.get_doc({
        "doctype": "RE Lead",
        "full_name": full_name,
        "mobile": mobile,
        "email": email,
        "status": "New",
        "source": source,
        "assigned_agent": assigned_agent,
        "interest_type": interest_type,
        "preferred_property_type": preferred_property_type,
        "preferred_location": preferred_location,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "unit_of_interest": unit_of_interest,
    }).insert()
    return {"name": doc.name}


# ─────────────────────────────────────────────
# RE DEAL LIST (for Site Visit picker)
# ─────────────────────────────────────────────
@frappe.whitelist()
def get_deals_list():
    return frappe.get_all(
        "RE Deal",
        fields=["name", "tenant_name", "unit", "pipeline_stage"],
        filters={"pipeline_stage": ["not in", ["Won", "Lost"]]},
        order_by="modified desc",
        limit_page_length=200,
    )


DEAL_PIPELINE_STAGES = ["New", "Contacted", "Site Visit Scheduled", "Negotiation",
                         "Reservation", "Won", "Lost"]


@frappe.whitelist()
def update_deal_stage(deal, new_stage, lost_reason=None):
    if new_stage not in DEAL_PIPELINE_STAGES:
        frappe.throw(_("Invalid pipeline stage: {0}").format(new_stage))
    doc = frappe.get_doc("RE Deal", deal)
    if new_stage == "Lost":
        if not lost_reason:
            frappe.throw(_("Please provide a Lost Reason."))
        doc.lost_reason = lost_reason
    doc.pipeline_stage = new_stage
    doc.save()
    return {"pipeline_stage": doc.pipeline_stage}


@frappe.whitelist()
def get_leads_list():
    return frappe.get_all(
        "RE Lead",
        filters={"status": ["in", ["New", "Contacted"]]},
        fields=["name", "full_name", "mobile", "email", "status", "interest_type",
                "preferred_property_type", "preferred_location", "budget_min", "budget_max",
                "unit_of_interest", "assigned_agent", "deal"],
        order_by="creation desc",
        limit_page_length=100,
    )


@frappe.whitelist()
def convert_lead_to_deal(lead):
    lead_doc = frappe.get_doc("RE Lead", lead)
    if lead_doc.deal:
        frappe.throw(_("This lead is already linked to Deal {0}.").format(lead_doc.deal))

    notes_parts = []
    if lead_doc.preferred_property_type:
        notes_parts.append(f"Preferred Property Type: {lead_doc.preferred_property_type}")
    if lead_doc.preferred_location:
        notes_parts.append(f"Preferred Location: {lead_doc.preferred_location}")
    if lead_doc.budget_min or lead_doc.budget_max:
        notes_parts.append(f"Budget: {lead_doc.budget_min or 0} - {lead_doc.budget_max or 0}")

    deal = frappe.new_doc("RE Deal")
    deal.lead = lead_doc.name
    deal.tenant_name = lead_doc.full_name
    deal.mobile = lead_doc.mobile
    deal.pipeline_stage = "New"
    deal.assigned_agent = lead_doc.assigned_agent
    deal.unit = lead_doc.unit_of_interest
    deal.interest_type = lead_doc.interest_type
    if lead_doc.budget_max:
        deal.expected_value = lead_doc.budget_max
    if notes_parts:
        deal.notes = "\n".join(notes_parts)
    deal.insert()

    lead_doc.db_set("deal", deal.name)
    lead_doc.db_set("status", "Contacted")

    return {"deal": deal.name}


# ─────────────────────────────────────────────
# SITE VISIT — CREATE (CRM "Schedule Viewing")
# ─────────────────────────────────────────────
@frappe.whitelist()
def create_site_visit(client_name, mobile, unit, visit_datetime, agent=None):
    # Reuse an existing open Deal for this client+unit if one exists, else create one.
    existing = frappe.get_all(
        "RE Deal",
        filters={
            "tenant_name": client_name,
            "unit": unit,
            "pipeline_stage": ["not in", ["Won", "Lost"]],
        },
        fields=["name"],
        limit_page_length=1,
    )
    if existing:
        deal_doc = frappe.get_doc("RE Deal", existing[0]["name"])
    else:
        deal_doc = frappe.get_doc({
            "doctype": "RE Deal",
            "tenant_name": client_name,
            "mobile": mobile,
            "unit": unit,
            "assigned_agent": agent,
            "pipeline_stage": "Site Visit Scheduled",
        }).insert()

    if deal_doc.pipeline_stage in ("New", "Contacted"):
        deal_doc.pipeline_stage = "Site Visit Scheduled"
        deal_doc.save()

    visit_doc = frappe.get_doc({
        "doctype": "Site Visit",
        "deal": deal_doc.name,
        "unit": unit,
        "visit_datetime": visit_datetime,
        "agent": agent,
        "client_mobile": mobile,
    }).insert()
    return {"name": visit_doc.name, "deal": deal_doc.name}
