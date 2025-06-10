# webhook_receiver.py - FINAL CORRECT VERSION

from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3

app = Flask(__name__)

DATABASE_FILE = 'sms_database.db'

@app.route("/sms", methods=['POST'])
def sms_webhook():
    # Get the message details from the form data Twilio sends
    # request.form is the correct way to access data for application/x-www-form-urlencoded
    sender_number = request.form.get('From', 'Unknown') # The sender's phone number
    message_body = request.form.get('Body', '')       # The text of the message

    # We print the message to our terminal for debugging purposes.
    # When you run this script, you'll see messages appear here.
    print(f"\n--- New Message Received ---")
    print(f"From: {sender_number}")
    print(f"Body: {message_body}")

    # --- Save the received message to our SQLite database ---
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Execute the SQL command to insert the new message.
        # Using (?, ?) is a security best practice to prevent SQL injection.
        cursor.execute(
            "INSERT INTO messages (sender_number, body) VALUES (?, ?)",
            (sender_number, message_body)
        )

        # Commit the transaction to save the changes
        conn.commit()
        conn.close()
        print("Message successfully saved to database.")
    except Exception as e:
        print(f"Error saving to database: {e}")
        # Consider returning an error message to Twilio here if saving fails
        # response = MessagingResponse()
        # response.message(f"Error processing your note: {e}")
        # return str(response), 500


    # --- Create a reply to send back to the user ---
    # This is optional, but provides great feedback to the person sending the text.
    response = MessagingResponse()
    response.message("Your note has been received by Micro-Atlas! 🧠")

    # Return the response to Twilio, which then sends it as an SMS.
    # We must convert it to a string.
    return str(response)

@app.route("/web_clip", methods=['POST'])
def web_clip_webhook():
    print(f"\n--- DEBUG: Incoming Web Clip Request Received! ---")
    # Web clippers usually send data as JSON
    if not request.is_json:
        print("ERROR: Web clip request did not contain JSON data.")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    clipped_url = data.get('url')
    clipped_text = data.get('text') # Assuming the extension sends 'text' for clipped content

    if not clipped_url or not clipped_text:
        print("ERROR: Missing 'url' or 'text' in web clip data.")
        return jsonify({"error": "Missing 'url' or 'text' in request body"}), 400

    print(f"DEBUG: Clipped URL: {clipped_url}")
    print(f"DEBUG: Clipped Text (first 100 chars): {clipped_text[:100]}...")

    # --- Save the received web clip to our SQLite database ---
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO web_clips (url, clipped_text) VALUES (?, ?)",
            (clipped_url, clipped_text)
        )

        conn.commit()
        conn.close()
        print("Web clip successfully saved to database.")
        return jsonify({"message": "Web clip received and saved!"}), 200
    except Exception as e:
        print(f"Error saving web clip to database: {e}")
        return jsonify({"error": f"Failed to save web clip: {e}"}), 500

# This block allows us to run the server directly from the command line
if __name__ == "__main__":
    # app.run() starts the web server.
    # port=5001 means it will run on http://localhost:5001
    # debug=True provides helpful error messages while we're developing.
    print("Starting Flask server on http://localhost:5001")
    app.run(port=5001, debug=True)