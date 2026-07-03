import frappe


def after_install():
    _seed_lead_sources()
    _make_kanban_board()


def _seed_lead_sources():
    for source in ["Website", "Walk-in", "WhatsApp", "Referral", "Phone Call",
                   "Property Finder", "Bayut", "Campaign", "Social Media"]:
        if not frappe.db.exists("Lead Source RE", source):
            frappe.get_doc({"doctype": "Lead Source RE",
                            "source_name": source}).insert(ignore_permissions=True)


def _make_kanban_board():
    if frappe.db.exists("Kanban Board", "Deal Pipeline"):
        return
    stages = ["New", "Contacted", "Site Visit Scheduled", "Negotiation",
              "Reservation", "Won", "Lost"]
    board = frappe.new_doc("Kanban Board")
    board.kanban_board_name = "Deal Pipeline"
    board.reference_doctype = "RE Deal"
    board.field_name = "pipeline_stage"
    for stage in stages:
        board.append("columns", {"column_name": stage})
    board.insert(ignore_permissions=True)
