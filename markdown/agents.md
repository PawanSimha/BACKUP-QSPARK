# QSPARK — AI Agent Operating Guidelines (`agents.md`)

## 1. Project Identity
- **Project Name:** QSPARK (Smart Parking Slot Booking & Management System)
- **Core Stack:** Oracle APEX (Database) + ORDS (REST APIs created inside APEX) + Python (FastAPI Backend & Business Logic) + Clean HTML/JS Frontend (designed modularly so Tailwind CSS and richer JS components can be layered in easily).

## 2. Strict File & Security Boundaries
1. **NEVER Touch Personal Files:** You must NEVER read, modify, or overwrite `mytrack.md` in the root folder. It is strictly reserved for the developer's manual notes.
2. **Leave `README.md` Untouched:** Do not edit `README.md` until the entire project is completed and verified.
3. **Environment Isolation:** Always execute Python commands and package installations inside the local `.venv` virtual environment. Never install packages globally on the company laptop.
4. **No Hardcoded Secrets:** Never hardcode Oracle APEX URLs, workspace credentials, or secret keys inside `.py` or `.html` files. Always load them from `.env` via `python-dotenv`.
5. **No External Gateways:** Strictly NO real payment gateways (no Razorpay/Stripe/UPI APIs) and NO external SMS/Email gateways. Authentication uses basic username/email + SHA-256 hashed passwords, and payments use the internal Metro Card (`wallet_balance`) column.

## 3. Architectural & Coding Rules
1. **Dual-Mode Data Layer (Live ORDS + Local Fallback):**
   - In production, Python communicates with Oracle APEX solely via ORDS REST APIs (`requests` / `httpx`).
   - Because Oracle APEX schema permissions may occasionally be pending or offline during development, `src/services/ords_client.py` MUST support `ORDS_SIMULATION_MODE=true` (using a local SQLite replica of the exact 7 `QSPARK_` tables) so the application and frontend can be built, run, and tested live at all times.
2. **Decoupled Frontend Design:**
   - Start with clean, semantic HTML5 and modular vanilla JavaScript (`fetch()` calls to FastAPI endpoints) so the core booking, wallet deduction, cancellation, overstay exit, and admin heatmap flows work end-to-end first.
   - Keep HTML templates and CSS classes clean and well-structured so upgrading the styling with Tailwind CSS and interactive JS enhancements is plug-and-play without rewriting backend routes.
3. **Mandatory Progress Tracking:**
   - Every time you complete a task, create/edit a file, or check off an item in `markdown/todo.md`, you MUST append a timestamped log entry in `markdown/agent_tracker.md` explaining what was done and what is next.
