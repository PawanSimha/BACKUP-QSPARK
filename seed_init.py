import os
os.environ["QSPARK_SUPER_ADMIN_PASSWORD"] = "superadmin123"

from app import create_app
from src.services.db import init_db

app = create_app()
init_db(app.config["DATABASE_PATH"])

with app.app_context():
    with app.test_client() as client:
        # First get CSRF token from a GET request
        resp = client.get('/api/auth/me')
        print("Me response:", resp.status_code, resp.get_json())
        # The setup-admin uses JSON and doesn't seem to require CSRF based on the code
        resp = client.post('/api/auth/setup-admin', json={})
        print("Setup admin response:", resp.status_code, resp.get_json())