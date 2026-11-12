import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from src.core.security import authenticate_user
from werkzeug.security import check_password_hash

# Create app with test config
app = create_app()
app.config.update(
    TESTING=True,
    DATABASE_PATH=None,
    WTF_CSRF_ENABLED=False,
    SECRET_KEY="test-secret",
)

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)

with app.app_context():
    # Set the database path
    app.config["DATABASE_PATH"] = db_path
    
    # Initialize database
    init_db(db_path)
    
    # Get connection inside context
    conn = get_connection(db_path)
    
    # Seed with standard credentials
    from tests.conftest import seed_base
    seed_base(db_path)
    
    # Verify initial state
    print("=== INITIAL STATE ===")
    users = conn.execute("SELECT username, role FROM users ORDER BY role, username").fetchall()
    for u in users:
        print(f"  {u[0]}: role={u[1]}")
    
    # Test authentication
    print("\n=== AUTHENTICATION TESTS ===")
    for name, pw in [('cust1', 'user123'), ('admin1', 'admin123'), ('superadmin', 'super123')]:
        result = authenticate_user(name, pw)
        status = 'SUCCESS' if result else 'FAILED'
        print(f"  authenticate_user('{name}', '{pw}'): {status}")
    
    # Check password hashes
    print("\n=== PASSWORD HASHES ===")
    rows = conn.execute("SELECT username, password_hash FROM users WHERE role IN ('ADMIN','SUPER_ADMIN')").fetchall()
    for r in rows:
        print(f"\n{r[0]}: hash_length={len(r[1])}, starts_with={r[1][:30]}...")
        # Check against defaults
        pw_map = {'admin1': 'admin123', 'superadmin': 'super123'}
        pw = pw_map.get(r[0], '')
        valid = check_password_hash(r[1], pw) if pw else False
        print(f"  check_password_hash('{pw}'): {valid}")
    
    conn.close()
os.remove(db_path)