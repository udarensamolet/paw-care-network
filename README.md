# Paw Care Network

A **Flask** app for pet owners and sitters.  
Owners create care requests; sitter friends apply and take shifts. The project is structured like a course assignment: clear modules, seeds, tests, and a small Plotly analytics page.

---

## Features
- Sign up / login with roles **Owner** and/or **Sitter**
- **Pets**: name, species, breed, age, care instructions, photo upload
- **Care Requests**: date interval *from–to* with statuses `open / assigned / active / done / cancelled`
- **Friends**: friendship requests, accept/decline, list
- **Assignments**: sitter applies → owner approves
- **Dashboard**: quick stats and last 5 requests
- **Analytics**: simple Plotly charts

---

## Tech Stack
- Python, Flask, Flask‑Login, Flask‑Migrate, SQLAlchemy  
- DB: **SQLite** (`instance/app.db`)  
- Tests: **pytest** (+ coverage)  
- Lint / types : **pylint**, **mypy**

---

## Quick Start

```bash
git clone <repo-url>
cd paw-care-network
python -m venv .venv
.venv\Scripts\activate

# Install needed requireme
pip install -r requirements.txt

# Tell Flask where the app is
$env:FLASK_APP = "wsgi.py"

# Create tables and seed small demo data
flask init-db
flask seed-small

# Run
flask run
```

**Demo accounts** (from seeds):  
- `demo@paw.com` / `demo` (owner)  
- `sitter@paw.com` / `demo` (sitter)  
- also `user000@paw.com`, `user001@paw.com`, … (password **demo**)

---

## Configuration
Default settings live in `config.Config` (SQLite in `instance/app.db`).  
You can override with `.env` or environment variables:

```ini
FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=dev-secret
SQLALCHEMY_DATABASE_URI=sqlite:///instance/app.db
```

> Note: SQLite is configured with WAL and a larger timeout to reduce “database is locked” during development.

---

## Database & Seed Commands (Flask CLI)

```bash
flask init-db                 # create tables
flask reset-db --force        # drop + create 
flask purge-data              # delete all rows, keep schema (resets AUTOINCREMENT on SQLite)

flask seed-demo               # 1 owner, 1 sitter, 1 pet, 1 request
flask seed-small              # ~20 users; 1–2 pets; 1–3 requests per pet
flask seed-big                # ~40 users; 1–3 pets; 2–5 requests per pet
# all seeded users share password: demo
```

---

## Analytics (Plotly)
The **/analytics** page renders Plotly charts.

---

## Tests
Tests are split into **unit** and **integration** (integration uses an in‑memory DB and does not touch `instance/app.db`).

```bash
pytest -q
coverage run -m pytest
coverage report -m   
```

---

## Lint & Type Checking 

```bash
pylint app
mypy app
```

---

## Project Structure (short)

```
app/
  __init__.py          # app factory, helpers, dashboard route
  cli.py               # init/reset/purge + seed commands
  extensions.py        # db, migrate, login_manager, csrf
  models/              # User, Pet, CareRequest, CareAssignment, Friendship
  auth/                # login/register/logout
  pets/                # CRUD for pets
  schedule/            # owner requests
  matching/            # sitter applications
  assignments/         # assignments lists (owner/sitter)
  analytics/           # Plotly page
templates/             # Jinja2
static/                # CSS, assets, uploads
tests/                 # unit/ and integration/
instance/app.db        # SQLite (generated)
wsgi.py                # entry point
```

---

## FAQ
- **“Invalid email address” with test domains?** Forms allow local/test domains; `paw.com` works.  
- **“database is locked”?** Close tools holding `app.db`, or run `flask reset-db --force`.  
- **Where are uploaded photos stored?** Under `static/uploads/...`, rendered via `url_for('static', filename=...)`.
