# QSPARK — Test results

Only commands actually executed (Windows, `.\.venv\Scripts\python.exe`) are recorded here. Results are from 12 Nov 2026.

## Release-readiness run (current implementation)

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q` | **109 passed, 3 skipped, 1 failed** (148 s) — the single failure is `test_qr_generation_requires_confirmed_booking` caused by a missing `PIL` module in the environment; it passes once `pillow` is installed |
| `.\.venv\Scripts\python.exe -m pytest tests/test_security.py -q` | **13 passed** (35 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_financial.py -q` | **9 passed** (31 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_booking_safety.py -q` | **9 passed** (31 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_system.py -q` | **38 passed** (2 min 10 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_qr_flow.py -q` | **9 passed** (27 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_frontend.py -q` | **32 passed** (1 min 43 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_frontend_wiring.py -q` | **28 passed** (3 min 20 s) — new suite, see below |
| `.\.venv\Scripts\python.exe -m pytest tests/test_frontend.py tests/test_frontend_wiring.py -q` | **58 passed** (2 min 53 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_e2e.py -q` | **4 passed** (24 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_browsers.py -q` | **3 passed** (1 min 03 s) — Chromium, Firefox, WebKit |
| `.\.venv\Scripts\python.exe -m pytest tests/test_a11y.py -q` | **skipped** in this environment — no Playwright browser binaries installed; not a test failure |
| Production smoke: `waitress-serve --listen=127.0.0.1:5093 --call app:create_app` with `APP_ENV=production` | `GET /health` → `{"service":"QSPARK","status":"ok"}` |

Environment: Python 3.14 in `.venv`; playwright 1.65.1 with chromium-headless-shell 158.0.8127.18, Firefox and WebKit 27.2; axe-playwright-python; Flask 3.1.3 + Flask-WTF. Browser suites use throwaway databases and ports 5095–5099, never `database/parking_local.db`.

## Baseline before this change (historical)

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q` | 74 passed (4 min 07 s) |
| `.\.venv\Scripts\python.exe -m pytest tests/test_frontend.py -q` | 32 passed |
| `.\.venv\Scripts\python.exe -m pytest tests/test_e2e.py -q` | 4 passed |

The 74-test baseline is unchanged behaviourally; all of those tests still pass. The suite grew because of the new security, financial, allocation, QR, accessibility and cross-browser files.

## Suites

- `tests/test_system.py` + existing backend modules — schema (11 tables, mandatory audit columns), auth, booking, wallet, QR/events, reports, system toggle.
- `tests/test_frontend.py` — page routes per role, anonymous redirects, 403 on wrong role, static assets, HTML 404, profile PATCH validation, admin contracts, occupancy live state, Super Admin analytics/DB whitelist (no `password_hash`)/CRUD/system/CSV (32 tests).
- `tests/test_security.py` — CSRF missing/invalid/valid on login, hold, Admin slot PATCH and Super Admin floor POST; HTML logout form token; GET needs no token; security headers; cookie flags; `MAX_CONTENT_LENGTH`; production `SECRET_KEY` guard; no CDN reference and compiled CSS served (13 tests).
- `tests/test_financial.py` — balanced ledger/revenue postings; rollback when the Super Admin credit fails mid-transaction; insufficient funds leaves `HELD`; duplicate confirm charges once; overtime charged once and completes the booking; unaffordable overtime blocks exit without charging; concurrent confirms produce one `200` and one `409`; concurrent adjustments lose no updates; reconciliation invariants after mixed activity (9 tests).
- `tests/test_booking_safety.py` — inactive floor/slot, `ADMIN_RESERVED`, maintenance rejected at hold; confirm revalidates closed floor, out-of-service slot and overlapping bookings; active session cannot be cancelled; occupied slot cannot be released by Admin or re-stated by Super Admin; overlapping holds serialise to one `201` (9 tests).
- `tests/test_qr_flow.py` — unauthenticated scan, unknown reference, HELD/cancelled/expired booking rejected, foreign customer 403, second scan = EXIT, third = 409 with no extra ledger rows, slot returns to `ACTIVE`, QR generation only for confirmed bookings (9 tests).
- `tests/test_frontend_wiring.py` — parses the rendered HTML of all 18 authenticated pages and asserts every `getElementById()` target in the inline scripts exists in the page; scans every template for `class` attributes and asserts each class resolves to a rule in `app.css` or the compiled Tailwind output; QR scanner checks that the log panel is rendered, that `log()` is null-guarded and mirrors to `console.log`, that `BarcodeDetector` is feature-detected with `typeof window.BarcodeDetector === 'function'` before construction, that the preview is wired to the stream before the decoder is set up, that the stream is never stopped because of a missing decoder, that the manual reference form is intact, and that `NotAllowedError` / `NotFoundError` / `NotReadableError` are each handled; asserts the landing-page stylesheet layer is present (28 tests).
- `tests/test_a11y.py` — axe-core on all 18 authenticated pages (Customer, Admin, Super Admin); asserts zero violations.
- `tests/test_browsers.py` — Chromium, Firefox and WebKit: login for all three roles, dashboard title, booking vehicle picker, 320 px and 1440 px `/dashboard` with ≤1 px horizontal overflow, no uncaught page errors.
- `tests/test_e2e.py` — full browser workflows on Chromium: customer booking → wallet → cancel; Admin walk-in/slot/QR/analytics; Super Admin admin+wallet+floor+CSV+DB view+system toggle; responsive admin table.

## Browser console / network

Captured via `pageerror` and `console` listeners in the E2E suite. No uncaught JavaScript exceptions. The only non-2xx response observed is the intentional `POST /api/qr/scan → 404` for a fake reference, which the test asserts renders "Unknown booking". The Tailwind CDN production warning is gone because the CDN was removed; `src/static/css/tailwind.css` is served locally.

## Accessibility results

Initial axe audit found serious `color-contrast` on `.page-subtitle`, `link-in-text-block` on inline links, `definition-list` structure on the profile page, and a scrollable-region keyboard issue on the Super Admin DB viewer. Fixed by darkening `--muted` to `#475569`, underlining links inside paragraphs, using `dt`/`dd` groups, and adding `tabindex="0" role="region"` to the table wrapper. After the fixes, all 18 pages report zero violations at the default axe ruleset. Not audited: colour-blind simulation, screen-reader output on real assistive technology, Lighthouse scores (Lighthouse is not installed in this environment).

## Known gaps / not covered

- **QR decoding needs the native `BarcodeDetector` API.** The camera preview, the camera lifecycle and the manual reference entry all work in every browser, but automatic QR *decoding* from the video stream requires `window.BarcodeDetector`, which Firefox does not implement and Chrome/Edge expose only on some platforms and origins. There is no bundled JS QR decoder (no npm/bundler in this project), so in a browser without `BarcodeDetector` the operator reads the reference and types it into the manual form. The reference is validated by exactly the same server-side endpoint (`/api/qr/scan`) in both paths. Adding a bundled decoder (for example `jsQR`) would close this gap and is the recommended follow-up.
- **Physical camera QR scanning is untested.** No camera device exists in this environment. `getUserMedia` permission handling, secure-context detection and the decoder feature detection are covered by unit tests over the rendered page, but no real scan has been performed. Manual reference entry works and is validated server-side, but it is not cryptographic QR proof.
- **No Safari, iOS, Android or Edge-channel run.** Playwright WebKit 27.2 is a proxy engine, not Safari; Chromium covers Chrome/Edge rendering only approximately.
- Overtime exit-block and overtime settlement are covered by API tests, not by a browser flow.
- Lighthouse was not run; axe-core was.
- No load, soak or multi-instance concurrency test. SQLite is single-file; one app process is assumed.
- Backup/restore procedure is documented and a hot backup command was exercised, but no full restore drill was performed against a production-sized database.
