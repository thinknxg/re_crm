# RE CRM — Leads, Deals, Reservations & Commissions (Phase 3)

Completes the Kreatao RE Platform. Requires `re_core`; pairs with `re_portal`
(website inquiries auto-create RE Leads the moment this app is installed — the
bridge already ships in re_portal).

## Included
- **RE Lead**: round-robin auto-assignment across active agents, first-contact SLA
  with hourly escalation, WhatsApp auto-reply on creation
- **RE Deal**: kanban pipeline (New → Contacted → Site Visit Scheduled → Negotiation →
  Reservation → Won/Lost); Won is enforced to require a submitted Lease Contract and
  auto-drafts the agent's Commission Entry
- **Site Visit**: scheduling + outcome capture, T-3h WhatsApp reminders
- **Reservation** (submittable): blocks the unit, records the booking fee Payment Entry,
  daily expiry job releases the unit and notifies the agent
- **RE Agent**: Flat / Percent / Tiered-slab commission plans
- **Commission Entry** (submittable): computed from the plan; posts a Journal Entry
  when expense/payable accounts are configured
- **WhatsApp layer**: Meta Cloud API adapter behind WhatsApp Settings (Single),
  every send logged to WhatsApp Message Log; rent-due reminders ride on re_core data
- Fixtures: RE Sales Manager / RE Sales Agent roles + RE CRM workspace;
  install seeds Lead Sources and a Deal Pipeline kanban board

## Install
```bash
bench get-app /path/to/re_crm
bench --site yoursite.local install-app re_crm
bench --site yoursite.local migrate
```
Then: CRM Settings (SLA minutes, escalation user, accounts) and WhatsApp Settings
(phone number ID + access token) if outbound messaging is wanted.

## Regenerating DocType JSONs
```bash
python3 scripts/generate_doctypes.py
```
