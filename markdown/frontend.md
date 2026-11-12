# QSPARK — Frontend architecture

Canonical frontend reference. Pages are Jinja2 shells; all data comes from the JSON APIs in `markdown/api.md`.

## Stack

Flask + Jinja2 templates, **compiled Tailwind CSS** (standalone binary, no Node/npm, no build step at runtime), one hand-written design-system stylesheet, vanilla ES2017 JavaScript, session-cookie auth. No frontend framework, no bundler, no npm dependencies.

## Files

```
src/templates/base.html            layout: sidebar, topbar, mobile nav, toast region, confirm <dialog>, blocks title|breadcrumb|content|scripts
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

Tailwind utilities handle layout only (grid/flex/spacing). Never introduce raw hex colours in templates; use the tokens.

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

The scan page uses `navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}})` and decodes with the in-page scanner; denial or absence of a camera shows an inline message and leaves manual reference entry available. Both paths call `POST /api/qr/scan`; the server validates the reference, the scanner's authority, booking state and duplicate entry/exit. Manual entry is convenience, not proof of a physical QR.

## Frontend tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend.py -q   # render + endpoint contracts
.\.venv\Scripts\python.exe -m pytest tests/test_e2e.py -q        # Playwright, temp DB on 127.0.0.1:5099
.\.venv\Scripts\python.exe -m pytest tests/test_a11y.py -q       # axe-core, temp DB on 127.0.0.1:5096
.\.venv\Scripts\python.exe -m pytest tests/test_browsers.py -q   # Chromium/Firefox/WebKit, port 5095
```

Playwright is the Python package (`pip install playwright`, `python -m playwright install chromium firefox webkit`). Node is not required.
