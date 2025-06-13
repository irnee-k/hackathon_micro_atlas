from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import datetime # Import datetime for current timestamp

app = Flask(__name__)

DATABASE_FILE = 'sms_database.db'

# --- NEW: init_db() function to ensure database schema ---
def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Create 'messages' table if it doesn't exist
    # Added 'type' column with a default of 'sms'
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_number TEXT,
            body TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            type TEXT DEFAULT 'sms' -- NEW: Added type column with default
        )
    ''')

    # Check if 'type' column already exists in 'messages' table.
    # This handles cases where the database already existed without the 'type' column.
    cursor.execute("PRAGMA table_info(messages)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'type' not in columns:
        print("Adding 'type' column to 'messages' table...")
        cursor.execute("ALTER TABLE messages ADD COLUMN type TEXT DEFAULT 'sms'")
        # Update existing rows to 'sms' if they were created before 'type' column existed
        cursor.execute("UPDATE messages SET type = 'sms' WHERE type IS NULL")
        print("Updated existing messages to type 'sms'.")


    # Create 'web_clips' table if it doesn't exist
    # Added 'timestamp' column for consistency with 'messages' table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS web_clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            clipped_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP -- ADDED: Timestamp
        )
    ''')

    conn.commit()
    conn.close()
    print("Database schema ensured.")

# --- Call init_db() when the app starts ---
init_db()

@app.route("/sms", methods=['POST'])
def sms_webhook():
    sender_number = request.form.get('From', 'Unknown')
    message_body = request.form.get('Body', '')

    print(f"\n--- New SMS Received ---")
    print(f"From: {sender_number}")
    print(f"Body: {message_body}")

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (sender_number, body, type) VALUES (?, ?, ?)", # ADDED 'type'
            (sender_number, message_body, 'sms') # Explicitly setting type as 'sms'
        )
        conn.commit()
        conn.close()
        print("SMS successfully saved to database.")
    except Exception as e:
        print(f"Error saving SMS to database: {e}")

    response = MessagingResponse()
    response.message("Your note has been received by Micro-Atlas! 🧠")
    return str(response)

@app.route("/web_clip", methods=['POST'])
def web_clip_webhook():
    print(f"\n--- DEBUG: Incoming Web Clip Request Received! ---")
    if not request.is_json:
        print("ERROR: Web clip request did not contain JSON data.")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    clipped_url = data.get('url')
    clipped_text = data.get('text')

    if not clipped_url or not clipped_text:
        print("ERROR: Missing 'url' or 'text' in web clip data.")
        return jsonify({"error": "Missing 'url' or 'text' in request body"}), 400

    print(f"DEBUG: Clipped URL: {clipped_url}")
    print(f"DEBUG: Clipped Text (first 100 chars): {clipped_text[:100]}...")

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO web_clips (url, clipped_text, timestamp) VALUES (?, ?, ?)", # ADDED 'timestamp'
            (clipped_url, clipped_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) # ADDED timestamp value
        )
        conn.commit()
        conn.close()
        print("Web clip successfully saved to database.")
        return jsonify({"message": "Web clip received and saved!"}), 200
    except Exception as e:
        print(f"Error saving web clip to database: {e}")
        return jsonify({"error": f"Failed to save web clip: {e}"}), 500

# --- NEW ROUTE FOR INCOMING EMAILS ---
@app.route('/email_inbound', methods=['POST'])
def receive_email():
    """
    Receives inbound emails from services like Mailgun or SendGrid.
    The exact fields might vary slightly depending on the service.
    """
    print(f"\n--- New Email Received ---")
    # --- ADJUST THESE LINES BASED ON YOUR EMAIL SERVICE ---
    # For Mailgun (common fields):
    sender = request.form.get('sender')
    subject = request.form.get('subject')
    body_plain = request.form.get('body-plain') # Plain text body (usually preferred)
    #
    # For SendGrid (they often send a JSON string under 'email', you'd need to parse that):
    # import json
    # email_json_str = request.form.get('email')
    # if email_json_str:
    #     email_data = json.loads(email_json_str)
    #     sender = email_data.get('from')
    #     subject = email_data.get('subject')
    #     body_plain = email_data.get('text') # Plain text content
    # else:
    #     sender = None
    #     subject = None
    #     body_plain = None
    # --- END ADJUSTMENT ---

    if not body_plain:
        print("ERROR: Received email without plain text body.")
        return "Missing email body", 400

    # Combine subject and body for analysis
    full_content = f"Subject: {subject}\n\n{body_plain}" if subject else body_plain

    print(f"From: {sender}")
    print(f"Subject: {subject}")
    print(f"Body (first 100 chars): {body_plain[:100]}...")

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender_number, body, type) VALUES (?, ?, ?)",
                     (sender, full_content, 'email')) # Explicitly set type as 'email'
        conn.commit()
        conn.close()
        print("Email successfully saved to database.")
        return "Email received and saved!", 200
    except Exception as e:
        print(f"Error saving email: {e}")
        return "Error saving email", 500

# This block allows us to run the server directly from the command line
if __name__ == "__main__":
    print("Starting Flask server on http://localhost:5001")
    app.run(port=5001, debug=True)