"""Accessibility tests: axe-core scans every page for critical/serious issues."""

import pytest

pytest.importorskip("axe_playwright_python")
pytest.importorskip("playwright.sync_api")

from axe_playwright_python.sync_playwright import Axe  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from tests.live_server import live_server, sign_in  # noqa: E402

PAGES = {
    "cust1": ("user123", ["/dashboard", "/booking", "/bookings/my", "/wallet", "/profile"]),
    "admin1": ("admin123", [
        "/admin/dashboard", "/admin/bookings", "/admin/customers", "/admin/slots",
        "/admin/analytics", "/admin/master", "/admin/qr-scan",
    ]),
    "superadmin": ("super123", [
        "/super-admin/dashboard", "/super-admin/admins", "/super-admin/infrastructure",
        "/super-admin/analytics", "/super-admin/data", "/super-admin/system",
    ]),
}
LANDING = {"cust1": "/dashboard", "admin1": "/admin/dashboard", "superadmin": "/super-admin/dashboard"}


@pytest.fixture(scope="module")
def base_url():
    with live_server(5096) as url:
        yield url


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


def test_all_pages_have_no_accessibility_violations(base_url, browser):
    axe = Axe()
    failures = []
    for username, (password, paths) in PAGES.items():
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        sign_in(page, base_url, username, password, LANDING[username])
        for path in paths:
            page.goto(base_url + path)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(300)
            results = axe.run(page)
            for violation in results.response.get("violations", []):
                failures.append(f"{path}: [{violation['impact']}] {violation['id']} "
                                f"({len(violation['nodes'])} nodes)")
        context.close()
    assert not failures, "axe violations:\n" + "\n".join(failures)
