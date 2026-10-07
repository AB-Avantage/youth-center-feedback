# Youth Center Complaints and Suggestions

An independent Django application for youth center complaints and suggestions. Customers submit and track requests on `/ar/` or `/en/`. Staff use `/staff/`; the superadmin uses `/admin/`.

## Roles and request flow

- Customers choose a youth center and complaint or suggestion type, write their message, and may optionally provide a name, phone, and email.
- Every submission receives a unique eight-digit tracking code. Customers must save it to follow up. Code lookups are rate limited, but the code alone grants access to the conversation, so it must be kept private.
- Staff can see all requests and respond once. They must wait for the customer to reply through the tracking page before sending another response. Staff can archive requests and create other staff accounts. The activity timeline records replies and archive actions with timestamps.
- Staff cannot use Django admin or list superadmins. The superadmin can see all local accounts in Django admin and create staff there. Staff can also create staff via `/staff/team/`.

## Data and integration

- The application reads active youth centers and matching customer profiles from the EZYXS database through a read-only connection. Local development uses `../ezyxs-backend/db.sqlite3` by default. Set `EZYXS_SQLITE_PATH` if it is elsewhere.
- If EZYXS has no centers or is unavailable, the application uses the seven centers captured from the `moys-test` facility API on September 30, 2026. This is a static snapshot and can become outdated. English names are in `feedback/data/moys_test_facilities.json`; Arabic names are in `feedback/translations/ar.json`.
- Submissions, staff accounts, tracking codes, conversation events, API tokens, and password-reset records are saved in this project's `feedback.sqlite3`, not in EZYXS. The local SQLite database is excluded from Git, so cloning the repository does not copy real data or local accounts.
- A phone number is optional and does not prove identity. If a provided phone uniquely matches an active EZYXS customer, the request stores that customer's ID and available profile details.

## Local setup

Run these commands in PowerShell from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8010
```

`migrate` creates the local tables and gives existing submissions tracking codes. Back up `feedback.sqlite3` before migrating a database with real data. `createsuperuser` creates the main admin account. Sign in at `/admin/`, then use **Create staff account** to add staff. **All users** lists local Django accounts; **Staff members** lists staff profiles. Anonymous customers and remote EZYXS customers are not user accounts in this database; their submitted contact details appear under **Submissions**.

In **All users**, the **Is staff (staff portal)** checkbox on the add and edit forms controls staff portal access. A checked account needs an email, name, and phone number; it receives a StaffMember profile and can sign in at `/staff/login/`. Unchecking removes staff portal access. Django's built-in `is_staff` flag is separate and controls Django admin eligibility; portal staff accounts have that flag turned off.

- Customer submission: `http://127.0.0.1:8010/ar/` and `/en/`
- Customer follow-up: `http://127.0.0.1:8010/ar/track/` and `/en/track/`
- Staff login and dashboard: `http://127.0.0.1:8010/staff/login/` and `/staff/`
- Superadmin: `http://127.0.0.1:8010/admin/`

## Email and deployment

The password-reset flow sends a six-digit OTP to a staff member's registered email. It expires after ten minutes, allows at most five attempts, and cannot be reused. Local development prints email messages to the server console. To deliver real email, configure `FEEDBACK_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, plus `FEEDBACK_EMAIL_HOST`, `FEEDBACK_EMAIL_PORT`, `FEEDBACK_EMAIL_USER`, `FEEDBACK_EMAIL_PASSWORD`, `FEEDBACK_EMAIL_USE_TLS`, and `FEEDBACK_FROM_EMAIL`. See `.env.example`.

Before deployment, set `FEEDBACK_DEBUG=false`, provide a secret `FEEDBACK_SECRET_KEY`, and add the hostname to `FEEDBACK_ALLOWED_HOSTS`. Production startup rejects the console email backend. For multiple servers, move the feedback database from SQLite to MySQL or PostgreSQL. Review rate-limit storage and trusted proxy IP handling before internet exposure. This repository is not yet deployed publicly.

## API for future customer and staff apps

All endpoints use `/api/v1/` and JSON. Customer endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `facilities/` | List youth centers; use `?lang=ar` for Arabic names |
| POST | `submissions/` | Submit a request and receive `tracking_code` |
| POST | `submissions/track/` | Look up a request with `{ "code": "12345678" }` |
| POST | `submissions/reply/` | Respond to staff with `code` and `text` |

Staff login uses `POST staff/login/` with `identity` (email or phone) and `password`, returning an opaque bearer token valid for 30 days. Send `Authorization: Bearer <token>` to protected endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `staff/logout/` | Revoke the current token |
| GET | `staff/me/` | Current staff profile |
| GET | `staff/dashboard/` | Counts and center comparison |
| GET | `staff/submissions/?tab=active` or `tab=archived` | Request lists |
| GET | `staff/submissions/{id}/` | Details and timeline |
| POST | `staff/submissions/{id}/reply/` | Reply once per customer turn |
| POST | `staff/submissions/{id}/archive/` | Archive a request |
| GET, POST | `staff/team/` | List and create staff only |

`POST staff/forgot/` requests an email OTP. `POST staff/reset/` requires `email`, `code`, `password`, and `confirm_password`. A successful reset revokes existing API tokens. The public customer API does not return contact details. Native apps can call the API directly; a browser app on another origin would need deliberate CORS configuration.

## Important files

- `config/settings.py` and `config/urls.py`: configuration and routes.
- `feedback/models.py` and `feedback/migrations/`: database structure and changes.
- `feedback/services.py`: read-only EZYXS lookup and center fallback.
- `feedback/operations.py`: shared business rules, OTP, permissions, and rate limits.
- `feedback/forms.py`, `feedback/views.py`, and `feedback/api.py`: validation, web pages, and JSON endpoints.
- `feedback/admin.py`: superadmin management.
- `feedback/templates/`, `feedback/static/`, and `feedback/translations/ar.json`: interface and Arabic copy.
- `feedback/tests.py`: customer, staff, OTP, permission, and API tests.

Run tests with `\.venv\Scripts\python.exe manage.py test feedback`.
