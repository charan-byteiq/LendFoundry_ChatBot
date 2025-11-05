
import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set.")
    st.stop()

genai.configure(api_key=api_key)

# --- Helper Functions ---
def get_gemini_response(question, pdf_content):
    """Sends the user's question and PDF content to the Gemini API."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    # The Gemini API can take the raw bytes of the PDF directly.
    pdf_part = {"mime_type": "application/pdf", "data": pdf_content}
    
    try:
        response = model.generate_content([question, pdf_part])
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"

# --- Main UI Layout ---
st.set_page_config(page_title="Doc Assist", page_icon=":robot_face:")
st.title("📄 Doc Assist Chatbot")
st.write("Upload a PDF and ask questions about its content.")

# File uploader for PDF files.
uploaded_file = st.file_uploader(
    "Upload a PDF file", 
    type="pdf",
    help="Upload a PDF to start chatting."
)

if uploaded_file:
    # Read the content of the uploaded file
    pdf_content = uploaded_file.read()
    
    st.success(f"Successfully uploaded `{uploaded_file.name}`!")
    
    # Chat input for the user
    question = st.text_input("Ask a question about the PDF:")
    
    if st.button("Get Answer"):
        if question:
            with st.spinner("Thinking..."):
                response = get_gemini_response(question, pdf_content)
                st.write("### Answer")
                st.write(response)
        else:
            st.warning("Please enter a question.")
