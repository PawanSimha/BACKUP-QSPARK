import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from src.core.security import authenticate_user
from werkzeug.security import check_password_hash

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
init_db(db_path)

from tests.conftest import seed_base

app = create_app()
app.config.update(
    TESTING=True,
    DATABASE_PATH=db_path,
    WTF_CSRF_ENABLED=False,
    SECRET_KEY="rot-test-secret",
)

with app.app_context():
    seed_base(db_path)
    
    # Test authentication
    result = authenticate_user('admin1', 'admin123')
    print(f"authenticate_user('admin1', 'admin123'): {result}")
    
    result2 = authenticate_user('admin1', 'user123')
    print(f"authenticate_user('admin1', 'user123'): {result2}")
    
    result3 = authenticate_user('superadmin', 'super123')
    print(f"authenticate_user('superadmin', 'super123'): {result3}")
    
    result4 = authenticate_user('superadmin', 'user123')
    print(f"authenticate_user('superadmin', 'user123'): {result4}")
    
    # Check password hashes
    rows = conn.execute("SELECT username, password_hash FROM users WHERE role IN ('ADMIN','SUPER_ADMIN')").fetchall()
    for r in rows:
        print(f"\n{r[0]}: hash starts with: {r[1][:20]}...")
        print(f"  length: {len(r[1])}")
        # Check against defaults
        pw_map = {'admin1': 'admin123', 'superadmin': 'super123'}
        pw = pw_map.get(r[0], '')
        valid_h = check_password_hash(r[1], pw) if pw else False
        print(f"  check_password_hash('{pw}'): {valid_h}")

conn.close()
os.remove(db_path)