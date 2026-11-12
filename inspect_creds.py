import tempfile, os
from app import create_app
from src.services.db import init_db, get_connection
from werkzeug.security import check_password_hash, generate_password_hash

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
init_db(db_path)

from tests.conftest import seed_base
seed_base(db_path)

conn = get_connection(db_path)

# Check ALL users
users = conn.execute("SELECT username, role, account_status, wallet_balance FROM users ORDER BY role, username").fetchall()
print("=== ALL USERS ===")
for u in users:
    print(f"  username={u[0]}, role={u[1]}, status={u[2]}, balance={u[3]}")

# Check ADMIN and SUPER_ADMIN specifically
print("\n=== PRIVILEGED ACCOUNTS ===")
for u in users:
    if u[1] in ('ADMIN', 'SUPER_ADMIN'):
        pw_map = {'admin1': 'admin123', 'superadmin': 'super123'}
        pw = pw_map.get(u[0], '?')
        valid = check_password_hash(u[2], pw) if u[2] else False
        print(f"  {u[0]}: password_hash exists={bool(u[2])}")
        print(f"  {u[0]}: default '{pw}' validates: {valid}")

conn.close()
os.remove(db_path)