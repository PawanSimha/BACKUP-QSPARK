"""End-to-end browser tests (Playwright) against an isolated temporary database."""

import os
import tempfile
import threading
import time
from datetime import date, timedelta

import pytest
from werkzeug.serving import make_server

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.conftest import seed_base  # noqa: E402


@pytest.fixture(scope="module")
def live_server():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_PATH"] = db_path
    os.environ["SECRET_KEY"] = "e2e-secret"

    from app import create_app

    app = create_app()
    app.config["TESTING"] = False
    seed_base(db_path)

    server = make_server("127.0.0.1", 5099, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    yield "http://127.0.0.1:5099"
    server.shutdown()
    thread.join(timeout=5)
    try:
        os.remove(db_path)
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = context.new_page()
    errors = []
    pg.on("pageerror", lambda exc: errors.append(str(exc)))
    pg.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    pg._qs_errors = errors
    yield pg
    context.close()


def sign_in(page, base, username, password, expect="/dashboard"):
    page.goto(base + "/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#loginBtn")
    page.wait_for_url("**" + expect, timeout=15000)


def test_customer_booking_wallet_and_cancel(live_server, page):
    base = live_server
    sign_in(page, base, "cust1", "user123")

    page.wait_for_selector("#walletBalance:not(:has-text('—'))")
    assert page.locator("#availableSlots").inner_text() == "4"

    page.click("text=Book a parking slot")
    page.wait_for_selector("[data-vtype]")
    page.click("[data-vtype='1']")
    page.fill("#vehicleNumber", "KA 04 A 2256")
    page.click("[data-next='3']")
    page.wait_for_selector("#slotGrid .slot[data-status='AVAILABLE']")
    page.locator("#slotGrid .slot[data-status='AVAILABLE']").first.click()
    page.click("[data-next='4']")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    page.fill("#bookDate", tomorrow)
    page.fill("#startTime", "10:00")
    page.select_option("#durationHours", "2")
    page.click("[data-next='5']")
    page.wait_for_selector("#confirmBtn")
    page.click("#confirmBtn")
    page.wait_for_selector("#successPanel:not(.hidden)", timeout=20000)
    ref = page.locator("#successDetails .mono").inner_text()
    assert ref.startswith("QSP-")
    assert page.locator("#successQr").get_attribute("src").startswith("data:image/png;base64,")

    page.goto(base + "/wallet")
    page.wait_for_selector("#walletBalance:not(:has-text('—'))")
    assert "990" in page.locator("#walletBalance").inner_text()

    page.goto(base + "/bookings/my")
    page.wait_for_selector("[data-detail='%s']" % ref)
    page.click("[data-cancel='%s']" % ref)
    page.click("#appDialogOk")
    page.wait_for_selector(".toast-region >> text=Booking cancelled", timeout=15000)

    assert not page._qs_errors, page._qs_errors


def test_admin_walk_in_slot_scan_and_analytics(live_server, page):
    base = live_server
    sign_in(page, base, "admin1", "admin123", expect="/admin/dashboard")
    page.wait_for_selector("[data-kpi='total_slots']:not(:has-text('—'))")
    assert page.locator("[data-kpi='total_slots']").inner_text() == "4"

    # walk-in registration
    page.goto(base + "/admin/customers")
    page.wait_for_selector("#rows tr")
    page.click("#newCustomerBtn")
    page.fill("#cFullName", "Walk In")
    page.fill("#cPhone", "9876500011")
    page.fill("#cCompany", "Acme")
    page.click("#cSubmit")
    page.wait_for_selector("#rows >> text=Walk In", timeout=15000)

    # slot maintenance toggle
    page.goto(base + "/admin/slots")
    page.wait_for_selector("#slotGrid .slot")
    page.locator("#slotGrid .slot").nth(1).click()
    page.wait_for_selector("#slotDetail [data-set='MAINTENANCE']")
    page.click("#slotDetail [data-set='MAINTENANCE']")
    page.click("#appDialogOk")
    page.wait_for_selector(".toast-region >> text=Slot updated", timeout=15000)
    page.wait_for_selector("#slotGrid .slot[data-status='MAINTENANCE']")
    page.click("#slotGrid .slot[data-status='MAINTENANCE']")
    page.click("#slotDetail [data-set='ACTIVE']")
    page.click("#appDialogOk")
    page.wait_for_selector(".toast-region >> text=Slot updated", timeout=15000)

    # QR scan: unknown reference degrades gracefully
    page.goto(base + "/admin/qr-scan")
    page.fill("#refInput", "QSP-DOES-NOT-EXIST")
    page.click("#scanBtn")
    page.wait_for_selector("#resultTitle >> text=Unknown booking", timeout=15000)

    page.goto(base + "/admin/analytics")
    page.wait_for_selector("#occupancyRows tr")
    assert "No occupancy" not in page.locator("#occupancyRows").inner_text()

    # the deliberately unknown reference above returns 404 by design; drop that one console entry
    page._qs_errors[:] = [e for e in page._qs_errors if "404" not in e]
    assert not page._qs_errors, page._qs_errors


def test_super_admin_management_flows(live_server, page):
    base = live_server
    sign_in(page, base, "superadmin", "super123", expect="/super-admin/dashboard")
    page.wait_for_selector("[data-kpi='total_slots']:not(:has-text('—'))")
    page.wait_for_selector("#sysBadge >> text=ONLINE")

    # create admin
    page.goto(base + "/super-admin/admins")
    page.wait_for_selector("#rows tr")
    page.click("#newAdminBtn")
    page.fill("#aName", "Ops Admin")
    page.fill("#aPhone", "9876500022")
    page.fill("#aUsername", "opsadmin")
    page.fill("#aPassword", "secret12345")
    page.click("#adminSubmit")
    page.wait_for_selector("#rows >> text=Ops Admin", timeout=15000)

    # block then unblock
    row = page.locator("#rows tr", has_text="Ops Admin")
    row.locator("[data-block]").click()
    page.click("#appDialogOk")
    page.wait_for_selector("#rows tr:has-text('Ops Admin') >> text=BLOCKED", timeout=15000)
    page.locator("#rows tr", has_text="Ops Admin").locator("[data-unblock]").click()
    page.click("#appDialogOk")
    page.wait_for_selector("#rows tr:has-text('Ops Admin') >> text=ACTIVE", timeout=15000)

    # wallet adjustment on the test customer
    page.goto(base + "/admin/customers")
    page.wait_for_selector("#rows tr")
    page.locator("#rows tr", has_text="Test Customer").locator("[data-wallet]").click()
    page.select_option("#wMode", "CREDIT")
    page.fill("#wAmount", "50")
    page.fill("#wReason", "E2E top-up")
    page.click("#wSubmit")
    page.click("#appDialogOk")
    page.wait_for_selector(".toast-region >> text=Balance updated", timeout=15000)

    # infrastructure: add and deactivate a floor
    page.goto(base + "/super-admin/infrastructure")
    page.wait_for_selector("#floorRows tr")
    page.click("#newFloorBtn")
    page.fill("#floorCode", "B9")
    page.click("#floorSubmit")
    page.wait_for_selector("#floorRows >> text=B9", timeout=15000)
    page.on("dialog", lambda d: d.accept())
    page.locator("#floorRows tr", has_text="B9").locator("[data-floor-off]").click()
    page.click("#appDialogOk")
    page.wait_for_selector(".toast-region >> text=Floor deactivated", timeout=15000)

    # analytics + CSV download
    page.goto(base + "/super-admin/analytics")
    page.wait_for_selector("#heatRows tr")
    with page.expect_download() as dl:
        page.click("[data-download='/api/super-admin/reports/occupancy.csv']")
    assert dl.value.suggested_filename.endswith(".csv")

    # database views
    page.goto(base + "/super-admin/data")
    page.wait_for_selector("#dataBody tr")
    page.select_option("#tableSelect", "system_settings")
    page.wait_for_selector("#dataBody >> text=SYSTEM_STATUS")

    # system toggle and restore
    page.goto(base + "/super-admin/system")
    page.wait_for_selector("#statusBadge >> text=ONLINE")
    page.click("#toggleBtn")
    page.click("#appDialogOk")
    page.wait_for_selector("#statusBadge >> text=OFFLINE", timeout=15000)
    page.click("#toggleBtn")
    page.click("#appDialogOk")
    page.wait_for_selector("#statusBadge >> text=ONLINE", timeout=15000)

    assert not page._qs_errors, page._qs_errors


def test_responsive_layouts_have_no_horizontal_overflow(live_server, page):
    base = live_server
    sign_in(page, base, "admin1", "admin123", expect="/admin/dashboard")
    for width, height in ((320, 720), (768, 900), (1440, 900)):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(base + "/admin/bookings")
        page.wait_for_selector("#rows tr")
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 1, f"{width}px overflowed by {overflow}px"
