# QSPARK — Smart Parking Slot Booking and Management System

Web application for booking, gate entry/exit, wallet settlement and revenue reporting across a
multi-floor parking facility. Three roles: **Customer**, **Admin**, **Super Admin**.

Phase 1 stack: Python, Flask, SQLite, Jinja2, compiled Tailwind CSS, vanilla JavaScript.
No Node, no bundler, no external database, no payment gateway (the wallet is an internal balance).

## Repository layout

```
app.py                  application factory, security headers, page routes
run.py                  development server (0.0.0.0:8000, debug)
schema.sql              executable SQLite schema — authoritative
requirements.txt        Python dependencies
.env.example            configuration template (copy to .env)

src/
  api/                  eight REST blueprints (auth, slots, bookings, qr, admin, super_admin, reports, system)
  core/                 pricing and security helpers
  services/             SQLite data access and transactions
  templates/            Jinja2 pages extending base.html
  static/               compiled CSS, hand-written app.css, JS core, vendor JS, images

scripts/
  seed_direct.py        seed Super Admin + default admins (skips if users exist)
  start_qspark.bat      Windows launcher (starts server, opens browser)

docs/
  project_spec.md       confirmed product scope and workflows
  technical_spec.md     architecture, data rules, security
  api.md                routes, permissions, request/response contracts
  db.md                 human-readable schema reference
  ERD.md                entity relationship diagram (Mermaid + tables)
  frontend.md           page inventory, design tokens, JS conventions
  deployment.md         production procedure, backup/restore, troubleshooting
  implementation_plan.md, open_questions.md, test_results.md
  diagrams/             architecture, ERD and process-flow images
  srs/                  generated SRS (docx, diagram prompts, analysis, build scripts)

database/               live SQLite file (gitignored)
database_backups/       dated snapshots (gitignored — contain real data)
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env      # set SECRET_KEY before any real use
.\.venv\Scripts\python.exe scripts\seed_direct.py
```

## Run

```powershell
.\.venv\Scripts\python.exe run.py      # http://localhost:8000
.\scripts\start_qspark.bat             # same, opens the browser
```

Production uses waitress behind HTTPS — see `docs/deployment.md`.

## Documentation

Start with `docs/project_spec.md`, then `docs/technical_spec.md`, `docs/api.md`, `docs/db.md`.
`AGENTS.md` records the working rules for automated contributors.

## Regenerating the SRS

```powershell
python docs\srs\build\build_srs.py
python docs\srs\build\validate.py
```
