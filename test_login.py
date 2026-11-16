import os
os.environ["QSPARK_SUPER_ADMIN_PASSWORD"] = "superadmin123"

from app import create_app
from src.services.db import init_db, get_connection

app = create_app()
init_db(app.config["DATABASE_PATH"])

with app.app_context():
    with app.test_client() as client:
        # First, get a CSRF token by loading the login page path
        # The test client should handle this
        resp = client.get('/login')
        print("Login page:", resp.status_code)
        
        # Try JSON login - should work without CSRF for JSON
        resp = client.post('/api/auth/login', json={
            'username': 'superadmin',
            'password': 'superadmin123'
        })
        print("Superadmin JSON login:", resp.status_code, resp.get_json())
        
        # Try with form data and CSRF token
        # Get CSRF token from the form
        resp = client.get('/login')
        print("Get login page cookies:", resp.cookies)