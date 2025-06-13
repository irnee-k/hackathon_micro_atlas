import streamlit as st
import openai
import os
import json
import datetime
import sqlite3
from collections import Counter
import re

import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from .env

openai_api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(layout="centered", page_title="My Micro-Atlas")

# --- Set up OpenAI API Key (at the top, outside any functions or blocks) ---
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

# --- Initialize session state for login status and text area content ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
# Initialize the main text area content in session state
if 'learning_input_text_area_content' not in st.session_state:
    st.session_state.learning_input_text_area_content = "Example: I read an article about 'reinforcement learning from human feedback' (RLHF) and how it's used to align large language models. This builds on my understanding of basic machine learning concepts. I also worked on a project analyzing user sentiment in customer reviews, using Python and NLP techniques. This involved data cleaning and visualization."


# --- Login/Logout UI (in the sidebar for a cleaner main page) ---
st.sidebar.image("https://em-content.zobj.net/source/microsoft-teams/363/brain_1f9e0.png", width=50)
st.sidebar.title("Account (Mock)")

if not st.session_state.logged_in:
    st.sidebar.header("Login / Create Account")
    username_input = st.sidebar.text_input("Enter a Username", key="login_username_input")
    password_input = st.sidebar.text_input("Enter a Password (any value)", type="password", key="login_password_input")

    if st.sidebar.button("Login / Register", key="login_button"):
        if username_input:
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.sidebar.success(f"Welcome, {username_input}! Your mock account is ready.")
            st.rerun()
        else:
            st.sidebar.error("Please enter a username.")
