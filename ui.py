import streamlit as st
import requests
import os
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Multi-Assistant Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .backend-badge {
        display: inline-block;
        padding: 0.25em 0.6em;
        font-size: 0.75em;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 0.375rem;
        margin-bottom: 0.5em;
    }
    .lf-assist {
        background-color: #4CAF50;
        color: white;
    }
    .doc-assist {
        background-color: #2196F3;
        color: white;
    }
    .db-assist {
        background-color: #FF9800;
        color: white;
    }
    .scope-guard {
        background-color: #9E9E9E;
        color: white;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = os.getenv("UNIFIED_API_URL", "http://127.0.0.1:8000/chat")
CLEAR_URL = os.getenv("UNIFIED_API_URL", "http://127.0.0.1:8000/chat/clear")

# Backend display configurations
BACKEND_CONFIG = {
    "lf_assist": {
        "name": "📚 LF Assist",
        "color": "green",
        "description": "General company policies and information"
    },
    "doc_assist": {
        "name": "📄 Doc Assist",
        "color": "blue",
        "description": "Answers from your uploaded document"
    },
    "db_assist": {
        "name": "💾 DB Assist",
        "color": "orange",
        "description": "Loan and customer data queries"
    },
    "scope_guard": {
        "name": "🛡️ LLM",
        "color": "gray",
        "description": "Out-of-scope query handler"
    }
}

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# Sidebar
with st.sidebar:
    st.title("🤖 Multi-Assistant Chatbot")
    st.markdown("---")
    
    # Session info
    st.subheader("📊 Session Info")
    if st.session_state.session_id:
        st.info(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
        st.caption(f"Messages: {len(st.session_state.messages)}")
    else:
        st.warning("No active session")
    
    st.markdown("---")
    
    # Backend status
    st.subheader("🎯 Available Assistants")
    for backend, config in BACKEND_CONFIG.items():
        st.markdown(f"**{config['name']}**")
        st.caption(config['description'])
        st.markdown("")
    
    st.markdown("---")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        if st.session_state.session_id:
            try:
                response = requests.post(
                    f"{CLEAR_URL}/{st.session_state.session_id}",
                    timeout=10
                )
                st.success("Chat cleared!")
            except:
                st.warning("Could not clear server history")
        
        st.session_state.messages = []
        st.session_state.session_id = None
        st.session_state.uploaded_file = None
        st.rerun()
    
    st.markdown("---")
    
    # File upload section
    st.subheader("📎 Upload Document")
    uploaded_file = st.file_uploader(
        "Upload PDF for Document Q&A",
        type=["pdf"],
        help="Upload a PDF to ask questions about its content"
    )
    
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
        st.session_state.uploaded_file = uploaded_file
    elif st.session_state.uploaded_file:
        st.session_state.uploaded_file = None
    
    st.markdown("---")
    st.caption("💡 **Tip:** Upload a PDF to ask document-specific questions!")

# Main chat interface
st.title("LendFoundry Chatbot")
st.markdown("Ask questions about company policies, uploaded documents, or loan data!")

# Display chat messages
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    backend = message.get("backend")
    tags = message.get("tags", [])
    
    with st.chat_message(role):
        if role == "assistant" and backend:
            # Show backend badge
            config = BACKEND_CONFIG.get(backend, {})
            st.badge(
                config.get("name", backend),
                color=config.get("color", "gray")
            )
            
            # Show tags if available (from LF Assist)
            if tags:
                tag_str = " • ".join([f"`{tag}`" for tag in tags])
                st.caption(f"🏷️ Tags: {tag_str}")
        
        st.markdown(content)

# Chat input
if prompt := st.chat_input("Ask a question about loans, policies, or documents..."):
    # Add user message to chat
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "timestamp": datetime.now().isoformat()
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response with streaming effect
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        backend_placeholder = st.empty()
        
        with st.spinner("Thinking..."):
            try:
                # Prepare request data
                files = {}
                data = {"message": prompt}
                
                # Add session_id if exists
                if st.session_state.session_id:
                    data["session_id"] = st.session_state.session_id
                
                # Add file if uploaded
                if st.session_state.uploaded_file:
                    # Reset file pointer
                    st.session_state.uploaded_file.seek(0)
                    files["file"] = (
                        st.session_state.uploaded_file.name,
                        st.session_state.uploaded_file,
                        "application/pdf"
                    )
                
                # Make API request
                response = requests.post(
                    API_URL,
                    data=data,
                    files=files if files else None,
                    timeout=60
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract response data
                answer = result.get("answer", "No response received.")
                backend = result.get("backend", "unknown")
                session_id = result.get("session_id")
                tags = result.get("tags", [])
                
                # Update session_id
                if session_id and not st.session_state.session_id:
                    st.session_state.session_id = session_id
                
                # Show backend badge
                config = BACKEND_CONFIG.get(backend, {})
                backend_placeholder.badge(
                    config.get("name", backend),
                    color=config.get("color", "gray")
                )
                
                # Show tags if available
                if tags:
                    tag_str = " • ".join([f"`{tag}`" for tag in tags])
                    st.caption(f"🏷️ Tags: {tag_str}")
                
                # Display answer
                message_placeholder.markdown(answer)
                
                # Save to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "backend": backend,
                    "tags": tags,
                    "timestamp": datetime.now().isoformat()
                })
                
            except requests.exceptions.Timeout:
                error_msg = "⏱️ Request timed out. Please try again."
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "backend": "error",
                    "timestamp": datetime.now().isoformat()
                })
                
            except requests.exceptions.RequestException as e:
                error_msg = f"❌ API Error: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "backend": "error",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                error_msg = f"❌ Unexpected error: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "backend": "error",
                    "timestamp": datetime.now().isoformat()
                })

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🟢 LF Assist")
with col2:
    st.caption("🔵 Doc Assist")
with col3:
    st.caption("🟠 DB Assist")
