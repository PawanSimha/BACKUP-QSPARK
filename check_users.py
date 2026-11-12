import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from werkzeug.security import check_password_hash

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)

from app import create_app
app = create_app()
app.config.update(TESTING=True, DATABASE_PATH=db_path, WTF_CSRF_ENABLED=False, SECRET_KEY="test")

with app.app_context():
    init_db(db_path)
    from tests.conftest import seed_base
    seed_base(db_path)
    conn = get_connection(db_path)
    
    # Check ALL users and their usernames
    users = conn.execute("SELECT username, role, admin_id FROM users").fetchall()
    print("=== ALL USERS ===")
    for u in users:
        print(f"  username={u[0]}, role={u[1]}, admin_id={u[2]}")
    
    # Try different username patterns
    print("\n=== TRYING DIFFERENT USERNAMES ===")
    for name_tuple in users:
        name = name_tuple[0]
        row = conn.execute("SELECT password_hash FROM users WHERE username=?", (name,)).fetchone()
        if row:
            # Try common passwords
            admin_valid = check_password_hash(row[0], 'admin123')
            sa_valid = check_password_hash(row[0], 'super123')
            cust_valid = check_password_hash(row[0], 'user123')
            print(f"  {name}: admin123={admin_valid}, super123={sa_valid}, user123={cust_valid}")
    
    conn.close()
os.close(fd)