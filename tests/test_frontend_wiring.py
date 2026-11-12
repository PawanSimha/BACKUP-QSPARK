"""Regression tests for frontend wiring: DOM element references and CSS coverage.

The QR scanner used to reference elements that were never rendered, which threw a
TypeError inside the page IIFE and silently killed every other listener on the
page. These tests fail if any inline script references a missing element.

The same failure mode has a styling twin: a class that resolves to neither
app.css nor the compiled Tailwind output renders unstyled. The landing page
shipped with 68 such classes. These tests fail on that too.
"""

import os
import re

import pytest

CUSTOMER_PAGES = [
    "/dashboard",
    "/booking",
    "/bookings/my",
    "/wallet",
    "/profile",
]
ADMIN_PAGES = [
    "/admin/dashboard",
    "/admin/bookings",
    "/admin/customers",
    "/admin/slots",
    "/admin/analytics",
    "/admin/master",
    "/admin/qr-scan",
]
SUPER_PAGES = [
    "/super-admin/dashboard",
    "/super-admin/admins",
    "/super-admin/infrastructure",
    "/super-admin/analytics",
    "/super-admin/data",
    "/super-admin/system",
]

GET_BY_ID = re.compile(r"""getElementById\(\s*['"]([A-Za-z][\w:-]*)['"]\s*\)""")

# Elements that live in base.html, so they are not part of the page body.
BASE_IDS = {
    "navToggle", "sidebar", "navWallet", "toastRegion",
    "appDialog", "appDialogTitle", "appDialogMessage", "appDialogOk", "main",
}


def _inline_script(html):
    """Return the inline <script> bodies of a rendered page."""
    return "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S))


def _declared_ids(html):
    return set(re.findall(r"""\bid=["']([\w:-]+)["']""", html))


@pytest.fixture
def admin(client):
    res = client.post("/api/auth/login", json={"username": "admin1", "password": "admin123"})
    assert res.status_code == 200
    return client


@pytest.fixture
def customer(client):
    res = client.post("/api/auth/login", json={"username": "cust1", "password": "user123"})
    assert res.status_code == 200
    return client


@pytest.fixture
def superadmin(client):
    res = client.post("/api/auth/login", json={"username": "superadmin", "password": "super123"})
    assert res.status_code == 200
    return client


@pytest.mark.parametrize("path", CUSTOMER_PAGES)
def test_customer_inline_scripts_reference_rendered_elements(customer, path):
    _assert_ids_resolve(customer, path)


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_admin_inline_scripts_reference_rendered_elements(admin, path):
    _assert_ids_resolve(admin, path)


@pytest.mark.parametrize("path", SUPER_PAGES)
def test_super_admin_inline_scripts_reference_rendered_elements(superadmin, path):
    _assert_ids_resolve(superadmin, path)


def _assert_ids_resolve(client, path):
    """Every getElementById() target must exist in the rendered page."""
    res = client.get(path)
    assert res.status_code == 200, path
    html = res.get_data(as_text=True)
    present = _declared_ids(html) | BASE_IDS
    missing = {eid for eid in GET_BY_ID.findall(_inline_script(html)) if eid not in present}
    assert not missing, f"{path} references missing element ids: {sorted(missing)}"


def test_qr_scan_has_no_undefined_element_reference(admin):
    """The removed log-panel toggle must not be referenced any more."""
    res = admin.get("/admin/qr-scan")
    html = res.get_data(as_text=True)
    assert "toggleLogs" not in html


def test_qr_scan_log_panel_exists(admin):
    """The optional log panel is rendered so log() has a real target."""
    res = admin.get("/admin/qr-scan")
    html = res.get_data(as_text=True)
    assert 'id="logConsole"' in html


def test_qr_scan_logging_cannot_throw(admin):
    """log() must be guarded so a missing panel cannot break the scanner."""
    res = admin.get("/admin/qr-scan")
    script = _inline_script(res.get_data(as_text=True))
    assert "if (!logConsole) return;" in script
    assert "console.log(" in script


def test_qr_scan_feature_detects_barcode_detector(admin):
    """The decoder is only constructed when the constructor really exists."""
    res = admin.get("/admin/qr-scan")
    script = _inline_script(res.get_data(as_text=True))
    assert "typeof window.BarcodeDetector === 'function'" in script
    assert script.index("typeof window.BarcodeDetector === 'function'") < script.index(
        "new window.BarcodeDetector("
    )


