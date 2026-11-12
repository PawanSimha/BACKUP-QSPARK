import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from src.core.security import hash_password
import secrets

fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
init_db(db_path)

from tests.conftest import seed_base
seed_base(db_path)

# Create app
app = create_app()
app.config.update(TESTING=True, DATABASE_PATH=db_path, WTF_CSRF_ENABLED=False, SECRET_KEY="test")

with app.app_context():
    conn = get_connection(db_path)
    
    # Check what's in the database before rotation
    print("=== BEFORE ROTATION ===")
    users = conn.execute("SELECT username, password_hash FROM users WHERE username IN ('admin1', 'superadmin')").fetchall()
    for u in users:
        print(f"  {u[0]}: hash_length={len(u[1])}")
    
    # Try a simple UPDATE to test
    test_pw = "newtestpw123"
    new_hash = hash_password(test_pw)
    
    print(f"\nAttempting UPDATE admin1 with new hash...")
    result = conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = 'admin1'",
        (new_hash,),
    )
    print(f"  rows_updated: {result.rowcount}")
    
    # Check if the update worked
    user = conn.execute("SELECT password_hash FROM users WHERE username = 'admin1'").fetchone()
    if user:
        print(f"  hash after update: {user[0][:30]}...")
        # Verify if it matches the test password
        from werkzeug.security import check_password_hash
        valid = check_password_hash(user[0], test_pw)
        print(f"  hash matches test pw: {valid}")
    
    # Rollback the test change
    conn.execute("UPDATE users SET password_hash = ? WHERE username = 'admin1'",
                 (hash_password("admin123"),))  # Reset to original
    conn.commit()
    
    # Now try the actual rotation password
    new_admin_pw = secrets.token_urlsafe(16)
    new_admin_pw_hash = hash_password(new_admin_pw)
    
    print(f"\nAttempting UPDATE admin1 with rotation hash (length: {len(new_admin_pw)})")
    result2 = conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = 'admin1'",
        (new_admin_pw_hash,),
    )
    print(f"  rows_updated: {result2.rowcount}")
    
    user2 = conn.execute("SELECT password_hash FROM users WHERE username = 'admin1'").fetchone()
    if user2:
        print(f"  hash after rotation: {user2[0][30]}...")
    
    conn.close()

os.close(fd)
print("\n=== DEBUG COMPLETE ===")