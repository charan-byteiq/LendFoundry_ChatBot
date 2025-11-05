import streamlit as st
import requests
import json

# --- App Configuration ---
st.set_page_config(page_title="Lendfoundry Chatbot", page_icon="🤖")

# --- Title and Description ---
st.title("Lendfoundry Chatbot")
st.write("Ask me questions about your data!")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Chat History Display ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- User Input and Chat Logic ---
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get bot response from the API
    with st.spinner("Thinking..."):
        try:
            response = requests.post("http://127.0.0.1:8000/api/chat", json={"prompt": prompt})
            response.raise_for_status()  # Raise an exception for bad status codes
            response_data = response.json()
            bot_response = response_data.get("response", "No response from the bot.")
        except requests.exceptions.RequestException as e:
            bot_response = f"Error connecting to the chatbot API: {e}"
        except json.JSONDecodeError:
            bot_response = "Error decoding the response from the chatbot API."

    # Display bot response in chat message container
    with st.chat_message("assistant"):
        st.markdown(bot_response)

    # Add bot response to chat history
    st.session_state.messages.append({"role": "assistant", "content": bot_response})
