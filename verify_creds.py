import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from werkzeug.security import check_password_hash

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
init_db(db_path)

# Seed base credentials
from tests.conftest import seed_base
seed_base(db_path)

conn = get_connection(db_path)

# Check the three default accounts
for name, expected_pw in [('cust1', 'user123'), ('admin1', 'admin123'), ('superadmin', 'super123')]:
    row = conn.execute("SELECT username, password_hash, account_status, role FROM users WHERE username=?", (name,)).fetchone()
    if row:
        ph = row[1]
        # Try to verify the expected password
        valid = check_password_hash(ph, expected_pw)
        print(f"{name}: status={row[2]}, role={row[3]}")
        print(f"  password_hash valid for '{expected_pw}': {valid}")
    else:
        print(f"{name}: NOT FOUND")

conn.close()
os.remove(db_path)