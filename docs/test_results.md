# QSPARK — Test and verification results

Only commands actually executed are recorded here. Two separate things are tracked:

- **Current verification (18 Nov 2026)** — run against the tree as it exists today.
- **Historical results (12 Nov 2026)** — produced against a build that still contained `tests/`.
  They are kept for traceability and **cannot be reproduced** from the current tree.

## 1. Current verification — 18 Nov 2026

Environment: Windows, global `python` (3.14). The local `.venv` is incomplete (`dotenv` missing),
so it was not used.

| Command | Result |
|---|---|
| `python -c "import app; app.create_app()"` | **OK**, 98 URL rules registered, no import errors |
| `python scripts\seed_direct.py` | **OK** — `Database already seeded. Skipping.` (idempotent guard works) |
| `cmd /c scripts\start_qspark.bat` | **OK** — server bound on `0.0.0.0:8000`, browser opened |
| `Invoke-WebRequest http://localhost:8000/login` | **HTTP 200**, 8125 bytes |
| `GET /static/css/tailwind.css`, `/static/js/core/api.js`, `/api/system/status` | **200** (login page shell loads its assets and status call) |
| `Qspark SRS.txt` | **Created** — Comprehensive SRS text file replacing the Word-document-based SRS |
| N/A (old build_srs.py removed) | SRS generation now uses the standalone `Qspark SRS.txt` document |
| SRS figure check | 12 figure captions, 0 `Image unavailable` runs |
| Route inventory check (`app.url_map` vs `docs/api.md`) | 62 `/api` paths and 23 page routes; appendix added, no route missing |
| Column coverage check (`schema.sql` → `docs/db.md`, `docs/erd.md`) | 11 tables, every column named, no gaps |

Not executed: any pytest suite, Playwright, axe-core. There is no `tests/` directory in this
repository, so no automated test can run. Nothing was claimed as passing that was not run.

## 2. Historical results — 12 Nov 2026 (suite no longer present)

These were recorded when `tests/` existed. They are **unverified claims** against today's tree.

| Command | Result as recorded |
|---|---|
| `pytest -q` | 109 passed, 3 skipped, 1 failed (missing `PIL`) |
| `pytest tests/test_security.py -q` | 13 passed |
| `pytest tests/test_financial.py -q` | 9 passed |
| `pytest tests/test_booking_safety.py -q` | 9 passed |
| `pytest tests/test_system.py -q` | 38 passed |
| `pytest tests/test_qr_flow.py -q` | 9 passed |
| `pytest tests/test_frontend.py -q` | 32 passed |
| `pytest tests/test_frontend_wiring.py -q` | 28 passed |
| `pytest tests/test_e2e.py -q` | 4 passed |
| `pytest tests/test_browsers.py -q` | 3 passed (Chromium, Firefox, WebKit) |
| `pytest tests/test_a11y.py -q` | skipped — no Playwright browser binaries installed |

Scope of that suite, for reference when it is restored: CSRF/security headers/production secret
guard; wallet–ledger–revenue atomicity, duplicate confirm, concurrency, reconciliation; floor and
slot state gates, overlapping holds; QR entry/exit state machine and overtime settlement; page
routes per role and endpoint contracts; DOM-wiring guard; Playwright end-to-end flows; axe-core on
18 authenticated pages; three-browser rendering.

## 3. Known gaps

- No executable test suite in the repository.
- No physical QR scan on hardware; no real mobile device.
- WebKit is not Safari; no Edge-channel run.
- No load, soak or multi-process concurrency test; SQLite single file, one app process assumed.
- No restore drill against a production-sized database.
- Lighthouse not run; axe-core results exist only in the historical section.
- The local `.venv` is missing installed dependencies; `pip install -r requirements.txt` is required
  before using it.

## 4. Manual checks after the documentation/cleanup passes

- Every page shell in `src/templates/` still extends `base.html`; no template was moved.
- `schema.sql` is untouched and remains the only schema source; `docs/db.md` and `docs/erd.md` still
  match it table-for-table (validated via the SRS ERD check).
- Seeding path used by `docs/deployment.md` is `scripts\seed_direct.py` and was executed above.
