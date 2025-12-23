
import streamlit as st
import os
from dotenv import load_dotenv
from services import get_gemini_client

# --- Configuration ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set.")
    st.stop()

# --- Helper Functions ---
def get_gemini_response_doc(question, pdf_content):
    """Sends the user's question and PDF content to the Gemini API."""
    gemini = get_gemini_client()
    
    # The Gemini API can take the raw bytes of the PDF directly.
    pdf_part = {"mime_type": "application/pdf", "data": pdf_content}
    
    try:
        response = gemini.generate_content([question, pdf_part])
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"

def get_gemini_response_db(question):
    """Sends the user's question to the Gemini API for a database query."""
    gemini = get_gemini_client()
    
    try:
        return gemini.generate(question)
    except Exception as e:
        return f"An error occurred: {e}"

# --- Main UI Layout ---
st.set_page_config(page_title="Combined Chatbot", page_icon=":robot_face:")
st.title("🤖 Combined Chatbot")
st.write("Select a chatbot and ask your questions.")

# Chatbot selection
chatbot_type = st.selectbox(
    "Select Chatbot",
    ("Doc Assist", "DB Query")
)

if chatbot_type == "Doc Assist":
    st.header("📄 Doc Assist")
    uploaded_file = st.file_uploader(
        "Upload a PDF file", 
        type="pdf",
        help="Upload a PDF to start chatting."
    )

    if uploaded_file:
        pdf_content = uploaded_file.read()
        st.success(f"Successfully uploaded `{uploaded_file.name}`!")
        
        question = st.text_input("Ask a question about the PDF:")
        
        if st.button("Get Answer"):
            if question:
                with st.spinner("Thinking..."):
                    response = get_gemini_response_doc(question, pdf_content)
                    st.write("### Answer")
                    st.write(response)
            else:
                st.warning("Please enter a question.")

elif chatbot_type == "DB Query":
    st.header("🗃️ DB Query")
    
    question = st.text_input("Enter your database query:")
    
    if st.button("Get Answer"):
        if question:
            with st.spinner("Thinking..."):
                response = get_gemini_response_db(question)
                st.write("### Answer")
                st.write(response)
        else:
            st.warning("Please enter a query.")
