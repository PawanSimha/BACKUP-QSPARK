# QSPARK — Phase 1 Deployment Guide

Phase 1 is a single Python/Flask process with a local SQLite file. There is no external payment gateway, no message queue and no separate frontend build server. Read `docs/technical_spec.md` §16–§18 for the security and financial rules this guide assumes.

## 1. Requirements

| Item | Value |
|---|---|
| Python | 3.11 or newer (the project is verified on CPython 3.14 on Windows) |
| OS | Windows 10/11 or any Linux with Python 3.11+ |
| Disk | ~150 MB (venv + dependencies) + database file |
| Database | SQLite file, created and seeded by the app; no SQLite server |
| Network | One HTTP port behind a TLS-terminating reverse proxy |

Node/npm is **not** required. Tailwind is compiled ahead of time.

## 2. Install

```powershell
git clone <repo> QSPARK
cd QSPARK
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On Linux use `.venv/bin/python` in place of `.venv\Scripts\python.exe`.

`requirements.txt` includes Flask, Flask-WTF, waitress, qrcode/Pillow, and the test tooling (pytest, playwright, axe-playwright-python).

## 3. Configure

```powershell
Copy-Item .env.example .env
```

Edit `.env` (never commit it; it is gitignored):

```ini
APP_ENV=production
SECRET_KEY=<64 hex chars>
DATABASE_PATH=C:/qspark/data/parking.db
SESSION_TIMEOUT=3600
MAX_CONTENT_LENGTH=1048576
SESSION_COOKIE_SECURE=1
```

- Generate `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`. `APP_ENV=production` without it raises `RuntimeError` at startup by design.
- `DATABASE_PATH` must be an absolute path to a directory the service account can write. The parent directory is created automatically.
- `SESSION_COOKIE_SECURE=1` only when the browser reaches the site over HTTPS. With plain HTTP local development, leave it at `0` or the session cookie will be dropped.
- Set seed passwords (`QSPARK_ADMIN*_PASSWORD`, `QSPARK_SUPER_ADMIN_PASSWORD`) before seeding. The scripts in `scripts/` fall back to the development password `superadmin123` for the Super Admin when the variable is unset, so always set it explicitly outside local development. They store PBKDF2 hashes only.

## 4. Database initialisation and seeding

```powershell
.\.venv\Scripts\python.exe scripts\seed_direct.py
```

- `scripts/seed_direct.py` calls `init_db()`, which runs `schema.sql` (the 11-table schema) against `DATABASE_PATH`, then inserts the Super Admin and two default admins.
- If the file already contains an incompatible legacy schema, `init_db()` renames it to `<name>.legacy_<timestamp>.db` and creates a fresh schema. It never deletes the file.
- Seeding is skipped when `users` already has rows (`Database already seeded. Skipping.`). Re-running is safe.
- Store the seeded credentials in your secret manager immediately. They are only recoverable as PBKDF2 hashes in the database, so a lost password means creating a new account.

## 5. CSS build (only after template/JS changes)

The compiled stylesheet `src/static/css/tailwind.css` is committed. Rebuild when a template or JS file gains a new Tailwind utility class:

```powershell
# one-off download of the standalone CLI (gitignored, ~40 MB)
curl.exe -sSL -o tools\tailwindcss.exe https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-windows-x64.exe

