import streamlit as st
import openai
import os
import json # Still needed for user_data.json login/logout if you keep it
import datetime
import re
import psycopg2 # For connecting to PostgreSQL/Supabase
import pandas as pd # Good for displaying fetched data

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Supabase Database Credentials ---
DB_HOST = os.getenv("SUPABASE_DB_HOST")
DB_PORT = os.getenv("SUPABASE_DB_PORT")
DB_NAME = os.getenv("SUPABASE_DB_NAME")
DB_USER = os.getenv("SUPABASE_DB_USER")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")

# --- OpenAI API Key ---
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

st.set_page_config(layout="centered", page_title="My Micro-Atlas")

# --- Initialize session state for login status and text area content ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
# Initialize the main text area content in session state
if 'learning_input_text_area_content' not in st.session_state:
    st.session_state.learning_input_text_area_content = "Example: I read an article about 'reinforcement learning from human feedback' (RLHF) and how it's used to align large language models. This builds on my understanding of basic machine learning concepts. I also worked on a project analyzing user sentiment in customer reviews, using Python and NLP techniques. This involved data cleaning and visualization."

# Initialize analysis results in session state
if 'current_summary' not in st.session_state:
    st.session_state.current_summary = ""
if 'current_sentiment' not in st.session_state:
    st.session_state.current_sentiment = ""
if 'current_keywords' not in st.session_state:
    st.session_state.current_keywords = []

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


