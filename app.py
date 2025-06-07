import streamlit as st
import openai
import os # Make sure these imports are at the very top of your app.py
import json
import datetime # For timestamping entries
import sqlite3

st.set_page_config(layout="centered", page_title="My Micro-Atlas")

# --- Set up OpenAI API Key (at the top, outside any functions or blocks) ---
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop() # Stop the app if the key isn't set

# --- Initialize session state for login status ---
# This ensures these variables exist when the app starts
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# --- Login/Logout UI (in the sidebar for a cleaner main page) ---
st.sidebar.image("https://em-content.zobj.net/source/microsoft-teams/363/brain_1f9e0.png", width=50) # Optional: add a small brain icon
st.sidebar.title("Account (Mock)")

if not st.session_state.logged_in:
    # Display login form if not logged in
    st.sidebar.header("Login / Create Account")
    username_input = st.sidebar.text_input("Enter a Username", key="login_username_input")
    password_input = st.sidebar.text_input("Enter a Password (any value)", type="password", key="login_password_input") # Password won't be checked, just for demo

    if st.sidebar.button("Login / Register", key="login_button"):
        if username_input:
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.sidebar.success(f"Welcome, {username_input}! Your mock account is ready.")
            st.rerun() # Rerun to update the UI after login
        else:
            st.sidebar.error("Please enter a username.")
