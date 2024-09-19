import sqlite3

# Connect to the database
conn = sqlite3.connect('sessions.db')
# Create a cursor
cursor = conn.cursor()
# Create a table for session tracking
cursor.execute('''
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    footage_url TEXT
)
''')

# Commit and close the connection
conn.commit()
conn.close()
