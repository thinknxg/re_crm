app_name = "re_crm"
app_title = "RE CRM"
app_publisher = "Kreatao"
app_description = "GCC Real Estate Platform — Leads, Deals, Reservations, Commissions & WhatsApp"
app_email = "dev@kreatao.com"
app_license = "MIT"

required_apps = ["erpnext", "re_core"]

after_install = "re_crm.install.after_install"

fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["RE Sales Manager", "RE Sales Agent"]]]},
    {"dt": "Workspace", "filters": [["name", "in", ["RE CRM"]]]},
]

scheduler_events = {
    "hourly": [
        "re_crm.tasks.lead_sla_escalation",
        "re_crm.tasks.site_visit_reminders",
    ],
    "daily": [
        "re_crm.tasks.release_expired_reservations",
        "re_crm.tasks.rent_due_whatsapp_reminders",
    ],
}
