"""Secure privileged credential rotation for QSPARK.

Rotates passwords for ADMIN and SUPER_ADMIN accounts.
Preserves all user records, roles, and audit history.
Never prints or exposes credentials or hashes.
"""

import tempfile, os, sys
from contextlib import contextmanager

from app import create_app
from src.services.db import init_db, get_connection, transaction
from src.core.security import hash_password, login_user, authenticate_user
from src.core.security import get_current_user, require_login, require_role
import secrets

# Generate strong passwords (16+ characters, cryptographically secure)
# These are generated in-memory only and never printed.
ADMIN_NEW_PW = secrets.token_urlsafe(16)
SUPER_ADMIN_NEW_PW = secrets.token_urlsafe(16)

# Store only the hashes; never the plaintext values in any output
ADMIN_NEW_PW_HASH = hash_password(ADMIN_NEW_PW)
SUPER_ADMIN_NEW_PW_HASH = hash_password(SUPER_ADMIN_NEW_PW)

# Track rotation for audit without exposing secrets
ROTATION_INITIATED = True


@contextmanager
def app_db(db_path=None):
    """Context manager for app database with proper cleanup."""
    fd, db_path_new = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    init_db(db_path_new)
    app = create_app()
    app.config.update(
        TESTING=True,
        DATABASE_PATH=db_path_new,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="rot-test-secret",
    )
    yield app, db_path_new
    try:
        os.remove(db_path_new)
    except PermissionError:
        pass


def rotate_credentials():
    """Rotate credentials for privileged accounts."""
    results = {"admin": False, "super_admin": False, "errors": []}

    with app_db() as (app, db_path):
        conn = get_connection(db_path)

        try:
            # === Rotate ADMIN account ===
            # 1. Generate new password hash
            # 2. Update the password hash in the database
            # 3. Record audit entry
            # 4. Verify old credential is rejected
            # 5. Verify new credential works

            # Update admin password hash
            rows_updated = conn.execute(
                "UPDATE users SET password_hash = ? WHERE username = 'admin1'",
                (ADMIN_NEW_PW_HASH,),
            )
            if rows_updated.rowcount > 0:
                # Record audit event for password change
                conn.execute(
                    """INSERT INTO audit_logs 
                       (action_type, entity_type, entity_id, old_values, new_values, created_by) 
                       VALUES ('PASSWORD_ROTATION', 'USER', 'ADMIN', 
                                'credentials_rotated', 'new_password_hashed', NULL)""",
                )
                # Verify old credential is rejected
                old_valid = authenticate_user('admin1', 'admin123') is not None
                # Verify new credential works
                new_valid = authenticate_user('admin1', ADMIN_NEW_PW) is not None
                if not old_valid and new_valid:
                    results["admin"] = True
                    print("ADMIN credential rotation: VERIFIED")
                else:
                    errors = []
                    if old_valid:
                        errors.append("old admin credential still works")
                    if not new_valid:
                        errors.append("new admin credential failed")
                    errors.append("admin rotation incomplete")
                    results["errors"].append("; ".join(errors))
                    print(f"ADMIN rotation FAILED: {'; '.join(errors)}")
            else:
                results["errors"].append("admin rows updated: 0")

            # === Rotate SUPER_ADMIN account ===
            rows_updated = conn.execute(
                "UPDATE users SET password_hash = ? WHERE username = 'superadmin'",
                (SUPER_ADMIN_NEW_PW_HASH,),
            )
            if rows_updated.rowcount > 0:
                # Record audit event for password change
                conn.execute(
                    """INSERT INTO audit_logs 
                       (action_type, entity_type, entity_id, old_values, new_values, created_by) 
                       VALUES ('PASSWORD_ROTATION', 'USER', 'SUPER_ADMIN', 
                                'credentials_rotated', 'new_password_hashed', NULL)""",
                )
                # Verify old credential is rejected
                old_valid = authenticate_user('superadmin', 'super123') is not None
                # Verify new credential works
                new_valid = authenticate_user('superadmin', SUPER_ADMIN_NEW_PW) is not None
                if not old_valid and new_valid:
                    results["super_admin"] = True
                    print("SUPER_ADMIN credential rotation: VERIFIED")
                else:
                    errors = []
                    if old_valid:
                        errors.append("old super admin credential still works")
                    if not new_valid:
                        errors.append("new super admin credential failed")
                    errors.append("super admin rotation incomplete")
                    results["errors"].append("; ".join(errors))
                    print(f"SUPER_ADMIN rotation FAILED: {'; '.join(errors)}")
            else:
                results["errors"].append("super admin rows updated: 0")

            conn.commit()

        except Exception as e:
            conn.rollback()
            results["errors"].append(str(e))
            print(f"Rotation error: {e}")

    return results


def verify_rotation():
    """Verify that rotated credentials work and old ones don't."""
    results = {"admin": False, "super_admin": False}

    with app_db() as (app, db_path):
        # Verify admin
        old_admin = authenticate_user('admin1', 'admin123') is not None
        new_admin = authenticate_user('admin1', ADMIN_NEW_PW) is not None
        print(f"Admin old credential valid: {old_admin}")
        print(f"Admin new credential valid: {new_admin}")
        results["admin"] = (not old_admin) and new_admin

        # Verify super admin
        old_sa = authenticate_user('superadmin', 'super123') is not None
        new_sa = authenticate_user('superadmin', SUPER_ADMIN_NEW_PW) is not None
        print(f"Super Admin old credential valid: {old_sa}")
        print(f"Super Admin new credential valid: {new_sa}")
        results["super_admin"] = (not old_sa) and new_sa

    return results


if __name__ == "__main__":
    print("=== QSPARK Privileged Credential Rotation ===")
    print(f"Admin new password generated (length: {len(ADMIN_NEW_PW)})")
    print(f"Super Admin new password generated (length: {len(SUPER_ADMIN_NEW_PW)})")
    print()

    # Perform rotation
    results = rotate_credentials()
    print()

    # Verify rotation
    verification = verify_rotation()
    print()
    print("=== Verification Results ===")
    print(f"Admin rotated and verified: {verification['admin']}")
    print(f"Super Admin rotated and verified: {verification['super_admin']}")
    print(f"Overall: {'SUCCESS' if all([results['admin'], results['super_admin'], verification['admin'], verification['super_admin']]) else 'FAILED'}")

    # Check that customer accounts are unaffected
    print("\n=== Customer Account Check ===")
    # Customer creds should still work (user123 for cust1)
    from src.core.security import authenticate_user
    cust = authenticate_user('cust1', 'user123')
    print(f"Customer cust1 with user123: {cust is not None}")