# Youth Center Complaints and Suggestions

An independent Django application for submitting youth center complaints and suggestions. `/ar/` shows the Arabic page, `/en/` shows the English page, and `/staff/` is the employee viewer.

## Data and integration

- The application reads active youth centers and customer profiles from the EZYXS database through a read-only connection.
- Local development uses `../ezyxs-backend/db.sqlite3` by default. Set `EZYXS_SQLITE_PATH` if the file is elsewhere.
- If the local EZYXS database has no facilities, the application uses the seven facilities retrieved from the `moys-test` facility API on September 30, 2026. This is a static snapshot and can become outdated.
- English facility names are stored in `feedback/data/moys_test_facilities.json`. Arabic names used only on the Arabic page are stored in `feedback/translations/ar.json`.
- Submissions are saved in this project's `feedback.sqlite3`, not in the EZYXS database.
- Each submission stores the selected facility and phone number. If the phone matches an EZYXS customer, it also stores the customer's ID, name, and email.
- Phone-only submission is temporarily allowed. The employee viewer identifies whether a customer match was found.
- A phone number does not prove that the submitter owns it. This version does not send an OTP.
- Employee accounts are local to this application; EZYXS staff accounts are not connected yet.

## Local setup

Run these commands from the project folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8010
```

`migrate` creates tables in this project's `feedback.sqlite3` only. `createsuperuser` creates a local employee account for `/staff/`.

- `http://127.0.0.1:8010/ar/` — Arabic submission page.
- `http://127.0.0.1:8010/en/` — English submission page.
- `http://127.0.0.1:8010/staff/` — employee viewer.

The local database file and virtual environment are excluded from Git.

## MySQL integration and deployment

Set `EZYXS_DB_ENGINE=mysql` and configure `EZYXS_DB_NAME`, `EZYXS_DB_USER`, `EZYXS_DB_PASSWORD`, `EZYXS_DB_HOST`, and `EZYXS_DB_PORT`. The MySQL account should have `SELECT` access only to `facility_facility`, `accounts_customerprofile`, and `accounts_customuser`.

Before deployment, set `FEEDBACK_DEBUG=false`, provide a secret `FEEDBACK_SECRET_KEY`, and add the site hostname to `FEEDBACK_ALLOWED_HOSTS`. If multiple servers are used, move the submission database from local SQLite to MySQL or PostgreSQL.

## Key files

- `config/settings.py`: Django settings and database connections.
- `feedback/services.py`: read-only access to EZYXS facilities and customers.
- `feedback/data/moys_test_facilities.json`: English facility snapshot from the test environment.
- `feedback/translations/ar.json`: Arabic page translations and Arabic facility labels.
- `feedback/texts.py`: loads Arabic translations and defines English page copy.
- `feedback/forms.py`: validates submission input.
- `feedback/models.py`: defines stored submissions.
- `feedback/views.py`: handles submissions and confirmation pages.
- `feedback/admin.py`: employee viewer and status editing.
