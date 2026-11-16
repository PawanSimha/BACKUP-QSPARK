import os
os.environ["QSPARK_SUPER_ADMIN_PASSWORD"] = "superadmin123"

from app import create_app
from src.services.db import init_db, get_connection
from werkzeug.security import generate_password_hash

app = create_app()
init_db(app.config["DATABASE_PATH"])

with app.app_context():
    db_path = app.config["DATABASE_PATH"]
    pwd_hash = generate_password_hash("superadmin123")
    
    conn = get_connection(db_path)
    
    # Insert Super Admin
    conn.execute(
        """INSERT INTO users
           (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("SADM001", "Super Admin", "superadmin@qspark.com", "9999900000", "superadmin",
         pwd_hash, "SUPER_ADMIN", 10000.00, "ACTIVE")
    )
    
    # Insert first default admin
    conn.execute(
        """INSERT INTO users
           (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("ADM001", "Default Admin", "admin1@qspark.com", "9999900001", "admin1",
         generate_password_hash("admin123"), "ADMIN", 1000.00, "ACTIVE")
    )
    
    # Insert second default admin
    conn.execute(
        """INSERT INTO users
           (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("ADM002", "Default Admin", "admin2@qspark.com", "9999900002", "admin2",
         generate_password_hash("admin123"), "ADMIN", 1000.00, "ACTIVE")
    )
    
    conn.commit()
    conn.close()
    
    # Verify
    conn2 = get_connection(db_path)
    users = conn2.execute("SELECT user_id, username, role, wallet_balance, account_status FROM users").fetchall()
    print("Users created:")
    for u in users:
        print(u)
    conn2.close()
    
    # Set system status
    conn3 = get_connection(db_path)
    conn3.execute("UPDATE system_settings SET setting_value = 'ONLINE' WHERE setting_key = 'SYSTEM_STATUS'")
    conn3.commit()
    conn3.close()
    
    print("\nDatabase seeded successfully!")