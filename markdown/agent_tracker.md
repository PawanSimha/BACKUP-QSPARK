# Agent Activity Log

> Placeholder: Dedicated AI agent activity log recording every action, file created, and milestone completed.

---

## Setup Entry 001 — Documentation Scaffold Initialized

- **Date:** 2026-11-08
- **Phase:** Project initialization (documentation & agent-guidance only)
- **Action:** Created the `markdown/` folder in the project root.
- **Files created:**
  - `markdown/agents.md` — master rules, coding conventions, agent behavior
  - `markdown/prd.md` — product requirements document
  - `markdown/architecture.md` — Python + ORDS + local mock fallback
  - `markdown/database_and_ords.md` — 7 QSPARK_ tables & 5 ORDS endpoints
  - `markdown/frontend_and_flows.md` — UI specs & booking/overstay flows
  - `markdown/roadmap.md` — phased execution plan
  - `markdown/todo.md` — granular task checklist
  - `markdown/agent_tracker.md` — this activity log
- **Placeholder state:** Each document contains only a `# Title` header and a one-line placeholder description.
- **Respect boundary:** `README.md` left untouched until project completion. `MY_TRACK.md` (private manual tracker) never read, edited, or overwritten.
- **Milestone:** M0 — Documentation structure ready. No application code generated.
- **Next step:** Awaiting exact project context from the user before filling in any document or writing code.

---

## Setup Entry 002 — Python Environment & Project Skeleton

- **Date:** 2026-11-08
- **Phase:** Project initialization (environment only, no business logic)
- **Interpreter found:** Python 3.14.10 at `%LOCALAPPDATA%\Programs\Python\Python314\python.exe` (not on shell PATH; the `python` command resolved to the Microsoft Store stub).
- **Virtual environment:** Created `.venv` (isolated from global Python) and installed `requirements.txt` into it.
- **Files created:**
  - `.gitignore` — blocks venvs, secrets/wallets, Python caches, local DBs, `mytrack.md`/`MY_TRACK.md`, IDE/OS files
  - `.env.example` — safe-to-commit template with `APP_ENV`, `ORDS_SIMULATION_MODE`, `ORDS_BASE_URL`, `ORDS_TIMEOUT`, `SECRET_KEY`
  - `.env` — local copy of the template (git-ignored)
  - `requirements.txt` — fastapi, uvicorn, requests, pydantic, python-dotenv, openpyxl, pytest, httpx
  - `src/__init__.py`, `src/api/__init__.py`, `src/core/__init__.py`, `src/services/__init__.py`, `tests/__init__.py`
- **Folders created:** `src/`, `src/api/`, `src/core/`, `src/services/`, `src/static/`, `src/templates/`, `database/`, `tests/`
- **Respect boundary:** `README.md` untouched. `MY_TRACK.md` never read, edited, or overwritten.
- **Milestone:** M1 — Development environment and skeleton ready. No application code written.
- **Next step:** Awaiting instruction before adding any routes, models, or SQL.

