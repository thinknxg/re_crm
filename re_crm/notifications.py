"""WhatsApp notification layer. Provider-agnostic entry point `send_whatsapp`;
Meta Cloud API adapter behind WhatsApp Settings. Every attempt is logged to
WhatsApp Message Log; sends run in the background queue."""

import frappe
from frappe.utils import cstr


def send_whatsapp(to_number, message, reference_doctype=None, reference_name=None):
    """Queue a WhatsApp text message. Safe to call unconditionally: logs Skipped
    when the integration is disabled or the number is missing."""
    settings = frappe.get_cached_doc("WhatsApp Settings")
    log = frappe.get_doc({
        "doctype": "WhatsApp Message Log",
        "to_number": _normalize(to_number, settings),
        "message": cstr(message)[:900],
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "status": "Queued",
    }).insert(ignore_permissions=True)

    if not (settings.enabled and to_number):
        log.db_set("status", "Skipped")
        return log.name

    frappe.enqueue("re_crm.notifications._dispatch", queue="short",
                   log_name=log.name, enqueue_after_commit=True)
    return log.name


def _normalize(number, settings):
    number = cstr(number).strip().replace(" ", "").replace("-", "")
    if number and not number.startswith("+"):
        code = cstr(settings.default_country_code or "+968")
        number = number if number.startswith(code.lstrip("+")) else code.lstrip("+") + number
    return number.lstrip("+")


def _dispatch(log_name):
    log = frappe.get_doc("WhatsApp Message Log", log_name)
    settings = frappe.get_cached_doc("WhatsApp Settings")
    try:
        token = settings.get_password("access_token")
        url = (f"https://graph.facebook.com/{settings.api_version or 'v19.0'}/"
               f"{settings.phone_number_id}/messages")
        response = frappe.make_post_request(
            url,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            data=frappe.as_json({
                "messaging_product": "whatsapp",
                "to": log.to_number,
                "type": "text",
                "text": {"body": log.message},
            }))
        log.db_set("status", "Sent")
        log.db_set("response", cstr(response)[:500])
    except Exception:
        log.db_set("status", "Failed")
        log.db_set("response", frappe.get_traceback()[-500:])
        frappe.log_error(title="re_crm: WhatsApp send failed",
                         message=f"Log {log.name}")
