"""Shared throwaway server for browser-based tests (never touches the real database)."""

import os
import tempfile
import threading
import time
from contextlib import contextmanager

from werkzeug.serving import make_server

from tests.conftest import seed_base


@contextmanager
def live_server(port):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_PATH"] = db_path
    os.environ["SECRET_KEY"] = "browser-test-secret"

    from app import create_app

    app = create_app()
    seed_base(db_path)
    server = make_server("127.0.0.1", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        try:
            os.remove(db_path)
        except PermissionError:
            pass


def sign_in(page, base, username, password, expect):
    page.goto(base + "/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#loginBtn")
    page.wait_for_url("**" + expect, timeout=20000)
