from werkzeug.security import generate_password_hash, check_password_hash

h = generate_password_hash('testpass')
print(f'Hash: {h}')
print(f'Check testpass: {check_password_hash(h, "testpass")}')
print(f'Check other: {check_password_hash(h, "otherpass")}')