.\tools\tailwindcss.exe -c tailwind.config.js -i src\static\css\tailwind.input.css -o src\static\css\tailwind.css --minify
```

There is no CDN fallback: if the output is missing or stale, layout utilities silently lose styling. Verify `src/static/css/tailwind.css` is non-empty after a build.

## 6. Run

Development only:

```powershell
.\.venv\Scripts\python.exe run.py      # http://127.0.0.1:5000, debug=True
```

Production (waitress, no debug, no reloader):

```powershell
$env:APP_ENV="production"
.\.venv\Scripts\waitress-serve.exe --listen=0.0.0.0:8000 --call app:create_app
```

`doctor`/`--url-prefix` are not needed. Waitress logs to stdout; capture it with your process manager (NSSM, systemd, Task Scheduler, Docker). Keep `debug=False` — the debugger is remote-code-execution if exposed.

## 7. HTTPS and reverse proxy

Terminate TLS in front of waitress (nginx, Caddy, IIS ARR, Cloudflare Tunnel). Requirements:

- Forward `Host` and `X-Forwarded-Proto: https`.
- Set `SESSION_COOKIE_SECURE=1` and `APP_ENV=production` so CSRF's SSL-strict mode is active.
- Keep the app port bound to localhost or a private network only.
- Do not add caching for `/api/*`; responses are session-specific.

## 8. Backup

SQLite allows a consistent hot backup without stopping the app:

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
.\.venv\Scripts\python.exe -c "import sqlite3,os; s=sqlite3.connect(os.environ['DATABASE_PATH']); d=sqlite3.connect(r'backups\parking_$stamp.db'); s.backup(d); d.close(); s.close()"
```

On Linux: `sqlite3 "$DATABASE_PATH" ".backup 'backups/parking_$(date +%Y%m%d_%H%M%S).db'"`.

Rules:

- Name with a UTC/local timestamp; never overwrite an existing backup.
- Verify each backup before trusting it: `sqlite3 backup.db "PRAGMA integrity_check;"` must return `ok`, and `SELECT COUNT(*) FROM users;` must return the expected row count.
- Copy backups off the host. A backup on the same disk is not disaster recovery.
- Suggested retention: 7 daily, 4 weekly, 12 monthly. Financial history is never pruned from the live database.
- Back up before every upgrade, seed, or schema-affecting change.

## 9. Restore

1. Stop the application (waitress/NSSM/systemd).
2. Copy the current database aside (`parking_before_restore_<timestamp>.db`) — never delete it.
3. Run `PRAGMA integrity_check;` on the backup you intend to restore.
4. Replace `DATABASE_PATH` with the backup file (copy, do not move, so a second attempt is possible).
5. Start the app and verify: `/health` returns `ok`, sign in as Super Admin, check `GET /api/super-admin/reports/revenue-summary` and the wallet ledger.
6. Restart the app; the compiled CSS is static and needs no rebuild. Re-run `scripts\seed_direct.py` only if you intentionally restored an empty database.

## 10. Logging and operations

- The app uses Python's standard `logging` through `app.logger`: startup secret-key warning, failed logins (username + remote address, never the password), CSRF rejections, and unhandled 500s with stack trace server-side only.
- Users see a generic error page/JSON; stack traces are never returned.
- Financial and management writes are recorded in `audit_logs` (actor, action, old/new values) inside the same transaction as the change.
- `GET /health` returns `{"service":"QSPARK","status":"ok"}` and is unauthenticated — use it for liveness checks, not as an auth bypass.
- SQLite: `PRAGMA foreign_keys=ON` on every connection, `BEGIN IMMEDIATE` for writes, WAL is not enabled by default. Keep one app process (waitress threads are fine); do not run two independent app instances against the same file over a network share.

## 11. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `RuntimeError: SECRET_KEY must be set when APP_ENV=production` | Set `SECRET_KEY` in `.env` or the service environment |
| Login succeeds but immediately redirects to `/login` | `SESSION_COOKIE_SECURE=1` while serving plain HTTP; set it to `0` or enable HTTPS |
| Every POST returns 400 `csrf: true` | Page loaded before the session existed, or the browser dropped the session cookie; reload. If it persists, check cookie domain/`SameSite` and that no proxy strips cookies |
| `database is locked` | Another process holds a write lock; ensure a single app instance and no long-running external `sqlite3` shell |
| Unstyled page | `src/static/css/tailwind.css` missing/empty — rebuild it (step 5) |
| `qrcode`/Pillow import error | `pip install -r requirements.txt` in the active venv |
| Seeded passwords lost | They exist only as PBKDF2 hashes. Create a new Admin via the Super Admin UI, or reset with a controlled script; do not hand-edit password hashes |