def test_qr_scan_camera_preview_is_independent_of_decoder(admin):
    """The preview is wired to the stream before any decoder setup."""
    res = admin.get("/admin/qr-scan")
    script = _inline_script(res.get_data(as_text=True))
    assert script.index("video.srcObject = stream;") < script.index(
        "typeof window.BarcodeDetector === 'function'"
    )
    # The stream is never stopped because of a missing decoder.
    assert "stopCamera();" not in script.split("typeof window.BarcodeDetector")[0]


def test_qr_scan_manual_entry_is_preserved(admin):
    """Manual reference submission stays available as the fallback."""
    res = admin.get("/admin/qr-scan")
    html = res.get_data(as_text=True)
    assert 'id="manualForm"' in html
    assert 'id="refInput"' in html
    assert 'id="scanBtn"' in html
    assert "manualForm" in _inline_script(html)


def test_qr_scan_camera_controls_present(admin):
    """Start/stop controls and their listeners exist."""
    res = admin.get("/admin/qr-scan")
    html = res.get_data(as_text=True)
    assert 'id="startCam"' in html
    assert 'id="stopCam"' in html
    script = _inline_script(html)
    assert "getElementById('startCam').addEventListener" in script
    assert "getElementById('stopCam').addEventListener" in script


def test_qr_scan_reports_camera_errors_per_reason(admin):
    """Distinct messages for denied, missing and busy cameras."""
    res = admin.get("/admin/qr-scan")
    script = _inline_script(res.get_data(as_text=True))
    assert "NotAllowedError" in script
    assert "NotFoundError" in script
    assert "NotReadableError" in script


# --------------------------------------------------------------------------
# CSS coverage
#
# A class that resolves to neither app.css nor the compiled Tailwind output
# renders unstyled, which is how the landing page shipped with 68 dead classes.
# --------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(ROOT, "src", "templates")
APP_CSS = os.path.join(ROOT, "src", "static", "css", "app.css")
TAILWIND_CSS = os.path.join(ROOT, "src", "static", "css", "tailwind.css")

# Classes that are intentionally not styled.
CSS_EXEMPT = {
    "hidden", "is-open", "is-visible", "faq-open", "sr-only",
}

with open(APP_CSS, encoding="utf-8") as fh:
    APP_CSS_TEXT = fh.read()
with open(TAILWIND_CSS, encoding="utf-8") as fh:
    TAILWIND_CSS_TEXT = fh.read()


def _tailwind_has(class_name):
    """True when the compiled Tailwind output contains a rule for this class."""
    escaped = re.sub(r"([:\[\]/%.])", r"\\\1", class_name)
    # The selector must not be the prefix of a longer class (.flex vs .flex-col).
    return re.search(r"\.%s(?![-\w])" % re.escape(escaped), TAILWIND_CSS_TEXT) is not None


def _template_classes():
    """Yield (template, class) for every class used in a real HTML class attribute."""
    for root, _dirs, files in os.walk(TEMPLATE_DIR):
        for name in sorted(files):
            if not name.endswith(".html"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as fh:
                html = fh.read()
            # Strip <script> bodies: their quotes are JavaScript, not markup.
            html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S)
            for match in re.finditer(r'class="([^"]*)"', html):
                raw = re.sub(r"\{\{.*?\}\}", " ", match.group(1))
                raw = re.sub(r"\{%.*?%\}", " ", raw)
                for cls in raw.split():
                    yield os.path.basename(path), cls.strip()


def test_every_template_class_is_defined():
    """Every class used in a template must resolve to app.css or compiled Tailwind."""
    missing = {}
    for template, cls in _template_classes():
        if not cls or cls in CSS_EXEMPT:
            continue
        if _tailwind_has(cls):
            continue
        if re.search(r"\.%s(?![-\w])" % re.escape(cls), APP_CSS_TEXT):
            continue
        missing.setdefault(cls, set()).add(template)

    assert not missing, "classes with no CSS rule: " + ", ".join(
        f".{cls} ({', '.join(sorted(files))})" for cls, files in sorted(missing.items())
    )


def test_app_css_defines_the_landing_page_layer():
    """The landing page stylesheet must not be empty or missing."""
    for cls in (
        "floating-nav",
        "hero-section",
        "features-section",
        "faq-section",
        "role-card",
        "final-cta-section",
    ):
        assert re.search(r"\.%s(?![-\w])" % re.escape(cls), APP_CSS_TEXT), (
            f".{cls} is missing from app.css"
        )