else:
    # Display logged-in status if logged in
    st.sidebar.success(f"Logged in as: **{st.session_state.username}**")
    if st.sidebar.button("Logout", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun() # Rerun to update the UI after logout

# --- Check if logged in before showing main app content ---
# If not logged in, stop the execution of the main app content
if not st.session_state.logged_in:
    st.info("Please log in on the sidebar to use 'My Micro-Atlas' and save your insights.")
    st.stop() # This halts the script execution here if not logged in

# --- Define the AI Analysis Function (at the top level, outside any if blocks) ---
def get_micro_atlas_analysis(text_input):
    # This is the CORRECT place for your detailed prompt string
    # It's dynamically created using f-string with text_input
    user_prompt_content = f"""
You are an expert knowledge curator and cognitive cartographer, helping individuals map their learning journey.
Your task is to analyze the following unstructured text, which describes a user's recent learning, consumption, or project experiences.
From this text, you need to extract and categorize the following key elements of their knowledge landscastreamlit run app.pype:

1.  **Core Concepts & Topics:** Identify the main subject matters or abstract ideas discussed.
2.  **Key Skills & Technologies:** List any specific practical abilities or tools (e.g., programming languages, software, methodologies) mentioned or clearly implied as being used or learned.
3.  **Cross-Cutting Competencies:** Identify broader, transferable skills demonstrated (e.g., Problem Solving, Data Analysis, Communication, Project Management, Critical Thinking, Leadership, User Research).
4.  **Noteworthy Connections & Insights:** Describe any explicit or implicit relationships you find between the concepts, skills, or competencies. This is where you connect disparate pieces of learning.

**Instructions for Formatting the Output:**
- Use clear, concise language.
- Format each section with a bold heading.
- Use bullet points for each item within a section.
- For "Core Concepts & Topics," provide a very brief, 1-sentence explanation if necessary.
- For "Noteworthy Connections & Insights," explain *how* different elements are related.

---
User's Learning Content to Analyze:
"{text_input}"
---
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo", # Or "gpt-4o" if you have access and prefer
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert knowledge curator and cognitive cartographer, skilled at analyzing learning goals and mapping out knowledge domains."
                },
                {
                    "role": "user",
                    "content": user_prompt_content # Pass the dynamically generated prompt here
                }
            ],
            temperature=0.7,
            max_tokens=800 # Good idea to limit response length for hackathons
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating analysis: {str(e)}"

def save_user_analysis(username, input_text, ai_output):
    """
    Saves a user's AI analysis to a JSON file.
    Each user has their own JSON file (e.g., 'user_data/irene.json').
    """
    data_dir = "user_data" # Define the directory to store user data
    os.makedirs(data_dir, exist_ok=True) # Create the directory if it doesn't exist

    user_file_path = os.path.join(data_dir, f"{username}.json")

    # Load existing data, or start with an empty list if file doesn't exist
    user_data = []
    if os.path.exists(user_file_path):
        try:
            with open(user_file_path, "r", encoding="utf-8") as f:
                user_data = json.load(f)
        except json.JSONDecodeError:
            # Handle case where file is empty or corrupted JSON
            st.warning(f"Could not read existing data for {username}. Starting fresh.")
            user_data = []
        except Exception as e:
            st.error(f"An unexpected error occurred while loading data for {username}: {e}")
            user_data = []

    # Prepare the new entry
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = {
        "timestamp": timestamp,
        "input_text": input_text,
        "ai_analysis": ai_output
    }

    # Add the new entry to the data
    user_data.insert(0, new_entry) # Insert at the beginning for reverse chronological order

    # Save the updated data back to the file
    try:
        with open(user_file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4, ensure_ascii=False) # indent for readability, ensure_ascii for emojis/unicode
        return True
    except Exception as e:
        st.error(f"Error saving data to {username}.json: {str(e)}")
        return False

def load_user_analyses(username):
    """
    Loads all saved analyses for a given user.
    """
    data_dir = "user_data"
    user_file_path = os.path.join(data_dir, f"{username}.json")

    if os.path.exists(user_file_path):
        try:
            with open(user_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning(f"Data file for {username} is corrupted or empty. Returning empty history.")
            return []
        except Exception as e:
            st.error(f"An unexpected error occurred while loading data for {username}: {e}")
            return []
    return [] # Return empty list if file doesn't exist

# Define the database file for SMS messages (must be the same as in webhook_receiver.py)
SMS_DATABASE_FILE = 'sms_database.db'

def get_sms_messages():
    """
    Retrieves all messages from the SQLite SMS database.
    Messages are ordered by timestamp in descending order (newest first).
    """
    conn = None # Initialize conn to None
    try:
        conn = sqlite3.connect(SMS_DATABASE_FILE)
        cursor = conn.cursor()
        # Select all columns and order by timestamp
        cursor.execute("SELECT id, sender_number, body, timestamp FROM messages ORDER BY timestamp DESC")
        messages = cursor.fetchall()
        return messages
    except sqlite3.Error as e:
        # Streamlit error display for database issues
        st.error(f"Error reading SMS database: {e}")
        return []
    finally:
        # Ensure the connection is closed even if an error occurs
        if conn:
            conn.close()

# --- Streamlit UI layout (this is the main part of your app) ---
st.title("🧠 My Micro-Atlas: Your Personal Learning Map")
st.write("Paste in your learning summaries (articles, projects, notes) and let AI map your cognitive landscape.")

st.markdown("---") # Visual separator
st.header("Your SMS Notes")
st.write("Messages received via SMS are listed below. Select one to analyze with AI.")

sms_messages = get_sms_messages() # Call the new function to get SMS data

if sms_messages:
    # Create a list of display options for the selectbox
    # Format: "Timestamp - Sender: Body (first ~70 chars)"
    sms_options = [
        f"{msg[3]} - {msg[1]}: {msg[2][:70]}{'...' if len(msg[2]) > 70 else ''}" # msg[3]=timestamp, msg[1]=sender, msg[2]=body
        for msg in sms_messages
    ]
    
    # Use st.selectbox to allow users to pick an SMS message
    selected_sms_display = st.selectbox(
        "Select an SMS note to analyze:",
        options=sms_options,
        index=0, # Default to the latest message (which is at index 0 because of DESC order)
        key="sms_select_box" # Unique key for Streamlit components
    )

    selected_sms_body = None
    if selected_sms_display:
        # Find the original message body based on the selected display text.
        # We need to iterate through the original `sms_messages` to find the full body.
        for msg_id, sender, body, timestamp in sms_messages:
            if f"{timestamp} - {sender}: {body[:70]}{'...' if len(body) > 70 else ''}" == selected_sms_display:
                selected_sms_body = body
                break

    if selected_sms_body:
        st.info(f"**Selected SMS Content:**\n\n{selected_sms_body}") # Show the full selected SMS content
        
        # Button to trigger AI analysis with the selected SMS
        if st.button("Analyze Selected SMS with AI", key="analyze_sms_button"):
            # Store the selected SMS content in session state to be picked up by the main analysis logic
            st.session_state.temp_sms_input_for_analysis = selected_sms_body
            st.rerun() # Rerun the app to trigger the main analysis button's logic
            
    else:
        st.warning("Could not retrieve full SMS message for analysis. Please try sending another SMS.")
else:
    st.info("No SMS messages received yet. Send a text to your Twilio number to get started!")


st.markdown("---") # Another separator

# Initialize a variable that will hold the actual content for AI analysis.
# This prioritizes content from a selected SMS if the "Analyze SMS" button was just clicked.
active_learning_input = ""

# Check if an SMS was just selected via the "Analyze Selected SMS with AI" button
if 'temp_sms_input_for_analysis' in st.session_state and st.session_state.temp_sms_input_for_analysis:
    active_learning_input = st.session_state.temp_sms_input_for_analysis
    # Clear this session state variable immediately after using it to prevent sticky behavior
    del st.session_state.temp_sms_input_for_analysis 
    
# Display the main text area. Its initial 'value' will be the selected SMS or the default example.
learning_input_text_area = st.text_area(
    "Paste your learning content here (or select an SMS above):",
    value=active_learning_input if active_learning_input else "Example: I read an article about 'reinforcement learning from human feedback' (RLHF) and how it's used to align large language models. This builds on my understanding of basic machine learning concepts. I also worked on a project analyzing user sentiment in customer reviews, using Python and NLP techniques. This involved data cleaning and visualization.",
    height=200,
    key="main_text_area" # Add a unique key for this component
)

# If no SMS was selected via its button, the primary input for analysis comes from the text area.
if not active_learning_input:
    active_learning_input = learning_input_text_area

# --- Button click logic (call the function here) ---
if st.button("Generate My Micro-Atlas"):
    # Change 'learning_input' to 'active_learning_input' here as well
    if not active_learning_input:
        st.warning("Please paste some content to analyze!")
    else:
        st.info("Generating your cognitive map...")
        with st.spinner("Analyzing your learning with AI..."):
            ai_analysis_output = get_micro_atlas_analysis(active_learning_input)
            st.subheader("Your AI-Enhanced Learning Snapshot:")
            st.markdown(ai_analysis_output) # Display the AI's response
            # --- New: Save the analysis if user is logged in ---
            if st.session_state.logged_in: 
                if save_user_analysis(st.session_state.username, active_learning_input, ai_analysis_output):
                    st.success("Analysis saved to your account!")
                else:
                    st.error("Failed to save analysis.")

st.markdown("---")
st.caption("Powered by AI and your brilliant mind.")

# --- Display User History (at the end of your main app content) ---
if st.session_state.logged_in: # Ensure history is only shown to logged-in users
    st.markdown("---") # Separator
    st.header(f"Your Learning History ({st.session_state.username})")

    user_history = load_user_analyses(st.session_state.username)
    if user_history:
        # Display results in reverse chronological order (newest first)
        for i, entry in enumerate(user_history): # user_data.insert(0, new_entry) already handles order
            expander_title = f"Analysis from {entry['timestamp']}"
            if 'input_text' in entry and len(entry['input_text']) > 50:
                # Show first 50 chars of input for quick identification
                expander_title += f": \"{entry['input_text'][:50]}...\""
            
            with st.expander(expander_title):
                st.markdown(entry['ai_analysis']) # Display the full AI analysis content
                # You can also display the input text if desired
                # st.info(f"**Original Input:**\n\n{entry['input_text']}")
    else:
        st.info("No saved analyses yet. Generate one to see your history!")