"""Cross-engine checks: login, dashboard, booking wizard and responsive layout."""

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.live_server import live_server, sign_in  # noqa: E402

ENGINES = ["chromium", "firefox", "webkit"]
LANDING = {"cust1": "/dashboard", "admin1": "/admin/dashboard", "superadmin": "/super-admin/dashboard"}


@pytest.fixture(scope="module")
def base_url():
    with live_server(5095) as url:
        yield url


@pytest.mark.parametrize("engine", ENGINES)
def test_login_dashboard_booking_and_layout(base_url, engine):
    with sync_playwright() as p:
        launcher = getattr(p, engine)
        browser = launcher.launch()
        try:
            for username, password in (("cust1", "user123"), ("admin1", "admin123"),
                                       ("superadmin", "super123")):
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))

                sign_in(page, base_url, username, password, LANDING[username])
                assert "QSPARK" in page.title()

                page.goto(base_url + "/booking")
                page.wait_for_selector("[data-vtype]")
                assert page.locator("[data-vtype]").count() > 0

                for width in (320, 1440):
                    page.set_viewport_size({"width": width, "height": 900})
                    page.goto(base_url + "/dashboard")
                    page.wait_for_load_state("networkidle")
                    overflow = page.evaluate(
                        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
                    )
                    assert overflow <= 1, f"{engine} {width}px overflowed {overflow}px"

                assert not errors, f"{engine} page errors: {errors}"
                context.close()
        finally:
            browser.close()
