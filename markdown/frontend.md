# QSPARK — Frontend architecture

Canonical frontend reference. Pages are Jinja2 shells; all data comes from the JSON APIs in `markdown/api.md`.

## Stack

Flask + Jinja2 templates, **compiled Tailwind CSS** (standalone binary, no Node/npm, no build step at runtime), one hand-written design-system stylesheet, vanilla ES2017 JavaScript, session-cookie auth. No frontend framework, no bundler, no npm dependencies.

## Files

```
src/templates/base.html            layout: sidebar, topbar, mobile nav, toast region, confirm <dialog>, blocks title|breadcrumb|content|scripts
src/templates/landing.html         public landing page (GET /landing) — static, no API calls
src/templates/login.html           public sign-in
src/templates/dashboard.html       customer dashboard
src/templates/booking.html         5-step booking wizard
src/templates/my_bookings.html     list, filters, detail dialog, cancel
src/templates/wallet.html          balance + ledger
src/templates/profile.html         self-service contact edit
src/templates/confirm.html         single booking + QR
src/templates/error.html           403/404/500
src/templates/admin_*.html         admin dashboard, bookings, customers, slots, analytics, master (configuration), qr_scan
src/templates/super_admin_*.html   dashboard, admins, infrastructure, analytics, data, system
src/static/css/app.css             design tokens + component classes
src/static/css/tailwind.input.css  Tailwind source (@tailwind directives)
src/static/css/tailwind.css        compiled output — committed, linked before app.css
src/static/images/                 logo-light.webp, logo-dark.webp, favicon.ico
tailwind.config.js                 content paths: src/templates/**/*.html, src/static/js/**/*.js
tools/tailwindcss.exe              standalone Tailwind v3.4.17 CLI (downloaded, gitignored)
src/static/js/core/api.js          window.QS — fetch wrapper + X-CSRFToken
src/static/js/core/ui.js           window.QSUI — esc, money, dateTime, debounce, toast, confirmDialog, setBusy, statusBadge, emptyRow
```

Page-to-API mapping is documented per route in `markdown/api.md`.

## CSS build

Tailwind is not fetched from a CDN. After changing templates or JS classes, rebuild and commit the output:

```powershell
.\tools\tailwindcss.exe -c tailwind.config.js -i src\static\css\tailwind.input.css -o src\static\css\tailwind.css --minify
```

If `tools\tailwindcss.exe` is missing (it is gitignored, ~40 MB), download the v3.4.17 Windows x64 binary from the Tailwind releases page. Node/npm are not required and must not be introduced. `tailwind.css` must be regenerated whenever a utility class is added dynamically in JS or a new template is created; missing classes silently lose their styling.

## Design tokens

Defined in `:root` in `app.css`: brand scale (`--brand-50/100/500/600/700`), `--surface`, `--canvas`, `--text`, `--muted`, `--border`, `--success`, `--warning`, `--danger`, `--info`, radii, shadows, `--ring`, z-index. Slot colours: available green, reserved amber, occupied red, maintenance/inactive slate. Components: `.card`, `.stat`, `.btn` (`-primary/-secondary/-danger/-ghost/-sm/-icon`), `.field/.label/.input/.select/.textarea/.hint/.field-error`, `.table`, `.badge` (`-blue/-green/-amber/-red/-slate`), `.slot`, `.slot-grid`, `.steps/.step`, `.skeleton`, `.bar-row/.bar-track/.bar-fill`, `.toast-region`, `dialog.app-dialog`.

`app.css` also carries the public **landing page** layer, appended after the application
tokens: `.floating-nav*`, `.hero-*`, `.value-proposition-*`, `.features-*`, `.feature-*`,
`.timeline-*`, `.architecture-*`, `.roles-*`, `.role-*`, `.tech-*`, `.faq-*`,
`.final-cta-*`, `.mobile-menu*`, `.vp-icon`, `.wallet-note` and `.section-*`. Tailwind
utilities handle layout only (grid/flex/spacing). Never introduce raw hex colours in
templates; use the tokens.

