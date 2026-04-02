# check_data.py banao aur ye code daalo:
import sqlite3

conn = sqlite3.connect('bus_tracker.db')
cursor = conn.cursor()

print("=== ADMINS ===")
cursor.execute("SELECT * FROM users WHERE role = 'admin'")
for row in cursor.fetchall():
    print(row)

print("\n=== STUDENTS ===")
cursor.execute("SELECT * FROM users WHERE role = 'student'")
for row in cursor.fetchall():
    print(row)

print("\n=== BUSES ===")
cursor.execute("SELECT * FROM buses")
for row in cursor.fetchall():
    print(row)

print("\n=== ROUTES ===")
cursor.execute("SELECT * FROM routes")
for row in cursor.fetchall():
    print(row)

print("\n=== GATE LOGS ===")
cursor.execute("SELECT * FROM gate_logs")
for row in cursor.fetchall():
    print(row)

print("\n=== notifications ===")
cursor.execute("SELECT * FROM notifications")
for row in cursor.fetchall():
    print(row)  
conn.close()