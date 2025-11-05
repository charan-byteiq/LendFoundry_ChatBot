import streamlit as st
import requests
import os

# --- Configuration ---
DOC_CHATBOT_URL = "http://127.0.0.1:8000/ask/"
DB_CHATBOT_URL = "http://127.0.0.1:8001/api/chat"

# --- Page Setup ---
st.set_page_config(page_title="LendFoundry AI Assistant", layout="wide")

# --- UI Styling (Dark Theme) ---
st.markdown("""
    <style>
        /* Main app background */
        .stApp {
            background-color: black;
        }
        /* Ensure headers and other text elements are white */
        h1, h3, .st-emotion-cache-16idsys p, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div, [data-testid="stSidebar"] label {
            color: white;
        }
        /* Keep original chat bubble styling for contrast, but ensure text inside is black */
        .st-emotion-cache-1c7y2kd {
            background-color: #FFFFFF;
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: black; /* Text inside assistant bubbles */
        }
        [data-testid="chat-message-container"] {
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        [data-testid="chat-message-container"] [data-testid="stChatMessageContent"] {
             background-color: #DCF8C6;
             color: black; /* Text inside user bubbles */
        }
    </style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
def initialize_session_state():
    """Initializes session state variables if they don't exist."""
    if "chatbot_type" not in st.session_state:
        st.session_state.chatbot_type = "Database Assistant"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_file_content" not in st.session_state:
        st.session_state.uploaded_file_content = None
    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = None

initialize_session_state()

# --- Helper Functions ---
def handle_db_query(prompt):
    """Sends a prompt to the database chatbot backend."""
    try:
        payload = {"prompt": prompt}
        res = requests.post(DB_CHATBOT_URL, json=payload, timeout=60)
        res.raise_for_status()
        return res.json().get("response", "Sorry, I couldn't get a response.")
    except requests.exceptions.RequestException as e:
        return f"Error connecting to the Database Assistant: {e}"

def handle_doc_query(prompt, file_content, file_name):
    """Sends a prompt and a file to the document chatbot backend."""
    try:
        files = {'file': (file_name, file_content, 'application/pdf')}
        data = {'question': prompt}
        res = requests.post(DOC_CHATBOT_URL, files=files, data=data, timeout=60)
        res.raise_for_status()
        return res.json().get("answer", "Sorry, I couldn't get an answer from the document.")
    except requests.exceptions.RequestException as e:
        return f"Error connecting to the Document Assistant: {e}"

# --- Sidebar for Chatbot Selection ---
with st.sidebar:
    st.title("LendFoundry")
    st.header("AI Assistant")
    
    # When the radio button changes, it resets the chat
    def on_chatbot_change():
        st.session_state.messages = []
        st.session_state.uploaded_file_content = None
        st.session_state.uploaded_file_name = None

    st.radio(
        "Choose an assistant:",
        ("Database Assistant", "Document Assistant"),
        key="chatbot_type",
        on_change=on_chatbot_change
    )
    st.markdown("---")
    if st.session_state.chatbot_type == "Document Assistant":
        st.info("Upload a PDF document to ask questions about its content.")
        uploaded_file = st.file_uploader("Upload PDF", type="pdf", label_visibility="collapsed")
        if uploaded_file:
            st.session_state.uploaded_file_content = uploaded_file.getvalue()
            st.session_state.uploaded_file_name = uploaded_file.name
            st.success(f"Uploaded `{uploaded_file.name}`. You can now ask questions about it.")
    else:
        st.info("Ask questions in natural language to query the database.")

# --- Main Chat Interface ---
st.header(f"AI {st.session_state.chatbot_type}")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Determine if the chat input should be disabled
is_doc_chat_ready = st.session_state.chatbot_type == "Document Assistant" and st.session_state.uploaded_file_content is not None
is_db_chat_ready = st.session_state.chatbot_type == "Database Assistant"
chat_input_disabled = not (is_doc_chat_ready or is_db_chat_ready)
placeholder_text = "Please upload a document to begin" if st.session_state.chatbot_type == "Document Assistant" and not is_doc_chat_ready else "Ask your question here..."

# Single chat input at the bottom
if prompt := st.chat_input(placeholder_text, disabled=chat_input_disabled):
    # Add user message to state and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = ""
            if st.session_state.chatbot_type == "Database Assistant":
                response = handle_db_query(prompt)
            elif st.session_state.chatbot_type == "Document Assistant":
                if st.session_state.uploaded_file_content:
                    response = handle_doc_query(prompt, st.session_state.uploaded_file_content, st.session_state.uploaded_file_name)
                else:
                    # This case should ideally not be hit due to disabled input
                    response = "There seems to be an issue. Please upload a file again."
            
            st.markdown(response)
    
    # Add assistant response to state
    st.session_state.messages.append({"role": "assistant", "content": response})