**CSS coverage rule:** every `class` used in a template must resolve to a rule in
`app.css` or to a compiled Tailwind utility. A class that resolves to neither renders
unstyled. `tests/test_frontend_wiring.py` enforces this for every template in the
project:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_wiring.py -q
```

## JavaScript rules

- Load `core/api.js` then `core/ui.js` (base.html does this); page script goes in `{% block scripts %}`.
- All HTTP goes through `QS.get/post/put/patch/del/del/download`. It sends `credentials: 'same-origin'` and `X-CSRFToken` (read from `<meta name="csrf-token">`) on every non-GET request, JSON by default, redirects to `/login?error=session_expired` on 401, and throws `Error` with `.status`, `.payload`, `.network`. Never call `fetch` directly in a page.
- Render dynamic HTML through `U.esc()` for every interpolated value. Never inject unescaped user data.
- Guard DOM lookups, use `U.setBusy(btn, …)` to prevent double submits, `U.confirmDialog()` for irreversible actions, `U.toast()` for outcomes.
- Dates: `U.dateTime` / `U.dateOnly` parse `YYYY-MM-DD HH:MM:SS` safely. Money is formatted for display only; the server is authoritative.
- Every data page must implement loading (skeleton), empty, business-error and network-error paths.

## Role navigation

`base.html` shows the customer block to every role, then the Operations block for ADMIN/SUPER_ADMIN and the Administration block for SUPER_ADMIN. Hidden links are not security: page routes re-check the role server-side and return 403, and every API enforces `require_admin` / `require_role`.

## Responsive behaviour

Sidebar is fixed at ≥1024px and off-canvas below it (`#navToggle`). Tables scroll inside `.table-wrap`. Slot grids use `auto-fill, minmax(56px, 1fr)`. Stat and two-column grids use `minmax(min(170px|320px, 100%), 1fr)` so a 320px viewport cannot be widened by the track minimum. Verified at 320/768/1440px with ≤1px horizontal overflow in Chromium, Firefox and WebKit (`tests/test_browsers.py`).

## Accessibility

Skip link, one `<h1>` per page, labelled inputs, `aria-current="page"` on the active nav item, `aria-pressed` on slot/vehicle pickers, `aria-describedby` help and errors, `role="alert"` on error boxes and toasts, `dt`/`dd` groups in definition lists, focus rings from `--ring`, native `<dialog>` focus handling, `prefers-reduced-motion` support, and a focusable `role="region"` wrapper around scrollable data tables.

Colour: body text `#0f172a`, muted text `#475569` (≥7:1 on white), links underlined when inline in a paragraph. Any new colour must keep 4.5:1 contrast on its background.

`tests/test_a11y.py` runs axe-core across all 18 authenticated pages and fails on any violation.

## Browser support

Tested engines via Playwright: Chromium 158 (Chrome/Edge equivalent), Firefox, WebKit 27.2. **WebKit is not Safari** — no Safari/OSX or physical Android/iOS run was performed. The code targets ES2017 and the APIs used by the pages (`fetch`, `URLSearchParams`, `dialog`, `getUserMedia`) are available in the tested engines.

## QR scanning behaviour

`src/templates/qr_scan.html` requests `navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}})`
only when the operator presses **Start camera**, then attaches the stream to
`video.srcObject` (with `playsInline`) and starts playback. The preview is wired **before**
any decoder work, so a browser without a QR decoder still shows a live camera.

Decoding uses the native `BarcodeDetector` API and is feature-detected with
`typeof window.BarcodeDetector === 'function'` before the constructor is called. If it is
absent the camera keeps running and the operator uses the manual reference form — both
paths call the same `POST /api/qr/scan`, so the server validates the reference, the
scanner's authority, booking state and duplicate entry/exit identically.

Error handling is per cause: `NotAllowedError` (permission denied), `NotFoundError` /
`OverconstrainedError` (no device), `NotReadableError` (device already in use), an
insecure context (`window.isSecureContext` must be true), and a browser without
`getUserMedia`. Tracks are stopped on **Stop camera** and on `pagehide`; a track `ended`
event flips the badge to "Interrupted". A "Scanner log" `<details>` panel mirrors the
same messages to `console.log`; `log()` is null-guarded so it can never break the
scanner.

**DOM wiring rule:** every `getElementById()` target in a page's inline script must exist
in the rendered page. A missing element throws inside the page IIFE and silently kills
every listener registered after it, which leaves the whole page inert. `tests/test_frontend_wiring.py`
enforces this for all 18 authenticated pages.

Manual entry is convenience, not proof of a physical QR.

## Frontend tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend.py -q          # render + endpoint contracts
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_wiring.py -q   # inline-script DOM wiring guard
.\.venv\Scripts\python.exe -m pytest tests/test_e2e.py -q                # Playwright, temp DB on 127.0.0.1:5099
.\.venv\Scripts\python.exe -m pytest tests/test_a11y.py -q               # axe-core, temp DB on 127.0.0.1:5096
.\.venv\Scripts\python.exe -m pytest tests/test_browsers.py -q           # Chromium/Firefox/WebKit, port 5095
```

Playwright is the Python package (`pip install playwright`, `python -m playwright install chromium firefox webkit`). Node is not required.

---

## New components (Nov 2026)

- **Slot hover tooltip** (`admin_slots.html`): floating `#slotTooltip` positioned at cursor; shows occupant details (customer, vehicle, reference, entry, expected exit) for occupied/reserved slots; hidden on mouseout; follows cursor with viewport clamping.
- **Floor status stacked bar** (`admin_dashboard.html`): 4-segment bar (available/reserved/occupied/maintenance) with color legend; replaces single occupied bar.
- **Slot heat map** (`admin_analytics.html`, `super_admin_analytics.html`): per-floor colored slot grid with 4 floor selector buttons; clicking switches floors.
- **SVG charts** (`admin_analytics.html`, `super_admin_analytics.html`): hand-rolled donut (slot status mix, revenue by vehicle type/floor) and line chart (daily collections trend); no external charting library.
