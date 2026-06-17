import sqlite3
import os

db_path = 'test.db'
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        if ('users',) in tables:
            cursor.execute("SELECT email, is_active, is_verified FROM users;")
            users = cursor.fetchall()
            print(f"Users: {users}")
        else:
            print("Users table not found.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