else:
    st.sidebar.success(f"Logged in as: **{st.session_state.username}**")
    if st.sidebar.button("Logout", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

# --- Check if logged in before showing main app content ---
if not st.session_state.logged_in:
    st.info("Please log in on the sidebar to use 'My Micro-Atlas' and save your insights.")
    st.stop()

# --- Define the AI Analysis Function ---
def get_micro_atlas_analysis(text_input):
    user_prompt_content = f"""
You are an expert knowledge curator and cognitive cartographer, helping individuals map their learning journey.
Your task is to analyze the following unstructured text, which describes a user's recent learning, consumption, or project experiences.
From this text, you need to extract and categorize the following key elements of their knowledge landscape:

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
                    "content": user_prompt_content
                }
            ],
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating analysis: {str(e)}"

def save_user_analysis(username, input_text, ai_output):
    data_dir = "user_data"
    os.makedirs(data_dir, exist_ok=True)
    user_file_path = os.path.join(data_dir, f"{username}.json")

    user_data = []
    if os.path.exists(user_file_path):
        try:
            with open(user_file_path, "r", encoding="utf-8") as f:
                user_data = json.load(f)
        except json.JSONDecodeError:
            st.warning(f"Could not read existing data for {username}. Starting fresh.")
            user_data = []
        except Exception as e:
            st.error(f"An unexpected error occurred while loading data for {username}: {e}")
            user_data = []

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = {
        "timestamp": timestamp,
        "input_text": input_text,
        "ai_analysis": ai_output
    }

    user_data.insert(0, new_entry)

    try:
        with open(user_file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving data to {username}.json: {str(e)}")
        return False

def load_user_analyses(username):
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
    return []

# Define the database file (must be the same as in webhook_receiver.py)
DATABASE_FILE = 'sms_database.db' # Renamed for clarity, was SMS_DATABASE_FILE

# --- MODIFIED: Renamed and updated function to get all learning inputs ---
def get_all_learning_inputs():
    """
    Retrieves all messages (SMS, Email) and web clips from the SQLite database.
    Messages are ordered by timestamp in descending order (newest first).
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Fetch messages (SMS and Email)
        cursor.execute("SELECT id, sender_number, body, timestamp, type FROM messages ORDER BY timestamp DESC")
        messages = cursor.fetchall()

        # Fetch web clips
        cursor.execute("SELECT id, url, clipped_text, timestamp FROM web_clips ORDER BY timestamp DESC")
        clips = cursor.fetchall()

        return messages, clips
    except sqlite3.Error as e:
        st.error(f"Error reading database: {e}")
        return [], []
    finally:
        if conn:
            conn.close()

# --- Functions for Theme Identification and Recommendations ---

def extract_core_concepts_from_analysis(ai_analysis_text):
    """
    Parses the AI analysis text to extract Core Concepts & Topics.
    Assumes the format: **Core Concepts & Topics:**\n- Concept 1\n- Concept 2
    """
    concepts = []
    # Regex to find the "Core Concepts & Topics" section and extract bullet points
    # It looks for the bold heading, then any lines starting with a hyphen until another bold heading or end of string
    match = re.search(r"\*\*Core Concepts & Topics:\*\*\s*\n([\s\S]*?)(?=\*\*|\Z)", ai_analysis_text, re.IGNORECASE)
    if match:
        section_content = match.group(1).strip()
        # Extract individual bullet points
        for line in section_content.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                concept = line[2:].strip() # Remove '- ' prefix
                # Further clean if there's a 1-sentence explanation
                if ":" in concept:
                    concept = concept.split(":")[0].strip() # Take only the main concept before any explanation
                concepts.append(concept)
    return concepts

def get_user_theme_profile(username, num_top_themes=5):
    """
    Loads user's historical analyses and identifies their top common themes.
    """
    user_history = load_user_analyses(username)
    all_concepts = []
    for entry in user_history:
        concepts_from_entry = extract_core_concepts_from_analysis(entry['ai_analysis'])
        all_concepts.extend(concepts_from_entry)

    # Count the frequency of each concept
    concept_counts = Counter(all_concepts)
    # Get the most common themes
    top_themes = [theme for theme, count in concept_counts.most_common(num_top_themes)]
    return top_themes

def generate_recommendations_with_llm(user_themes):
    """
    Uses an LLM to generate content recommendations based on user's top themes.
    """
    if not user_themes:
        return "No specific themes identified yet. Analyze more content to get recommendations!"

    themes_str = ", ".join([f"'{t}'" for t in user_themes])

    recommendation_prompt = f"""
Based on the following top learning themes: {themes_str},
suggest 3-5 hypothetical articles, courses, or projects that would be highly relevant.
For each suggestion, provide:
1.  **A catchy title for the content.**
2.  **A brief summary (1-2 sentences) of what it's about.**
3.  **A very short explanation (1 sentence) of how it relates to one or more of the user's existing interests.**

Format your response clearly with numbered bullet points for each suggestion.
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo", # Use the same model as your main analysis
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant specialized in learning and content recommendations."
                },
                {
                    "role": "user",
                    "content": recommendation_prompt
                }
            ],
            temperature=0.7,
            max_tokens=600 # Adjust as needed
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating recommendations: {str(e)}"

# Removed: generate_harvard_course_recommendations function and its import


# --- Streamlit UI layout (this is the main part of your app) ---
st.title("🧠 My Micro-Atlas: Your Personal Learning Map")
st.write("Paste in your learning summaries (articles, projects, notes) and let AI map your cognitive landscape.")

st.markdown("---")
st.header("Your Learning Inputs")
# Updated instructions based on our previous discussion about simplified email input
st.write("To analyze content: select from your SMS messages or web clippings below, or **paste email content (subject and body) or any other text directly into the input box.**")

# --- Fetch all learning inputs ---
if st.session_state.username:
    all_messages, all_web_clips = get_all_learning_inputs()

    # Combine all inputs into a single list
    all_inputs = []
    for msg_id, sender, message, timestamp, msg_type in all_messages:
        all_inputs.append({
            "id": msg_id,
            "type": msg_type.capitalize() if msg_type else "SMS",
            "sender": sender,
            "content": message,
            "timestamp": timestamp
        })
    for clip_id, url, text, timestamp in all_web_clips:
        all_inputs.append({
            "id": clip_id,
            "type": "Web Clip",
            "url": url,
            "content": text,
            "timestamp": timestamp
        })

    # Sort all inputs by timestamp in descending order (newest first)
    all_inputs.sort(key=lambda x: x['timestamp'], reverse=True)

    # Create display options for the dropdown
    display_options = ["(Select an input to analyze)"]
    for item in all_inputs:
        display_str = ""
        if item['type'] == "SMS":
            display_str = f"SMS from {item['sender']} ({item['timestamp']}): {item['content'][:70]}..."
        elif item['type'] == "Web Clip":
            display_str = f"Web Clip ({item['timestamp']}) - {item['url'].split('//')[-1].split('/')[0]}: {item['content'][:70]}..."
        elif item['type'] == "Email":
            # Attempt to show subject or sender for email
            first_line = item['content'].split('\n')[0]
            display_str = f"Email from {item['sender'] or 'Unknown'} ({item['timestamp']}): {first_line[:70]}..."
            if "Subject: " in first_line:
                # If content starts with "Subject: " assume it was combined
                display_str = f"Email: {first_line.replace('Subject: ', '')[:70]}... ({item['timestamp']})"
        display_options.append(display_str)


    # --- Update the dropdown selection ---
    selected_input_display = st.selectbox(
        "Select an input from your history to analyze:",
        options=display_options,
        index=0,
        key="input_selection_dropdown"
    )

    selected_input_content = ""
    if selected_input_display != "(Select an input to analyze)":
        for item in all_inputs:
            item_display_string = ""
            if item['type'] == "SMS":
                item_display_string = f"SMS from {item['sender']} ({item['timestamp']}): {item['content'][:70]}..."
            elif item['type'] == "Web Clip":
                item_display_string = f"Web Clip ({item['timestamp']}) - {item['url'].split('//')[-1].split('/')[0]}: {item['content'][:70]}..."
            elif item['type'] == "Email":
                first_line = item['content'].split('\n')[0]
                item_display_string = f"Email from {item['sender'] or 'Unknown'} ({item['timestamp']}): {first_line[:70]}..."
                if "Subject: " in first_line:
                    item_display_string = f"Email: {first_line.replace('Subject: ', '')[:70]}... ({item['timestamp']})"

            if item_display_string == selected_input_display:
                selected_input_content = item['content']
                break

    # If an item was selected from the dropdown, update the session state variable
    if selected_input_content:
        st.session_state.learning_input_text_area_content = selected_input_content


# --- Unified Text Area for Learning Input ---
active_learning_input = st.text_area(
    "Paste your learning content here (or select from history):",
    value=st.session_state.learning_input_text_area_content,
    height=200,
    key="unified_main_learning_input_text_area"
)

st.session_state.learning_input_text_area_content = active_learning_input

# --- Button click logic (call the function here) ---
st.markdown("---") # Separator before the button

if st.button("Generate My Micro-Atlas"):
    if not active_learning_input.strip():
        st.warning("Please paste some content to analyze!")
    else:
        st.info("Generating your cognitive map...")
        with st.spinner("Analyzing your learning with AI..."):
            ai_analysis_output = get_micro_atlas_analysis(active_learning_input)
            st.subheader("Your AI-Enhanced Learning Snapshot:")
            st.markdown(ai_analysis_output)
            if st.session_state.logged_in:
                if save_user_analysis(st.session_state.username, active_learning_input, ai_analysis_output):
                    st.success("Analysis saved to your account!")
                else:
                    st.error("Failed to save analysis.")

st.markdown("---")
st.caption("Powered by AI and your brilliant mind.")

# --- Display User History ---
if st.session_state.logged_in:
    st.markdown("---")
    st.header(f"Your Learning History ({st.session_state.username})")

    user_history = load_user_analyses(st.session_state.username)
    if user_history:
        for i, entry in enumerate(user_history):
            expander_title = f"Analysis from {entry['timestamp']}"
            if 'input_text' in entry and len(entry['input_text']) > 50:
                expander_title += f": \"{entry['input_text'][:50]}...\""

            with st.expander(expander_title):
                st.markdown(entry['ai_analysis'])
    else:
        st.info("No saved analyses yet. Generate one to see your history!")

    # --- NEW SECTIONS: Top Learning Themes and General Recommendations ---
    st.markdown("---")
    st.header("Your Top Learning Themes")
    with st.spinner("Identifying your top themes..."):
        user_top_themes = get_user_theme_profile(st.session_state.username)
        st.session_state.user_top_themes = user_top_themes # Store themes in session_state

    if user_top_themes:
        st.write("Based on your past analyses, your most prominent learning interests include:")
        st.markdown(", ".join([f"**{theme}**" for theme in user_top_themes]))
    else:
        st.info("Analyze more content to build your learning theme profile!")

    st.markdown("---")
    st.header("Content Recommendations for You")
    with st.spinner("Generating personalized recommendations..."):
        recommendations = generate_recommendations_with_llm(user_top_themes)
        st.markdown(recommendations)

# Removed: Harvard Course Recommendations section