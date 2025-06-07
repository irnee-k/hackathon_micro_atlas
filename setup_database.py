# setup_database.py
import sqlite3

# Define the name of our database file
DATABASE_FILE = 'sms_database.db'

print(f"Setting up database: {DATABASE_FILE}")

# Connect to the database.
# This command creates the file if it doesn't already exist.
conn = sqlite3.connect(DATABASE_FILE)

# A 'cursor' is an object used to execute SQL commands
cursor = conn.cursor()

# --- Define and create the table ---
# We use '''triple quotes''' for a multi-line string.
# 'IF NOT EXISTS' prevents an error if we accidentally run the script again.
# We define columns:
#   - id: A unique number for each message (Primary Key)
#   - sender_number: The phone number of the person who sent the text
#   - body: The actual text content of the message
#   - timestamp: The date and time the message was saved
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_number TEXT NOT NULL,
        body TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

print("Table 'messages' created successfully (if it didn't already exist).")

# Save (commit) the changes to the database file
conn.commit()

# Close the connection to the database
conn.close()

print("Database setup complete.")