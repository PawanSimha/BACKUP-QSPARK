import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from src.core.security import authenticate_user
from werkzeug.security import check_password_hash

# Create fresh database with seed
fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
init_db(db_path)

from tests.conftest import seed_base
seed_base(db_path)

app = create_app()
app.config.update(TESTING=True, DATABASE_PATH=db_path, WTF_CSRF_ENABLED=False, SECRET_KEY="test")

with app.app_context():
    conn = get_connection(db_path)
    
    # Check ALL users
    print("=== ALL USERS ===")
    users = conn.execute("SELECT username, role, account_status, wallet_balance, admin_id FROM users").fetchall()
    for u in users:
        print(f"  username={u[0]:12s} role={u[1]:10s} status={u[2]:8s} balance={u[3]:>6} admin_id={u[4]}")
    
    # Authentication tests
    print("\n=== AUTHENTICATION TESTS ===")
    for name, pw in [('cust1', 'user123'), ('admin1', 'admin123'), ('superadmin', 'super123')]:
        result = authenticate_user(name, pw)
        status = 'VALID' if result else 'REJECTED'
        print(f"  authenticate_user('{name}', '{pw}'): {status}")
        if result:
            print(f"    -> user_id={result['user_id']}, admin_id={result['admin_id']}, wallet={result['wallet_balance']}")
    
    # Password hashes
    print("\n=== PASSWORD HASHES ===")
    rows = conn.execute("SELECT username, password_hash FROM users WHERE role IN ('ADMIN','SUPER_ADMIN')").fetchall()
    for r in rows:
        print(f"  {r[0]}: hash_length={len(r[1])}, starts_with={r[1][:30]}...")
        pw_map = {'admin1': 'admin123', 'superadmin': 'super123'}
        pw = pw_map.get(r[0], '')
        valid = check_password_hash(r[1], pw) if pw else False
        print(f"  check_password_hash('{pw}'): {valid}")
    
    # Audit logs
    print("\n=== AUDIT LOGS (last 5) ===")
    audit = conn.execute("SELECT action_type, entity_type, entity_id, old_values, new_values, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 5").fetchall()
    for a in audit:
        print(f"  action={a[0]:20s} entity={a[1]:12s} id={a[2]} old={a[3]:20s} new={a[4]:20s} time={a[5]}")
    
    conn.close()
os.close(fd)
PYEOF