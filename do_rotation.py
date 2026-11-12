import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from src.core.security import hash_password, authenticate_user
from werkzeug.security import check_password_hash
import secrets

# Create fresh database
fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
init_db(db_path)

from tests.conftest import seed_base
seed_base(db_path)

app = create_app()
app.config.update(TESTING=True, DATABASE_PATH=db_path, WTF_CSRF_ENABLED=False, SECRET_KEY="test")

with app.app_context():
    conn = get_connection(db_path)
    
    # ===== ROTATE ADMIN CREDENTIALS =====
    print("=== ROTATING ADMIN CREDENTIALS ===")
    
    # Generate new password and hash
    new_admin_pw = secrets.token_urlsafe(16)
    new_admin_pw_hash = hash_password(new_admin_pw)
    
    # Update the password hash
    result = conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = 'admin1'",
        (new_admin_pw_hash,),
    )
    print(f"  UPDATE admin1 rows: {result.rowcount}")
    
    # Verify the update
    user = conn.execute("SELECT password_hash FROM users WHERE username = 'admin1'").fetchone()
    if user:
        print(f"  New hash: {user[0][:30]}...")
        # Verify it works
        valid = check_password_hash(user[0], new_admin_pw)
        print(f"  New password validates: {valid}")
    
    # Verify old credential is rejected
    old_valid = authenticate_user("admin1", "admin123") is not None
    print(f"  Old credential still works: {old_valid}")
    
    # ===== ROTATE SUPER_ADMIN CREDENTIALS =====
    print("\n=== ROTATING SUPER_ADMIN CREDENTIALS ===")
    
    new_sa_pw = secrets.token_urlsafe(16)
    new_sa_pw_hash = hash_password(new_sa_pw)
    
    result = conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = 'superadmin'",
        (new_sa_pw_hash,),
    )
    print(f"  UPDATE superadmin rows: {result.rowcount}")
    
    user = conn.execute("SELECT password_hash FROM users WHERE username = 'superadmin'").fetchone()
    if user:
        print(f"  New hash: {user[0][:30]}...")
    
    # Verify old credential is rejected
    old_sa_valid = authenticate_user("superadmin", "super123") is not None
    print(f"  Old super admin credential still works: {old_sa_valid}")
    
    # === Verify customer accounts unaffected ===
    print("\n=== VERIFYING CUSTOMER ACCOUNTS ===")
    cust_valid = authenticate_user("cust1", "user123") is not None
    print(f"  Customer cust1 with user123: {'VALID' if cust_valid else 'INVALID'}")
    
    # Commit changes
    conn.commit()
    
    # === FINAL VERIFICATION ===
    print("\n=== FINAL VERIFICATION ===")
    # Check admin
    admin_user = conn.execute("SELECT password_hash FROM users WHERE username = 'admin1'").fetchone()
    admin_new_works = check_password_hash(admin_user[0], secrets.token_urlsafe(16)) if admin_user else False
    print(f"  admin1 new pw works: {admin_new_works}")
    
    # Check superadmin
    sa_user = conn.execute("SELECT password_hash FROM users WHERE username = 'superadmin'").fetchone()
    sa_new_works = check_password_hash(sa_user[0], secrets.token_urlsafe(16)) if sa_user else False
    print(f"  superadmin new pw works: {sa_new_works}")
    
    # Check customer
    cust_user = conn.execute("SELECT password_hash FROM users WHERE username = 'cust1'").fetchone()
    cust_works = check_password_hash(cust_user[0], 'user123') if cust_user else False
    print(f"  cust1/user123 still works: {cust_works}")
    
    conn.close()
os.close(fd)
print("\n=== ROTATION COMPLETE ===")
PYEOF