# --- Database Connection and Fetching Functions (for Supabase) ---
#@st.cache_resource
def get_supabase_connection_streamlit():
    """Establishes and returns a connection to the Supabase PostgreSQL database for Streamlit."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

# Replace your existing fetch_notes_from_database function with this one:
def fetch_notes_from_database(username): # Add username parameter
    """Fetches all notes for the given user from the Supabase user_notes table."""
    conn = None
    cur = None

    try:
        conn = get_supabase_connection_streamlit()
        if conn is None:
            return pd.DataFrame() # Return empty DataFrame on connection error

        cur = conn.cursor()
        # Modified SELECT query to filter by username
        cur.execute(
            "SELECT id, created_at, content, summary, sentiment, keywords FROM user_notes WHERE username = %s ORDER BY created_at DESC;",
            (username,) # Pass the username as a tuple
        )
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description] # Get column names directly from cursor

        notes_data = []
        for row in rows:
            note_dict = dict(zip(column_names, row))
            if note_dict['keywords'] is None:
                note_dict['keywords'] = []
            else:
                try:
                    # Keywords are stored as JSON string in DB, need to parse to Python list
                    note_dict['keywords'] = json.loads(note_dict['keywords'])
                except json.JSONDecodeError:
                    note_dict['keywords'] = [] # Handle cases where JSON parsing fails
            notes_data.append(note_dict)

        return pd.DataFrame(notes_data)

    except Exception as e:
        st.error(f"Error fetching notes from database: {e}")
        return pd.DataFrame() # Return empty DataFrame on fetch error
    finally:
        # Only close if the cursor/connection were successfully created
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- OLD LOCAL FILE FUNCTIONS (Removed or Adapted) ---
# save_user_analysis and load_user_analyses are for local JSON files and are effectively replaced by Supabase
# If you want user-specific history within the Supabase table, you'd need a 'username' column in user_notes
# and filter by it during fetch. For now, we're fetching ALL user_notes.
# If you want to keep per-user history, you need to add a 'username' column to your Supabase table.
# For simplicity, assuming 'user_notes' stores all notes regardless of mock user.
# If 'username' is critical for filtering, you'd add it to 'user_notes' table and
# modify save_note_to_database() and fetch_notes_from_database() to include it.

# --- Define the AI Analysis Function (if you want live analysis in Streamlit) ---
# Keeping this for now, but note that the primary AI analysis happens in webhook_receiver.py
# when data is first ingested. This would be for manual "analyze now" in Streamlit.
def get_micro_atlas_analysis_live(text_input):
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

# --- Functions for Theme Identification and Recommendations ---
# Ensure `from collections import Counter` is at the top of your app.py
from collections import Counter

# Replace your existing get_user_theme_profile_from_db function with this one:
def get_user_theme_profile_from_db(username, num_top_themes=5): # Add username parameter
    """
    Loads historical notes for a specific user from Supabase and identifies top common themes
    based on keywords.
    """
    # Fetch notes for the specific user
    all_notes_df = fetch_notes_from_database(username) # Pass username here
    if all_notes_df.empty:
        return []

    all_keywords = []
    # Ensure 'keywords' column exists and contains lists (after JSON parsing in fetch_notes_from_database)
    if 'keywords' in all_notes_df.columns:
        for keywords_list in all_notes_df['keywords'].dropna():
            all_keywords.extend(keywords_list)

    # Count the frequency of each keyword
    keyword_counts = Counter(all_keywords)
    # Get the most common themes/keywords
    top_themes = [theme for theme, count in keyword_counts.most_common(num_top_themes)]
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


# --- Streamlit UI layout (this is the main part of your app) ---
st.title("🧠 My Micro-Atlas: Your Personal Learning Map")
st.write("Paste in your learning summaries (articles, projects, notes) and let AI map your cognitive landscape.")

st.markdown("---")
st.header("Your Learning Inputs")
st.write("To analyze content: select from your historical notes below, or **paste any other text directly into the input box.**")

# --- Fetch all learning inputs from Supabase for the logged-in user ---
# Pass the username to filter notes for the currently logged-in user
all_notes_df = fetch_notes_from_database(st.session_state.username)

display_options = ["(Select an input from history to view analysis)"]
if not all_notes_df.empty:
    # Format for display: Timestamp - Content Snippet
    all_notes_df['display_text'] = all_notes_df['created_at'].dt.strftime('%Y-%m-%d %H:%M') + " - " + all_notes_df['content'].str[:70].replace('\n', ' ') + "..."
    display_options.extend(all_notes_df['display_text'].tolist())


selected_input_display = st.selectbox(
    "Select an input from your history to view its analysis:",
    options=display_options,
    index=0,
    key="input_selection_dropdown"
)

# If an item was selected from the dropdown, update the session state variables
if selected_input_display != "(Select an input from history to view analysis)":
    selected_note_data = all_notes_df[all_notes_df['display_text'] == selected_input_display].iloc[0]
    
    st.session_state.learning_input_text_area_content = selected_note_data['content']
    st.session_state.current_summary = selected_note_data['summary']
    st.session_state.current_sentiment = selected_note_data['sentiment']
    st.session_state.current_keywords = selected_note_data['keywords']
else:
    # Reset display if default option selected
    if 'current_summary' in st.session_state:
        st.session_state.current_summary = ""
        st.session_state.current_sentiment = ""
        st.session_state.current_keywords = []


# --- Unified Text Area for Learning Input ---
active_learning_input = st.text_area(
    "Paste your learning content here (or select from history):",
    value=st.session_state.learning_input_text_area_content,
    height=200,
    key="unified_main_learning_input_text_area"
)
st.session_state.learning_input_text_area_content = active_learning_input


# --- "Analyze Note" Button Logic (for live analysis within Streamlit) ---
st.markdown("---")
if st.button("Analyze Note (Live)"):
    if not active_learning_input.strip():
        st.warning("Please paste some content to analyze!")
    else:
        st.info("Generating your cognitive map...")
        with st.spinner("Analyzing your learning with AI..."):
            ai_analysis_output = get_micro_atlas_analysis_live(active_learning_input)
            
            st.subheader("Your AI-Enhanced Learning Snapshot:")
            st.markdown(ai_analysis_output)
            
            # If you want this live analysis to also be saved to Supabase,
            # you would need to call a save function here, passing
            # active_learning_input, parsed analysis, and st.session_state.username.
            # For now, we are assuming saving happens via webhooks (email/sms/webclip).


# --- Display Analysis Results (pre-computed from DB or live-computed) ---
st.subheader("Analysis Results")
if st.session_state.learning_input_text_area_content:
    st.write("**Original Content:**")
    st.info(st.session_state.learning_input_text_area_content)

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Summary:**")
        st.success(st.session_state.current_summary if st.session_state.current_summary else "No summary available.")
    with col2:
        st.write("**Sentiment:**")
        st.info(st.session_state.current_sentiment if st.session_state.current_sentiment else "No sentiment available.")

    st.write("**Keywords:**")
    if st.session_state.current_keywords:
        st.code(", ".join(st.session_state.current_keywords))
    else:
        st.write("No keywords extracted.")

else:
    st.info("Enter text above or select from history to see analysis.")

st.markdown("---")
st.caption("Powered by AI and your brilliant mind.")


# --- Display User History (from Supabase, now user-filtered) ---
if st.session_state.logged_in: # This block is already within the logged-in check
    st.markdown("---")
    # Updated header to reflect user-specific data
    st.header(f"Your Historical Notes ({st.session_state.username})") 

    # all_notes_df is already fetched for the current user at the top of this block
    if not all_notes_df.empty:
        # Example of iterating through notes and displaying in expanders
        st.subheader("Details from History:")
        for index, entry in all_notes_df.iterrows():
            expander_title = f"Note from {entry['created_at'].strftime('%Y-%m-%d %H:%M:%S')}"
            if 'content' in entry and len(entry['content']) > 50:
                expander_title += f": \"{entry['content'][:50].replace('\n', ' ')}...\""

            with st.expander(expander_title):
                st.write("**Original Content:**")
                st.info(entry['content'])
                st.write("**Summary:**")
                st.success(entry['summary'])
                st.write("**Sentiment:**")
                st.info(entry['sentiment'])
                st.write("**Keywords:**")
                if entry['keywords']:
                    # Ensure keywords are correctly displayed as a comma-separated string
                    st.code(", ".join(entry['keywords']))
                else:
                    st.write("No keywords.")
    else:
        st.info(f"No saved notes yet in Supabase for user '{st.session_state.username}'. Send an email/SMS/web clip via your Flask app to populate!")


    # --- NEW SECTIONS: Top Learning Themes and General Recommendations ---
    st.markdown("---")
    st.header("Your Top Learning Themes")
    with st.spinner("Identifying your top themes..."):
        # This now gets themes only for the logged-in user
        user_top_themes = get_user_theme_profile_from_db(st.session_state.username) # Pass username here
        st.session_state.user_top_themes = user_top_themes # Store themes in session_state

    if user_top_themes:
        st.write("Based on your past analyses, your most prominent learning interests include:")
        st.markdown(", ".join([f"**{theme}**" for theme in user_top_themes]))
    else:
        st.info("Analyze more content to build your learning theme profile!")

    st.markdown("---")
    st.header("Content Recommendations for You")
    with st.spinner("Generating personalized recommendations..."):
        # This function uses user_top_themes which is now user-specific
        recommendations = generate_recommendations_with_llm(st.session_state.user_top_themes)
        st.markdown(recommendations)