import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
init_db(db_path)

from tests.conftest import seed_base
seed_base(db_path)

app = create_app()
app.config.update(TESTING=True, DATABASE_PATH=db_path, WTF_CSRF_ENABLED=False, SECRET_KEY="test")

with app.app_context():
    conn = get_connection(db_path)
    
    # Check connection type and properties
    print(f"connection type: {type(conn)}")
    print(f"connection autocommit: {conn.autocommit if hasattr(conn, 'autocommit') else 'N/A'}")
    
    # Try a simple test
    result = conn.execute("SELECT 'test'")
    print(f"SELECT test: {result.fetchone()}")
    
    # Try UPDATE
    result2 = conn.execute("UPDATE users SET password_hash = password_hash WHERE username = 'admin1'")
    print(f"UPDATE rows: {result2.rowcount}")
    
    # Check if the update worked
    user = conn.execute("SELECT password_hash FROM users WHERE username = 'admin1'").fetchone()
    if user:
        print(f"hash after UPDATE: {user[0][:30]}...")
    
    conn.close()
os.close(fd)
print("\n=== DEBUG COMPLETE ===")
PYEOF