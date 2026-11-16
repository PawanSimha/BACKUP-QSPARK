import sqlite3
conn = sqlite3.connect('database/parking_local.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', tables)
try:
    rows = conn.execute('SELECT COUNT(*) FROM users').fetchone()
    print('User count:', rows)
    users = conn.execute('SELECT user_id, admin_id, full_name, email, username, role, account_status, wallet_balance FROM users').fetchall()
    print('Users:')
    for r in users:
        print(r)
except Exception as e:
    print('Error:', e)
conn.close()