import streamlit as st
import httpx  # Using httpx instead of requests

# Configuration
BACKEND_URL = "http://localhost:8000/chat"
st.set_page_config(page_title="Unified Chatbot", page_icon="🤖", layout="wide")

# Custom CSS for styling the backend badges
st.markdown("""
<style>
    .backend-badge {
        font-size: 0.75em;
        padding: 4px 8px;
        border-radius: 12px;
        background-color: #f0f2f6;
        color: #31333F;
        font-weight: 600;
        display: inline-block;
        margin-top: 8px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# We store the file bytes in session state so it persists 
# when the user hits 'Enter' in the chat input (which triggers a rerun)
if "file_bytes" not in st.session_state:
    st.session_state.file_bytes = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None

# --- Sidebar: Document Management ---
with st.sidebar:
    st.header("📂 Document Context")
    
    # File Uploader
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

    # Logic to persist file in session state
    if uploaded_file is not None:
        # Only update if a new file is selected to avoid reloading bytes unnecessarily
        if st.session_state.file_name != uploaded_file.name:
            st.session_state.file_bytes = uploaded_file.getvalue()
            st.session_state.file_name = uploaded_file.name
            st.toast(f"File '{uploaded_file.name}' attached!", icon="✅")

    # Display active file status
    if st.session_state.file_name:
        st.success(f"📎 Active: **{st.session_state.file_name}**")
        if st.button("🗑️ Clear File", type="primary"):
            st.session_state.file_bytes = None
            st.session_state.file_name = None
            st.rerun()
    else:
        st.info("No document attached. Queries will use Company Knowledge or Database.")

# --- Main Chat Interface ---
st.title("🤖 Unified Enterprise Assistant")

# 1. Display Chat History (Must be done BEFORE handling new input)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # If it's an assistant message, show the source badge
        if msg["role"] == "assistant" and "backend" in msg:
            backend_map = {
                "lf_assist": "🏢 Company Knowledge",
                "doc_assist": "📄 Document Q&A",
                "db_assist": "🗄️ Database"
            }
            readable_backend = backend_map.get(msg["backend"], msg["backend"])
            st.markdown(f'<div class="backend-badge">Source: {readable_backend}</div>', unsafe_allow_html=True)

# 2. Handle User Input
if prompt := st.chat_input("Type your question here..."):
    # Add user message to state immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Call Backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Prepare data for httpx
                # 'data' is for form fields, 'files' is for file uploads
                form_data = {"message": prompt}
                files_data = None

                # If we have a file in session state, add it to the request
                if st.session_state.file_bytes is not None:
                    files_data = {
                        "file": (
                            st.session_state.file_name, 
                            st.session_state.file_bytes, 
                            "application/pdf"
                        )
                    }

                # Send POST request using httpx
                # timeout=60.0 is important because LLMs can be slow
                response = httpx.post(
                    BACKEND_URL, 
                    data=form_data, 
                    files=files_data,
                    timeout=60.0 
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No response text.")
                    backend = data.get("backend", "unknown")

                    st.markdown(answer)
                    
                    # Display Badge
                    backend_map = {
                        "lf_assist": "🏢 Company Knowledge",
                        "doc_assist": "📄 Document Q&A",
                        "db_assist": "🗄️ Database"
                    }
                    readable_backend = backend_map.get(backend, backend)
                    st.markdown(f'<div class="backend-badge">Source: {readable_backend}</div>', unsafe_allow_html=True)

                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer, 
                        "backend": backend
                    })
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

            except httpx.ConnectError:
                st.error("❌ Could not connect to backend. Is localhost:8000 running?")
            except httpx.TimeoutException:
                st.error("❌ The backend took too long to respond.")
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")